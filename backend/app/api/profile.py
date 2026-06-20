"""``/api/profile`` — the ``Me`` block plus a data-coverage summary."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import DB_PATH
from app.interpretation.context import DataContext
from app.interpretation.highlights import compute_highlights
from app.models.contracts import Profile
from app.processing import quality
from app.storage import db

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/profile", response_model=Profile)
def get_profile() -> Profile:
    """Return the user's ``Me`` characteristics plus current headline metrics.

    Headline metrics carry real values (e.g. resting HR in bpm) computed over
    each signal's recent window — far more informative than raw record counts.
    """
    with db.connection() as conn:
        prof_rows = {
            r["key"]: r["value"]
            for r in conn.execute("SELECT key, value FROM profile").fetchall()
        }
        coverage = quality.coverage_counts(conn)

    with DataContext(str(DB_PATH)) as ctx:
        highlights = compute_highlights(ctx)

    return Profile(
        dob=prof_rows.get("dob"),
        biological_sex=prof_rows.get("biological_sex"),
        blood_type=prof_rows.get("blood_type"),
        skin_type=prof_rows.get("skin_type"),
        coverage=coverage,
        highlights=highlights,
    )
