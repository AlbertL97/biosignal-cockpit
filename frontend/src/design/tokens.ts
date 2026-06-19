// Design tokens for the "futuristic biohacker cockpit" system.
// Dark-mode-first, sci-fi but clinically serious. These TS tokens mirror the
// Tailwind palette (tailwind.config.js) and the CSS custom properties in
// theme.css. Import these when you need token values inside JS (e.g. SVG fills,
// framer-motion colors) rather than utility classes.
//
// See README_DESIGN.md for usage guidance.

import type {
  Confidence,
  EvidenceGrade,
  Trend,
} from "@/api/types";

/** Canonical status used by status rings, badges and the avatar heatmap. */
export type Status = "ok" | "watch" | "alert" | "unknown";

/** Core surface + accent palette. Keep in sync with tailwind.config.js. */
export const palette = {
  base: {
    900: "#06090f", // app background (deep space)
    800: "#0b111b", // panel background
    700: "#121a28", // raised panel / inset
    600: "#1a2536", // borders / hovered surfaces
  },
  cyan: {
    DEFAULT: "#22d3ee", // primary accent (instrumentation glow)
    glow: "#67e8f9",
  },
  // Semantic status colors. Chosen for WCAG AA contrast on base.800/.900.
  status: {
    ok: "#34d399", // supportive / within baseline
    watch: "#fbbf24", // monitor / mild deviation
    alert: "#f87171", // attention / notable deviation
    unknown: "#64748b", // insufficient data / uncertain
  },
  text: {
    primary: "#e2e8f0", // slate-200
    secondary: "#94a3b8", // slate-400
    muted: "#64748b", // slate-500
  },
} as const;

/** Map a Status to its hex color. */
export const statusColor: Record<Status, string> = {
  ok: palette.status.ok,
  watch: palette.status.watch,
  alert: palette.status.alert,
  unknown: palette.status.unknown,
};

/** Human-readable status labels (non-diagnostic wording). */
export const statusLabel: Record<Status, string> = {
  ok: "Supportive",
  watch: "Monitor",
  alert: "Attention",
  unknown: "Insufficient data",
};

/**
 * Map a 0..100 domain score (or null) to a coarse Status. Within-person, not a
 * clinical threshold — see ARCHITECTURE.md §8. Null/undefined => "unknown".
 */
export function scoreToStatus(score: number | null | undefined): Status {
  if (score == null || Number.isNaN(score)) return "unknown";
  if (score >= 70) return "ok";
  if (score >= 45) return "watch";
  return "alert";
}

/** Confidence ordering + display metadata for ConfidenceMeter. */
export const confidenceOrder: Confidence[] = [
  "exploratory",
  "low",
  "moderate",
  "high",
];

export const confidenceLevel: Record<Confidence, number> = {
  exploratory: 1,
  low: 2,
  moderate: 3,
  high: 4,
};

export const confidenceLabel: Record<Confidence, string> = {
  high: "High confidence",
  moderate: "Moderate confidence",
  low: "Low confidence",
  exploratory: "Exploratory",
};

/** Evidence grade display metadata for EvidenceBadge. */
export const evidenceLabel: Record<EvidenceGrade, string> = {
  high: "Strong evidence",
  moderate: "Moderate evidence",
  low: "Limited evidence",
  exploratory: "Exploratory",
  unsupported: "Unsupported",
};

export const evidenceColor: Record<EvidenceGrade, string> = {
  high: palette.status.ok,
  moderate: palette.cyan.DEFAULT,
  low: palette.status.watch,
  exploratory: "#a78bfa", // violet — clearly "research only"
  unsupported: palette.status.alert,
};

/** Trend display metadata (glyph + accessible label). */
export const trendMeta: Record<Trend, { glyph: string; label: string }> = {
  improving: { glyph: "▲", label: "Improving" },
  stable: { glyph: "■", label: "Stable" },
  declining: { glyph: "▼", label: "Declining" },
  unknown: { glyph: "–", label: "Trend unknown" },
};

/**
 * Provenance of a value: directly MEASURED vs cautiously INFERRED.
 * This distinction is mandatory across the UI (ARCHITECTURE.md §8). The avatar
 * and primitives render inferred data with a dashed / desaturated treatment.
 */
export type Provenance = "measured" | "inferred";

/** Canonical human-readable names for the nine domains. */
export const domainLabel: Record<string, string> = {
  gut: "Gut",
  brain: "Brain & Cognition",
  cardiovascular: "Cardiovascular",
  oral_dental: "Oral / Dental",
  musculoskeletal: "Musculoskeletal",
  metabolic: "Metabolic",
  sleep_recovery: "Sleep & Recovery",
  stress_autonomic: "Stress & Autonomic",
  immune_inflammation: "Immune & Inflammation",
};

/** Short labels for tight spaces (avatar tooltips, compact cards). */
export const domainLabelShort: Record<string, string> = {
  gut: "Gut",
  brain: "Brain",
  cardiovascular: "Heart",
  oral_dental: "Oral",
  musculoskeletal: "Muscles",
  metabolic: "Metabolic",
  sleep_recovery: "Sleep",
  stress_autonomic: "Stress",
  immune_inflammation: "Immune",
};

/** Motion timings (seconds) — keep animations subtle and clinical. */
export const motion = {
  fast: 0.18,
  base: 0.28,
  slow: 0.5,
  pulse: 2.2, // gentle alert pulse period
} as const;
