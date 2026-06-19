"""Data-quality helpers: coverage, missing-data, and duplicate detection.

These surface gaps and noise so the interpretation layer can attach explicit
uncertainty / missing-data notes (ARCHITECTURE §8, task §10/§12.3). Nothing here
mutates source data; it only reports.

Public entry points: :func:`metric_coverage`, :func:`missing_days`,
:func:`duplicate_measurements`, :func:`quality_report`.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta


def metric_coverage(conn: sqlite3.Connection) -> dict[str, dict[str, object]]:
    """Return per-metric coverage: count, first/last timestamp, distinct days.

    Returns:
        Mapping of metric -> ``{"n", "first_ts", "last_ts", "days"}``.
    """
    rows = conn.execute(
        "SELECT metric, COUNT(*) AS n, MIN(start_ts) AS first_ts, "
        "MAX(start_ts) AS last_ts, COUNT(DISTINCT substr(start_ts,1,10)) AS days "
        "FROM measurements GROUP BY metric"
    ).fetchall()
    return {
        r["metric"]: {
            "n": r["n"],
            "first_ts": r["first_ts"],
            "last_ts": r["last_ts"],
            "days": r["days"],
        }
        for r in rows
    }


def coverage_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Return a simple metric -> record-count map (for the profile endpoint)."""
    rows = conn.execute(
        "SELECT metric, COUNT(*) AS n FROM measurements GROUP BY metric"
    ).fetchall()
    return {r["metric"]: r["n"] for r in rows}


def missing_days(conn: sqlite3.Connection, metric: str) -> dict[str, object]:
    """Estimate gaps for a metric between its first and last observed day.

    Returns:
        ``{"expected_days", "observed_days", "missing_days", "coverage_ratio"}``.
        Empty/insufficient data yields zeros.
    """
    rows = conn.execute(
        "SELECT DISTINCT substr(start_ts,1,10) AS day FROM measurements "
        "WHERE metric = ? AND start_ts IS NOT NULL ORDER BY day",
        (metric,),
    ).fetchall()
    days = [r["day"] for r in rows if r["day"]]
    if len(days) < 2:
        return {
            "expected_days": len(days),
            "observed_days": len(days),
            "missing_days": 0,
            "coverage_ratio": 1.0 if days else 0.0,
        }
    first = date.fromisoformat(days[0])
    last = date.fromisoformat(days[-1])
    expected = (last - first).days + 1
    observed = len(set(days))
    missing = max(expected - observed, 0)
    return {
        "expected_days": expected,
        "observed_days": observed,
        "missing_days": missing,
        "coverage_ratio": round(observed / expected, 4) if expected else 0.0,
    }


def duplicate_measurements(conn: sqlite3.Connection) -> int:
    """Count exact duplicate measurement rows (same metric/value/start_ts/source).

    Returns:
        Number of *extra* rows beyond the first occurrence of each group.
    """
    row = conn.execute(
        "SELECT COALESCE(SUM(c - 1), 0) AS dups FROM ("
        "  SELECT COUNT(*) AS c FROM measurements "
        "  GROUP BY metric, value, start_ts, source HAVING c > 1"
        ")"
    ).fetchone()
    return int(row["dups"]) if row else 0


def recency_days(last_ts: str | None, *, now: datetime | None = None) -> int | None:
    """Whole days since ``last_ts`` (ISO 8601); ``None`` if unparseable."""
    if not last_ts:
        return None
    try:
        last = datetime.fromisoformat(last_ts)
    except ValueError:
        return None
    if now is not None:
        ref = now
    else:
        ref = datetime.now(last.tzinfo) if last.tzinfo else datetime.now()
    return max((ref - last).days, 0)


def quality_report(conn: sqlite3.Connection) -> dict[str, object]:
    """Aggregate a compact data-quality snapshot across all metrics."""
    coverage = metric_coverage(conn)
    stale_threshold = timedelta(days=14)
    now = datetime.now()
    stale: list[str] = []
    for metric, info in coverage.items():
        last = info.get("last_ts")
        if isinstance(last, str):
            try:
                last_dt = datetime.fromisoformat(last)
                ref = now.replace(tzinfo=last_dt.tzinfo) if last_dt.tzinfo else now
                if ref - last_dt > stale_threshold:
                    stale.append(metric)
            except ValueError:
                continue
    return {
        "metrics_tracked": len(coverage),
        "duplicate_measurements": duplicate_measurements(conn),
        "stale_metrics": sorted(stale),
        "coverage": coverage,
    }
