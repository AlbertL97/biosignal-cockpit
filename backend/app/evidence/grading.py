"""Evidence grading heuristics.

Maps a PubMed-style record (or any study description) to an
:class:`~app.models.contracts.EvidenceGrade` using publication-type heuristics
that follow the evidence hierarchy described in ``task(2).md`` §5:

* **high**        meta-analysis, systematic review, practice guideline,
                  consensus statement.
* **moderate**    randomised controlled trial, large/prospective cohort.
* **low**         observational, case-control, cross-sectional, case series.
* **exploratory** preprint, in-vitro, animal-only, single small study, comment.
* **unsupported** nothing recognisable / explicitly retracted.

The grader is deliberately conservative (``task(2).md`` §14): when a record's
publication type is ambiguous it defaults to ``exploratory`` rather than
over-claiming. A record is a plain ``dict`` so it works for both live PubMed
summaries and synthetic test fixtures.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from app.models.contracts import EvidenceGrade, EvidenceRef

__all__ = ["grade_record", "grade_pubtypes", "best_refs", "GRADE_RANK"]

# Higher number == stronger evidence. Used to rank/select refs.
GRADE_RANK: dict[EvidenceGrade, int] = {
    EvidenceGrade.high: 4,
    EvidenceGrade.moderate: 3,
    EvidenceGrade.low: 2,
    EvidenceGrade.exploratory: 1,
    EvidenceGrade.unsupported: 0,
}

# Publication-type substrings (lower-cased) mapped to a grade. Order matters:
# the strongest matching signal in a record wins, so we evaluate high -> low.
_HIGH = (
    "meta-analysis",
    "meta analysis",
    "systematic review",
    "practice guideline",
    "guideline",
    "consensus",
)
_MODERATE = (
    "randomized controlled trial",
    "randomised controlled trial",
    "controlled clinical trial",
    "clinical trial, phase iii",
    "clinical trial, phase iv",
    "multicenter study",
    "cohort",
)
_LOW = (
    "observational study",
    "case-control",
    "case control",
    "cross-sectional",
    "comparative study",
    "clinical trial",  # generic / early-phase trial -> low rather than moderate
    "case reports",
    "case series",
)
_EXPLORATORY = (
    "preprint",
    "in vitro",
    "comment",
    "editorial",
    "letter",
    "review",  # narrative (non-systematic) review
)


def grade_pubtypes(pubtypes: Iterable[str]) -> EvidenceGrade:
    """Grade a study from its list of PubMed publication types.

    Returns the strongest grade whose signature appears in *pubtypes*. Returns
    :attr:`EvidenceGrade.unsupported` when nothing is recognised.
    """
    joined = " | ".join(str(p).lower() for p in pubtypes if p)
    if not joined.strip():
        return EvidenceGrade.unsupported
    if any(k in joined for k in _HIGH):
        return EvidenceGrade.high
    if any(k in joined for k in _MODERATE):
        return EvidenceGrade.moderate
    if any(k in joined for k in _LOW):
        return EvidenceGrade.low
    if any(k in joined for k in _EXPLORATORY):
        return EvidenceGrade.exploratory
    # Recognisable journal article but no informative type -> conservative.
    return EvidenceGrade.exploratory


def grade_record(rec: Mapping[str, Any]) -> EvidenceGrade:
    """Grade a single PubMed-style record.

    The record may carry publication-type information under ``"pubtype"`` (a
    string or list) and/or expose ``"title"``/``"journal"`` text we scan for
    strong signals (e.g. a "systematic review" in the title). An explicit
    ``"retracted"`` flag forces :attr:`EvidenceGrade.unsupported`.
    """
    if rec.get("retracted"):
        return EvidenceGrade.unsupported

    pubtype = rec.get("pubtype")
    if isinstance(pubtype, str):
        pubtypes: list[str] = [pubtype]
    elif isinstance(pubtype, Iterable):
        pubtypes = [str(p) for p in pubtype]
    else:
        pubtypes = []

    # Titles often disclose strong designs even when pubtypes are sparse.
    title = str(rec.get("title", ""))
    grade = grade_pubtypes([*pubtypes, title])
    return grade


def best_refs(refs: Iterable[EvidenceRef], limit: int = 5) -> list[EvidenceRef]:
    """Return up to *limit* refs ranked best-graded first.

    Ties keep stable input order (most relevant first as returned by PubMed).
    """
    ranked = sorted(
        enumerate(refs),
        key=lambda pair: (-GRADE_RANK.get(pair[1].grade, 0), pair[0]),
    )
    return [ref for _, ref in ranked[: max(0, limit)]]
