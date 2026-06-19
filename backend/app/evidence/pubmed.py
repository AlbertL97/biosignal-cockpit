"""Live PubMed access via NCBI E-utilities (Biopython ``Bio.Entrez``).

Public surface
--------------
* :func:`search` -- query PubMed, return a list of PMIDs.
* :func:`fetch_summaries` -- expand PMIDs into lightweight record dicts.
* :func:`find_evidence` -- high-level helper used by the interpretation agent:
  ``find_evidence(claim, domain, retmax=5) -> list[EvidenceRef]``.

Design notes (``task(2).md`` §5/§14, ``docs/ARCHITECTURE.md`` §8)
----------------------------------------------------------------
* Every E-utilities response is cached as JSON under ``app.config.PUBMED_CACHE``
  keyed by a hash of the request, so repeat calls hit disk and the layer works
  **offline after the first fetch**.
* Network / rate-limit / parse errors are swallowed: callers always receive
  cached data or an empty list -- the evidence layer never crashes the app.
* NCBI rate limits are respected: a small sleep keeps us under 3 req/s without
  an API key (10 req/s with one).
* ``ENTREZ_EMAIL`` may be empty in this environment; live calls may then fail,
  which is fine -- :func:`find_evidence` falls back to curated references.

The grading of fetched records is delegated to :mod:`app.evidence.grading`.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from app.config import ENTREZ_API_KEY, ENTREZ_EMAIL, PUBMED_CACHE
from app.evidence import curated, grading
from app.models.contracts import EvidenceRef

__all__ = ["search", "fetch_summaries", "find_evidence", "configure_entrez"]

# NCBI: <=3 req/s without key, <=10 with key. Sleep a touch over the floor.
_MIN_INTERVAL_S = 0.12 if ENTREZ_API_KEY else 0.34
_last_request_ts = 0.0

# Map a free-text claim's domain to extra MeSH-ish query terms for relevance.
_DOMAIN_TERMS: dict[str, str] = {
    "gut": "gastrointestinal OR gut OR microbiota OR fiber",
    "brain": "cognition OR brain OR cognitive",
    "cardiovascular": "cardiovascular OR heart rate OR fitness",
    "oral_dental": "dental OR oral health OR caries",
    "musculoskeletal": "muscle OR resistance training OR injury",
    "metabolic": "metabolic OR energy balance OR glucose",
    "sleep_recovery": "sleep OR recovery",
    "stress_autonomic": "heart rate variability OR autonomic OR stress",
    "immune_inflammation": "inflammation OR immune OR cytokine",
}


def configure_entrez() -> Any | None:
    """Import and configure :mod:`Bio.Entrez`. Returns the module or ``None``.

    Returns ``None`` when Biopython is unavailable so callers can fall back
    gracefully instead of raising at import time.
    """
    try:
        from Bio import Entrez  # noqa: PLC0415 (lazy import keeps module light)
    except ImportError:
        return None
    Entrez.email = ENTREZ_EMAIL or "anonymous@example.com"
    if ENTREZ_API_KEY:
        Entrez.api_key = ENTREZ_API_KEY
    Entrez.tool = "health-intelligence"
    return Entrez


def _throttle() -> None:
    """Sleep just enough to respect NCBI's rate limit."""
    global _last_request_ts
    now = time.monotonic()
    wait = _MIN_INTERVAL_S - (now - _last_request_ts)
    if wait > 0:
        time.sleep(wait)
    _last_request_ts = time.monotonic()


def _cache_path(kind: str, key: str) -> Path:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]  # noqa: S324
    return PUBMED_CACHE / f"{kind}_{digest}.json"


def _read_cache(kind: str, key: str) -> Any | None:
    path = _cache_path(kind, key)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
    return None


def _write_cache(kind: str, key: str, data: Any) -> None:
    try:
        PUBMED_CACHE.mkdir(parents=True, exist_ok=True)
        _cache_path(kind, key).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass  # cache is best-effort; never fatal


