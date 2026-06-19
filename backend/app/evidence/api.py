"""Evidence API router (mounted by ``app/main.py`` under base ``/api``).

Endpoints
---------
* ``GET /api/evidence?domain=...``
    Graded evidence references for a domain. Reads persisted refs from the DB
    first; if none are stored it falls back to the curated guideline set so the
    response is never empty for a known domain (``docs/ARCHITECTURE.md`` §7).
* ``GET /api/evidence/search?q=...&domain=...``
    Live PubMed lookup for an ad-hoc claim (cached + offline-safe).

Both return ``list[EvidenceRef]`` matching the shared Pydantic contract.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.evidence import curated, pubmed, store
from app.models.contracts import EvidenceRef

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("", response_model=list[EvidenceRef])
def get_evidence(
    domain: str = Query(..., description="Canonical body-system domain"),
) -> list[EvidenceRef]:
    """Return graded evidence refs for *domain* (DB first, else curated)."""
    refs = store.load_refs(domain)
    if not refs:
        refs = curated.curated_for(domain)
    return refs


@router.get("/search", response_model=list[EvidenceRef])
def search_evidence(
    q: str = Query(..., description="Claim / free-text query to find support for"),
    domain: str = Query("", description="Optional domain to boost relevance"),
    retmax: int = Query(5, ge=1, le=20),
) -> list[EvidenceRef]:
    """Live PubMed lookup for *q* (cached; falls back to curated for a domain)."""
    return pubmed.find_evidence(q, domain or "", retmax=retmax)
