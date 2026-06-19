"""Parser for workout route GPX files (``workout-routes/*.gpx``).

Low priority (ARCHITECTURE §4): we extract a basic per-route summary (start
time, duration, distance, elevation gain, point count) and store it as a
``workouts`` row with ``activity_type='GPXRoute'`` so routes appear alongside
HealthKit workouts without a new table.

Public entry point: :func:`ingest_gpx`.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import gpxpy

from app.config import GPX_DIR
from app.storage import db

logger = logging.getLogger(__name__)


@dataclass
class RouteSummary:
    """Basic summary of one GPX route file."""

    name: str
    start_ts: str | None
    end_ts: str | None
    duration_s: float | None
    distance_m: float | None
    elevation_gain_m: float | None
    n_points: int


def parse_gpx(path: str | Path) -> RouteSummary:
    """Parse a GPX file into a :class:`RouteSummary`.

    Args:
        path: Path to a GPX file.

    Returns:
        A :class:`RouteSummary` (fields may be ``None`` if the track is empty).
    """
    p = Path(path)
    with open(p, encoding="utf-8") as fh:
        gpx = gpxpy.parse(fh)

    times = []
    n_points = 0
    distance = 0.0
    elevation_gain = 0.0
    for track in gpx.tracks:
        for segment in track.segments:
            n_points += len(segment.points)
            distance += segment.length_3d() or 0.0
            ud = segment.get_uphill_downhill()
            if ud is not None:
                elevation_gain += ud.uphill or 0.0
            for pt in segment.points:
                if pt.time is not None:
                    times.append(pt.time)

    start = min(times).isoformat() if times else None
    end = max(times).isoformat() if times else None
    duration = (max(times) - min(times)).total_seconds() if len(times) >= 2 else None
    name = gpx.tracks[0].name if gpx.tracks and gpx.tracks[0].name else p.stem

    return RouteSummary(
        name=name,
        start_ts=start,
        end_ts=end,
        duration_s=duration,
        distance_m=round(distance, 2) if distance else None,
        elevation_gain_m=round(elevation_gain, 2) if elevation_gain else None,
        n_points=n_points,
    )


def ingest_gpx(
    conn: sqlite3.Connection,
    gpx_dir: str | Path | None = None,
) -> dict[str, int]:
    """Parse every GPX file in ``gpx_dir`` and store route summaries.

    Args:
        conn: Open SQLite connection.
        gpx_dir: Override directory; defaults to :data:`app.config.GPX_DIR`.

    Returns:
        Counts keyed by ``routes``, ``failed``.
    """
    directory = Path(gpx_dir) if gpx_dir is not None else GPX_DIR
    counts = {"routes": 0, "failed": 0}
    if not directory.exists():
        db.audit(conn, "ingest.gpx", f"missing dir {directory}")
        return counts

    rows: list[dict[str, object]] = []
    for gpx_path in sorted(directory.glob("*.gpx")):
        try:
            summary = parse_gpx(gpx_path)
        except Exception as exc:  # pragma: no cover - malformed gpx
            logger.warning("Skipping %s: %s", gpx_path.name, exc)
            counts["failed"] += 1
            continue
        rows.append(
            {
                "activity_type": "GPXRoute",
                "start_ts": summary.start_ts,
                "end_ts": summary.end_ts,
                "duration_s": summary.duration_s,
                "energy_kcal": None,
                "distance_m": summary.distance_m,
                "source": summary.name,
            }
        )
        counts["routes"] += 1

    if rows:
        db.bulk_insert(conn, "workouts", rows)
    conn.commit()
    db.audit(conn, "ingest.gpx", str(counts))
    conn.commit()
    return counts
