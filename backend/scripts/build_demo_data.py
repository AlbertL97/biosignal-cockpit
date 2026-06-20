"""Build the STATIC DEMO data bundle for the public GitHub Pages site.

Generates a synthetic-but-realistic health dataset (so no real biometric/nutrition
data is published), combines it with a CURATED SUBSET of the real genome
(examples only), runs the real interpretation pipeline, and exports a single
``frontend/public/demo/bundle.json`` the demo frontend reads instead of the API.

Run from backend/:  python -m scripts.build_demo_data
"""
from __future__ import annotations

import json
import math
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from app import config
from app.interpretation import engine
from app.interpretation.context import DataContext, _alias
from app.interpretation.highlights import compute_highlights
from app.interpretation.trait_explain import describe_trait, interpret_percentile
from app.processing import baselines, trends

SEED = 42
DAYS = 150
N_TRAITS = 32            # curated NON-SENSITIVE real trait examples

# Only these (benign appearance / taste / nutrition / fitness / sleep) traits may
# appear in the PUBLIC demo, and never anything matching the sensitive blocklist.
BENIGN_KEYWORDS = [
    "eye color", "hair color", "baldness", "bald", "hair texture", "freckl",
    "tanning", "skin pigmentation", "wrinkl", "skin aging", "bitter taste",
    "sweet taste", "taste perception", "earwax", "cerumen", "lactose",
    "caffeine", "coffee", "carbohydrate consumption", "25-hydroxyvitamin",
    "vitamin d level", "bone mineral density", "height", "short stature",
    "photic sneeze", "misophonia", "chronotype", "morning person", "napping",
    "beat synchron", "musical", "reaction time", "handed", "ambidext",
    "walking pace", "snoring", "sleep duration", "cilantro", "dental development",
    "birth weight", "freckling", "adventurous",
]
SENSITIVE_KEYWORDS = [
    "cancer", "carcinoma", "tumor", "tumour", "leukaem", "leukem", "melanoma",
    "alzheim", "dementia", "parkinson", "schizophren", "bipolar", "depress",
    "anxiety", "autism", "adhd", "addiction", "alcohol", "nicotine", "cannabis",
    "opioid", "suicid", "psych", "covid", "hiv", "diabet", "kidney", "renal",
    "liver", "cirrhosis", "hepat", "cardiac", "heart", "coronary", "stroke",
    "arter", "aneurysm", "atrial", "lupus", "arthrit", "autoimmun", "thyroid",
    "crohn", "colitis", "celiac", "ulcerative", "fibrosis", "glaucoma",
    "macular", "intelligence", "income", "fertil", "childless", "menopause",
    "prostate", "breast", "ovar", "testic", "puberty", "scoliosis", "caries",
    "cleft", "epilep", "migraine", "dyslexia",
]
OUT = config.PROJECT_ROOT / "frontend" / "public" / "demo" / "bundle.json"
SCHEMA = config.PROJECT_ROOT / "backend" / "app" / "storage" / "schema.sql"

