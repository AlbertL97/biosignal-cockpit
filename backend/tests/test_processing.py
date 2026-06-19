"""Tests for baselines, trends, and quality helpers."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from app.processing import baselines, quality, trends
from app.storage import db


def _seed_measurements(
    conn: sqlite3.Connection, metric: str, values: list[float], *, start: datetime
) -> None:
    """Insert one measurement per day starting at ``start``."""
    rows = [
        {
            "metric": metric,
            "unit": "count/min",
            "value": v,
            "start_ts": (start + timedelta(days=i)).isoformat(),
            "end_ts": (start + timedelta(days=i)).isoformat(),
            "source": "test",
            "device": None,
            "raw_type": "HKQuantityTypeIdentifierHeartRate",
        }
        for i, v in enumerate(values)
    ]
    db.bulk_insert(conn, "measurements", rows)
    conn.commit()


def test_baseline_computation(conn: sqlite3.Connection) -> None:
    as_of = datetime(2024, 2, 1, tzinfo=timezone.utc)
    start = as_of - timedelta(days=10)
    _seed_measurements(conn, "heart_rate", [60, 62, 64, 66, 68, 70, 72], start=start)
    n = baselines.compute_baselines(conn, window_days=90, as_of=as_of)
    assert n == 1
    b = baselines.get_baseline(conn, "heart_rate")
    assert b is not None
    assert b["n"] == 7
    assert 64.0 < b["mean"] < 68.0
    assert b["sd"] > 0


def test_baseline_skips_sparse_metric(conn: sqlite3.Connection) -> None:
    as_of = datetime(2024, 2, 1, tzinfo=timezone.utc)
    _seed_measurements(conn, "vo2max", [40, 41], start=as_of - timedelta(days=5))
    n = baselines.compute_baselines(conn, as_of=as_of)
    assert n == 0  # fewer than MIN_SAMPLES


def test_trends_rolling_and_zscore(conn: sqlite3.Connection) -> None:
    as_of = datetime(2024, 3, 1, tzinfo=timezone.utc)
    start = as_of - timedelta(days=40)
    vals = [60 + i for i in range(40)]  # rising trend
    _seed_measurements(conn, "heart_rate", vals, start=start)
    baselines.compute_baselines(conn, as_of=as_of)
    count = trends.compute_trends(conn, as_of=as_of)
    assert count > 0

    methods = {
        r["method"]
        for r in conn.execute("SELECT DISTINCT method FROM derived_metrics").fetchall()
    }
    assert "rolling_mean" in methods
    assert "zscore" in methods
    assert "slope" in methods

    slope = conn.execute(
        "SELECT value FROM derived_metrics WHERE method='slope'"
    ).fetchone()
    assert slope["value"] > 0  # rising trend => positive slope


def test_quality_helpers(conn: sqlite3.Connection) -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    # day 1, 2, then a gap, then day 5
    rows = [
        {
            "metric": "step_count",
            "unit": "count",
            "value": 1000,
            "start_ts": (start + timedelta(days=d)).isoformat(),
            "end_ts": None,
            "source": "test",
            "device": None,
            "raw_type": "x",
        }
        for d in (0, 1, 4)
    ]
    db.bulk_insert(conn, "measurements", rows)
    conn.commit()

    cov = quality.metric_coverage(conn)
    assert cov["step_count"]["n"] == 3
    md = quality.missing_days(conn, "step_count")
    assert md["expected_days"] == 5
    assert md["observed_days"] == 3
    assert md["missing_days"] == 2

    assert quality.duplicate_measurements(conn) == 0
    report = quality.quality_report(conn)
    assert report["metrics_tracked"] == 1


def test_duplicate_detection(conn: sqlite3.Connection) -> None:
    row = {
        "metric": "heart_rate",
        "unit": "count/min",
        "value": 60,
        "start_ts": "2024-01-01T08:00:00+00:00",
        "end_ts": None,
        "source": "test",
        "device": None,
        "raw_type": "x",
    }
    db.bulk_insert(conn, "measurements", [row, dict(row)])
    conn.commit()
    assert quality.duplicate_measurements(conn) == 1
