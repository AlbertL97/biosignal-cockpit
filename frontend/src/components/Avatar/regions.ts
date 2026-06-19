// Geometry + metadata for the interactive avatar's clickable regions.
// Body drawn in a 240 x 500 viewBox (front view). Each domain maps to an
// anatomically-placed, recognizable glyph aligned to the silhouette:
//  - brain          -> lobed brain inside the head
//  - oral_dental    -> teeth/mouth at the jaw
//  - cardiovascular -> heart in the chest
//  - metabolic      -> liver under the right ribs
//  - gut            -> coiled intestines in the abdomen
//  - musculoskeletal-> both thigh muscle groups
//  - stress_autonomic -> vagal/throat node (system overlay, inferred)
//  - immune_inflammation -> lymph-node cluster (system overlay, inferred)
//  - sleep_recovery -> crescent moon docked at the head (system overlay, inferred)

import type { Domain } from "@/api/types";
import { domainLabel } from "@/design/tokens";

export const AVATAR_VIEWBOX = { w: 240, h: 500 } as const;

/** How a region is anchored/represented anatomically. */
export type RegionKind = "organ" | "system";

export interface RegionDef {
  id: Domain;
  label: string;
  kind: RegionKind;
  /** Short note shown in tooltip/aria. */
  note: string;
  /** Filled/heatmap shape (in viewBox coords). */
  path: string;
  /** Optional thin inner-detail stroke for higher fidelity (no fill). */
  detail?: string;
  /** Center point for tooltip anchoring. */
  center: { x: number; y: number };
  /** Side the callout label sits on. */
  labelSide: "left" | "right";
}

export const REGIONS: RegionDef[] = [
  {
    id: "brain",
    label: domainLabel.brain,
    kind: "organ",
    note: "Cognition & recovery (cerebrum).",
    path:
      "M120 33 c-13 0 -22 7 -22 16 c-6 1 -9 8 -4 13 c-3 6 2 12 9 11 " +
      "c3 4 9 5 17 5 c8 0 14 -1 17 -5 c7 1 12 -5 9 -11 c5 -5 2 -12 -4 -13 " +
      "c0 -9 -9 -16 -22 -16 Z",
    detail:
      "M120 35 l0 42 M120 50 q-11 4 -12 -4 M120 50 q11 4 12 -4 " +
      "M120 62 q-12 5 -14 -2 M120 62 q12 5 14 -2",
    center: { x: 120, y: 54 },
    labelSide: "right",
  },
  {
    id: "sleep_recovery",
    label: domainLabel.sleep_recovery,
    kind: "system",
    note: "Sleep & recovery axis (inferred from sleep + HRV).",
    // crescent moon docked against the head's upper-right
    path: "M168 26 a16 16 0 1 0 6 27 a12 12 0 1 1 -6 -27 Z",
    center: { x: 170, y: 40 },
    labelSide: "right",
  },
  {
    id: "oral_dental",
    label: domainLabel.oral_dental,
    kind: "organ",
    note: "Oral cavity & teeth (jaw).",
    path: "M107 74 q13 8 26 0 l0 9 q-13 7 -26 0 Z",
    detail: "M113 75 l0 11 M120 76 l0 11 M127 75 l0 11 M107 80 q13 6 26 0",
    center: { x: 120, y: 80 },
    labelSide: "left",
  },
  {
    id: "stress_autonomic",
    label: domainLabel.stress_autonomic,
    kind: "system",
    note: "Autonomic / vagal axis, throat–chest (inferred from HRV).",
    path: "M113 92 q7 -5 14 0 q3 11 -2 18 q-9 5 -14 -2 q-2 -9 2 -16 Z",
    detail: "M120 110 q-7 11 0 22 q7 11 0 22",
    center: { x: 120, y: 104 },
    labelSide: "right",
  },
  {
    id: "cardiovascular",
    label: domainLabel.cardiovascular,
    kind: "organ",
    note: "Heart & circulation.",
    path:
      "M114 130 c-7 -11 -24 -8 -24 5 c0 13 15 23 24 31 c9 -8 24 -18 24 -31 " +
      "c0 -13 -17 -16 -24 -5 Z",
    detail: "M114 130 q-5 -11 -13 -12 M114 130 q5 -11 13 -12 M101 140 q9 8 13 6",
    center: { x: 114, y: 144 },
    labelSide: "left",
  },
  {
    id: "metabolic",
    label: domainLabel.metabolic,
    kind: "organ",
    note: "Liver / metabolic processing (right upper abdomen).",
    path: "M84 170 q36 -9 54 1 q-2 17 -23 19 q-23 0 -31 -9 q-2 -6 0 -11 Z",
    detail: "M95 175 l20 7 M100 184 q12 2 22 -2",
    center: { x: 108, y: 180 },
    labelSide: "left",
  },
  {
    id: "immune_inflammation",
    label: domainLabel.immune_inflammation,
    kind: "system",
    note: "Lymphatic / inflammatory nodes (inferred — no direct labs).",
    // cluster of lymph nodes: neck, axillae, groin
    path:
      "M103 98 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0 Z " +
      "M137 98 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0 Z " +
      "M86 156 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0 Z " +
      "M154 156 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0 Z " +
      "M104 262 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0 Z " +
      "M136 262 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0 Z",
    center: { x: 120, y: 156 },
    labelSide: "right",
  },
  {
    id: "gut",
    label: domainLabel.gut,
    kind: "organ",
    note: "Stomach & intestines (abdomen).",
    path: "M92 198 q28 -8 56 0 q9 30 -2 52 q-26 12 -52 0 q-10 -23 -2 -52 Z",
    detail:
      "M100 208 q20 -5 40 0 M98 221 q22 -3 44 0 M100 234 q20 4 40 0 M120 202 l0 44",
    center: { x: 120, y: 226 },
    labelSide: "left",
  },
  {
    id: "musculoskeletal",
    label: domainLabel.musculoskeletal,
    kind: "organ",
    note: "Large muscle groups (quadriceps).",
    path:
      "M92 312 q-7 42 0 82 q12 6 23 0 q5 -42 -2 -82 q-11 -5 -21 0 Z " +
      "M127 312 q-6 40 -2 82 q11 6 23 0 q6 -40 0 -82 q-11 -5 -21 0 Z",
    detail: "M103 326 q2 30 0 58 M137 326 q2 30 0 58",
    center: { x: 120, y: 360 },
    labelSide: "right",
  },
];

/** Static silhouette path drawn under the regions (non-interactive body). */
export const BODY_SILHOUETTE =
  // head (circle) + neck
  "M120 24 a30 30 0 0 1 0 60 a30 30 0 0 1 0 -60 Z " +
  // torso + arms + legs
  "M112 86 q8 6 16 0 l1 13 l30 12 q15 6 17 23 l8 55 q1 9 -8 10 q-9 1 -11 -8 " +
  "l-6 -43 l-9 -4 l3 70 l-2 62 l10 95 q1 9 -9 10 l-6 0 q-8 0 -9 -9 l-9 -90 " +
  "l-6 0 l-9 90 q-1 9 -9 9 l-6 0 q-10 -1 -9 -10 l10 -95 l-2 -62 l3 -70 l-9 4 " +
  "l-6 43 q-2 9 -11 8 q-9 -1 -8 -10 l8 -55 q2 -17 17 -23 l30 -12 l1 -13 Z";