# Chart metrics the frontend requests (HK names) -> synthetic generator params.
# (mean, sd, min, max, unit, slight daily drift)
METRIC_SPEC = {
    "RestingHeartRate": (54, 4, 44, 70, "count/min", -0.01),
    "HeartRateVariabilitySDNN": (62, 14, 25, 110, "ms", 0.03),
    "StepCount": (8800, 2600, 1500, 18000, "count", 1.5),
    "ActiveEnergyBurned": (620, 180, 120, 1200, "kcal", 0.2),
    "OxygenSaturation": (97.5, 0.8, 94, 100, "%", 0.0),
    "HeartRate": (72, 9, 50, 150, "count/min", 0.0),
    "DistanceWalkingRunning": (6.4, 2.1, 1.0, 14, "km", 0.001),
    "FlightsClimbed": (9, 5, 0, 28, "count", 0.0),
}
# nutrition (nutrition_daily) synthetic params: (mean, sd, min, max, unit)
NUTR_SPEC = {
    "energy": (2550, 360, 1500, 3600, "kcal"),
    "protein": (135, 28, 60, 220, "g"),
    "carbohydrates": (250, 60, 100, 420, "g"),
    "fat_total": (90, 22, 35, 160, "g"),
    "fiber": (26, 7, 8, 48, "g"),
    "sugar": (74, 24, 20, 160, "g"),
    "sodium": (2900, 700, 1200, 5200, "mg"),
    "water": (2.4, 0.7, 0.5, 4.5, "L"),
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def build_synthetic(conn: sqlite3.Connection) -> None:
    rng = random.Random(SEED)
    today = date.today()
    start = today - timedelta(days=DAYS)

    # measurements
    for name, (mean, sd, lo, hi, unit, drift) in METRIC_SPEC.items():
        stored = _alias(name)
        for i in range(DAYS):
            d = start + timedelta(days=i)
            # weekly + noise + drift
            season = math.sin(i / 7 * math.pi) * sd * 0.3
            val = _clamp(mean + drift * i + season + rng.gauss(0, sd), lo, hi)
            ts = f"{d.isoformat()}T08:00:00+02:00"
            conn.execute(
                "INSERT INTO measurements(metric,unit,value,start_ts,end_ts,source,device,raw_type)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (stored, unit, round(val, 2), ts, ts, "demo", "Demo Watch", name),
            )

    # nutrition_daily
    for i in range(DAYS):
        d = (start + timedelta(days=i)).isoformat()
        for metric, (mean, sd, lo, hi, unit) in NUTR_SPEC.items():
            val = _clamp(rng.gauss(mean, sd), lo, hi)
            conn.execute(
                "INSERT INTO nutrition_daily(date,metric,value,unit) VALUES(?,?,?,?)",
                (d, metric, round(val, 1), unit),
            )

    # sleep_segments (staged)
    for i in range(DAYS):
        d = start + timedelta(days=i)
        total = _clamp(rng.gauss(7.4, 0.9), 4.5, 9.5)
        frac = {"asleepCore": 0.55, "asleepDeep": 0.18, "asleepREM": 0.22, "awake": 0.05}
        t0 = datetime(d.year, d.month, d.day, 23, 0)
        cursor = t0
        for stage, fr in frac.items():
            dur = total * fr
            end = cursor + timedelta(hours=dur)
            conn.execute(
                "INSERT INTO sleep_segments(stage,start_ts,end_ts,source) VALUES(?,?,?,?)",
                (stage, cursor.isoformat(), end.isoformat(), "demo"),
            )
            cursor = end

    # workouts
    kinds = ["HighIntensityIntervalTraining", "FunctionalStrengthTraining", "Running", "Walking"]
    for i in range(0, DAYS, 2):
        d = start + timedelta(days=i)
        k = rng.choice(kinds)
        dur = rng.uniform(25, 75) * 60
        t0 = datetime(d.year, d.month, d.day, 18, 0)
        conn.execute(
            "INSERT INTO workouts(activity_type,start_ts,end_ts,duration_s,energy_kcal,distance_m,source)"
            " VALUES(?,?,?,?,?,?,?)",
            (k, t0.isoformat(), (t0 + timedelta(seconds=dur)).isoformat(),
             round(dur, 0), round(rng.uniform(200, 700), 0),
             round(rng.uniform(2000, 9000), 0) if k in ("Running", "Walking") else None, "demo"),
        )

    # profile (synthetic)
    for k, v in {
        "dob": "1997-07-14", "biological_sex": "male",
        "blood_type": "NotSet", "skin_type": "NotSet",
        "export_date": today.isoformat(),
    }.items():
        conn.execute("INSERT INTO profile(key,value) VALUES(?,?)", (k, v))


def copy_curated_genome(demo: sqlite3.Connection) -> list[str]:
    """Copy a curated subset of REAL variants + traits from the real DB."""
    real = sqlite3.connect(str(config.DB_PATH))
    real.row_factory = sqlite3.Row
    notes: list[str] = []

    def is_benign(name: str) -> bool:
        ln = (name or "").lower()
        if any(k in ln for k in SENSITIVE_KEYWORDS):
            return False
        return any(k in ln for k in BENIGN_KEYWORDS)

    # only non-sensitive traits, deduped by name, prefer ones with a percentile
    rows = real.execute(
        "SELECT * FROM nebula_traits ORDER BY (percentile IS NULL), trait"
    ).fetchall()
    picked: list[sqlite3.Row] = []
    seen_names: set[str] = set()
    for t in rows:
        if len(picked) >= N_TRAITS:
            break
        if not is_benign(t["trait"]) or t["trait"] in seen_names:
            continue
        seen_names.add(t["trait"])
        picked.append(t)

    rsids: set[str] = set()
    for t in picked:
        cur = demo.execute(
            "INSERT INTO nebula_traits(trait,category,citation,percentile,score,score_label,pdf_path)"
            " VALUES(?,?,?,?,?,?,?)",
            (t["trait"], t["category"], t["citation"], t["percentile"], t["score"],
             t["score_label"], None),
        )
        tid = cur.lastrowid
        vrows = real.execute(
            "SELECT * FROM nebula_trait_variants WHERE trait_id=? LIMIT 14", (t["id"],)
        ).fetchall()
        for v in vrows:
            demo.execute(
                "INSERT INTO nebula_trait_variants"
                "(trait_id,rsid,genotype,gene,effect_size,frequency,p_value,highlighted)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (tid, v["rsid"], v["genotype"], v["gene"], v["effect_size"],
                 v["frequency"], v["p_value"], v["highlighted"]),
            )
            if v["rsid"]:
                rsids.add(v["rsid"])

    # copy genotypes for the real variants referenced by the benign traits above
    picked_rsids = sorted(rsids)
    for rsid in picked_rsids:
        gv = real.execute("SELECT * FROM genome_variants WHERE rsid=?", (rsid,)).fetchone()
        if gv:
            demo.execute(
                "INSERT OR IGNORE INTO genome_variants(rsid,chrom,pos,ref,alt,genotype,gene,source)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (gv["rsid"], gv["chrom"], gv["pos"], gv["ref"], gv["alt"],
                 gv["genotype"], gv["gene"], gv["source"]),
            )
    notes.append(f"{len(picked)} traits, {len(picked_rsids)} genotyped variants")
    real.close()
    return notes


