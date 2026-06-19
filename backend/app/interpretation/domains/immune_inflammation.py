"""Immune & inflammation-related context (task §9.7).

Lifestyle-only proxy combining sleep, HRV/stress, micronutrient patterns,
activity, and recent deviations. Inflammation CANNOT be inferred without lab
markers; this limit is stated explicitly per task §9.7 / §14.
"""
from __future__ import annotations

from app.interpretation import scoring
from app.interpretation.context import DataContext
from app.interpretation.domains import (
    DomainBuilder,
    consult_clause,
    insufficient,
    map_nebula,
)
from app.models.contracts import DomainStatus, EvidenceGrade, EvidenceRef, Trend

DOMAIN = "immune_inflammation"

# Micronutrients with immune relevance and rough daily adequacy references.
_MICRO_REFS: dict[str, float] = {
    "DietaryVitaminC": 90.0,   # mg
    "DietaryVitaminD": 15.0,   # mcg
    "DietaryZinc": 11.0,       # mg
    "DietaryIron": 8.0,        # mg
}


def compute(ctx: DataContext) -> DomainStatus:
    """Compute the immune-support lifestyle context."""
    b = DomainBuilder(DOMAIN, ctx)

    sleep = ctx.sleep_hours_recent(21)
    hrv = ctx.mean_value("HeartRateVariabilitySDNN", days=14)
    steps = ctx.mean_value("StepCount", days=30)

    micro_scored = False
    for metric, ref in _MICRO_REFS.items():
        val = ctx.nutrition_mean(metric, days=30)
        if val is not None:
            micro_scored = True
            b.observations.append(f"Mean {metric.replace('Dietary', '')} ~{val:.1f} vs ~{ref:g} reference.")
            s = scoring.clamp((val / ref) * 80.0)
            b.add_contribution("nutrition", metric, round(val, 1), s, 0.1, EvidenceGrade.moderate)
        else:
            b.note_missing(f"{metric.replace('Dietary', '')} intake")

    if not sleep and hrv is None and not micro_scored:
        return insufficient(
            DOMAIN, ctx,
            missing=["sleep", "HRV", "micronutrient intake", "laboratory markers (CRP, etc.)"],
            note="No sleep, HRV, or micronutrient data were available, and no lab markers exist.",
        )

    if sleep:
        mean_sleep = sum(sleep) / len(sleep)
        s = scoring.clamp((mean_sleep / 8.0) * 100.0)
        b.observations.append(f"Mean sleep ~{mean_sleep:.1f} h (immune-recovery support).")
        b.add_contribution("apple_health", "sleep_hours", round(mean_sleep, 1), s, 0.3,
                           EvidenceGrade.high)
        if mean_sleep < 6.0:
            b.inferences.append("Short sleep may reduce immune-supportive recovery (lifestyle context only).")
    else:
        b.note_missing("sleep")

    if hrv:
        bl = ctx.baseline("HeartRateVariabilitySDNN")
        s = scoring.normalize_signal(hrv, bl.mean, bl.sd, higher_is_better=True)
        b.derived.append(f"Mean HRV ~{hrv:.0f} ms vs baseline (stress/recovery context).")
        b.add_contribution("apple_health", "HeartRateVariabilitySDNN", round(hrv, 1), s, 0.2,
                           EvidenceGrade.moderate)
    else:
        b.note_missing("HRV")

    if steps is not None:
        s = scoring.clamp((steps / 8000.0) * 100.0)
        b.add_contribution("apple_health", "StepCount", round(steps, 0), s, 0.15,
                           EvidenceGrade.moderate)

    b.hypotheses.append(
        "Reduced sleep and HRV with low micronutrient intake may be consistent with reduced "
        "immune-supportive lifestyle conditions; this is not an inflammation measurement."
    )
    map_nebula(b, ["immune", "inflammation", "CRP", "allergy", "autoimmune", "interleukin", "cytokine"])

    b.add_evidence(EvidenceRef(
        claim="Adequate sleep, activity, and micronutrient sufficiency support immune function.",
        grade=EvidenceGrade.moderate, source="guideline",
        title="Lifestyle factors and immune function (reviews)", pmid=None, year=None, url=None,
    ))
    # Explicit, mandatory limitation per task §9.7.
    b.note_missing("laboratory inflammation markers (e.g. CRP, leukocytes, ferritin)")
    b.inferences.append(
        "Inflammation cannot be inferred directly without laboratory markers; only lifestyle "
        "support context is estimated here."
    )
    b.recommendations.append(
        "Consider laboratory testing (e.g. CRP) for any direct inflammation assessment."
    )
    b.recommendations.append(consult_clause(strong=True))

    trend = scoring.derive_trend(
        [(float(i), v) for i, v in enumerate(sleep)], higher_is_better=True
    ) if sleep else Trend.unknown

    summary = (
        "This is a non-diagnostic immune-support lifestyle context from sleep, stress, "
        "activity, and micronutrient signals. The available data do not allow any conclusion "
        "about inflammation, which requires laboratory markers."
    )
    return b.finish(summary, trend=trend, evidence_strength=0.5, signal_quality=0.5)
