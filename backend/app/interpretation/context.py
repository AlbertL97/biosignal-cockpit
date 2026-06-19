"""DataContext: decoupled, read-only access to the health SQLite database.

This module deliberately talks to the schema (``app/storage/schema.sql``) via
plain ``sqlite3`` rather than depending on the backend agent's Python helpers,
so the interpretation layer stays decoupled. Every accessor tolerates missing
or empty tables and returns ``None`` / empty collections instead of raising.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from app.config import DB_PATH


def _connect(db_path: str) -> sqlite3.Connection:
    """Open a read-only-ish connection with row access by column name."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    """Return whether ``name`` exists as a table in the database."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


# Interpretation modules reference HK-style metric names (per ARCHITECTURE.md §4);
# the ingestion layer stores snake_case keys. This bridges the two so neither side
# had to change. Unknown names pass through unchanged.
_ALIAS: dict[str, str] = {
    # measurements
    "HeartRate": "heart_rate",
    "RestingHeartRate": "resting_heart_rate",
    "WalkingHeartRateAverage": "walking_heart_rate_avg",
    "HeartRateVariabilitySDNN": "hrv_sdnn",
    "OxygenSaturation": "oxygen_saturation",
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
    "BodyMass": "body_mass",
    "VO2Max": "vo2max",
    "VO2max": "vo2max",
    "Height": "height",
    # nutrition (nutrition_daily)
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
    "DietaryWater": "water",
    "DietaryCholesterol": "cholesterol",
    "DietaryVitaminA": "vitamin_a",
    "DietaryVitaminC": "vitamin_c",
    "DietaryVitaminD": "vitamin_d",
    "DietaryVitaminE": "vitamin_e",
    "DietaryVitaminK": "vitamin_k",
    "DietaryFolate": "folate",
}


def _alias(metric: str) -> str:
    """Map an interpretation metric name to the stored key (identity if unknown)."""
    return _ALIAS.get(metric, metric)


@dataclass
class BaselineStat:
    """A within-person baseline for one metric."""

    metric: str
    mean: float | None
    sd: float | None
    n: int | None


