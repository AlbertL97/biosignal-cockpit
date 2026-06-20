// Geometry + metadata for the interactive avatar's clickable regions.
// Body drawn in a 240 x 520 viewBox (front view). Organ glyphs are positioned to
// align with the silhouette below, and shaped to be recognizable:
//  - brain            -> lobed brain in the head
//  - sleep_recovery   -> crescent moon docked at the head (system overlay)
//  - oral_dental      -> teeth/mouth at the jaw
//  - stress_autonomic -> vagal/throat node in the neck (system overlay)
//  - cardiovascular   -> ANATOMICAL heart in the chest
//  - metabolic        -> STOMACH in the upper-left abdomen
//  - gut              -> coiled INTESTINES / digestive tract in the abdomen
//  - immune_inflammation -> lymph-node cluster (system overlay)
//  - musculoskeletal  -> both thigh muscle groups (aligned to the legs)

import type { Domain } from "@/api/types";
import { domainLabel } from "@/design/tokens";

export const AVATAR_VIEWBOX = { w: 240, h: 520 } as const;

/** How a region is anchored/represented anatomically. */
export type RegionKind = "organ" | "system";

export interface RegionDef {
  id: Domain;
  label: string;
  kind: RegionKind;
  note: string;
  /** Filled/heatmap shape (in viewBox coords). */
  path: string;
  /** Optional thin inner-detail stroke for higher fidelity (no fill). */
  detail?: string;
  /** Center point for tooltip anchoring. */
  center: { x: number; y: number };
  labelSide: "left" | "right";
}

