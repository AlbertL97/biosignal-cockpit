"""Gut status interpretation (task §9.1).

Within-person, evidence-aware proxy combining fiber sufficiency, dietary
regularity, sugar/saturated-fat load, hydration, and stress/sleep context.
No direct gut measurement exists, so all output is a cautious lifestyle proxy.
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

DOMAIN = "gut"


def compute(ctx: DataContext) -> DomainStatus:
    """Compute the gut-supportive lifestyle status."""
    b = DomainBuilder(DOMAIN, ctx)

    fiber = ctx.nutrition_mean("DietaryFiber", days=30)
    sugar = ctx.nutrition_mean("DietarySugar", days=30)
    days_logged = ctx.nutrition_days_logged(30)
    hrv = ctx.mean_value("HeartRateVariabilitySDNN", days=14)
    sleep = ctx.sleep_hours_recent(14)

    if fiber is None and sugar is None and hrv is None and not sleep:
        return insufficient(
            DOMAIN, ctx,
            missing=["nutrition (fiber/sugar)", "HRV", "sleep"],
            note="No nutrition, HRV, or sleep data were available.",
        )

    # Fiber sufficiency: ~30 g/day is a common adequacy reference; scored as a
    # within-person-friendly ramp anchored on that guideline.
    if fiber is not None:
        b.observations.append(f"Mean dietary fiber ~{fiber:.0f} g/day over 30 days.")
        fiber_score = scoring.clamp((fiber / 30.0) * 75.0)
        b.add_contribution("nutrition", "DietaryFiber", round(fiber, 1), fiber_score, 0.35,
                           EvidenceGrade.high)
        if fiber < 20:
            b.inferences.append("Fiber intake appears chronically below common adequacy references.")
            b.recommendations.append("Gradually increase dietary fiber (e.g. legumes, whole grains, vegetables).")
    else:
        b.note_missing("dietary fiber intake")

    if sugar is not None:
        b.observations.append(f"Mean added/total sugar ~{sugar:.0f} g/day over 30 days.")
        sugar_score = scoring.clamp(100.0 - (sugar / 90.0) * 100.0)
        b.add_contribution("nutrition", "DietarySugar", round(sugar, 1), sugar_score, 0.2,
                           EvidenceGrade.moderate)
    else:
        b.note_missing("dietary sugar intake")

    if days_logged:
        regularity = scoring.clamp((days_logged / 30.0) * 100.0)
        b.derived.append(f"Nutrition logged on {days_logged}/30 days (diet-regularity proxy).")
        b.add_contribution("nutrition", "logging_regularity", days_logged, regularity, 0.15,
                           EvidenceGrade.low)

    if hrv:
        bl = ctx.baseline("HeartRateVariabilitySDNN")
        s = scoring.normalize_signal(hrv, bl.mean, bl.sd, higher_is_better=True)
        b.derived.append(f"Recent HRV ~{hrv:.0f} ms (autonomic/stress context for the gut-brain axis).")
        b.add_contribution("apple_health", "HeartRateVariabilitySDNN", round(hrv, 1), s, 0.15,
                           EvidenceGrade.moderate)
    else:
        b.note_missing("HRV (stress context)")

    if sleep:
        mean_sleep = sum(sleep) / len(sleep)
        s = scoring.clamp((mean_sleep / 8.0) * 100.0)
        b.derived.append(f"Mean sleep ~{mean_sleep:.1f} h/night (recovery context).")
        b.add_contribution("apple_health", "sleep_hours", round(mean_sleep, 1), s, 0.15,
                           EvidenceGrade.moderate)
    else:
        b.note_missing("sleep duration")

    map_nebula(b, ["IBS", "irritable bowel", "diverticular", "reflux", "celiac", "lactose", "Crohn"])

    b.add_evidence(EvidenceRef(
        claim="Higher dietary fiber intake is associated with improved gastrointestinal and metabolic outcomes.",
        grade=EvidenceGrade.high, source="guideline",
        title="Dietary fiber and health outcomes (umbrella reviews)", pmid=None, year=None, url=None,
    ))

    b.recommendations.append(consult_clause())
    trend = _fiber_trend(ctx)

    preview = b.current_score()
    tone = "supportive" if (preview is not None and preview >= 60) else "mixed"
    summary = (
        f"The current pattern may be consistent with a {tone} "
        "gut-supportive lifestyle. This is a non-diagnostic proxy based on diet, "
        "sleep, and stress signals; direct gut assessment would require clinical testing."
    )
    return b.finish(summary, trend=trend, evidence_strength=0.6, signal_quality=0.6)


def _fiber_trend(ctx: DataContext) -> Trend:
    """Trend of fiber intake as the dominant gut-supportive driver."""
    series = ctx.nutrition_series("DietaryFiber", days=90)
    pts = [(float(i), v) for i, (_, v) in enumerate(series)]
    return scoring.derive_trend(pts, higher_is_better=True)
