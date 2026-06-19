"""Streaming parser for the Apple Health export (``eksport.xml``, ~173 MB).

The file is streamed with :func:`lxml.etree.iterparse` and elements are cleared
immediately after use so the whole document is never held in memory
(ARCHITECTURE §4). HealthKit identifiers are mapped to canonical metric keys and
written to the ``measurements``, ``sleep_segments``, ``workouts``,
``nutrition_daily`` and ``profile`` tables.

Public entry point: :func:`ingest_apple_health`.
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from lxml import etree

from app.config import APPLE_HEALTH_XML
from app.storage import db

# --- HealthKit identifier -> canonical metric key -------------------------------
# Quantity types we keep (ARCHITECTURE §4). Anything not listed is ignored except
# Dietary* (handled separately) and SleepAnalysis (category).
_QUANTITY_PREFIX = "HKQuantityTypeIdentifier"
_CATEGORY_PREFIX = "HKCategoryTypeIdentifier"

HK_QUANTITY_METRICS: dict[str, str] = {
    "HeartRate": "heart_rate",
    "RestingHeartRate": "resting_heart_rate",
    "WalkingHeartRateAverage": "walking_heart_rate_avg",
    "HeartRateVariabilitySDNN": "hrv_sdnn",
    "OxygenSaturation": "oxygen_saturation",
    "RespiratoryRate": "respiratory_rate",
    "VO2Max": "vo2max",
    "BodyMass": "body_mass",
    "BodyMassIndex": "bmi",
    "BodyFatPercentage": "body_fat_pct",
    "Height": "height",
    "StepCount": "step_count",
    "DistanceWalkingRunning": "distance_walking_running",
    "ActiveEnergyBurned": "active_energy",
    "BasalEnergyBurned": "basal_energy",
    "AppleExerciseTime": "exercise_time",
    "AppleStandTime": "stand_time",
    "FlightsClimbed": "flights_climbed",
    "WalkingSpeed": "walking_speed",
    "WalkingStepLength": "walking_step_length",
    "WalkingAsymmetryPercentage": "walking_asymmetry_pct",
    "WalkingDoubleSupportPercentage": "walking_double_support_pct",
    "AppleWalkingSteadiness": "walking_steadiness",
    "StairAscentSpeed": "stair_ascent_speed",
    "StairDescentSpeed": "stair_descent_speed",
    "SixMinuteWalkTestDistance": "six_minute_walk_distance",
    "PhysicalEffort": "physical_effort",
    "TimeInDaylight": "time_in_daylight",
    "EnvironmentalAudioExposure": "environmental_audio_exposure",
    "HeadphoneAudioExposure": "headphone_audio_exposure",
    "AppleSleepingWristTemperature": "sleeping_wrist_temperature",
}

# Dietary metrics aggregated daily into nutrition_daily.
HK_DIETARY_METRICS: dict[str, str] = {
    "DietaryEnergyConsumed": "energy",
    "DietaryProtein": "protein",
    "DietaryCarbohydrates": "carbohydrates",
    "DietaryFatTotal": "fat_total",
    "DietaryFatSaturated": "fat_saturated",
    "DietaryFatMonounsaturated": "fat_mono",
    "DietaryFatPolyunsaturated": "fat_poly",
    "DietarySugar": "sugar",
    "DietaryFiber": "fiber",
    "DietarySodium": "sodium",
    "DietaryPotassium": "potassium",
    "DietaryCalcium": "calcium",
    "DietaryMagnesium": "magnesium",
    "DietaryIron": "iron",
    "DietaryZinc": "zinc",
    "DietaryVitaminA": "vitamin_a",
    "DietaryVitaminC": "vitamin_c",
    "DietaryVitaminD": "vitamin_d",
    "DietaryVitaminE": "vitamin_e",
    "DietaryVitaminK": "vitamin_k",
    "DietaryFolate": "folate",
    "DietaryWater": "water",
    "DietaryCholesterol": "cholesterol",
    "DietaryCaffeine": "caffeine",
}

# SleepAnalysis category values -> canonical stage.
SLEEP_STAGES: dict[str, str] = {
    "HKCategoryValueSleepAnalysisInBed": "inBed",
    "HKCategoryValueSleepAnalysisAsleepUnspecified": "asleep",
    "HKCategoryValueSleepAnalysisAsleep": "asleep",
    "HKCategoryValueSleepAnalysisAsleepCore": "asleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep": "asleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM": "asleepREM",
    "HKCategoryValueSleepAnalysisAwake": "awake",
}

_PROFILE_KEYS = {
    "HKCharacteristicTypeIdentifierDateOfBirth": "dob",
    "HKCharacteristicTypeIdentifierBiologicalSex": "biological_sex",
    "HKCharacteristicTypeIdentifierBloodType": "blood_type",
    "HKCharacteristicTypeIdentifierFitzpatrickSkinType": "skin_type",
}


def parse_hk_datetime(raw: str | None) -> str | None:
    """Normalise an Apple Health timestamp to ISO 8601.

    Apple emits ``"YYYY-MM-DD HH:MM:SS +ZZZZ"``. Returns the ISO 8601 form, or
    the raw string if it cannot be parsed, or ``None`` if empty.
    """
    if not raw:
        return None
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S %z")
        return dt.isoformat()
    except ValueError:
        return raw


def _day(ts_iso: str | None) -> str | None:
    """Return the ``YYYY-MM-DD`` date from an ISO timestamp."""
    if not ts_iso:
        return None
    return ts_iso[:10]


def _to_float(value: str | None) -> float | None:
    """Best-effort float conversion; ``None`` on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def iter_records(xml_path: str | Path) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(kind, attrs)`` tuples streamed from the export file.

    ``kind`` is one of ``"ExportDate"``, ``"Me"``, ``"Record"``, ``"Workout"``.
    Each element is cleared (and prior siblings dropped) right after it is
    yielded to bound memory use.

    Args:
        xml_path: Path to the Apple Health export XML.

    Yields:
        Tuples of element kind and its attribute dict.
    """
    tags = ("ExportDate", "Me", "Record", "Workout")
    context = etree.iterparse(str(xml_path), events=("end",), tag=tags, recover=True)
    for _event, elem in context:
        kind = etree.QName(elem).localname if elem.tag is not None else str(elem.tag)
        attrs = dict(elem.attrib)
        if kind == "Workout":
            # capture the energy/distance from child WorkoutStatistics
            for child in elem:
                cl = etree.QName(child).localname
                if cl == "WorkoutStatistics":
                    ctype = child.get("type", "")
                    if ctype.endswith("ActiveEnergyBurned"):
                        attrs["_energy_kcal"] = child.get("sum")
                    elif ctype.endswith("DistanceWalkingRunning"):
                        attrs["_distance_m"] = child.get("sum")
        yield kind, attrs
        # Free memory: clear element and any now-unneeded previous siblings.
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
    del context


def ingest_apple_health(
    conn: sqlite3.Connection,
    xml_path: str | Path | None = None,
    *,
    flush_every: int = 5000,
) -> dict[str, int]:
    """Stream the export and populate the Apple Health tables.

    Args:
        conn: Open SQLite connection (caller owns the transaction; this commits
            periodically to bound the WAL).
        xml_path: Override export path; defaults to
            :data:`app.config.APPLE_HEALTH_XML`.
        flush_every: Commit cadence for the measurements stream.

    Returns:
        Counts keyed by ``measurements``, ``sleep_segments``, ``workouts``,
        ``nutrition_daily``, ``profile``.
    """
    path = Path(xml_path) if xml_path is not None else APPLE_HEALTH_XML
    counts = {
        "measurements": 0,
        "sleep_segments": 0,
        "workouts": 0,
        "nutrition_daily": 0,
        "profile": 0,
    }
    # nutrition aggregation: (date, metric) -> [sum, unit]
    nutrition: dict[tuple[str, str], list[Any]] = defaultdict(lambda: [0.0, None])
    profile: dict[str, str] = {}
    meas_buf: list[dict[str, Any]] = []
    sleep_buf: list[dict[str, Any]] = []
    workout_buf: list[dict[str, Any]] = []

    def flush_meas() -> None:
        nonlocal meas_buf
        if meas_buf:
            counts["measurements"] += db.bulk_insert(conn, "measurements", meas_buf)
            meas_buf = []
            conn.commit()

    for kind, a in iter_records(path):
        if kind == "ExportDate":
            profile["export_date"] = parse_hk_datetime(a.get("value")) or ""
        elif kind == "Me":
            for hk_key, pkey in _PROFILE_KEYS.items():
                if hk_key in a:
                    profile[pkey] = a[hk_key]
        elif kind == "Record":
            rtype = a.get("type", "")
            if rtype == f"{_CATEGORY_PREFIX}SleepAnalysis":
                sleep_buf.append(
                    {
                        "stage": SLEEP_STAGES.get(a.get("value", ""), a.get("value")),
                        "start_ts": parse_hk_datetime(a.get("startDate")),
                        "end_ts": parse_hk_datetime(a.get("endDate")),
                        "source": a.get("sourceName"),
                    }
                )
                if len(sleep_buf) >= flush_every:
                    counts["sleep_segments"] += db.bulk_insert(
                        conn, "sleep_segments", sleep_buf
                    )
                    sleep_buf = []
            elif rtype.startswith(_QUANTITY_PREFIX):
                short = rtype[len(_QUANTITY_PREFIX) :]
                if short in HK_DIETARY_METRICS:
                    day = _day(parse_hk_datetime(a.get("startDate")))
                    val = _to_float(a.get("value"))
                    if day and val is not None:
                        key = (day, HK_DIETARY_METRICS[short])
                        nutrition[key][0] += val
                        nutrition[key][1] = a.get("unit")
                elif short in HK_QUANTITY_METRICS:
                    meas_buf.append(
                        {
                            "metric": HK_QUANTITY_METRICS[short],
                            "unit": a.get("unit"),
                            "value": _to_float(a.get("value")),
                            "start_ts": parse_hk_datetime(a.get("startDate")),
                            "end_ts": parse_hk_datetime(a.get("endDate")),
                            "source": a.get("sourceName"),
                            "device": a.get("device"),
                            "raw_type": rtype,
                        }
                    )
                    if len(meas_buf) >= flush_every:
                        flush_meas()
        elif kind == "Workout":
            start = parse_hk_datetime(a.get("startDate"))
            end = parse_hk_datetime(a.get("endDate"))
            dur = _to_float(a.get("duration"))
            if dur is not None and a.get("durationUnit") == "min":
                dur *= 60.0
            workout_buf.append(
                {
                    "activity_type": (a.get("workoutActivityType") or "")
                    .replace("HKWorkoutActivityType", ""),
                    "start_ts": start,
                    "end_ts": end,
                    "duration_s": dur,
                    "energy_kcal": _to_float(a.get("_energy_kcal"))
                    or _to_float(a.get("totalEnergyBurned")),
                    "distance_m": _to_float(a.get("_distance_m"))
                    or _to_float(a.get("totalDistance")),
                    "source": a.get("sourceName"),
                }
            )

    # Final flushes.
    flush_meas()
    if sleep_buf:
        counts["sleep_segments"] += db.bulk_insert(conn, "sleep_segments", sleep_buf)
    if workout_buf:
        counts["workouts"] += db.bulk_insert(conn, "workouts", workout_buf)

    nutrition_rows = [
        {"date": d, "metric": m, "value": round(v[0], 4), "unit": v[1]}
        for (d, m), v in nutrition.items()
    ]
    if nutrition_rows:
        counts["nutrition_daily"] += db.bulk_insert(
            conn, "nutrition_daily", nutrition_rows, or_replace=True
        )

    profile_rows = [{"key": k, "value": v} for k, v in profile.items()]
    if profile_rows:
        counts["profile"] += db.bulk_insert(
            conn, "profile", profile_rows, or_replace=True
        )

    conn.commit()
    db.audit(conn, "ingest.apple_health", str(counts))
    conn.commit()
    return counts