class DataContext:
    """Convenience accessors over the health database for domain modules.

    Construct with a path (defaults to ``config.DB_PATH``) or an existing
    :class:`sqlite3.Connection` (used by tests with in-memory databases).
    """

    def __init__(
        self,
        db_path: str | None = None,
        conn: sqlite3.Connection | None = None,
        now: datetime | None = None,
    ) -> None:
        self._owns_conn = conn is None
        self._conn = conn if conn is not None else _connect(str(db_path or DB_PATH))
        self._conn.row_factory = sqlite3.Row
        self.now = now or datetime.now()

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        """Close the connection if this context owns it."""
        if self._owns_conn:
            self._conn.close()

    def __enter__(self) -> DataContext:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- low-level ---------------------------------------------------------

    def _has(self, table: str) -> bool:
        return _table_exists(self._conn, table)

    def _query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Run a query, returning ``[]`` if the underlying table is missing."""
        try:
            return list(self._conn.execute(sql, params).fetchall())
        except sqlite3.OperationalError:
            return []

    # -- measurements ------------------------------------------------------

    def latest_value(self, metric: str) -> float | None:
        """Most recent value for a measurement metric, or ``None``."""
        metric = _alias(metric)
        if not self._has("measurements"):
            return None
        row = self._query(
            "SELECT value FROM measurements WHERE metric=? AND value IS NOT NULL "
            "ORDER BY start_ts DESC LIMIT 1",
            (metric,),
        )
        return float(row[0]["value"]) if row else None

    def values(self, metric: str, days: int | None = None) -> list[tuple[str, float]]:
        """Return ``(start_ts, value)`` for a metric, optionally last ``days``."""
        metric = _alias(metric)
        if not self._has("measurements"):
            return []
        sql = (
            "SELECT start_ts, value FROM measurements "
            "WHERE metric=? AND value IS NOT NULL"
        )
        params: tuple = (metric,)
        if days is not None:
            # Anchor the window to this metric's own latest data, not wall-clock
            # 'now' — the export is static and streams stop at different dates.
            sql += (
                " AND substr(start_ts,1,10) >= date("
                "(SELECT MAX(substr(start_ts,1,10)) FROM measurements WHERE metric=?), ?)"
            )
            params = (metric, metric, f"-{int(days)} days")
        sql += " ORDER BY start_ts ASC"
        return [(r["start_ts"], float(r["value"])) for r in self._query(sql, params)]

    def mean_value(self, metric: str, days: int | None = None) -> float | None:
        """Arithmetic mean of a metric over an optional recent window."""
        vals = [v for _, v in self.values(metric, days=days)]
        return sum(vals) / len(vals) if vals else None

    def count(self, metric: str) -> int:
        """Number of non-null measurement rows for a metric."""
        metric = _alias(metric)
        if not self._has("measurements"):
            return 0
        row = self._query(
            "SELECT COUNT(*) AS c FROM measurements WHERE metric=? AND value IS NOT NULL",
            (metric,),
        )
        return int(row[0]["c"]) if row else 0

    # -- baselines / derived ----------------------------------------------

    def baseline(self, metric: str) -> BaselineStat:
        """Stored within-person baseline, falling back to computed stats.

        If no baseline row exists, computes a mean/sd over the last 90 days of
        measurements so domains still get a usable personal reference.
        """
        metric = _alias(metric)
        if self._has("baselines"):
            row = self._query("SELECT * FROM baselines WHERE metric=?", (metric,))
            if row:
                r = row[0]
                return BaselineStat(metric, _f(r["mean"]), _f(r["sd"]), _i(r["n"]))
        vals = [v for _, v in self.values(metric, days=90)]
        if len(vals) >= 2:
            mean = sum(vals) / len(vals)
            var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
            return BaselineStat(metric, mean, var**0.5, len(vals))
        if len(vals) == 1:
            return BaselineStat(metric, vals[0], None, 1)
        return BaselineStat(metric, None, None, 0)

    def derived(self, metric: str, method: str | None = None) -> float | None:
        """Most recent derived metric value (optionally filtered by method)."""
        metric = _alias(metric)
        if not self._has("derived_metrics"):
            return None
        sql = "SELECT value FROM derived_metrics WHERE metric=?"
        params: tuple = (metric,)
        if method:
            sql += " AND method=?"
            params = (metric, method)
        sql += " ORDER BY as_of_ts DESC LIMIT 1"
        row = self._query(sql, params)
        return _f(row[0]["value"]) if row else None

    # -- nutrition ---------------------------------------------------------

    def nutrition_mean(self, metric: str, days: int | None = 30) -> float | None:
        """Mean of a daily nutrition metric over the last ``days``."""
        metric = _alias(metric)
        if not self._has("nutrition_daily"):
            return None
        sql = "SELECT value FROM nutrition_daily WHERE metric=? AND value IS NOT NULL"
        params: tuple = (metric,)
        if days is not None:
            sql += " AND date >= date((SELECT MAX(date) FROM nutrition_daily WHERE metric=?), ?)"
            params = (metric, metric, f"-{int(days)} days")
        rows = self._query(sql, params)
        vals = [_f(r["value"]) for r in rows if _f(r["value"]) is not None]
        return sum(vals) / len(vals) if vals else None  # type: ignore[arg-type]

    def nutrition_series(self, metric: str, days: int = 90) -> list[tuple[str, float]]:
        """Return ``(date, value)`` for a daily nutrition metric."""
        metric = _alias(metric)
        if not self._has("nutrition_daily"):
            return []
        rows = self._query(
            "SELECT date, value FROM nutrition_daily WHERE metric=? AND value IS NOT NULL "
            "AND date >= date((SELECT MAX(date) FROM nutrition_daily WHERE metric=?), ?) "
            "ORDER BY date ASC",
            (metric, metric, f"-{int(days)} days"),
        )
        return [(r["date"], float(r["value"])) for r in rows]

    def nutrition_days_logged(self, days: int = 30) -> int:
        """Distinct days with any nutrition entry in the last ``days``."""
        if not self._has("nutrition_daily"):
            return 0
        row = self._query(
            "SELECT COUNT(DISTINCT date) AS c FROM nutrition_daily "
            "WHERE date >= date((SELECT MAX(date) FROM nutrition_daily), ?)",
            (f"-{int(days)} days",),
        )
        return int(row[0]["c"]) if row else 0

    # -- sleep -------------------------------------------------------------

    def sleep_hours_recent(self, days: int = 30) -> list[float]:
        """Per-night asleep hours (core+deep+rem) over the last ``days``."""
        if not self._has("sleep_segments"):
            return []
        # Prefer staged sleep; fall back to 'inBed' when stages weren't recorded.
        has_asleep = self._query(
            "SELECT 1 FROM sleep_segments WHERE stage LIKE 'asleep%' LIMIT 1"
        )
        stage_filter = "stage LIKE 'asleep%'" if has_asleep else "stage = 'inBed'"
        rows = self._query(
            "SELECT date(start_ts) AS d, "
            "SUM((julianday(end_ts)-julianday(start_ts))*24.0) AS hrs "
            f"FROM sleep_segments WHERE {stage_filter} "
            "AND substr(start_ts,1,10) >= date("
            "(SELECT MAX(substr(start_ts,1,10)) FROM sleep_segments), ?) "
            "GROUP BY d ORDER BY d ASC",
            (f"-{int(days)} days",),
        )
        return [float(r["hrs"]) for r in rows if r["hrs"] is not None]

    def sleep_stage_fraction(self, stage: str, days: int = 30) -> float | None:
        """Fraction of asleep time spent in ``stage`` (e.g. ``asleepDeep``)."""
        if not self._has("sleep_segments"):
            return None
        anchor = "date((SELECT MAX(substr(start_ts,1,10)) FROM sleep_segments), ?)"
        total = self._query(
            "SELECT SUM((julianday(end_ts)-julianday(start_ts))) AS t "
            f"FROM sleep_segments WHERE stage LIKE 'asleep%' AND substr(start_ts,1,10) >= {anchor}",
            (f"-{int(days)} days",),
        )
        part = self._query(
            "SELECT SUM((julianday(end_ts)-julianday(start_ts))) AS t "
            f"FROM sleep_segments WHERE stage=? AND substr(start_ts,1,10) >= {anchor}",
            (stage, f"-{int(days)} days"),
        )
        t_total = _f(total[0]["t"]) if total else None
        t_part = _f(part[0]["t"]) if part else None
        if not t_total or t_part is None or t_total <= 0:
            return None
        return t_part / t_total

    # -- workouts ----------------------------------------------------------

    def workout_count(self, days: int = 30, activity_type: str | None = None) -> int:
        """Count workouts in the last ``days`` (optionally by activity type)."""
        if not self._has("workouts"):
            return 0
        sql = (
            "SELECT COUNT(*) AS c FROM workouts WHERE substr(start_ts,1,10) >= "
            "date((SELECT MAX(substr(start_ts,1,10)) FROM workouts), ?)"
        )
        params: tuple = (f"-{int(days)} days",)
        if activity_type:
            sql += " AND activity_type=?"
            params = (f"-{int(days)} days", activity_type)
        row = self._query(sql, params)
        return int(row[0]["c"]) if row else 0

    def workout_load_series(self, days: int = 56) -> list[tuple[str, float]]:
        """Daily summed workout energy (kcal) as a training-load proxy."""
        if not self._has("workouts"):
            return []
        rows = self._query(
            "SELECT date(start_ts) AS d, SUM(COALESCE(energy_kcal, duration_s/60.0, 0)) AS load "
            "FROM workouts WHERE substr(start_ts,1,10) >= "
            "date((SELECT MAX(substr(start_ts,1,10)) FROM workouts), ?) "
            "GROUP BY d ORDER BY d ASC",
            (f"-{int(days)} days",),
        )
        return [(r["d"], float(r["load"])) for r in rows if r["load"] is not None]

    # -- genome ------------------------------------------------------------

    def genotype(self, rsid: str) -> str | None:
        """Genotype string for a variant by rsID, or ``None``."""
        if not self._has("genome_variants"):
            return None
        row = self._query("SELECT genotype FROM genome_variants WHERE rsid=?", (rsid,))
        return row[0]["genotype"] if row else None

    # -- nebula ------------------------------------------------------------

    def nebula_trait(self, name: str) -> sqlite3.Row | None:
        """Look up a Nebula trait by (case-insensitive) name substring."""
        if not self._has("nebula_traits"):
            return None
        row = self._query(
            "SELECT * FROM nebula_traits WHERE lower(trait) LIKE lower(?) LIMIT 1",
            (f"%{name}%",),
        )
        return row[0] if row else None

    def nebula_by_category(self, category: str) -> list[sqlite3.Row]:
        """All Nebula traits whose category matches ``category`` (substring)."""
        if not self._has("nebula_traits"):
            return []
        return self._query(
            "SELECT * FROM nebula_traits WHERE lower(category) LIKE lower(?)",
            (f"%{category}%",),
        )

    def nebula_search(self, keywords: list[str]) -> list[sqlite3.Row]:
        """Return Nebula traits whose name/category matches any keyword."""
        if not self._has("nebula_traits") or not keywords:
            return []
        clauses = " OR ".join(
            ["lower(trait) LIKE lower(?) OR lower(category) LIKE lower(?)"] * len(keywords)
        )
        params: list[str] = []
        for kw in keywords:
            params.extend([f"%{kw}%", f"%{kw}%"])
        seen: dict[int, sqlite3.Row] = {}
        for r in self._query(f"SELECT * FROM nebula_traits WHERE {clauses}", tuple(params)):
            seen[int(r["id"])] = r
        return list(seen.values())

    # -- coverage ----------------------------------------------------------

    @lru_cache(maxsize=1)  # noqa: B019 - context is short-lived, cache is per-instance
    def has_any_data(self) -> bool:
        """Whether the database holds any measurements, nutrition, or sleep."""
        for table in ("measurements", "nutrition_daily", "sleep_segments", "workouts"):
            if self._has(table):
                row = self._query(f"SELECT 1 FROM {table} LIMIT 1")
                if row:
                    return True
        return False


def _f(x: object) -> float | None:
    """Best-effort float coercion."""
    try:
        return float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _i(x: object) -> int | None:
    """Best-effort int coercion."""
    try:
        return int(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
