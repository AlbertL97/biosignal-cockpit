"""Per-metric personal baselines.

A baseline is the mean / standard deviation / sample count of a metric over a
configurable trailing window, interpreted *within-person* rather than against
population norms (ARCHITECTURE §8, task §10). Results are written to the
``baselines`` table.

Public entry point: :func:`compute_baselines`.
"""
from __future__ import annotations

import sqlite3
import statistics
from datetime import datetime, timedelta, timezone

from app.storage import db

DEFAULT_WINDOW_DAYS = 90
MIN_SAMPLES = 5


def _distinct_metrics(conn: sqlite3.Connection) -> list[str]:
    """Return all metric keys present in ``measurements``."""
    rows = conn.execute("SELECT DISTINCT metric FROM measurements").fetchall()
    return [r["metric"] for r in rows]


def _values_in_window(
    conn: sqlite3.Connection, metric: str, since_iso: str
) -> list[float]:
    """Return non-null values of ``metric`` with ``start_ts >= since_iso``."""
    rows = conn.execute(
        "SELECT value FROM measurements "
        "WHERE metric = ? AND value IS NOT NULL AND start_ts >= ? ",
        (metric, since_iso),
    ).fetchall()
    return [float(r["value"]) for r in rows]


def compute_baseline_for(
    conn: sqlite3.Connection,
    metric: str,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    as_of: datetime | None = None,
) -> dict[str, float | int | str] | None:
    """Compute a single metric's baseline over the trailing window.

    Args:
        conn: Open connection.
        metric: Canonical metric key.
        window_days: Trailing window length.
        as_of: End of the window (defaults to now, UTC).

    Returns:
        A baseline row dict, or ``None`` if there are fewer than
        :data:`MIN_SAMPLES` samples.
    """
    now = as_of or datetime.now(timezone.utc)
    since = (now - timedelta(days=window_days)).isoformat()
    values = _values_in_window(conn, metric, since)
    if len(values) < MIN_SAMPLES:
        return None
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return {
        "metric": metric,
        "mean": round(mean, 6),
        "sd": round(sd, 6),
        "n": len(values),
        "window_days": window_days,
        "computed_ts": now.isoformat(),
    }


def compute_baselines(
    conn: sqlite3.Connection,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    as_of: datetime | None = None,
) -> int:
    """Compute and persist baselines for every measured metric.

    Args:
        conn: Open connection.
        window_days: Trailing window length.
        as_of: End of the window (defaults to now, UTC).

    Returns:
        Number of baselines written.
    """
    rows: list[dict[str, float | int | str]] = []
    for metric in _distinct_metrics(conn):
        baseline = compute_baseline_for(
            conn, metric, window_days=window_days, as_of=as_of
        )
        if baseline is not None:
            rows.append(baseline)
    if rows:
        db.bulk_insert(conn, "baselines", rows, or_replace=True)
    conn.commit()
    db.audit(conn, "process.baselines", f"{len(rows)} metrics window={window_days}d")
    conn.commit()
    return len(rows)


def get_baseline(conn: sqlite3.Connection, metric: str) -> sqlite3.Row | None:
    """Return the stored baseline row for ``metric``, or ``None``."""
    return conn.execute(
        "SELECT * FROM baselines WHERE metric = ?", (metric,)
    ).fetchone()