export const REGIONS: RegionDef[] = [
  {
    id: "brain",
    label: domainLabel.brain,
    kind: "organ",
    note: "Cognition & recovery (cerebrum).",
    path:
      "M120 32 C107 32 99 39 100 48 C94 49 92 56 97 61 C95 67 101 72 108 70 " +
      "C111 74 116 75 120 75 C124 75 129 74 132 70 C139 72 145 67 143 61 " +
      "C148 56 146 49 140 48 C141 39 133 32 120 32 Z",
    detail:
      "M120 34 L120 73 M120 47 C112 50 108 46 107 42 M120 47 C128 50 132 46 133 42 " +
      "M120 59 C111 62 106 58 104 54 M120 59 C129 62 134 58 136 54",
    center: { x: 120, y: 52 },
    labelSide: "right",
  },
  {
    id: "sleep_recovery",
    label: domainLabel.sleep_recovery,
    kind: "system",
    note: "Sleep & recovery axis (inferred from sleep + HRV).",
    path: "M150 21 a15 15 0 1 0 5 27 a11 11 0 1 1 -5 -27 Z",
    center: { x: 152, y: 35 },
    labelSide: "right",
  },
  {
    id: "oral_dental",
    label: domainLabel.oral_dental,
    kind: "organ",
    note: "Oral cavity & teeth (jaw).",
    path: "M108 69 q12 7 24 0 l0 7 q-12 6 -24 0 Z",
    detail: "M114 69 l0 11 M120 70 l0 11 M126 69 l0 11 M108 74 q12 5 24 0",
    center: { x: 120, y: 73 },
    labelSide: "left",
  },
  {
    id: "stress_autonomic",
    label: domainLabel.stress_autonomic,
    kind: "system",
    note: "Autonomic / vagal axis, throat–chest (inferred from HRV).",
    path: "M113 80 q7 -4 14 0 q3 8 -1 14 q-8 4 -13 -1 q-2 -8 0 -13 Z",
    detail: "M120 94 q-6 9 0 18 q6 9 0 18",
    center: { x: 120, y: 88 },
    labelSide: "right",
  },
  {
    id: "cardiovascular",
    label: domainLabel.cardiovascular,
    kind: "organ",
    note: "Heart & circulation.",
    // anatomical heart: vessels at top, apex toward lower-left
    path:
      "M110 120 C100 112 86 117 88 131 C90 144 101 153 114 163 " +
      "C120 156 129 150 135 141 C143 130 141 118 130 119 " +
      "C124 120 120 125 118 130 C115 125 113 122 110 120 Z",
    detail:
      "M108 120 C106 104 98 100 93 104 M120 122 C123 106 133 104 138 110 " +
      "M116 128 C121 140 119 152 116 162 M100 131 C108 137 112 135 116 133",
    center: { x: 116, y: 138 },
    labelSide: "left",
  },
  {
    id: "metabolic",
    label: domainLabel.metabolic,
    kind: "organ",
    note: "Stomach / metabolic processing (upper-left abdomen).",
    // J-shaped stomach
    path:
      "M98 162 C84 164 82 184 96 195 C107 203 124 200 127 188 C129 180 122 176 115 179 " +
      "C112 180 111 185 113 189 C103 191 94 185 94 176 C94 169 99 165 105 166 " +
      "C111 167 113 172 110 176 C119 174 118 162 107 160 C103 159 100 160 98 162 Z",
    detail: "M99 178 q12 6 22 3 M101 186 q9 4 16 1",
    center: { x: 105, y: 183 },
    labelSide: "left",
  },
  {
    id: "immune_inflammation",
    label: domainLabel.immune_inflammation,
    kind: "system",
    note: "Lymphatic / inflammatory nodes (inferred — no direct labs).",
    path:
      "M110 100 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0 Z " +
      "M130 100 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0 Z " +
      "M86 150 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0 Z " +
      "M154 150 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0 Z " +
      "M108 258 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0 Z " +
      "M132 258 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0 Z",
    center: { x: 120, y: 150 },
    labelSide: "right",
  },
  {
    id: "gut",
    label: domainLabel.gut,
    kind: "organ",
    note: "Stomach, intestines & digestive tract (abdomen).",
    path: "M95 202 Q120 196 145 202 Q150 230 144 256 Q120 264 96 256 Q90 230 95 202 Z",
    // colon frame (inverted U) + small-intestine coils — a tract, not flat lines
    detail:
      "M105 252 Q98 252 98 242 L98 216 Q98 209 107 209 L133 209 Q142 209 142 216 " +
      "L142 242 Q142 252 135 252 " +
      "M110 215 C103 220 103 227 110 231 C117 235 117 242 110 246 " +
      "M122 215 C115 220 115 227 122 231 C129 235 129 242 122 246 " +
      "M134 215 C141 220 141 227 134 231 C127 235 127 242 134 246",
    center: { x: 120, y: 230 },
    labelSide: "left",
  },
  {
    id: "musculoskeletal",
    label: domainLabel.musculoskeletal,
    kind: "organ",
    note: "Large muscle groups (quadriceps).",
    path:
      "M95 274 Q92 316 98 358 Q104 362 112 358 Q116 316 113 274 Q104 270 95 274 Z " +
      "M127 274 Q124 316 130 358 Q136 362 144 358 Q148 316 145 274 Q136 270 127 274 Z",
    detail: "M104 284 L104 352 M136 284 L136 352",
    center: { x: 120, y: 320 },
    labelSide: "right",
  },
];

/** Static silhouette path drawn under the regions (head, neck, torso, arms, legs). */
export const BODY_SILHOUETTE =
  // head
  "M120 22 a28 28 0 1 0 0 56 a28 28 0 1 0 0 -56 Z " +
  // neck
  "M111 76 h18 v18 h-18 Z " +
  // torso
  "M80 104 Q120 94 160 104 L153 200 Q151 240 150 266 Q120 274 90 266 Q89 240 87 200 Z " +
  // left arm
  "M82 108 Q66 114 64 152 L62 240 Q62 250 72 250 Q81 250 81 240 L86 156 Q88 126 92 116 Z " +
  // right arm
  "M158 108 Q174 114 176 152 L178 240 Q178 250 168 250 Q159 250 159 240 L154 156 Q152 126 148 116 Z " +
  // left leg
  "M91 268 L117 268 L114 386 L112 502 L96 502 L94 386 Z " +
  // right leg
  "M123 268 L149 268 L146 386 L144 502 L128 502 L126 386 Z";
