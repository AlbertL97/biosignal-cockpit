"""Tests for the evidence layer (grading, curated, store, pubmed, api).

Network is mocked everywhere except one optional live integration test guarded
by the ``RUN_PUBMED_LIVE`` env flag. Run from ``backend/``::

    python -m pytest tests/test_evidence.py
    RUN_PUBMED_LIVE=1 python -m pytest tests/test_evidence.py -k live   # real call
"""
from __future__ import annotations

import os

import pytest

from app.evidence import api, curated, grading, pubmed, store
from app.models.contracts import EvidenceGrade, EvidenceRef


# --------------------------------------------------------------------------- #
# grading.py                                                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("pubtypes", "expected"),
    [
        (["Meta-Analysis"], EvidenceGrade.high),
        (["Systematic Review"], EvidenceGrade.high),
        (["Practice Guideline"], EvidenceGrade.high),
        (["Randomized Controlled Trial"], EvidenceGrade.moderate),
        (["Multicenter Study", "Cohort Studies"], EvidenceGrade.moderate),
        (["Observational Study"], EvidenceGrade.low),
        (["Case-Control Studies"], EvidenceGrade.low),
        (["Case Reports"], EvidenceGrade.low),
        (["Preprint"], EvidenceGrade.exploratory),
        (["Editorial"], EvidenceGrade.exploratory),
        (["Journal Article"], EvidenceGrade.exploratory),  # uninformative -> cautious
        ([], EvidenceGrade.unsupported),
    ],
)
def test_grade_pubtypes(pubtypes: list[str], expected: EvidenceGrade) -> None:
    assert grading.grade_pubtypes(pubtypes) == expected


def test_grade_record_strongest_signal_wins() -> None:
    rec = {"pubtype": ["Journal Article", "Meta-Analysis"], "title": "x"}
    assert grading.grade_record(rec) == EvidenceGrade.high


def test_grade_record_title_signal() -> None:
    rec = {"pubtype": ["Journal Article"], "title": "A systematic review of X"}
    assert grading.grade_record(rec) == EvidenceGrade.high


def test_grade_record_retracted_is_unsupported() -> None:
    rec = {"pubtype": ["Meta-Analysis"], "retracted": True}
    assert grading.grade_record(rec) == EvidenceGrade.unsupported


def test_best_refs_orders_by_grade_then_stable() -> None:
    refs = [
        EvidenceRef(claim="c", grade=EvidenceGrade.low, source="pubmed"),
        EvidenceRef(claim="c", grade=EvidenceGrade.high, source="pubmed"),
        EvidenceRef(claim="c", grade=EvidenceGrade.moderate, source="pubmed"),
    ]
    out = grading.best_refs(refs, limit=2)
    assert [r.grade for r in out] == [EvidenceGrade.high, EvidenceGrade.moderate]


# --------------------------------------------------------------------------- #
# curated.py                                                                  #
# --------------------------------------------------------------------------- #
def test_curated_covers_all_nine_domains() -> None:
    assert curated.all_domains_covered()
    assert len(curated.DOMAINS) == 9
    for domain in curated.DOMAINS:
        refs = curated.curated_for(domain)
        assert refs, f"no curated evidence for {domain}"
        for ref in refs:
            assert ref.source in {"guideline", "curated"}
            assert isinstance(ref.grade, EvidenceGrade)


def test_curated_unknown_domain_is_empty() -> None:
    assert curated.curated_for("nonexistent") == []


# --------------------------------------------------------------------------- #
# store.py round-trip on a temp DB                                            #
# --------------------------------------------------------------------------- #
def test_store_roundtrip_and_upsert(tmp_path) -> None:
    db = tmp_path / "ev.sqlite"
    refs = [
        EvidenceRef(
            claim="fiber helps gut",
            grade=EvidenceGrade.high,
            pmid="111",
            title="T1",
            year=2019,
            url="https://pubmed.ncbi.nlm.nih.gov/111/",
            source="pubmed",
        ),
        EvidenceRef(
            claim="curated free text",
            grade=EvidenceGrade.moderate,
            pmid=None,
            source="curated",
        ),
    ]
    assert store.save_refs("gut", refs, db_path=db) == 2

    loaded = store.load_refs("gut", db_path=db)
    assert len(loaded) == 2
    by_pmid = {r.pmid: r for r in loaded}
    assert by_pmid["111"].grade == EvidenceGrade.high
    assert by_pmid["111"].title == "T1"

    # Upsert by (domain, pmid): same pmid, changed grade -> update, not insert.
    updated = EvidenceRef(
        claim="fiber helps gut", grade=EvidenceGrade.moderate, pmid="111",
        title="T1b", year=2020, source="pubmed",
    )
    store.save_refs("gut", [updated], db_path=db)
    loaded2 = store.load_refs("gut", db_path=db)
    assert len(loaded2) == 2  # still 2, not 3
    assert {r.pmid: r for r in loaded2}["111"].grade == EvidenceGrade.moderate

    # Domain isolation.
    assert store.load_refs("brain", db_path=db) == []
    assert store.clear_domain("gut", db_path=db) == 2
    assert store.load_refs("gut", db_path=db) == []


