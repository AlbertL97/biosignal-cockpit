// Shared API contract types. Mirror of backend/app/models/contracts.py.
// Keep both in sync (see docs/ARCHITECTURE.md §6–§7).

export type Confidence = "high" | "moderate" | "low" | "exploratory";
export type EvidenceGrade =
  | "high"
  | "moderate"
  | "low"
  | "exploratory"
  | "unsupported";
export type Trend = "improving" | "stable" | "declining" | "unknown";

export interface Contribution {
  source: "apple_health" | "genome" | "nebula" | "nutrition" | string;
  metric: string;
  value: number | string | null;
  weight: number; // 0..1
  direction: "supportive" | "adverse" | "neutral" | "uncertain";
}

export interface Driver {
  factor: string;
  direction: "raising" | "lowering" | "neutral" | string;
  detail: string;
}

export interface EvidenceRef {
  claim: string;
  grade: EvidenceGrade;
  pmid: string | null;
  title: string | null;
  year: number | null;
  url: string | null;
  source: "pubmed" | "nebula" | "guideline" | "curated" | string;
}

export interface DomainStatus {
  domain: string;
  score: number | null; // 0..100
  score_label: string;
  trend: Trend;
  confidence: Confidence;
  evidence_grade: EvidenceGrade;
  summary: string;
  observations: string[];
  derived: string[];
  inferences: string[];
  hypotheses: string[];
  recommendations: string[];
  contributions: Contribution[];
  evidence: EvidenceRef[];
  missing_data: string[];
  drivers: Driver[];
  levers: string[];
  as_of: string;
}

export interface TimePoint {
  ts: string;
  value: number;
}

export interface MetricSeries {
  metric: string;
  unit: string | null;
  points: TimePoint[];
  baseline_mean: number | null;
  baseline_sd: number | null;
}

export interface TraitVariant {
  rsid: string;
  genotype: string | null;
  gene: string | null;
  effect_size: number | null;
  frequency: number | null;
  p_value: number | null;
  highlighted: boolean;
}

export interface NebulaTrait {
  id: number;
  trait: string;
  category: string | null;
  citation: string | null;
  percentile: number | null;
  score: number | null;
  score_label: string | null;
  variants: TraitVariant[];
  description?: string | null;
  interpretation?: string | null;
}

export interface Highlight {
  label: string;
  value: string; // preformatted, e.g. "54 bpm"
  detail: string | null;
}

export interface Profile {
  dob: string | null;
  biological_sex: string | null;
  blood_type: string | null;
  skin_type: string | null;
  coverage: Record<string, number>;
  highlights: Highlight[];
}

// The nine canonical domains in this build.
export const DOMAINS = [
  "gut",
  "brain",
  "cardiovascular",
  "oral_dental",
  "musculoskeletal",
  "metabolic",
  "sleep_recovery",
  "stress_autonomic",
  "immune_inflammation",
] as const;
export type Domain = (typeof DOMAINS)[number];
