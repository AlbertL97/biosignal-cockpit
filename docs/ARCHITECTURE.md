# Architecture & Shared Contracts

**This document is the single source of truth for all agents building this app.**
Read it fully before writing code. Do not change the contracts here without
updating this file. Honor the medical/ethical boundaries in `../task(2).md` §14.

---

## 1. System overview

A local-first, single-user "personal health intelligence" app that ingests
Apple Health, a whole-genome VCF, Nebula Genomics trait reports, and GPX routes;
normalizes them; computes personal baselines and trends; runs a rule-based +
statistical interpretation engine across body-system domains; attaches graded
scientific evidence (live PubMed + Nebula citations); and serves a futuristic
React dashboard with a clickable SVG avatar and per-domain reports.

```
data files ──► ingestion ──► SQLite ──► processing ──► interpretation ──► API ──► React UI
(eksport.xml,                (raw +     (baselines,    (domain status,           (avatar,
 VCF, PDFs,                   derived)   trends)        confidence,               cards,
 GPX)                                                   evidence)                 reports)
```

## 2. Repository layout & module ownership

Shared root files (`requirements.txt`, `package.json`, configs, `app/models`,
`app/storage/schema.sql`, this doc) are **pre-created by the orchestrator**.
Agents only create/edit files inside their assigned subtree and **never** edit
shared root files or another agent's subtree.

```
backend/
  requirements.txt                  [orchestrator]
  app/
    config.py                       [orchestrator]
    main.py                         [orchestrator] FastAPI app; includes routers
    models/                         [orchestrator] Pydantic contract types (shared)
    ingestion/                      [BACKEND agent] apple_health.py, vcf.py, nebula_reports.py, gpx.py
    storage/                        [BACKEND agent] db.py (+ schema.sql by orchestrator)
    processing/                     [BACKEND agent] baselines.py, trends.py, quality.py
    interpretation/                 [DATA-SCIENCE agent] engine.py, domains/*.py
    evidence/                       [RESEARCH agent] pubmed.py, grading.py, store.py
    api/                            [BACKEND agent] routers; other agents expose APIRouter objects
  tests/                            each agent adds tests for its own module
frontend/
  package.json, vite/ts/tailwind    [orchestrator]
  src/
    design/                         [DESIGN agent] tokens, theme, primitives
    components/Avatar/              [DESIGN agent] interactive SVG body
    components/{cards,charts,reports,layout}/  [FRONTEND agent]
    pages/                          [FRONTEND agent]
    api/                            [FRONTEND agent] client + types (mirror of models)
docs/                               [orchestrator]
```

## 3. Canonical body-system domains (this build)

`gut`, `brain`, `cardiovascular`, `oral_dental`, `musculoskeletal`,
`metabolic`, `sleep_recovery`, `stress_autonomic`, `immune_inflammation`.

Each domain module exposes: `compute(context) -> DomainStatus` (see §6).

## 4. Data sources (actual files, all git-ignored)

Located at the project root (`Health_analysis/`); paths come from `config.py`.

| Source | File(s) | Parser | Notes |
|---|---|---|---|
| Apple Health | `eksport.xml` (~173 MB) | `ingestion/apple_health.py` | HealthKit Export v14. Stream with `lxml.etree.iterparse` — DO NOT load into memory. Also contains nutrition (Yazio-synced). |
| Apple Health CDA | `export_cda.xml` (~16 MB) | (optional) | Clinical Document Architecture; secondary. |
| Genome VCF | `NG1E19KTCQ.mm2.sortdup.bqsr.hc (1).vcf` (~1.1 GB) | `ingestion/vcf.py` | VCFv4.2, GRCh38, ~4–5M variants. Stream line-by-line; index only rsIDs we care about (those in Nebula reports + a curated actionable set). DO NOT load all variants into SQLite. |
| Nebula reports | `DNA_reports/*.pdf` (379 files) | `ingestion/nebula_reports.py` | One trait per PDF. Extract: trait, citation, category tag, percentile, and the variant table (rsID, genotype, gene, effect size, frequency, p-value). Use `pdfplumber`. |
| Genome CRAM | `*.cram` (66 GB) | — | IGNORED this build (raw alignments; not needed). |
| Routes | `workout-routes/*.gpx` | `ingestion/gpx.py` | 2 files; low priority. |

### Apple Health record-type mapping (HK identifier → canonical metric)
Streaming parser maps `HKQuantityTypeIdentifier*` / `HKCategoryTypeIdentifier*`
to canonical metric keys. Key ones present in this dataset:
`HeartRate, RestingHeartRate, WalkingHeartRateAverage, HeartRateVariabilitySDNN,
OxygenSaturation, SleepAnalysis (category), StepCount, DistanceWalkingRunning,
ActiveEnergyBurned, BasalEnergyBurned, AppleExerciseTime, AppleStandTime,
FlightsClimbed, WalkingSpeed, WalkingStepLength, WalkingAsymmetryPercentage,
WalkingDoubleSupportPercentage, AppleWalkingSteadiness, StairAscent/DescentSpeed,
SixMinuteWalkTestDistance, PhysicalEffort, TimeInDaylight,
Environmental/HeadphoneAudioExposure, BodyMass`, and dietary:
`DietaryEnergyConsumed, DietaryProtein, DietaryCarbohydrates, DietaryFatTotal,
DietaryFatSaturated/Mono/Poly, DietarySugar, DietaryFiber, DietarySodium,
DietaryPotassium, DietaryCalcium, DietaryMagnesium, DietaryIron, DietaryZinc,
DietaryVitamin{A,C,D,E,K}, DietaryFolate, DietaryWater, DietaryCholesterol`, etc.
Workouts: `HIIT, Walking, FunctionalStrengthTraining, Running`.

