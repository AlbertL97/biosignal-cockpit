"""Tests for the ingestion parsers using small crafted fixtures."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.ingestion import apple_health, gpx, vcf
from app.ingestion.apple_health import parse_hk_datetime
from app.ingestion.nebula_reports import _parse_filename, _parse_variant_row
from app.ingestion.vcf import _genotype_from_gt


def test_parse_hk_datetime() -> None:
    iso = parse_hk_datetime("2024-01-01 08:00:00 +0200")
    assert iso is not None
    assert iso.startswith("2024-01-01T08:00:00")
    assert parse_hk_datetime(None) is None
    # Unparseable falls back to raw.
    assert parse_hk_datetime("garbage") == "garbage"


def test_apple_health_ingest(conn: sqlite3.Connection, mini_xml: Path) -> None:
    counts = apple_health.ingest_apple_health(conn, mini_xml)
    assert counts["measurements"] == 3  # 2 HR + 1 steps
    assert counts["sleep_segments"] == 1
    assert counts["workouts"] == 1
    # 1 nutrition day x 1 metric (protein aggregated)
    assert counts["nutrition_daily"] == 1

    # protein aggregated 20 + 30 = 50
    row = conn.execute(
        "SELECT value FROM nutrition_daily WHERE metric='protein'"
    ).fetchone()
    assert row["value"] == 50.0

    # profile captured from <Me>
    sex = conn.execute(
        "SELECT value FROM profile WHERE key='biological_sex'"
    ).fetchone()
    assert sex["value"] == "HKBiologicalSexMale"

    # workout duration normalised to seconds, energy from WorkoutStatistics
    w = conn.execute("SELECT duration_s, energy_kcal FROM workouts").fetchone()
    assert w["duration_s"] == 1800.0
    assert w["energy_kcal"] == 90.0

    # audit logged
    n = conn.execute(
        "SELECT COUNT(*) AS c FROM audit_log WHERE event='ingest.apple_health'"
    ).fetchone()
    assert n["c"] == 1


def test_genotype_from_gt() -> None:
    assert _genotype_from_gt("0/1", "C", "T") == "CT"
    assert _genotype_from_gt("1/1", "T", "A") == "AA"
    assert _genotype_from_gt("0|0", "G", "A") == "GG"
    assert _genotype_from_gt("./.", "C", "T") is None
    # multi-allelic
    assert _genotype_from_gt("1/2", "C", "T,G") == "TG"


def test_vcf_ingest_filters_to_targets(
    conn: sqlite3.Connection, mini_vcf: Path
) -> None:
    wanted = {"rs55998931", "rs1801133"}  # rs707680 excluded, rs-less row excluded
    counts = vcf.ingest_vcf(conn, mini_vcf, wanted=wanted)
    assert counts["variants"] == 2
    assert counts["targeted"] == 2

    geno = vcf.lookup_genotype(conn, "rs1801133")
    assert geno == "GA"
    # not requested
    assert vcf.lookup_genotype(conn, "rs707680") is None


def test_vcf_empty_target_set(conn: sqlite3.Connection, mini_vcf: Path) -> None:
    counts = vcf.ingest_vcf(conn, mini_vcf, wanted=set())
    assert counts["variants"] == 0


def test_gpx_ingest(conn: sqlite3.Connection, mini_gpx_dir: Path) -> None:
    counts = gpx.ingest_gpx(conn, mini_gpx_dir)
    assert counts["routes"] == 1
    row = conn.execute(
        "SELECT activity_type, source, duration_s FROM workouts "
        "WHERE activity_type='GPXRoute'"
    ).fetchone()
    assert row is not None
    assert row["source"] == "Test Route"
    assert row["duration_s"] == 600.0  # 10 minutes


def test_nebula_filename_parse() -> None:
    trait, citation = _parse_filename(Path("Heart rate variability (Tegegne, 2023).pdf"))
    assert trait == "Heart rate variability"
    assert citation == "Tegegne, 2023"
    # no parenthetical citation
    t2, c2 = _parse_filename(Path("Pain susceptibility.pdf"))
    assert t2 == "Pain susceptibility"
    assert c2 is None


def test_nebula_variant_row_parse() -> None:
    row = _parse_variant_row(["rs1801133", "MTHFR", "AG", "0.12", "0.30", "5e-8"])
    assert row is not None
    assert row["rsid"] == "rs1801133"
    assert row["genotype"] == "AG"
    assert row["gene"] == "MTHFR"
    assert row["p_value"] is not None
    # non-variant row returns None
    assert _parse_variant_row(["some", "header", "text"]) is None
