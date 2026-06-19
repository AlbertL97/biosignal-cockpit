"""Sleep & recovery status interpretation.

Within-person proxy combining sleep duration, regularity, deep/REM fractions,
HRV, and resting heart rate as a recovery-readiness signal.
"""
from __future__ import annotations

import numpy as np

from app.interpretation import scoring
from app.interpretation.context import DataContext
from app.interpretation.domains import (
    DomainBuilder,
    consult_clause,
    insufficient,
    map_nebula,
)
from app.models.contracts import DomainStatus, EvidenceGrade, EvidenceRef, Trend

DOMAIN = "sleep_recovery"


def compute(ctx: DataContext) -> DomainStatus:
    """Compute the sleep & recovery-readiness status."""
    b = DomainBuilder(DOMAIN, ctx)

    sleep = ctx.sleep_hours_recent(21)
    deep = ctx.sleep_stage_fraction("asleepDeep", days=21)
    rem = ctx.sleep_stage_fraction("asleepREM", days=21)
    hrv = ctx.mean_value("HeartRateVariabilitySDNN", days=14)
    rhr = ctx.mean_value("RestingHeartRate", days=14)

    if not sleep and hrv is None and rhr is None:
        return insufficient(
            DOMAIN, ctx,
            missing=["sleep segments", "HRV", "resting heart rate"],
            note="No sleep, HRV, or resting-heart-rate data were available.",
        )

    if sleep:
        mean_sleep = sum(sleep) / len(sleep)
        b.observations.append(f"Mean sleep ~{mean_sleep:.1f} h over {len(sleep)} nights.")
        dur_score = scoring.clamp((mean_sleep / 8.0) * 100.0)
        b.add_contribution("apple_health", "sleep_hours", round(mean_sleep, 1), dur_score, 0.3,
                           EvidenceGrade.high)
        if len(sleep) > 1:
            var = float(np.std(sleep))
            b.derived.append(f"Sleep-duration variability ~{var:.1f} h (regularity proxy).")
            reg_score = scoring.clamp(100.0 - var * 40.0)
            b.add_contribution("apple_health", "sleep_regularity", round(var, 2), reg_score, 0.2,
                               EvidenceGrade.moderate)
        debt = max(0.0, 7.5 - mean_sleep) * len(sleep)
        if debt > 7:
            b.inferences.append("Accumulated sleep-debt proxy is elevated, which may reduce recovery readiness.")
            b.recommendations.append("Prioritise recovery sleep; aim for consistent sufficient duration.")
    else:
        b.note_missing("sleep segments")

    if deep is not None:
        b.derived.append(f"Deep-sleep fraction ~{deep * 100:.0f}% of asleep time.")
        b.add_contribution("apple_health", "deep_sleep_fraction", round(deep, 3),
                           scoring.clamp((deep / 0.18) * 100.0), 0.15, EvidenceGrade.low)
    else:
        b.note_missing("deep-sleep staging")

    if rem is not None:
        b.derived.append(f"REM fraction ~{rem * 100:.0f}% of asleep time.")
        b.add_contribution("apple_health", "rem_fraction", round(rem, 3),
                           scoring.clamp((rem / 0.22) * 100.0), 0.1, EvidenceGrade.low)

    if hrv:
        bl = ctx.baseline("HeartRateVariabilitySDNN")
        s = scoring.normalize_signal(hrv, bl.mean, bl.sd, higher_is_better=True)
        b.observations.append(f"Mean HRV ~{hrv:.0f} ms vs baseline (recovery proxy).")
        b.add_contribution("apple_health", "HeartRateVariabilitySDNN", round(hrv, 1), s, 0.15,
                           EvidenceGrade.moderate)
    else:
        b.note_missing("HRV")

    if rhr:
        bl = ctx.baseline("RestingHeartRate")
        s = scoring.normalize_signal(rhr, bl.mean, bl.sd, higher_is_better=False)
        b.add_contribution("apple_health", "RestingHeartRate", round(rhr, 1), s, 0.1,
                           EvidenceGrade.moderate)

    b.hypotheses.append(
        "Low sleep duration with reduced HRV and elevated resting heart rate may be consistent "
        "with under-recovery; interpret cautiously alongside training and stress context."
    )
    map_nebula(b, ["sleep", "insomnia", "circadian", "chronotype", "morning", "CLOCK"])

    b.add_evidence(EvidenceRef(
        claim="Sufficient and regular sleep supports physiological recovery and next-day readiness.",
        grade=EvidenceGrade.high, source="guideline",
        title="Sleep and recovery (consensus reviews)", pmid=None, year=None, url=None,
    ))
    b.recommendations.append(consult_clause())

    trend = scoring.derive_trend(
        [(float(i), v) for i, v in enumerate(sleep)], higher_is_better=True
    ) if sleep else Trend.unknown

    summary = (
        "This is a non-diagnostic recovery-readiness proxy from sleep architecture and "
        "autonomic signals, interpreted within-person. It is not a clinical sleep study."
    )
    return b.finish(summary, trend=trend, evidence_strength=0.65, signal_quality=0.6)
