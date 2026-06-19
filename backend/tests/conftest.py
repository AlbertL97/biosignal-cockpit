"""Shared pytest fixtures: an isolated in-file SQLite DB and small sample data.

Tests never touch the real 173 MB / 1.1 GB source files; they use crafted
mini-fixtures written to a temp dir, and a temp database initialised from the
real ``schema.sql``.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.storage import db


@pytest.fixture()
def temp_db(tmp_path: Path) -> Iterator[Path]:
    """Create a fresh SQLite DB from schema.sql in a temp dir; yield its path."""
    path = tmp_path / "test.sqlite"
    db.init_db(path)
    yield path


@pytest.fixture()
def conn(temp_db: Path):
    """Yield an open connection to the temp DB (committed/closed on teardown)."""
    c = db.get_conn(temp_db)
    try:
        yield c
        c.commit()
    finally:
        c.close()


# --- Crafted sample source files ------------------------------------------------

MINI_HEALTH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="pl_PL">
 <ExportDate value="2026-06-16 13:05:01 +0200"/>
 <Me HKCharacteristicTypeIdentifierDateOfBirth="1997-07-14" HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexMale" HKCharacteristicTypeIdentifierBloodType="HKBloodTypeNotSet" HKCharacteristicTypeIdentifierFitzpatrickSkinType="HKFitzpatrickSkinTypeNotSet"/>
 <Record type="HKQuantityTypeIdentifierHeartRate" sourceName="Apple Watch" unit="count/min" startDate="2024-01-01 08:00:00 +0200" endDate="2024-01-01 08:00:00 +0200" value="62"/>
 <Record type="HKQuantityTypeIdentifierHeartRate" sourceName="Apple Watch" unit="count/min" startDate="2024-01-02 08:00:00 +0200" endDate="2024-01-02 08:00:00 +0200" value="65"/>
 <Record type="HKQuantityTypeIdentifierStepCount" sourceName="iPhone" unit="count" startDate="2024-01-01 09:00:00 +0200" endDate="2024-01-01 09:10:00 +0200" value="1200"/>
 <Record type="HKQuantityTypeIdentifierDietaryProtein" sourceName="Yazio" unit="g" startDate="2024-01-01 12:00:00 +0200" endDate="2024-01-01 12:00:00 +0200" value="20">
  <MetadataEntry key="HKFoodType" value="Eggs"/>
 </Record>
 <Record type="HKQuantityTypeIdentifierDietaryProtein" sourceName="Yazio" unit="g" startDate="2024-01-01 18:00:00 +0200" endDate="2024-01-01 18:00:00 +0200" value="30"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="iPhone" startDate="2024-01-01 23:00:00 +0200" endDate="2024-01-02 06:30:00 +0200" value="HKCategoryValueSleepAnalysisAsleepCore"/>
 <Workout workoutActivityType="HKWorkoutActivityTypeHighIntensityIntervalTraining" duration="30" durationUnit="min" sourceName="Nike Training" startDate="2024-01-01 13:00:00 +0200" endDate="2024-01-01 13:30:00 +0200">
  <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned" startDate="2024-01-01 13:00:00 +0200" endDate="2024-01-01 13:30:00 +0200" sum="90" unit="kcal"/>
 </Workout>
</HealthData>
"""

MINI_VCF = """##fileformat=VCFv4.2
##FILTER=<ID=LowQual,Description="Low quality">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE
chr1\t10492\trs55998931\tC\tT\t36.77\t.\tAC=1\tGT:AD:DP\t0/1:13,3:16
chr1\t14599\trs707680\tT\tA\t62.74\t.\tAC=2\tGT:AD:DP\t1/1:0,2:2
chr1\t99999\trs1801133\tG\tA\t99.0\t.\tAC=1\tGT:AD:DP\t0/1:5,5:10
chr2\t12345\t.\tC\tG\t50.0\t.\tAC=2\tGT:AD:DP\t1/1:0,4:4
"""

MINI_GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
 <trk><name>Test Route</name><trkseg>
  <trkpt lon="22.5610" lat="51.2389"><ele>180.0</ele><time>2024-01-01T15:00:00Z</time></trkpt>
  <trkpt lon="22.5620" lat="51.2399"><ele>185.0</ele><time>2024-01-01T15:05:00Z</time></trkpt>
  <trkpt lon="22.5630" lat="51.2409"><ele>182.0</ele><time>2024-01-01T15:10:00Z</time></trkpt>
 </trkseg></trk>
</gpx>
"""


@pytest.fixture()
def mini_xml(tmp_path: Path) -> Path:
    """Write a small Apple Health export and return its path."""
    p = tmp_path / "mini_health.xml"
    p.write_text(MINI_HEALTH_XML, encoding="utf-8")
    return p


@pytest.fixture()
def mini_vcf(tmp_path: Path) -> Path:
    """Write a small VCF and return its path."""
    p = tmp_path / "mini.vcf"
    p.write_text(MINI_VCF, encoding="utf-8")
    return p


@pytest.fixture()
def mini_gpx_dir(tmp_path: Path) -> Path:
    """Write a small GPX file into a routes dir and return the dir."""
    d = tmp_path / "routes"
    d.mkdir()
    (d / "test.gpx").write_text(MINI_GPX, encoding="utf-8")
    return d