# --------------------------------------------------------------------------- #
# pubmed.py with mocked network                                               #
# --------------------------------------------------------------------------- #
def test_find_evidence_with_mocked_pubmed(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(pubmed, "PUBMED_CACHE", tmp_path / "cache")
    monkeypatch.setattr(pubmed, "search", lambda *a, **k: ["12345"])
    monkeypatch.setattr(
        pubmed,
        "fetch_summaries",
        lambda *a, **k: [
            {
                "pmid": "12345",
                "title": "A meta-analysis of fiber and gut health",
                "year": 2021,
                "journal": "Gut",
                "pubtype": ["Meta-Analysis"],
            }
        ],
    )
    refs = pubmed.find_evidence("dietary fiber supports gut", "gut")
    assert len(refs) == 1
    assert refs[0].pmid == "12345"
    assert refs[0].source == "pubmed"
    assert refs[0].grade == EvidenceGrade.high
    assert refs[0].url == "https://pubmed.ncbi.nlm.nih.gov/12345/"


def test_find_evidence_falls_back_to_curated(monkeypatch) -> None:
    # Simulate offline / no results from PubMed.
    monkeypatch.setattr(pubmed, "search", lambda *a, **k: [])
    refs = pubmed.find_evidence("anything", "brain")
    assert refs  # never empty for a known domain
    assert all(r.source in {"guideline", "curated"} for r in refs)


def test_search_returns_empty_without_entrez(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(pubmed, "PUBMED_CACHE", tmp_path / "c")
    monkeypatch.setattr(pubmed, "configure_entrez", lambda: None)
    assert pubmed.search("query", retmax=3) == []


def test_fetch_summaries_empty_pmids() -> None:
    assert pubmed.fetch_summaries([]) == []


def test_search_caches_and_reads_offline(monkeypatch, tmp_path) -> None:
    """First call writes cache; a later call with Entrez disabled reads it."""
    monkeypatch.setattr(pubmed, "PUBMED_CACHE", tmp_path / "cache")

    class _FakeEntrez:
        @staticmethod
        def esearch(**_kw):
            return object()

        @staticmethod
        def read(_handle):
            return {"IdList": ["999", "888"]}

    monkeypatch.setattr(pubmed, "configure_entrez", lambda: _FakeEntrez)
    # Need a closeable handle: patch esearch to return one.
    monkeypatch.setattr(
        _FakeEntrez, "esearch", staticmethod(lambda **_kw: _Handle())
    )
    first = pubmed.search("q", retmax=2)
    assert first == ["999", "888"]

    # Now disable network entirely; cached result must still come back.
    monkeypatch.setattr(pubmed, "configure_entrez", lambda: None)
    assert pubmed.search("q", retmax=2) == ["999", "888"]


class _Handle:
    def close(self) -> None:  # pragma: no cover - trivial
        pass


# --------------------------------------------------------------------------- #
# api.py                                                                       #
# --------------------------------------------------------------------------- #
def test_api_imports_cleanly() -> None:
    assert api.router is not None


def test_api_get_evidence_falls_back_to_curated(monkeypatch) -> None:
    monkeypatch.setattr(store, "load_refs", lambda *a, **k: [])
    out = api.get_evidence(domain="cardiovascular")
    assert out
    assert all(isinstance(r, EvidenceRef) for r in out)


# --------------------------------------------------------------------------- #
# Optional live integration test (guarded)                                    #
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(
    os.environ.get("RUN_PUBMED_LIVE") != "1",
    reason="set RUN_PUBMED_LIVE=1 to run a real PubMed query",
)
def test_live_pubmed_search() -> None:  # pragma: no cover - network
    pmids = pubmed.search("dietary fiber gut health meta-analysis", retmax=3)
    assert isinstance(pmids, list)
    if pmids:  # may be empty if no ENTREZ_EMAIL / rate-limited; that's allowed
        summaries = pubmed.fetch_summaries(pmids)
        assert all("pmid" in s for s in summaries)
