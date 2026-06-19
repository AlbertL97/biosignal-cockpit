"""Musculoskeletal load & injury-risk proxy (task §9.6).

Within-person proxy combining training load (acute vs chronic), gait quality
(walking asymmetry, double-support, step length), protein intake, and recovery.
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

DOMAIN = "musculoskeletal"


def compute(ctx: DataContext) -> DomainStatus:
    """Compute the musculoskeletal load & injury-risk proxy."""
    b = DomainBuilder(DOMAIN, ctx)

    load = ctx.workout_load_series(56)
    asymmetry = ctx.mean_value("WalkingAsymmetryPercentage", days=30)
    double_support = ctx.mean_value("WalkingDoubleSupportPercentage", days=30)
    protein = ctx.nutrition_mean("DietaryProtein", days=30)
    sleep = ctx.sleep_hours_recent(14)

    if not load and asymmetry is None and protein is None:
        return insufficient(
            DOMAIN, ctx,
            missing=["workout load", "gait metrics", "protein intake"],
            note="No workout, gait, or protein-intake data were available.",
        )

    acwr = _acute_chronic_ratio(load)
    if acwr is not None:
        b.derived.append(f"Acute:chronic workload ratio ~{acwr:.2f} (load-balance proxy).")
        # Sweet spot ~0.8–1.3; extremes (very high or detraining) score lower.
        if acwr <= 1.3:
            score = scoring.clamp(60.0 + (1.0 - abs(acwr - 1.0)) * 40.0)
        else:
            score = scoring.clamp(60.0 - (acwr - 1.3) * 60.0)
        b.add_contribution("apple_health", "acute_chronic_ratio", round(acwr, 2), score, 0.3,
                           EvidenceGrade.moderate)
        if acwr > 1.5:
            b.inferences.append("Acute training load is high vs the chronic baseline, a recognised injury-risk context.")
            b.recommendations.append("Consider moderating training spikes or adding a recovery/deload block.")
    else:
        b.note_missing("training-load history")

    if asymmetry is not None:
        b.observations.append(f"Mean walking asymmetry ~{asymmetry:.1f}% (gait-quality proxy).")
        s = scoring.clamp(100.0 - asymmetry * 8.0)
        b.add_contribution("apple_health", "WalkingAsymmetryPercentage", round(asymmetry, 1), s, 0.2,
                           EvidenceGrade.low)
    else:
        b.note_missing("walking asymmetry")

    if double_support is not None:
        b.observations.append(f"Mean double-support time ~{double_support:.1f}% (stability proxy).")

    if protein is not None:
        b.observations.append(f"Mean protein intake ~{protein:.0f} g/day (tissue-repair support).")
        s = scoring.clamp((protein / 130.0) * 100.0)
        b.add_contribution("nutrition", "DietaryProtein", round(protein, 1), s, 0.25,
                           EvidenceGrade.high)
        if protein < 80:
            b.recommendations.append("Improve protein distribution/intake to support recovery if training volume is high.")
    else:
        b.note_missing("protein intake")

    if sleep:
        mean_sleep = sum(sleep) / len(sleep)
        s = scoring.clamp((mean_sleep / 8.0) * 100.0)
        b.add_contribution("apple_health", "sleep_hours", round(mean_sleep, 1), s, 0.15,
                           EvidenceGrade.moderate)

    b.hypotheses.append(
        "A sustained high acute:chronic load with limited recovery may be consistent with "
        "elevated injury risk; this is a probabilistic proxy, not a diagnosis."
    )
    map_nebula(b, ["muscle", "strength", "tendon", "injury", "bone", "collagen", "ACTN3", "power"])

    b.add_evidence(EvidenceRef(
        claim="Rapid increases in training load relative to chronic load are associated with higher injury risk.",
        grade=EvidenceGrade.moderate, source="guideline",
        title="Acute:chronic workload ratio and injury risk (sports-science reviews)",
        pmid=None, year=None, url=None,
    ))
    b.recommendations.append(consult_clause())

    trend = scoring.derive_trend(
        [(float(i), v) for i, (_, v) in enumerate(load)], higher_is_better=True
    ) if load else Trend.unknown

    summary = (
        "This is a non-diagnostic proxy for musculoskeletal load and recovery adequacy "
        "based on training load, gait, protein, and sleep. It cannot detect injury; "
        "persistent pain warrants professional assessment."
    )
    return b.finish(summary, trend=trend, evidence_strength=0.55, signal_quality=0.6)


def _acute_chronic_ratio(load: list[tuple[str, float]]) -> float | None:
    """Acute (7d) vs chronic (28d) mean daily workload ratio."""
    if len(load) < 7:
        return None
    vals = [v for _, v in load]
    acute = np.mean(vals[-7:])
    chronic = np.mean(vals[-28:]) if len(vals) >= 14 else np.mean(vals)
    if chronic <= 0:
        return None
    return float(acute / chronic)
