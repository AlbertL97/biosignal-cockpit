"""FastAPI router for interpretation domains (ARCHITECTURE.md §7).

Exposes:
- ``GET /api/domains``            -> list of DomainStatus (overview cards)
- ``GET /api/domains/{domain}``   -> full DomainStatus for one domain

Results are computed on the fly from a fresh :class:`DataContext`; cached
persisted rows are used as a fallback if live computation fails.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.interpretation import engine
from app.interpretation.context import DataContext
from app.models.contracts import DomainStatus

router = APIRouter()


@router.get("/api/domains", response_model=list[DomainStatus])
def list_domains() -> list[DomainStatus]:
    """Return a DomainStatus for every canonical domain (overview cards)."""
    with DataContext() as ctx:
        try:
            return engine.run_all(ctx, persist=True)
        except Exception:  # pragma: no cover - defensive fallback to cache
            cached = [engine.load_cached(ctx, d) for d in engine.DOMAINS]
            return [c for c in cached if c is not None]


@router.get("/api/domains/{domain}", response_model=DomainStatus)
def get_domain(domain: str) -> DomainStatus:
    """Return the full DomainStatus for a single domain."""
    if domain not in engine.DOMAIN_REGISTRY:
        raise HTTPException(status_code=404, detail=f"unknown domain: {domain}")
    with DataContext() as ctx:
        try:
            return engine.run_one(ctx, domain, persist=True)
        except Exception:  # pragma: no cover - defensive fallback to cache
            cached = engine.load_cached(ctx, domain)
            if cached is None:
                raise HTTPException(status_code=503, detail="interpretation unavailable") from None
            return cached
