"""``/api/metrics/{metric}`` — timeseries + baseline for charts."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.interpretation.context import _alias
from app.models.contracts import MetricSeries, TimePoint
from app.storage import db

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics/{metric}", response_model=MetricSeries)
def get_metric(
    metric: str,
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    window: str | None = Query(default=None, description="aggregate, e.g. 'day'"),
    limit: int = Query(default=5000, ge=1, le=100000),
) -> MetricSeries:
    """Return a metric's timeseries and stored baseline.

    Args:
        metric: Canonical metric key.
        from_: ISO lower bound on ``start_ts`` (inclusive), query param ``from``.
        to: ISO upper bound on ``start_ts`` (inclusive).
        window: If ``"day"``, return daily means instead of raw points.
        limit: Maximum number of points returned.

    Raises:
        HTTPException: 404 when the metric has no data and no baseline.
    """
    metric = _alias(metric)  # accept HK-style canonical names from the frontend
    clauses = ["metric = ?", "value IS NOT NULL"]
    params: list[object] = [metric]
    if from_:
        clauses.append("start_ts >= ?")
        params.append(from_)
    if to:
        clauses.append("start_ts <= ?")
        params.append(to)
    where = " AND ".join(clauses)

    with db.connection() as conn:
        if window == "day":
            sql = (
                f"SELECT substr(start_ts,1,10) AS ts, AVG(value) AS v "  # noqa: S608
                f"FROM measurements WHERE {where} "
                f"GROUP BY ts ORDER BY ts LIMIT ?"
            )
        else:
            sql = (
                f"SELECT start_ts AS ts, value AS v "  # noqa: S608
                f"FROM measurements WHERE {where} ORDER BY ts LIMIT ?"
            )
        rows = conn.execute(sql, [*params, limit]).fetchall()

        unit_row = conn.execute(
            "SELECT unit FROM measurements WHERE metric = ? AND unit IS NOT NULL LIMIT 1",
            (metric,),
        ).fetchone()
        baseline = conn.execute(
            "SELECT mean, sd FROM baselines WHERE metric = ?", (metric,)
        ).fetchone()

    if not rows and baseline is None:
        raise HTTPException(status_code=404, detail=f"No data for metric '{metric}'")

    points: list[TimePoint] = []
    for r in rows:
        ts = r["ts"]
        try:
            dt = datetime.fromisoformat(ts if len(ts) > 10 else f"{ts}T00:00:00")
        except (ValueError, TypeError):
            continue
        points.append(TimePoint(ts=dt, value=float(r["v"])))

    return MetricSeries(
        metric=metric,
        unit=unit_row["unit"] if unit_row else None,
        points=points,
        baseline_mean=baseline["mean"] if baseline else None,
        baseline_sd=baseline["sd"] if baseline else None,
    )
