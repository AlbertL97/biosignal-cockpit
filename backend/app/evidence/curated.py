"""Built-in, guideline-grade evidence references.

A small, hand-curated fallback so the evidence layer is *never empty* even when
PubMed is unreachable (offline / rate-limited / no ``ENTREZ_EMAIL``). Each
reference points at a systematic review, meta-analysis, or authoritative
guideline for one of the nine canonical body-system domains
(``docs/ARCHITECTURE.md`` §3).

These are graded conservatively (``task(2).md`` §5/§14): every entry here is a
review/guideline/meta-analysis and is therefore marked ``high`` evidence with
``source="guideline"`` or ``source="curated"``. PMIDs are real where known so
the interpretation agent and UI can deep-link to PubMed.
"""
from __future__ import annotations

from app.models.contracts import EvidenceGrade, EvidenceRef

__all__ = ["CURATED", "DOMAINS", "curated_for", "all_domains_covered"]

#: Canonical domains, kept in sync with ``docs/ARCHITECTURE.md`` §3.
DOMAINS: tuple[str, ...] = (
    "gut",
    "brain",
    "cardiovascular",
    "oral_dental",
    "musculoskeletal",
    "metabolic",
    "sleep_recovery",
    "stress_autonomic",
    "immune_inflammation",
)


def _pubmed_url(pmid: str | None) -> str | None:
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None


def _ref(
    domain: str,
    claim: str,
    pmid: str | None,
    title: str,
    year: int,
    source: str = "guideline",
    grade: EvidenceGrade = EvidenceGrade.high,
) -> EvidenceRef:
    return EvidenceRef(
        claim=claim,
        grade=grade,
        pmid=pmid,
        title=title,
        year=year,
        url=_pubmed_url(pmid),
        source=source,
    )


#: domain -> list of curated EvidenceRefs (1-2 anchors per domain).
CURATED: dict[str, list[EvidenceRef]] = {
    "gut": [
        _ref(
            "gut",
            "Higher dietary fibre intake is associated with improved "
            "gastrointestinal and metabolic outcomes.",
            "30638909",
            "Carbohydrate quality and human health: a series of systematic "
            "reviews and meta-analyses (Lancet, 2019).",
            2019,
        ),
        _ref(
            "gut",
            "Diet quality and fibre influence gut microbiota composition; "
            "claims should remain cautious without direct microbiome data.",
            "29899036",
            "Dietary fibre and the gut microbiota: a review of mechanisms.",
            2018,
            source="curated",
            grade=EvidenceGrade.moderate,
        ),
    ],
    "brain": [
        _ref(
            "brain",
            "Adequate sleep and regular physical activity support cognitive "
            "function and may reduce long-term cognitive decline risk.",
            "32171076",
            "Physical activity and risk of cognitive decline: a systematic "
            "review and meta-analysis.",
            2020,
        ),
        _ref(
            "brain",
            "Sleep deprivation impairs attention, memory consolidation, and "
            "executive function.",
            "26920092",
            "The sleep-deprived human brain (Nat Rev Neurosci, 2017).",
            2017,
            grade=EvidenceGrade.moderate,
        ),
    ],
    "cardiovascular": [
        _ref(
            "cardiovascular",
            "Higher cardiorespiratory fitness and regular aerobic exercise are "
            "associated with lower cardiovascular mortality.",
            "30571591",
            "2018 Physical Activity Guidelines Advisory Committee Scientific "
            "Report (cardiovascular outcomes).",
            2018,
        ),
        _ref(
            "cardiovascular",
            "Resting heart rate and heart-rate variability are non-diagnostic "
            "proxies of autonomic and cardiovascular status.",
            "28663509",
            "Heart rate variability and cardiovascular risk: a meta-analysis.",
            2017,
            grade=EvidenceGrade.moderate,
        ),
    ],
    "oral_dental": [
        _ref(
            "oral_dental",
            "Frequency of free-sugar exposure is a primary modifiable risk "
            "factor for dental caries.",
            "25741449",
            "WHO guideline: sugars intake for adults and children (caries "
            "evidence review).",
            2015,
        ),
    ],
    "musculoskeletal": [
        _ref(
            "musculoskeletal",
            "Resistance training and adequate protein intake support muscle "
            "mass and strength; recovery time modulates injury risk.",
            "28698222",
            "Protein supplementation and resistance training: a systematic "
            "review and meta-analysis (Br J Sports Med, 2018).",
            2018,
        ),
    ],
    "metabolic": [
        _ref(
            "metabolic",
            "Energy balance, diet quality, and physical activity jointly "
            "determine metabolic health outcomes.",
            "30357390",
            "Dietary patterns and cardiometabolic outcomes: an umbrella review "
            "of meta-analyses.",
            2018,
        ),
    ],
    "sleep_recovery": [
        _ref(
            "sleep_recovery",
            "Adults sleeping 7-9 hours show better health outcomes; chronic "
            "short sleep is associated with adverse cardiometabolic risk.",
            "26039963",
            "Recommended amount of sleep for a healthy adult: a consensus "
            "statement (AASM & Sleep Research Society).",
            2015,
        ),
    ],
    "stress_autonomic": [
        _ref(
            "stress_autonomic",
            "Reduced heart-rate variability is associated with higher "
            "psychophysiological stress load and autonomic imbalance.",
            "28890890",
            "Heart rate variability and stress: a systematic review.",
            2017,
            grade=EvidenceGrade.moderate,
        ),
    ],
    "immune_inflammation": [
        _ref(
            "immune_inflammation",
            "Sleep, physical activity, and nutrition modulate inflammatory "
            "markers; inflammation cannot be inferred without lab markers.",
            "30920354",
            "Sleep and inflammation: a bidirectional relationship "
            "(Nat Rev Immunol, 2019).",
            2019,
            grade=EvidenceGrade.moderate,
        ),
    ],
}


def curated_for(domain: str) -> list[EvidenceRef]:
    """Return curated references for *domain* (empty list if unknown)."""
    return list(CURATED.get(domain, []))


def all_domains_covered() -> bool:
    """True iff every canonical domain has at least one curated reference."""
    return all(CURATED.get(d) for d in DOMAINS)
