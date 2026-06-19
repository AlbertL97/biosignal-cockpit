"""Cardiovascular & recovery status interpretation (task §9.4).

Within-person proxy combining resting heart rate, HRV, VO2 max estimates,
activity consistency, and sleep, with cardiovascular genomic context.
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

DOMAIN = "cardiovascular"


def compute(ctx: DataContext) -> DomainStatus:
    """Compute the cardiovascular fitness & recovery status."""
    b = DomainBuilder(DOMAIN, ctx)

    rhr = ctx.mean_value("RestingHeartRate", days=14)
    hrv = ctx.mean_value("HeartRateVariabilitySDNN", days=14)
    vo2 = ctx.latest_value("VO2Max") or ctx.latest_value("VO2max")
    workouts = ctx.workout_count(28)
    spo2 = ctx.mean_value("OxygenSaturation", days=30)

    if rhr is None and hrv is None and vo2 is None and not workouts:
        return insufficient(
            DOMAIN, ctx,
            missing=["resting heart rate", "HRV", "VO2 max", "workouts"],
            note="No cardiovascular biometrics or workout data were available.",
        )

    if rhr:
        bl = ctx.baseline("RestingHeartRate")
        s = scoring.normalize_signal(rhr, bl.mean, bl.sd, higher_is_better=False)
        b.observations.append(f"Mean resting heart rate ~{rhr:.0f} bpm vs personal baseline.")
        b.add_contribution("apple_health", "RestingHeartRate", round(rhr, 1), s, 0.25,
                           EvidenceGrade.high)
        if bl.mean and rhr > bl.mean + (bl.sd or 0) * 1.5:
            b.inferences.append("Resting heart rate is elevated vs baseline, which may reflect under-recovery or strain.")
    else:
        b.note_missing("resting heart rate")

    if hrv:
        bl = ctx.baseline("HeartRateVariabilitySDNN")
        s = scoring.normalize_signal(hrv, bl.mean, bl.sd, higher_is_better=True)
        b.observations.append(f"Mean HRV ~{hrv:.0f} ms vs personal baseline (autonomic load proxy).")
        b.add_contribution("apple_health", "HeartRateVariabilitySDNN", round(hrv, 1), s, 0.25,
                           EvidenceGrade.moderate)
    else:
        b.note_missing("HRV")

    if vo2:
        b.observations.append(f"Latest VO2 max estimate ~{vo2:.1f} mL/kg/min (cardiorespiratory fitness).")
        s = scoring.clamp((vo2 / 50.0) * 100.0)
        b.add_contribution("apple_health", "VO2Max", round(vo2, 1), s, 0.2, EvidenceGrade.high)
    else:
        b.note_missing("VO2 max estimate")

    if workouts:
        s = scoring.clamp((workouts / 12.0) * 100.0)
        b.derived.append(f"{workouts} workouts in 28 days (activity consistency).")
        b.add_contribution("apple_health", "workout_count_28d", workouts, s, 0.2, EvidenceGrade.high)

    if spo2 is not None:
        b.observations.append(f"Mean SpO2 ~{spo2:.1f}% (oxygenation context).")

    b.hypotheses.append(
        "A combination of rising resting heart rate and falling HRV may be consistent with "
        "autonomic strain or incomplete recovery; this is a cautious hypothesis."
    )
    map_nebula(b, ["heart rate", "HRV", "heart rate variability", "VO2", "blood pressure",
                   "cholesterol", "LDL", "HDL", "lipid", "coronary", "atrial"])

    b.add_evidence(EvidenceRef(
        claim="Higher cardiorespiratory fitness and HRV are associated with favourable cardiovascular outcomes.",
        grade=EvidenceGrade.high, source="guideline",
        title="Cardiorespiratory fitness and cardiovascular risk (meta-analyses)",
        pmid=None, year=None, url=None,
    ))
    b.recommendations.append(consult_clause(strong=True))

    trend = scoring.derive_trend(
        [(float(i), v) for i, (_, v) in enumerate(ctx.values("RestingHeartRate", days=60))],
        higher_is_better=False,
    )

    summary = (
        "This is a non-diagnostic proxy for cardiovascular fitness and recovery, "
        "interpreted against your own baseline. A clinical evaluation would be required "
        "to assess cardiovascular health directly."
    )
    return b.finish(summary, trend=trend, evidence_strength=0.7, signal_quality=0.6)
