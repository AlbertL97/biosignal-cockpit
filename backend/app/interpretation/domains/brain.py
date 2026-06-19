"""Brain & cognitive status interpretation (task §9.2).

Within-person proxy for cognitive readiness combining sleep duration/regularity,
HRV, resting heart rate, exercise frequency, and circadian/daylight context.
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

DOMAIN = "brain"


def compute(ctx: DataContext) -> DomainStatus:
    """Compute the brain/cognitive readiness status."""
    b = DomainBuilder(DOMAIN, ctx)

    sleep = ctx.sleep_hours_recent(14)
    hrv = ctx.mean_value("HeartRateVariabilitySDNN", days=14)
    rhr = ctx.mean_value("RestingHeartRate", days=14)
    workouts = ctx.workout_count(14)
    daylight = ctx.mean_value("TimeInDaylight", days=14)

    if not sleep and hrv is None and rhr is None:
        return insufficient(
            DOMAIN, ctx,
            missing=["sleep", "HRV", "resting heart rate"],
            note="No sleep, HRV, or resting-heart-rate data were available.",
        )

    if sleep:
        mean_sleep = sum(sleep) / len(sleep)
        reg = float(np.std(sleep)) if len(sleep) > 1 else None
        b.observations.append(f"Mean sleep ~{mean_sleep:.1f} h over {len(sleep)} nights.")
        sleep_score = scoring.clamp((mean_sleep / 8.0) * 100.0)
        b.add_contribution("apple_health", "sleep_hours", round(mean_sleep, 1), sleep_score, 0.35,
                           EvidenceGrade.high)
        if reg is not None:
            b.derived.append(f"Sleep-duration variability ~{reg:.1f} h (regularity proxy).")
            reg_score = scoring.clamp(100.0 - reg * 40.0)
            b.add_contribution("apple_health", "sleep_regularity", round(reg, 2), reg_score, 0.15,
                               EvidenceGrade.moderate)
        if mean_sleep < 6.5:
            b.inferences.append("Sleep-supported cognitive readiness may be reduced relative to typical adult needs.")
            b.recommendations.append("Prioritise consistent sleep timing and duration to support cognitive recovery.")
    else:
        b.note_missing("sleep")

    if hrv:
        bl = ctx.baseline("HeartRateVariabilitySDNN")
        s = scoring.normalize_signal(hrv, bl.mean, bl.sd, higher_is_better=True)
        b.derived.append(f"Recent HRV ~{hrv:.0f} ms vs personal baseline (recovery/stress proxy).")
        b.add_contribution("apple_health", "HeartRateVariabilitySDNN", round(hrv, 1), s, 0.2,
                           EvidenceGrade.moderate)
    else:
        b.note_missing("HRV")

    if rhr:
        bl = ctx.baseline("RestingHeartRate")
        s = scoring.normalize_signal(rhr, bl.mean, bl.sd, higher_is_better=False)
        b.add_contribution("apple_health", "RestingHeartRate", round(rhr, 1), s, 0.1,
                           EvidenceGrade.moderate)

    if workouts:
        s = scoring.clamp((workouts / 6.0) * 100.0)
        b.derived.append(f"{workouts} workouts in 14 days (exercise supports cognition).")
        b.add_contribution("apple_health", "workout_count_14d", workouts, s, 0.1,
                           EvidenceGrade.high)

    if daylight is not None:
        b.observations.append(f"Mean daylight exposure ~{daylight:.0f} min/day (circadian context).")
        s = scoring.clamp((daylight / 120.0) * 100.0)
        b.add_contribution("apple_health", "TimeInDaylight", round(daylight, 1), s, 0.1,
                           EvidenceGrade.low)
    else:
        b.note_missing("daylight exposure (circadian proxy)")

    b.hypotheses.append(
        "If sleep and HRV decline together, this may be consistent with elevated cognitive "
        "load or under-recovery; this is a hypothesis, not a conclusion."
    )
    map_nebula(b, ["cognitive", "memory", "intelligence", "Alzheimer", "neuroticism", "depression", "BDNF"])

    b.add_evidence(EvidenceRef(
        claim="Adequate sleep duration and regularity support cognitive performance and memory consolidation.",
        grade=EvidenceGrade.high, source="guideline",
        title="Sleep and cognitive function (consensus reviews)", pmid=None, year=None, url=None,
    ))
    b.recommendations.append(consult_clause())

    trend = scoring.derive_trend(
        [(float(i), v) for i, v in enumerate(sleep)], higher_is_better=True
    ) if sleep else Trend.unknown

    summary = (
        "This is a non-diagnostic proxy for cognitive readiness based on sleep, "
        "autonomic, and activity signals. The available data do not allow a direct "
        "conclusion about brain health; interpret cautiously."
    )
    return b.finish(summary, trend=trend, evidence_strength=0.6, signal_quality=0.6)
