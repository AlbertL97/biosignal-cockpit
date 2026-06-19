"""Shared scoring, confidence, and trend helpers for the interpretation engine.

All interpretation is **within-person**: signals are normalized against the
user's own baseline (mean / sd) rather than population thresholds. Helpers here
are deliberately small, pure, and numpy-backed so domain modules can compose
them without duplicating statistics.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from app.models.contracts import Confidence, EvidenceGrade, Trend

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp ``value`` into the inclusive ``[low, high]`` range."""
    return max(low, min(high, value))


def zscore(value: float, mean: float, sd: float) -> float | None:
    """Return the within-person z-score, or ``None`` if ``sd`` is unusable."""
    if sd is None or sd <= 0 or any(map(_is_nan, (value, mean, sd))):
        return None
    return (value - mean) / sd


def z_to_score(z: float, higher_is_better: bool = True, spread: float = 2.0) -> float:
    """Map a z-score to a 0..100 within-person score.

    ``z == 0`` (at baseline) maps to 50. ``+spread`` SD maps near 100 when
    ``higher_is_better`` else near 0. The mapping is a clamped linear ramp,
    which keeps the score interpretable and avoids false precision.
    """
    signed = z if higher_is_better else -z
    return clamp(50.0 + (signed / spread) * 50.0)


def normalize_signal(
    value: float | None,
    mean: float | None,
    sd: float | None,
    higher_is_better: bool = True,
    spread: float = 2.0,
) -> float | None:
    """Normalize a raw value to 0..100 vs personal baseline.

    Returns ``None`` when inputs are insufficient (missing value or baseline),
    so callers can treat the signal as unavailable rather than fabricate a
    midpoint score.
    """
    if value is None or mean is None:
        return None
    z = zscore(value, mean, sd) if sd else None
    if z is None:
        # No spread information: fall back to a neutral, low-confidence midpoint.
        return 50.0
    return z_to_score(z, higher_is_better=higher_is_better, spread=spread)


# ---------------------------------------------------------------------------
# Weighted combination
# ---------------------------------------------------------------------------


def combine_weighted(scores: Sequence[tuple[float, float]]) -> float | None:
    """Combine ``(score, weight)`` pairs into a single 0..100 value.

    ``None`` is returned when no usable (finite, positive-weight) pairs exist.
    Weights need not sum to 1; they are renormalized internally.
    """
    usable = [(s, w) for s, w in scores if s is not None and w > 0 and not _is_nan(s)]
    if not usable:
        return None
    total_w = sum(w for _, w in usable)
    if total_w <= 0:
        return None
    return clamp(sum(s * w for s, w in usable) / total_w)


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


def derive_confidence(
    completeness: float,
    signal_quality: float,
    evidence_strength: float,
) -> Confidence:
    """Derive a confidence enum from three 0..1 factors.

    - ``completeness``: share of expected inputs that were available.
    - ``signal_quality``: data density / baseline stability proxy.
    - ``evidence_strength``: strength of the underlying scientific evidence.

    The factors are multiplied (a weak link drags confidence down) and bucketed
    conservatively, in line with the "never imply false precision" guardrail.
    """
    factors = [max(0.0, min(1.0, f)) for f in (completeness, signal_quality, evidence_strength)]
    combined = math.prod(factors)
    if combined >= 0.6:
        return Confidence.high
    if combined >= 0.35:
        return Confidence.moderate
    if combined >= 0.15:
        return Confidence.low
    return Confidence.exploratory


def combine_evidence_grades(grades: Sequence[EvidenceGrade]) -> EvidenceGrade:
    """Return the strongest available evidence grade among ``grades``."""
    order = [
        EvidenceGrade.high,
        EvidenceGrade.moderate,
        EvidenceGrade.low,
        EvidenceGrade.exploratory,
        EvidenceGrade.unsupported,
    ]
    present = [g for g in grades if g in order]
    if not present:
        return EvidenceGrade.unsupported
    return min(present, key=order.index)


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------


def derive_trend(
    points: Sequence[tuple[float, float]],
    higher_is_better: bool = True,
    min_points: int = 4,
    z_threshold: float = 1.0,
) -> Trend:
    """Derive a trend from ``(t, value)`` points via a normalized slope.

    The ordinary-least-squares slope is standardized by the value spread to a
    pseudo-z; ``|z| < z_threshold`` is reported as ``stable``. Too few points
    yield ``unknown`` rather than an over-confident direction.
    """
    pts = [(t, v) for t, v in points if not _is_nan(t) and not _is_nan(v)]
    if len(pts) < min_points:
        return Trend.unknown
    t = np.array([p[0] for p in pts], dtype=float)
    v = np.array([p[1] for p in pts], dtype=float)
    if np.ptp(t) == 0 or np.std(v) == 0:
        return Trend.stable
    slope = float(np.polyfit(t, v, 1)[0])
    # Standardize: change over the observed time span relative to value spread.
    span_change = slope * float(np.ptp(t))
    pseudo_z = span_change / (float(np.std(v)) + 1e-9)
    if abs(pseudo_z) < z_threshold:
        return Trend.stable
    rising = pseudo_z > 0
    improving = rising if higher_is_better else not rising
    return Trend.improving if improving else Trend.declining


def score_label_for(score: float | None) -> str:
    """Map a 0..100 score to a coarse, non-diagnostic label."""
    if score is None:
        return "insufficient data"
    if score >= 66:
        return "supportive"
    if score >= 40:
        return "watch"
    return "needs attention"


def _is_nan(x: object) -> bool:
    """Safe NaN check for floats and float-like values."""
    try:
        return math.isnan(float(x))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