def day_series(conn: sqlite3.Connection, hk_name: str) -> dict:
    stored = _alias(hk_name)
    rows = conn.execute(
        "SELECT substr(start_ts,1,10) d, AVG(value) v, "
        "(SELECT unit FROM measurements WHERE metric=? LIMIT 1) u "
        "FROM measurements WHERE metric=? GROUP BY d ORDER BY d",
        (stored, stored),
    ).fetchall()
    b = conn.execute("SELECT mean,sd FROM baselines WHERE metric=?", (stored,)).fetchone()
    return {
        "metric": hk_name,
        "unit": rows[0][2] if rows else None,
        "points": [{"ts": f"{r[0]}T00:00:00", "value": round(r[1], 2)} for r in rows],
        "baseline_mean": b[0] if b else None,
        "baseline_sd": b[1] if b else None,
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    demo = sqlite3.connect(":memory:")
    demo.row_factory = sqlite3.Row
    demo.executescript(SCHEMA.read_text(encoding="utf-8"))

    build_synthetic(demo)
    notes = copy_curated_genome(demo)
    baselines.compute_baselines(demo)
    trends.compute_trends(demo)
    demo.commit()

    ctx = DataContext(conn=demo)
    domains = engine.run_all(ctx, persist=False)

    metrics = {name: day_series(demo, name) for name in METRIC_SPEC}
    # nutrition-based key metrics used by the gut/oral_dental charts
    for hk, stored in (("DietaryEnergyConsumed", "energy"), ("DietarySugar", "sugar")):
        rows = demo.execute(
            "SELECT date d, value v, (SELECT unit FROM nutrition_daily WHERE metric=? LIMIT 1) u "
            "FROM nutrition_daily WHERE metric=? ORDER BY date", (stored, stored)
        ).fetchall()
        vals = [r[1] for r in rows]
        mean = sum(vals) / len(vals) if vals else None
        sd = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5 if vals else None
        metrics[hk] = {
            "metric": hk, "unit": rows[0][2] if rows else None,
            "points": [{"ts": f"{r[0]}T00:00:00", "value": round(r[1], 1)} for r in rows],
            "baseline_mean": round(mean, 1) if mean else None,
            "baseline_sd": round(sd, 1) if sd else None,
        }

    traits = [dict(r) for r in demo.execute(
        "SELECT id,trait,category,citation,percentile,score,score_label FROM nebula_traits ORDER BY trait"
    ).fetchall()]
    trait_details: dict[str, dict] = {}
    for t in traits:
        vs = [dict(r) for r in demo.execute(
            "SELECT rsid,genotype,gene,effect_size,frequency,p_value,highlighted "
            "FROM nebula_trait_variants WHERE trait_id=?", (t["id"],)
        ).fetchall()]
        for v in vs:
            v["highlighted"] = bool(v["highlighted"])
        trait_details[str(t["id"])] = {
            **t,
            "variants": vs,
            "description": describe_trait(t["trait"]),
            "interpretation": interpret_percentile(
                t["trait"], t["percentile"], t["score_label"]
            ),
        }

    prof = {r["key"]: r["value"] for r in demo.execute("SELECT key,value FROM profile").fetchall()}
    coverage = {r[0]: r[1] for r in demo.execute(
        "SELECT metric,COUNT(*) FROM measurements GROUP BY metric"
    ).fetchall()}

    bundle = {
        "generated": datetime.now().isoformat(),
        "demo": True,
        "profile": {
            "dob": prof.get("dob"), "biological_sex": prof.get("biological_sex"),
            "blood_type": prof.get("blood_type"), "skin_type": prof.get("skin_type"),
            "coverage": coverage,
            "highlights": [json.loads(h.model_dump_json()) for h in compute_highlights(ctx)],
        },
        "domains": [json.loads(d.model_dump_json()) for d in domains],
        "metrics": metrics,
        "genomeTraits": [{**t, "variants": []} for t in traits],
        "genomeTraitDetails": trait_details,
        "evidence": {d.domain: [json.loads(e.model_dump_json()) for e in d.evidence] for d in domains},
    }
    OUT.write_text(json.dumps(bundle, indent=None), encoding="utf-8")
    size = OUT.stat().st_size / 1024
    print(f"wrote {OUT}  ({size:.0f} KB)")
    print("curated genome:", notes)
    print("domains:", [f'{d.domain}={round(d.score,1) if d.score else None}' for d in domains])


if __name__ == "__main__":
    main()
