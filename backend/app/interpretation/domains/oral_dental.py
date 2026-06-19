"""Oral / dental status interpretation (task §9.3).

Lifestyle-only proxy: sugar exposure, meal frequency, hydration. There are no
direct dental measurements, so uncertainty is high and stated explicitly.
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
from app.models.contracts import DomainStatus, EvidenceGrade, EvidenceRef

DOMAIN = "oral_dental"


def compute(ctx: DataContext) -> DomainStatus:
    """Compute the oral/dental lifestyle-risk proxy."""
    b = DomainBuilder(DOMAIN, ctx)

    sugar = ctx.nutrition_mean("DietarySugar", days=30)
    energy_intake = ctx.nutrition_mean("DietaryEnergyConsumed", days=30)
    water = ctx.nutrition_mean("DietaryWater", days=30)
    days_logged = ctx.nutrition_days_logged(30)

    if sugar is None and energy_intake is None and water is None:
        return insufficient(
            DOMAIN, ctx,
            missing=["dietary sugar", "meal-frequency proxy", "hydration",
                     "direct dental measurements"],
            note="No nutrition data were available, and no direct dental measurements exist.",
        )

    if sugar is not None:
        b.observations.append(f"Mean sugar intake ~{sugar:.0f} g/day over 30 days.")
        sugar_score = scoring.clamp(100.0 - (sugar / 90.0) * 100.0)
        b.add_contribution("nutrition", "DietarySugar", round(sugar, 1), sugar_score, 0.5,
                           EvidenceGrade.high)
        if sugar > 60:
            b.inferences.append("Sugar-exposure pattern is relatively high, a known dental-caries risk factor.")
            b.recommendations.append("Reduce frequency of sugary food/drink exposure to lower caries risk.")
    else:
        b.note_missing("dietary sugar")

    if water is not None:
        b.observations.append(f"Mean water intake ~{water:.0f} mL/day (saliva/hydration context).")
        s = scoring.clamp((water / 2500.0) * 100.0)
        b.add_contribution("nutrition", "DietaryWater", round(water, 1), s, 0.2,
                           EvidenceGrade.low)
    else:
        b.note_missing("hydration")

    if days_logged:
        b.derived.append(f"Nutrition logged on {days_logged}/30 days (meal-frequency proxy quality).")
        # Logging completeness only affects confidence, not the risk score directly.

    b.hypotheses.append(
        "Frequent sugar exposure together with low hydration may be consistent with a "
        "higher dental-risk lifestyle pattern; this cannot substitute for a dental exam."
    )
    map_nebula(b, ["dental", "tooth", "caries", "periodontal", "gum"])

    b.add_evidence(EvidenceRef(
        claim="Frequency and amount of free-sugar intake are associated with dental caries risk.",
        grade=EvidenceGrade.high, source="guideline",
        title="WHO guideline on free sugars and dental caries", pmid=None, year=None, url=None,
    ))
    b.note_missing("direct dental measurements (no oral exam data)")
    b.recommendations.append("Maintain regular dental check-ups; this tool cannot assess oral health directly.")
    b.recommendations.append(consult_clause())

    series = ctx.nutrition_series("DietarySugar", days=90)
    trend = scoring.derive_trend(
        [(float(i), v) for i, (_, v) in enumerate(series)], higher_is_better=False
    )

    summary = (
        "This is a non-diagnostic dental-risk lifestyle proxy based on sugar exposure and "
        "hydration. The available data do not allow any conclusion about actual oral health; "
        "a dental examination would be required."
    )
    return b.finish(summary, trend=trend, evidence_strength=0.6, signal_quality=0.45)