def search(query: str, retmax: int = 5, *, use_cache: bool = True) -> list[str]:
    """Search PubMed and return a list of PMID strings (most relevant first).

    On any network/parse error returns the cached result if present, else ``[]``.
    """
    cache_key = f"{query}::{retmax}"
    if use_cache:
        cached = _read_cache("search", cache_key)
        if cached is not None:
            return list(cached)

    entrez = configure_entrez()
    if entrez is None:
        return []

    try:
        _throttle()
        handle = entrez.esearch(
            db="pubmed", term=query, retmax=retmax, sort="relevance"
        )
        record = entrez.read(handle)
        handle.close()
        pmids = [str(p) for p in record.get("IdList", [])]
    except Exception:  # noqa: BLE001 - network/parse/rate-limit: degrade gracefully
        fallback = _read_cache("search", cache_key)
        return list(fallback) if fallback is not None else []

    _write_cache("search", cache_key, pmids)
    return pmids


def _parse_summary(doc: Any) -> dict[str, Any]:
    """Normalise one ESummary document into a flat record dict."""
    pub_date = str(doc.get("PubDate", "") or doc.get("EPubDate", ""))
    year: int | None = None
    for token in pub_date.replace("-", " ").split():
        if token.isdigit() and len(token) == 4:
            year = int(token)
            break
    pubtypes = doc.get("PubTypeList") or doc.get("PubType") or []
    if isinstance(pubtypes, str):
        pubtypes = [pubtypes]
    return {
        "pmid": str(doc.get("Id", "") or doc.get("ArticleIds", {}).get("pubmed", "")),
        "title": str(doc.get("Title", "")).rstrip("."),
        "year": year,
        "journal": str(doc.get("FullJournalName", "") or doc.get("Source", "")),
        "pubtype": [str(p) for p in pubtypes],
    }


def fetch_summaries(
    pmids: list[str], *, use_cache: bool = True
) -> list[dict[str, Any]]:
    """Fetch lightweight summaries for *pmids*.

    Each record: ``{pmid, title, year, journal, pubtype}``. Returns cached or
    ``[]`` on failure; an empty *pmids* list short-circuits to ``[]``.
    """
    if not pmids:
        return []
    cache_key = ",".join(pmids)
    if use_cache:
        cached = _read_cache("summary", cache_key)
        if cached is not None:
            return list(cached)

    entrez = configure_entrez()
    if entrez is None:
        return []

    try:
        _throttle()
        handle = entrez.esummary(db="pubmed", id=",".join(pmids))
        docs = entrez.read(handle)
        handle.close()
        records = [_parse_summary(doc) for doc in docs]
    except Exception:  # noqa: BLE001 - degrade gracefully
        fallback = _read_cache("summary", cache_key)
        return list(fallback) if fallback is not None else []

    _write_cache("summary", cache_key, records)
    return records


def record_to_ref(rec: dict[str, Any], claim: str) -> EvidenceRef:
    """Convert a fetched PubMed record into a graded :class:`EvidenceRef`."""
    pmid = rec.get("pmid") or None
    return EvidenceRef(
        claim=claim,
        grade=grading.grade_record(rec),
        pmid=pmid,
        title=rec.get("title") or None,
        year=rec.get("year"),
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
        source="pubmed",
    )


def find_evidence(claim: str, domain: str, retmax: int = 5) -> list[EvidenceRef]:
    """Return graded evidence references for *claim* within *domain*.

    This is the stable entry point the **interpretation agent** calls to attach
    evidence to a domain report. Behaviour:

    1. Build a relevance-boosted PubMed query from *claim* + domain terms.
    2. Search + fetch summaries (cached; offline-safe).
    3. Grade each record and keep the best-graded refs (:func:`grading.best_refs`).
    4. If PubMed yields nothing (offline / no email / rate-limited), fall back to
       :mod:`app.evidence.curated` so the result is **never empty** for a known
       domain.

    Args:
        claim: The interpretation claim text to find support for.
        domain: One of the canonical domains (``docs/ARCHITECTURE.md`` §3).
        retmax: Maximum number of PubMed hits to consider.

    Returns:
        A list of :class:`EvidenceRef`, best-graded first; possibly empty only
        for an unknown domain with no PubMed results.
    """
    domain_terms = _DOMAIN_TERMS.get(domain, domain.replace("_", " "))
    query = f"({claim}) AND ({domain_terms})"

    refs: list[EvidenceRef] = []
    pmids = search(query, retmax=retmax)
    if pmids:
        records = fetch_summaries(pmids)
        refs = [record_to_ref(r, claim) for r in records if r.get("pmid")]
        refs = grading.best_refs(refs, limit=retmax)
        # Drop unsupported-grade hits; we never assert unsupported claims.
        refs = [r for r in refs if r.grade.value != "unsupported"]

    if not refs:
        refs = curated.curated_for(domain)
    return refs
