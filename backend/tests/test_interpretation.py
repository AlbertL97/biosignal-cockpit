"""Tests for the interpretation layer.

Builds a tiny in-memory SQLite database seeded with synthetic rows matching
``app/storage/schema.sql``, then asserts each domain's ``compute`` returns a
contract-valid ``DomainStatus``, honours the insufficient-data rule, and that
the safety filter blocks banned diagnostic phrasing.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.interpretation import engine, safety, scoring
from app.interpretation.context import DataContext
from app.models.contracts import (
    Confidence,
    DomainStatus,
    EvidenceGrade,
    Trend,
)

SCHEMA = Path(__file__).resolve().parents[1] / "app" / "storage" / "schema.sql"


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _new_db() -> sqlite3.Connection:
    """Create an in-memory DB with the production schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn


def _seed_full(conn: sqlite3.Connection) -> None:
    """Seed a realistic, multi-source dataset across ~60 days."""
    now = datetime(2026, 6, 17, 12, 0, 0)
    meas: list[tuple] = []
    sleep: list[tuple] = []
    nutri: list[tuple] = []
    workouts: list[tuple] = []

    for d in range(60):
        ts = now - timedelta(days=d)
        iso = ts.isoformat()
        meas.append(("HeartRateVariabilitySDNN", "ms", 55 + (d % 5), iso, iso, "Watch", "W", "HKx"))
        meas.append(("RestingHeartRate", "bpm", 52 + (d % 3), iso, iso, "Watch", "W", "HKx"))
        meas.append(("StepCount", "count", 9000 + (d % 7) * 200, iso, iso, "Phone", "P", "HKx"))
        meas.append(("ActiveEnergyBurned", "kcal", 600 + (d % 4) * 30, iso, iso, "Watch", "W", "HKx"))
        meas.append(("BasalEnergyBurned", "kcal", 1700, iso, iso, "Watch", "W", "HKx"))
        meas.append(("BodyMass", "kg", 78 - d * 0.01, iso, iso, "Scale", "S", "HKx"))
        meas.append(("OxygenSaturation", "%", 97, iso, iso, "Watch", "W", "HKx"))
        meas.append(("WalkingAsymmetryPercentage", "%", 1.5, iso, iso, "Phone", "P", "HKx"))
        meas.append(("TimeInDaylight", "min", 90, iso, iso, "Watch", "W", "HKx"))

        # Sleep segments: a core + deep + rem block per night.
        night = ts - timedelta(hours=8)
        sleep.append(("asleepCore", night.isoformat(), (night + timedelta(hours=5)).isoformat(), "Watch"))
        sleep.append(("asleepDeep", (night + timedelta(hours=5)).isoformat(),
                      (night + timedelta(hours=6, minutes=30)).isoformat(), "Watch"))
        sleep.append(("asleepREM", (night + timedelta(hours=6, minutes=30)).isoformat(),
                      (night + timedelta(hours=7, minutes=30)).isoformat(), "Watch"))

        date = ts.date().isoformat()
        nutri.append((date, "DietaryFiber", 28 + (d % 4), "g"))
        nutri.append((date, "DietarySugar", 45 + (d % 6), "g"))
        nutri.append((date, "DietaryProtein", 120 + (d % 5), "g"))
        nutri.append((date, "DietaryCarbohydrates", 250, "g"))
        nutri.append((date, "DietaryEnergyConsumed", 2300, "kcal"))
        nutri.append((date, "DietaryWater", 2400, "mL"))
        nutri.append((date, "DietaryVitaminC", 95, "mg"))
        nutri.append((date, "DietaryZinc", 12, "mg"))

        if d % 3 == 0:
            workouts.append(("FunctionalStrengthTraining", iso,
                             (ts + timedelta(minutes=50)).isoformat(), 3000, 450, 0, "Watch"))

    conn.executemany(
        "INSERT INTO measurements (metric,unit,value,start_ts,end_ts,source,device,raw_type) "
        "VALUES (?,?,?,?,?,?,?,?)", meas)
    conn.executemany(
        "INSERT INTO sleep_segments (stage,start_ts,end_ts,source) VALUES (?,?,?,?)", sleep)
    conn.executemany(
        "INSERT INTO nutrition_daily (date,metric,value,unit) VALUES (?,?,?,?)", nutri)
    conn.executemany(
        "INSERT INTO workouts (activity_type,start_ts,end_ts,duration_s,energy_kcal,distance_m,source) "
        "VALUES (?,?,?,?,?,?,?)", workouts)

    # Baselines.
    for metric, mean, sd in [("HeartRateVariabilitySDNN", 55, 6), ("RestingHeartRate", 53, 3)]:
        conn.execute(
            "INSERT INTO baselines (metric,mean,sd,n,window_days,computed_ts) VALUES (?,?,?,?,?,?)",
            (metric, mean, sd, 60, 90, now.isoformat()))

    # Genome + Nebula context.
    conn.execute(
        "INSERT INTO genome_variants (rsid,chrom,pos,ref,alt,genotype,gene,source) "
        "VALUES (?,?,?,?,?,?,?,?)", ("rs1815739", "11", 66560624, "C", "T", "CT", "ACTN3", "vcf"))
    conn.execute(
        "INSERT INTO nebula_traits (id,trait,category,citation,percentile,score,score_label,pdf_path) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (1, "VO2 max trainability", "cardiovascular", "Smith 2020", 60, 0.6, "average", "x.pdf"))
    conn.execute(
        "INSERT INTO nebula_traits (id,trait,category,citation,percentile,score,score_label,pdf_path) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (2, "Muscle power (ACTN3)", "fitness", "Jones 2019", 50, 0.5, "intermediate", "y.pdf"))
    conn.execute(
        "INSERT INTO nebula_traits (id,trait,category,citation,percentile,score,score_label,pdf_path) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (3, "IBS predisposition", "gut", "Lee 2021", 40, 0.4, "lower", "z.pdf"))
    conn.commit()


@pytest.fixture()
def full_ctx() -> DataContext:
    """DataContext over a fully seeded in-memory DB."""
    conn = _new_db()
    _seed_full(conn)
    return DataContext(conn=conn, now=datetime(2026, 6, 17, 12, 0, 0))


@pytest.fixture()
def empty_ctx() -> DataContext:
    """DataContext over an empty (schema-only) in-memory DB."""
    conn = _new_db()
    return DataContext(conn=conn, now=datetime(2026, 6, 17, 12, 0, 0))


# --------------------------------------------------------------------------- #
# Domain contract tests
# --------------------------------------------------------------------------- #


def test_run_all_returns_all_domains(full_ctx: DataContext) -> None:
    results = engine.run_all(full_ctx)
    assert len(results) == len(engine.DOMAINS)
    assert {r.domain for r in results} == set(engine.DOMAINS)


@pytest.mark.parametrize("domain", list(engine.DOMAIN_REGISTRY))
def test_domain_contract_valid(full_ctx: DataContext, domain: str) -> None:
    status = engine.run_one(full_ctx, domain)
    assert isinstance(status, DomainStatus)
    # Contract enums.
    assert isinstance(status.confidence, Confidence)
    assert isinstance(status.evidence_grade, EvidenceGrade)
    assert isinstance(status.trend, Trend)
    # Score bounds.
    if status.score is not None:
        assert 0.0 <= status.score <= 100.0
    # All five layers present as lists.
    for layer in (status.observations, status.derived, status.inferences,
                  status.hypotheses, status.recommendations):
        assert isinstance(layer, list)
    # Contribution weights are valid 0..1.
    for c in status.contributions:
        assert 0.0 <= c.weight <= 1.0
        assert c.direction in {"supportive", "adverse", "neutral", "uncertain"}


def test_full_data_produces_scores(full_ctx: DataContext) -> None:
    results = engine.run_all(full_ctx)
    scored = [r for r in results if r.score is not None]
    # With rich data most domains should produce a numeric score.
    assert len(scored) >= 7
    for r in scored:
        assert r.score_label != "insufficient data"
        assert r.contributions


def test_nebula_mapped_into_genetic_context(full_ctx: DataContext) -> None:
    cardio = engine.run_one(full_ctx, "cardiovascular")
    sources = {c.source for c in cardio.contributions}
    assert "nebula" in sources
    assert any("non-deterministic" in h.lower() or "research-only" in h.lower()
               for h in cardio.hypotheses)


# --------------------------------------------------------------------------- #
# Insufficient-data behaviour
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("domain", list(engine.DOMAIN_REGISTRY))
def test_insufficient_data_when_empty(empty_ctx: DataContext, domain: str) -> None:
    status = engine.run_one(empty_ctx, domain)
    assert status.score is None
    assert status.score_label == "insufficient data"
    assert status.confidence == Confidence.exploratory
    assert status.missing_data
    assert "do not allow a direct conclusion" in status.summary


# --------------------------------------------------------------------------- #
# Safety filter
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("banned", [
    "You have a serious gut disease.",
    "This proves your heart is failing.",
    "Your gut is unhealthy and needs help.",
    "Your genome means you will develop this.",
    "This diagnosis indicates a problem.",
    "This supplement will fix your immune system.",
])
def test_safety_rewrites_banned_phrases(banned: str) -> None:
    res = safety.sanitize(banned)
    assert res.changed
    assert not safety.contains_banned(res.text)


def test_safety_preserves_safe_text() -> None:
    safe = "The current pattern may be consistent with reduced recovery."
    res = safety.sanitize(safe)
    assert not res.changed
    assert res.text == safe


def test_engine_strips_banned_text(full_ctx: DataContext) -> None:
    status = engine.run_one(full_ctx, "gut")
    blob = " ".join(
        [status.summary, *status.observations, *status.derived, *status.inferences,
         *status.hypotheses, *status.recommendations]
        + [e.claim for e in status.evidence]
    )
    assert not safety.contains_banned(blob)


def test_apply_safety_flags_in_missing_data() -> None:
    bad = DomainStatus(
        domain="gut", score=50.0, score_label="watch", trend=Trend.unknown,
        confidence=Confidence.low, evidence_grade=EvidenceGrade.low,
        summary="You have a problem.", recommendations=["This supplement will fix it."],
        as_of=datetime(2026, 6, 17),
    )
    cleaned = engine.apply_safety(bad)
    assert not safety.contains_banned(cleaned.summary)
    assert any("safety filter" in m for m in cleaned.missing_data)


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #


def test_persist_and_load_cached(full_ctx: DataContext) -> None:
    status = engine.run_one(full_ctx, "metabolic", persist=True)
    cached = engine.load_cached(full_ctx, "metabolic")
    assert cached is not None
    assert cached.domain == status.domain
    assert cached.score == status.score


# --------------------------------------------------------------------------- #
# Scoring helpers
# --------------------------------------------------------------------------- #


def test_normalize_signal_baseline_midpoint() -> None:
    assert scoring.normalize_signal(55, 55, 6) == pytest.approx(50.0)
    assert scoring.normalize_signal(None, 55, 6) is None


def test_combine_weighted_handles_empty() -> None:
    assert scoring.combine_weighted([]) is None
    assert scoring.combine_weighted([(80.0, 1.0), (40.0, 1.0)]) == pytest.approx(60.0)


def test_derive_trend_directions() -> None:
    rising = [(float(i), float(i)) for i in range(10)]
    assert scoring.derive_trend(rising, higher_is_better=True) == Trend.improving
    assert scoring.derive_trend(rising, higher_is_better=False) == Trend.declining
    assert scoring.derive_trend([(0.0, 1.0)]) == Trend.unknown


def test_derive_confidence_buckets() -> None:
    assert scoring.derive_confidence(1.0, 1.0, 1.0) == Confidence.high
    assert scoring.derive_confidence(0.1, 0.1, 0.1) == Confidence.exploratory


def test_api_imports_cleanly() -> None:
    import app.interpretation.api as api  # noqa: PLC0415

    assert api.router is not None
