"""Domain interpretation modules.

Each module exposes ``compute(ctx: DataContext) -> DomainStatus`` implementing an
evidence-aware, within-person, rule-based interpretation for one body system.
This package also provides shared helpers (:class:`DomainBuilder`,
``insufficient``) used by every domain to keep them consistent with the contract.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from app.interpretation import scoring
from app.interpretation.context import DataContext
from app.models.contracts import (
    Confidence,
    Contribution,
    DomainStatus,
    EvidenceGrade,
    EvidenceRef,
    Trend,
)

# Public registry of domain compute callables, filled by ``DOMAIN_REGISTRY``.
ComputeFn = Callable[[DataContext], DomainStatus]


def insufficient(
    domain: str,
    ctx: DataContext,
    missing: list[str],
    note: str,
) -> DomainStatus:
    """Build a contract-valid ``insufficient data`` status.

    Used when a domain lacks the inputs needed for any honest interpretation;
    score is ``None`` and the summary says so explicitly (no fabricated precision).
    """
    return DomainStatus(
        domain=domain,
        score=None,
        score_label="insufficient data",
        trend=Trend.unknown,
        confidence=Confidence.exploratory,
        evidence_grade=EvidenceGrade.unsupported,
        summary=(
            f"The available data do not allow a direct conclusion about "
            f"{domain.replace('_', ' ')} status. {note}"
        ),
        observations=[],
        derived=[],
        inferences=[],
        hypotheses=[],
        recommendations=[
            "Add or sync more data so a within-person baseline can be established.",
        ],
        contributions=[],
        evidence=[],
        missing_data=missing,
        as_of=ctx.now,
    )


@dataclass
class DomainBuilder:
    """Accumulates the five interpretation layers and contributions for a domain.

    Domains push observations / derived / inferences / hypotheses /
    recommendations and weighted ``(score, weight)`` contributions, then call
    :meth:`finish` to produce a validated :class:`DomainStatus`.
    """

    domain: str
    ctx: DataContext
    observations: list[str] = field(default_factory=list)
    derived: list[str] = field(default_factory=list)
    inferences: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    contributions: list[Contribution] = field(default_factory=list)
    evidence: list[EvidenceRef] = field(default_factory=list)
    _scored: list[tuple[float, float]] = field(default_factory=list)
    _grades: list[EvidenceGrade] = field(default_factory=list)
    _expected_inputs: int = 0
    _present_inputs: int = 0

    # -- input bookkeeping -------------------------------------------------

    def expect(self, n: int = 1) -> None:
        """Declare ``n`` expected inputs (for completeness scoring)."""
        self._expected_inputs += n

    def add_contribution(
        self,
        source: str,
        metric: str,
        value: float | str | None,
        score: float | None,
        weight: float,
        grade: EvidenceGrade = EvidenceGrade.moderate,
    ) -> None:
        """Register a weighted contribution and (if scored) fold it into the score."""
        self.expect(1)
        direction = "uncertain"
        if score is not None:
            self._present_inputs += 1
            self._scored.append((score, weight))
            self._grades.append(grade)
            if score >= 60:
                direction = "supportive"
            elif score <= 40:
                direction = "adverse"
            else:
                direction = "neutral"
        self.contributions.append(
            Contribution(
                source=source,
                metric=metric,
                value=value,
                weight=max(0.0, min(1.0, weight)),
                direction=direction,
            )
        )

    def add_evidence(self, ref: EvidenceRef) -> None:
        """Attach a graded evidence reference and track its grade."""
        self.evidence.append(ref)
        self._grades.append(ref.grade)

    def note_missing(self, *items: str) -> None:
        """Record explicit missing-data gaps."""
        self.missing_data.extend(items)

    # -- output ------------------------------------------------------------

    def has_signal(self) -> bool:
        """Whether at least one scored contribution exists."""
        return bool(self._scored)

    def current_score(self) -> float | None:
        """Preview the combined 0..100 score from contributions so far."""
        return scoring.combine_weighted(self._scored)

    def finish(
        self,
        summary: str,
        trend: Trend = Trend.unknown,
        evidence_strength: float = 0.5,
        signal_quality: float = 0.6,
    ) -> DomainStatus:
        """Compute score/confidence/grade and assemble a ``DomainStatus``."""
        score = scoring.combine_weighted(self._scored)
        completeness = (
            self._present_inputs / self._expected_inputs if self._expected_inputs else 0.0
        )
        confidence = scoring.derive_confidence(
            completeness=completeness,
            signal_quality=signal_quality if self.has_signal() else 0.1,
            evidence_strength=evidence_strength,
        )
        grade = scoring.combine_evidence_grades(self._grades) if self._grades else EvidenceGrade.exploratory
        return DomainStatus(
            domain=self.domain,
            score=score,
            score_label=scoring.score_label_for(score),
            trend=trend,
            confidence=confidence,
            evidence_grade=grade,
            summary=summary,
            observations=self.observations,
            derived=self.derived,
            inferences=self.inferences,
            hypotheses=self.hypotheses,
            recommendations=self.recommendations,
            contributions=self.contributions,
            evidence=self.evidence,
            missing_data=self.missing_data,
            as_of=self.ctx.now,
        )


def map_nebula(
    builder: DomainBuilder,
    keywords: Sequence[str],
    grade: EvidenceGrade = EvidenceGrade.exploratory,
) -> None:
    """Map matching Nebula traits into the domain's genetic context.

    Adds cautious, non-deterministic hypotheses and a low-weight genome
    contribution, honoring the "flag research-only, never deterministic" rule.
    """
    traits = builder.ctx.nebula_search(list(keywords))
    if not traits:
        builder.note_missing("no matched Nebula genomic trait reports for this domain")
        return
    for row in traits[:4]:
        name = row["trait"]
        label = row["score_label"] or "see report"
        builder.hypotheses.append(
            f"Genomic context (research-only, non-deterministic): the Nebula trait "
            f"'{name}' reports a polygenic tendency ({label}); this is a "
            f"probabilistic signal, not a clinical finding."
        )
        builder.add_contribution(
            source="nebula",
            metric=f"trait:{name}",
            value=label,
            score=None,  # genomic context informs, but does not move the score
            weight=0.05,
            grade=grade,
        )
        if row["citation"]:
            builder.add_evidence(
                EvidenceRef(
                    claim=f"Genomic association for '{name}'",
                    grade=grade,
                    source="nebula",
                    title=str(row["citation"])[:300],
                    pmid=None,
                    year=None,
                    url=None,
                )
            )


def consult_clause(strong: bool = False) -> str:
    """Standard professional-consultation recommendation text."""
    if strong:
        return (
            "If concerning patterns persist, consider consulting a qualified "
            "healthcare professional; a clinical test would be required to evaluate this directly."
        )
    return "Consider professional consultation if the pattern persists or worsens."
