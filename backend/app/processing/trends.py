"""Trend features: rolling means, z-scores vs baseline, and linear slope.

All features are written to ``derived_metrics`` with a ``method`` tag
(``rolling_mean`` / ``zscore`` / ``slope`` / ``deviation``) and a ``window``
label. Interpretation stays within-person (ARCHITECTURE §8).

Public entry point: :func:`compute_trends`.
"""
from __future__ import annotations

import sqlite3
import statistics
from datetime import datetime, timedelta, timezone

from app.processing.baselines import get_baseline
from app.storage import db

ROLLING_WINDOWS = (7, 30, 90)


def _daily_values(conn: sqlite3.Connection, metric: str) -> list[tuple[str, float]]:
    """Return ``(day, mean_value)`` pairs for a metric, ordered by day.

    Multiple same-day measurements are averaged so that high-frequency metrics
    (e.g. heart rate) do not swamp the trend.
    """
    rows = conn.execute(
        "SELECT substr(start_ts,1,10) AS day, AVG(value) AS v "
        "FROM measurements WHERE metric = ? AND value IS NOT NULL "
        "GROUP BY day ORDER BY day",
        (metric,),
    ).fetchall()
    return [(r["day"], float(r["v"])) for r in rows if r["v"] is not None]


def _slope(points: list[tuple[float, float]]) -> float | None:
    """Ordinary least-squares slope of ``y`` vs ``x``; ``None`` if degenerate."""
    n = len(points)
    if n < 2:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return None
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return num / denom


def compute_trends_for(
    conn: sqlite3.Connection,
    metric: str,
    *,
    as_of: datetime | None = None,
) -> list[dict[str, object]]:
    """Compute derived-metric rows for a single metric.

    Produces, for the most recent timestamp: rolling means over
    :data:`ROLLING_WINDOWS`, a z-score and deviation vs the stored baseline, and
    a 30-day slope. Returns the rows (not yet inserted).
    """
    daily = _daily_values(conn, metric)
    if not daily:
        return []
    now = as_of or datetime.now(timezone.utc)
    as_of_iso = now.isoformat()
    rows: list[dict[str, object]] = []

    # Rolling means anchored at the latest available day.
    by_date = {datetime.fromisoformat(d): v for d, v in daily}
    latest_day = max(by_date)
    for w in ROLLING_WINDOWS:
        cutoff = latest_day - timedelta(days=w)
        window_vals = [v for d, v in by_date.items() if d > cutoff]
        if window_vals:
            rows.append(
                {
                    "metric": metric,
                    "value": round(statistics.fmean(window_vals), 6),
                    "window": f"{w}d",
                    "as_of_ts": as_of_iso,
                    "method": "rolling_mean",
                }
            )

    # z-score and deviation vs baseline using the latest value.
    baseline = get_baseline(conn, metric)
    latest_value = by_date[latest_day]
    if baseline is not None and baseline["sd"]:
        z = (latest_value - baseline["mean"]) / baseline["sd"]
        rows.append(
            {
                "metric": metric,
                "value": round(z, 6),
                "window": "latest",
                "as_of_ts": as_of_iso,
                "method": "zscore",
            }
        )
        rows.append(
            {
                "metric": metric,
                "value": round(latest_value - baseline["mean"], 6),
                "window": "latest",
                "as_of_ts": as_of_iso,
                "method": "deviation",
            }
        )

    # 30-day slope (value change per day) over ordinal days.
    cutoff = latest_day - timedelta(days=30)
    recent = sorted((d, v) for d, v in by_date.items() if d > cutoff)
    if len(recent) >= 2:
        base_ord = recent[0][0].toordinal()
        slope = _slope([(d.toordinal() - base_ord, v) for d, v in recent])
        if slope is not None:
            rows.append(
                {
                    "metric": metric,
                    "value": round(slope, 6),
                    "window": "30d",
                    "as_of_ts": as_of_iso,
                    "method": "slope",
                }
            )
    return rows


def compute_trends(
    conn: sqlite3.Connection,
    *,
    as_of: datetime | None = None,
) -> int:
    """Compute and persist derived metrics for every measured metric.

    Returns the number of derived rows written.
    """
    metrics = [
        r["metric"]
        for r in conn.execute("SELECT DISTINCT metric FROM measurements").fetchall()
    ]
    all_rows: list[dict[str, object]] = []
    for metric in metrics:
        all_rows.extend(compute_trends_for(conn, metric, as_of=as_of))
    if all_rows:
        db.bulk_insert(conn, "derived_metrics", all_rows)
    conn.commit()
    db.audit(conn, "process.trends", f"{len(all_rows)} derived rows")
    conn.commit()
    return len(all_rows)