## 5. Storage model (SQLite; see `app/storage/schema.sql`)

- `measurements(id, metric, unit, value, start_ts, end_ts, source, device, raw_type)` — directly measured Apple Health values.
- `sleep_segments(id, stage, start_ts, end_ts, source)` — from SleepAnalysis.
- `workouts(id, activity_type, start_ts, end_ts, duration_s, energy_kcal, distance_m, source)`.
- `nutrition_daily(date, metric, value, unit)` — daily-aggregated dietary metrics.
- `derived_metrics(id, metric, value, window, as_of_ts, method)` — rolling means, baselines, deviations, z-scores.
- `baselines(metric, mean, sd, n, window_days, computed_ts)`.
- `genome_variants(rsid, chrom, pos, ref, alt, genotype, gene, source)` — only curated/needed rsIDs.
- `nebula_traits(id, trait, category, citation, percentile, score, score_label, pdf_path)`.
- `nebula_trait_variants(trait_id, rsid, genotype, gene, effect_size, frequency, p_value, highlighted)`.
- `domain_status(domain, as_of_ts, score, score_label, trend, confidence, evidence_grade, summary_json)`.
- `evidence_refs(id, domain, claim, pmid, title, year, source, evidence_grade, url)`.
- `audit_log(ts, event, detail)` — every import & generated interpretation.

Raw, derived, interpretation, and evidence stay in **separate tables** (task §12.2).

## 6. Interpretation output contract (Pydantic — `app/models/contracts.py`)

Every interpretation MUST separate the five layers (task §10) and surface
uncertainty. Confidence ∈ {high, moderate, low, exploratory}. Evidence grade ∈
{high, moderate, low, exploratory, unsupported}.

```python
class Contribution(BaseModel):
    source: str            # "apple_health" | "genome" | "nebula" | "nutrition"
    metric: str
    value: float | str | None
    weight: float          # 0..1 relative contribution
    direction: str         # "supportive" | "adverse" | "neutral" | "uncertain"

class EvidenceRef(BaseModel):
    claim: str
    grade: str             # evidence grade enum
    pmid: str | None
    title: str | None
    year: int | None
    url: str | None
    source: str            # "pubmed" | "nebula" | "guideline" | "curated"

class DomainStatus(BaseModel):
    domain: str
    score: float | None            # 0..100, may be None if insufficient data
    score_label: str               # e.g. "supportive", "watch", "insufficient data"
    trend: str                     # "improving" | "stable" | "declining" | "unknown"
    confidence: str                # confidence enum
    evidence_grade: str            # evidence grade enum
    summary: str                   # cautious, non-diagnostic prose
    observations: list[str]        # measured
    derived: list[str]             # derived metrics
    inferences: list[str]          # cautious inferred states
    hypotheses: list[str]          # plausible but uncertain
    recommendations: list[str]     # non-diagnostic, ranked
    contributions: list[Contribution]
    evidence: list[EvidenceRef]
    missing_data: list[str]        # explicit gaps
    as_of: datetime
```

## 7. API contract (FastAPI; base `/api`)

| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | service status |
| GET | `/api/profile` | `Me` block (DOB, sex, blood type, skin type) + data coverage summary |
| GET | `/api/domains` | list of `DomainStatus` (overview cards) |
| GET | `/api/domains/{domain}` | full `DomainStatus` + timeseries for the report view |
| GET | `/api/metrics/{metric}` | timeseries + baseline for charts (query: from, to, window) |
| GET | `/api/genome/traits` | list of `nebula_traits` (filter by category) |
| GET | `/api/genome/traits/{id}` | trait detail + variant table |
| GET | `/api/evidence?domain=` | graded evidence refs for a domain |
| POST | `/api/ingest` | (re)run ingestion pipeline; returns audit summary |

Responses are JSON matching the Pydantic models. The frontend mirrors these in
`src/api/types.ts`.

## 8. Conventions & guardrails (NON-NEGOTIABLE)

- **No diagnosis.** Use cautious wording (task §8). A `safety` filter rejects
  banned phrasings ("you have", "this proves", "your gut is unhealthy", etc.).
- Interpret **within-person** (vs personal baseline), not population thresholds.
- Always show **missing-data** and **uncertainty**; never imply false precision.
- Distinguish **measured vs inferred** everywhere in UI and data.
- Genomic findings: cautious, non-deterministic; flag VUS / research-only.
- Python: type hints, `ruff`-clean, docstrings; tests with `pytest`.
- TS: strict mode; functional components; no `any`.
- Dark-mode-first, "biohacker cockpit" aesthetic; accessible (WCAG AA contrast).
- Never write real personal data into git-tracked files; outputs go to git-ignored dirs.
```
