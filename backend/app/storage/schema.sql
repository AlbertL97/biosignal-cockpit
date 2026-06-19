-- Health_analysis SQLite schema.
-- Raw / derived / interpretation / evidence are kept in SEPARATE tables (task §12.2).
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---------- Raw measured data ----------
CREATE TABLE IF NOT EXISTS measurements (
    id        INTEGER PRIMARY KEY,
    metric    TEXT NOT NULL,            -- canonical metric key
    unit      TEXT,
    value     REAL,
    start_ts  TEXT NOT NULL,            -- ISO 8601
    end_ts    TEXT,
    source    TEXT,                     -- sourceName
    device    TEXT,
    raw_type  TEXT                      -- original HK identifier
);
CREATE INDEX IF NOT EXISTS ix_meas_metric_ts ON measurements(metric, start_ts);

CREATE TABLE IF NOT EXISTS sleep_segments (
    id        INTEGER PRIMARY KEY,
    stage     TEXT,                     -- inBed/asleepCore/asleepDeep/asleepREM/awake
    start_ts  TEXT NOT NULL,
    end_ts    TEXT NOT NULL,
    source    TEXT
);
CREATE INDEX IF NOT EXISTS ix_sleep_ts ON sleep_segments(start_ts);

CREATE TABLE IF NOT EXISTS workouts (
    id            INTEGER PRIMARY KEY,
    activity_type TEXT,
    start_ts      TEXT NOT NULL,
    end_ts        TEXT,
    duration_s    REAL,
    energy_kcal   REAL,
    distance_m    REAL,
    source        TEXT
);

CREATE TABLE IF NOT EXISTS nutrition_daily (
    date   TEXT NOT NULL,               -- YYYY-MM-DD
    metric TEXT NOT NULL,
    value  REAL,
    unit   TEXT,
    PRIMARY KEY (date, metric)
);

CREATE TABLE IF NOT EXISTS profile (
    key   TEXT PRIMARY KEY,             -- dob, biological_sex, blood_type, skin_type
    value TEXT
);

-- ---------- Genome ----------
CREATE TABLE IF NOT EXISTS genome_variants (
    rsid     TEXT PRIMARY KEY,
    chrom    TEXT,
    pos      INTEGER,
    ref      TEXT,
    alt      TEXT,
    genotype TEXT,
    gene     TEXT,
    source   TEXT
);

CREATE TABLE IF NOT EXISTS nebula_traits (
    id          INTEGER PRIMARY KEY,
    trait       TEXT NOT NULL,
    category    TEXT,
    citation    TEXT,
    percentile  REAL,
    score       REAL,
    score_label TEXT,
    pdf_path    TEXT
);

CREATE TABLE IF NOT EXISTS nebula_trait_variants (
    trait_id    INTEGER REFERENCES nebula_traits(id),
    rsid        TEXT,
    genotype    TEXT,
    gene        TEXT,
    effect_size REAL,
    frequency   REAL,
    p_value     REAL,
    highlighted INTEGER                 -- 0/1
);

-- ---------- Derived ----------
CREATE TABLE IF NOT EXISTS derived_metrics (
    id      INTEGER PRIMARY KEY,
    metric  TEXT NOT NULL,
    value   REAL,
    window  TEXT,                       -- e.g. "7d","30d","90d"
    as_of_ts TEXT,
    method  TEXT                        -- rolling_mean | zscore | deviation | slope
);
CREATE INDEX IF NOT EXISTS ix_derived ON derived_metrics(metric, as_of_ts);

CREATE TABLE IF NOT EXISTS baselines (
    metric       TEXT PRIMARY KEY,
    mean         REAL,
    sd           REAL,
    n            INTEGER,
    window_days  INTEGER,
    computed_ts  TEXT
);

-- ---------- Interpretation ----------
CREATE TABLE IF NOT EXISTS domain_status (
    domain         TEXT NOT NULL,
    as_of_ts       TEXT NOT NULL,
    score          REAL,
    score_label    TEXT,
    trend          TEXT,
    confidence     TEXT,
    evidence_grade TEXT,
    summary_json   TEXT,                -- full DomainStatus serialized
    PRIMARY KEY (domain, as_of_ts)
);

-- ---------- Evidence ----------
CREATE TABLE IF NOT EXISTS evidence_refs (
    id             INTEGER PRIMARY KEY,
    domain         TEXT,
    claim          TEXT,
    pmid           TEXT,
    title          TEXT,
    year           INTEGER,
    source         TEXT,                -- pubmed | nebula | guideline | curated
    evidence_grade TEXT,
    url            TEXT
);

-- ---------- Audit ----------
CREATE TABLE IF NOT EXISTS audit_log (
    ts     TEXT NOT NULL,
    event  TEXT NOT NULL,
    detail TEXT
);
