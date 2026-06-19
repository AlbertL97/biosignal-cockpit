"""``/api/ingest`` — (re)run the ingestion pipeline and return an audit summary.

The pipeline can be slow (the VCF stream takes minutes), so this endpoint runs
it synchronously and is intended for local single-user operation. Use the
``skip`` / ``reset`` body fields to control scope.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.ingestion import run as pipeline
from app.ingestion.run import STAGES
from app.storage import db

router = APIRouter(prefix="/api", tags=["ingest"])


class IngestRequest(BaseModel):
    """Body for a pipeline run."""

    reset: bool = False
    skip: list[str] = []


class IngestResponse(BaseModel):
    """Per-stage counts plus the tail of the audit log."""

    results: dict[str, dict[str, int]]
    audit_tail: list[dict[str, str]]


@router.post("/ingest", response_model=IngestResponse)
def run_ingest(req: IngestRequest | None = None) -> IngestResponse:
    """Run (or re-run) the ingestion pipeline.

    Args:
        req: Optional run options. Unknown ``skip`` stages are ignored.

    Returns:
        An :class:`IngestResponse` with per-stage counts and recent audit rows.
    """
    req = req or IngestRequest()
    skip = {s for s in req.skip if s in STAGES}
    results = pipeline.run_pipeline(reset=req.reset, skip=skip)

    with db.connection() as conn:
        rows = conn.execute(
            "SELECT ts, event, detail FROM audit_log ORDER BY ts DESC LIMIT 20"
        ).fetchall()
    audit_tail = [
        {"ts": r["ts"], "event": r["event"], "detail": r["detail"] or ""}
        for r in rows
    ]
    return IngestResponse(results=results, audit_tail=audit_tail)
