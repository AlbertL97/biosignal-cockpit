"""``/api/profile`` — the ``Me`` block plus a data-coverage summary."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.contracts import Profile
from app.processing import quality
from app.storage import db

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/profile", response_model=Profile)
def get_profile() -> Profile:
    """Return the user's ``Me`` characteristics and per-metric record counts.

    Reads the ``profile`` table (populated from ``<Me>``) and derives a
    ``coverage`` map (metric -> record count) from ``measurements``.
    """
    with db.connection() as conn:
        prof_rows = {
            r["key"]: r["value"]
            for r in conn.execute("SELECT key, value FROM profile").fetchall()
        }
        coverage = quality.coverage_counts(conn)

    return Profile(
        dob=prof_rows.get("dob"),
        biological_sex=prof_rows.get("biological_sex"),
        blood_type=prof_rows.get("blood_type"),
        skin_type=prof_rows.get("skin_type"),
        coverage=coverage,
    )
