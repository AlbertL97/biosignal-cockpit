"""Stress & autonomic-load status interpretation.

Within-person proxy combining HRV (vs baseline), resting/walking heart rate,
sleep, and mindful-minutes context as an autonomic-load signal.
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

DOMAIN = "stress_autonomic"


def compute(ctx: DataContext) -> DomainStatus:
    """Compute the stress & autonomic-load status."""
    b = DomainBuilder(DOMAIN, ctx)

    hrv = ctx.mean_value("HeartRateVariabilitySDNN", days=14)
    rhr = ctx.mean_value("RestingHeartRate", days=14)
    walking_hr = ctx.mean_value("WalkingHeartRateAverage", days=14)
    sleep = ctx.sleep_hours_recent(14)
    mindful = ctx.count("MindfulSession")

    if hrv is None and rhr is None and not sleep:
        return insufficient(
            DOMAIN, ctx,
            missing=["HRV", "resting heart rate", "sleep"],
            note="No HRV, resting-heart-rate, or sleep data were available.",
        )

    if hrv:
        bl = ctx.baseline("HeartRateVariabilitySDNN")
        s = scoring.normalize_signal(hrv, bl.mean, bl.sd, higher_is_better=True)
        b.observations.append(f"Mean HRV ~{hrv:.0f} ms vs personal baseline (primary autonomic signal).")
        b.add_contribution("apple_health", "HeartRateVariabilitySDNN", round(hrv, 1), s, 0.4,
                           EvidenceGrade.moderate)
        if s is not None and s < 40:
            b.inferences.append("HRV is suppressed vs baseline, which may reflect elevated autonomic/stress load.")
            b.recommendations.append("Consider stress-management and recovery practices if low HRV persists.")
    else:
        b.note_missing("HRV")

    if rhr:
        bl = ctx.baseline("RestingHeartRate")
        s = scoring.normalize_signal(rhr, bl.mean, bl.sd, higher_is_better=False)
        b.observations.append(f"Mean resting heart rate ~{rhr:.0f} bpm vs baseline.")
        b.add_contribution("apple_health", "RestingHeartRate", round(rhr, 1), s, 0.25,
                           EvidenceGrade.moderate)
    else:
        b.note_missing("resting heart rate")

    if walking_hr:
        b.observations.append(f"Mean walking heart rate ~{walking_hr:.0f} bpm (effort context).")

    if sleep:
        mean_sleep = sum(sleep) / len(sleep)
        s = scoring.clamp((mean_sleep / 8.0) * 100.0)
        b.derived.append(f"Mean sleep ~{mean_sleep:.1f} h (recovery buffer against stress load).")
        b.add_contribution("apple_health", "sleep_hours", round(mean_sleep, 1), s, 0.2,
                           EvidenceGrade.moderate)

    if mindful:
        b.derived.append(f"{mindful} logged mindful sessions (active stress-regulation behaviour).")
        b.add_contribution("apple_health", "mindful_sessions", mindful,
                           scoring.clamp(50.0 + mindful * 2.0), 0.1, EvidenceGrade.low)
    else:
        b.note_missing("mindful-minute logging")

    b.hypotheses.append(
        "A sustained drop in HRV with a rise in resting heart rate may be consistent with "
        "elevated autonomic load from training, sleep loss, stress, or early illness."
    )
    map_nebula(b, ["stress", "anxiety", "cortisol", "neuroticism", "resilience"])

    b.add_evidence(EvidenceRef(
        claim="Reduced HRV relative to personal baseline is associated with elevated autonomic/stress load.",
        grade=EvidenceGrade.moderate, source="guideline",
        title="HRV as an autonomic-load marker (reviews)", pmid=None, year=None, url=None,
    ))
    b.recommendations.append(consult_clause())

    trend = scoring.derive_trend(
        [(float(i), v) for i, (_, v) in enumerate(ctx.values("HeartRateVariabilitySDNN", days=45))],
        higher_is_better=True,
    )

    summary = (
        "This is a non-diagnostic autonomic-load proxy from HRV and heart-rate signals "
        "interpreted against your own baseline. It is not a measure of psychological stress per se."
    )
    return b.finish(summary, trend=trend, evidence_strength=0.55, signal_quality=0.6)
