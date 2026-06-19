"""Metabolic status interpretation (task §9.5).

Within-person proxy combining energy balance (intake vs expenditure),
macronutrient distribution, fiber, activity, and body-mass trend.
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

DOMAIN = "metabolic"


def compute(ctx: DataContext) -> DomainStatus:
    """Compute the metabolic-support lifestyle status."""
    b = DomainBuilder(DOMAIN, ctx)

    intake = ctx.nutrition_mean("DietaryEnergyConsumed", days=30)
    active = ctx.mean_value("ActiveEnergyBurned", days=30)
    basal = ctx.mean_value("BasalEnergyBurned", days=30)
    protein = ctx.nutrition_mean("DietaryProtein", days=30)
    carbs = ctx.nutrition_mean("DietaryCarbohydrates", days=30)
    fiber = ctx.nutrition_mean("DietaryFiber", days=30)
    steps = ctx.mean_value("StepCount", days=30)

    if intake is None and active is None and steps is None:
        return insufficient(
            DOMAIN, ctx,
            missing=["caloric intake", "energy expenditure", "activity"],
            note="No nutrition or energy-expenditure data were available.",
        )

    expenditure = _expenditure(active, basal)
    if intake is not None and expenditure is not None:
        balance = intake - expenditure
        b.derived.append(f"Estimated daily energy balance ~{balance:+.0f} kcal (intake - expenditure).")
        # Closeness to balance scores highest; large surplus/deficit lowers it.
        score = scoring.clamp(100.0 - abs(balance) / 8.0)
        b.add_contribution("nutrition", "energy_balance", round(balance, 0), score, 0.3,
                           EvidenceGrade.moderate)
        if balance > 500:
            b.hypotheses.append("A sustained caloric surplus proxy may be consistent with gradual weight gain.")
        elif balance < -700:
            b.hypotheses.append("A sustained caloric deficit proxy may be consistent with under-fuelling risk.")
    else:
        if intake is None:
            b.note_missing("caloric intake")
        if expenditure is None:
            b.note_missing("energy expenditure")

    if protein is not None and intake:
        prot_kcal = protein * 4.0
        prot_pct = (prot_kcal / intake) * 100.0 if intake else None
        if prot_pct is not None:
            b.derived.append(f"Protein ~{prot_pct:.0f}% of energy intake.")
            s = scoring.clamp((prot_pct / 25.0) * 100.0)
            b.add_contribution("nutrition", "protein_pct", round(prot_pct, 1), s, 0.2,
                               EvidenceGrade.moderate)

    if fiber is not None:
        s = scoring.clamp((fiber / 30.0) * 100.0)
        b.observations.append(f"Mean fiber ~{fiber:.0f} g/day (metabolic support).")
        b.add_contribution("nutrition", "DietaryFiber", round(fiber, 1), s, 0.15,
                           EvidenceGrade.high)
    else:
        b.note_missing("fiber intake")

    if steps is not None:
        s = scoring.clamp((steps / 10000.0) * 100.0)
        b.observations.append(f"Mean ~{steps:.0f} steps/day (activity contribution to metabolism).")
        b.add_contribution("apple_health", "StepCount", round(steps, 0), s, 0.2,
                           EvidenceGrade.high)

    if carbs is not None:
        b.observations.append(f"Mean carbohydrate intake ~{carbs:.0f} g/day.")

    map_nebula(b, ["metabolism", "obesity", "BMI", "type 2 diabetes", "glucose", "insulin",
                   "FTO", "lipid", "triglyceride"])

    b.add_evidence(EvidenceRef(
        claim="Energy balance, dietary fiber, protein adequacy, and daily activity influence metabolic health.",
        grade=EvidenceGrade.high, source="guideline",
        title="Diet, activity, and metabolic health (consensus guidelines)",
        pmid=None, year=None, url=None,
    ))
    b.recommendations.append(consult_clause())

    bm_series = ctx.values("BodyMass", days=120)
    trend = scoring.derive_trend(
        [(float(i), v) for i, (_, v) in enumerate(bm_series)], higher_is_better=False
    ) if bm_series else Trend.unknown

    summary = (
        "This is a non-diagnostic metabolic-support proxy from energy balance, macronutrient, "
        "and activity signals. It does not measure metabolic health directly; laboratory testing "
        "would be required for that."
    )
    return b.finish(summary, trend=trend, evidence_strength=0.65, signal_quality=0.6)


def _expenditure(active: float | None, basal: float | None) -> float | None:
    """Estimate total daily expenditure from active + basal energy."""
    if active is None and basal is None:
        return None
    if basal is None:
        # Fall back to a conservative basal estimate so balance is still usable.
        return (active or 0.0) + 1600.0
    return (active or 0.0) + basal
