"""Shared Pydantic contract types. ALL agents import from here — do not redefine.

See docs/ARCHITECTURE.md §6–§7. These mirror the TypeScript types in
frontend/src/api/types.ts; keep both in sync.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    high = "high"
    moderate = "moderate"
    low = "low"
    exploratory = "exploratory"


class EvidenceGrade(str, Enum):
    high = "high"
    moderate = "moderate"
    low = "low"
    exploratory = "exploratory"
    unsupported = "unsupported"


class Trend(str, Enum):
    improving = "improving"
    stable = "stable"
    declining = "declining"
    unknown = "unknown"


class Contribution(BaseModel):
    source: str  # apple_health | genome | nebula | nutrition
    metric: str
    value: float | str | None = None
    weight: float = Field(ge=0, le=1)
    direction: str  # supportive | adverse | neutral | uncertain


class Driver(BaseModel):
    """A factor currently pushing a domain score up or down."""

    factor: str
    direction: str  # "raising" | "lowering" | "neutral"
    detail: str


class EvidenceRef(BaseModel):
    claim: str
    grade: EvidenceGrade
    pmid: str | None = None
    title: str | None = None
    year: int | None = None
    url: str | None = None
    source: str  # pubmed | nebula | guideline | curated


class DomainStatus(BaseModel):
    domain: str
    score: float | None = None  # 0..100
    score_label: str
    trend: Trend = Trend.unknown
    confidence: Confidence
    evidence_grade: EvidenceGrade
    summary: str
    observations: list[str] = []
    derived: list[str] = []
    inferences: list[str] = []
    hypotheses: list[str] = []
    recommendations: list[str] = []
    contributions: list[Contribution] = []
    evidence: list[EvidenceRef] = []
    missing_data: list[str] = []
    # What is currently raising/lowering this score (derived from contributions)
    drivers: list[Driver] = []
    # Evidence-informed, non-clinical levers that may improve this score
    levers: list[str] = []
    as_of: datetime


class TimePoint(BaseModel):
    ts: datetime
    value: float


class MetricSeries(BaseModel):
    metric: str
    unit: str | None = None
    points: list[TimePoint] = []
    baseline_mean: float | None = None
    baseline_sd: float | None = None


class TraitVariant(BaseModel):
    rsid: str
    genotype: str | None = None
    gene: str | None = None
    effect_size: float | None = None
    frequency: float | None = None
    p_value: float | None = None
    highlighted: bool = False


class NebulaTrait(BaseModel):
    id: int
    trait: str
    category: str | None = None
    citation: str | None = None
    percentile: float | None = None
    score: float | None = None
    score_label: str | None = None
    variants: list[TraitVariant] = []
    description: str | None = None     # what this trait/measure is
    interpretation: str | None = None  # what this percentile means (non-deterministic)


class Highlight(BaseModel):
    """A current, human-readable headline metric (real value + unit)."""

    label: str
    value: str  # preformatted, e.g. "54 bpm"
    detail: str | None = None


class Profile(BaseModel):
    dob: str | None = None
    biological_sex: str | None = None
    blood_type: str | None = None
    skin_type: str | None = None
    coverage: dict[str, int] = {}  # metric -> record count (raw; UI prefers highlights)
    highlights: list[Highlight] = []  # current key metrics with real values
