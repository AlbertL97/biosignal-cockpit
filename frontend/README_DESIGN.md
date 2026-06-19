# Design System & Avatar — "Biohacker Cockpit"

This document is the contract for the visual design layer built by the DESIGN
agent. The FRONTEND agent consumes these pieces to build data-bound pages.
**Do not restyle from scratch — compose these primitives.**

Aesthetic: dark-mode-first, sci-fi instrumentation, *clinically serious* (never
gimmicky or pseudoscientific). Cyan accent on deep-space surfaces, monospaced
numerals, hairline borders, subtle glows, restrained motion.

---

## 1. Where things live

```
src/
  design/
    tokens.ts          colors, status/score/confidence/evidence maps, motion, domain labels
    theme.css          CSS vars + cockpit utility classes (.cockpit-bg, .panel-surface, glows…)
    cn.ts              clsx wrapper (className helper)
    Panel.tsx          base frosted-glass surface (corner ticks, optional glow)
    SectionHeader.tsx  kicker + title + trailing slot
    Badge.tsx          Badge + StatusBadge (status pills)
    StatRing.tsx       circular score gauge (dashed when unknown)
    ConfidenceMeter.tsx 4-step confidence bar
    EvidenceBadge.tsx  evidence-grade pill (violet = exploratory, red = unsupported)
    GlowButton.tsx     primary/outline/ghost buttons
    Sparkline.tsx      inline trend line (dashed = inferred)
    TrendIndicator.tsx directional glyph for Trend
    ProvenanceTag.tsx  Measured vs Inferred marker
    index.ts           barrel — import everything from "@/design"
  components/
    Avatar/            interactive SVG body (Avatar, regions)
    layout/            AppFrame, CockpitHeader, SideRail (visual chrome)
  App.tsx              runnable cockpit DEMO (static data; replace with real pages)
  main.tsx             React bootstrap
  index.css            font imports + Tailwind + theme.css
```

Import primitives from the barrel:

```tsx
import { Panel, StatRing, StatusBadge, EvidenceBadge, cn } from "@/design";
import { Avatar } from "@/components/Avatar";
import { AppFrame } from "@/components/layout";
```

---

## 2. Tokens & palette decisions

| Token | Value | Use |
|---|---|---|
| `base.900/800/700/600` | `#06090f → #1a2536` | app bg → panels → insets → borders |
| `cyan` / `cyan.glow` | `#22d3ee` / `#67e8f9` | primary accent, instrumentation |
| status `ok` | `#34d399` | supportive / within baseline |
| status `watch` | `#fbbf24` | monitor / mild deviation |
| status `alert` | `#f87171` | attention / notable deviation |
| status `unknown` | `#64748b` | **insufficient data** (always shown, never hidden) |
| evidence `exploratory` | `#a78bfa` (violet) | research-only — visually distinct from status colors |

Helpers in `tokens.ts`:

- `scoreToStatus(score)` — 0..100 → `ok|watch|alert`, `null → unknown`
  (within-person bands, **not** clinical thresholds).
- `statusColor`, `statusLabel`, `confidenceLabel`, `evidenceLabel`,
  `evidenceColor`, `trendMeta`, `domainLabel`, `domainLabelShort`, `motion`.

Fonts: **Inter** (UI) + **JetBrains Mono** (all numbers — use `.tnum`). Loaded
via Google Fonts `@import` in `index.css`, with system fallbacks.

### Measured vs Inferred (mandatory convention — ARCHITECTURE.md §8)

- **Measured** = solid, full-saturation cyan/status color. Use `<ProvenanceTag
  provenance="measured" />`.
- **Inferred** = dashed outline + desaturated. Use `provenance="inferred"`,
  `Sparkline inferred`, and dashed strokes. The avatar's "system" hotspots and
  any `unknown` region render dashed automatically.

---

## 3. Primitive cheat-sheet

```tsx
<Panel glow ticks>…</Panel>                         // frosted surface
<SectionHeader kicker="Domain" title="Gut" trailing={…} />
<StatusBadge status="watch" />                       // dot + "Monitor"
<Badge tone="accent" dot>live</Badge>
<StatRing score={72} caption="score" />              // null score → dashed "—"
<ConfidenceMeter confidence="moderate" />
<EvidenceBadge grade="exploratory" />                // violet research-only pill
<TrendIndicator trend="declining" showLabel />
<Sparkline data={[…]} status="ok" inferred={false} />
<ProvenanceTag provenance="inferred" />
<GlowButton variant="outline" size="sm">Re-run</GlowButton>
```

All primitives: WCAG-AA contrast on dark surfaces, status conveyed by text +
icon (never color alone), keyboard-focusable where interactive
(`.focusable` focus ring), `prefers-reduced-motion` respected.

---

## 4. Avatar API

```tsx
import { Avatar, type AvatarRegion } from "@/components/Avatar";
import type { Domain } from "@/api/types";

const regions: AvatarRegion[] = domains.map(d => ({
  id: d.domain as Domain,         // one of the 9 canonical domains
  status: scoreToStatus(d.score), // "ok" | "watch" | "alert" | "unknown"
  score: d.score,                 // number | null
}));

<Avatar
  regions={regions}
  selected={selectedDomain}        // Domain | null
  onSelectRegion={(id) => navigate(`/domains/${id}`)}
  view="overview"                  // optional system-view switch (see below)
  width={300}                      // height auto from viewBox
/>
```

### Props

| Prop | Type | Notes |
|---|---|---|
| `regions` | `AvatarRegion[]` | `{ id: Domain; status: Status; score?: number\|null }`. Missing domains → `unknown`. |
| `onSelectRegion` | `(id: Domain) => void` | Fired on click / Enter / Space. |
| `selected` | `Domain \| null` | Controlled highlight (brighter glow + thicker outline). |
| `view` | `AvatarView` | `"overview"` (default) or a system view that dims non-members. |
| `width` | `number` | px; default 320. Height derives from the 220×460 viewBox. |
| `className` | `string` | — |

`AvatarView = "overview" | "digestive" | "nervous" | "cardiovascular" |
"musculoskeletal" | "immune" | "metabolic" | "oral"`.

### Region → anatomy mapping

| Domain | Hotspot | Kind |
|---|---|---|
| `brain` | head | organ |
| `oral_dental` | mouth/jaw | organ |
| `cardiovascular` | heart (thorax) | organ |
| `gut` | abdomen (stomach/intestine) | organ |
| `metabolic` | liver (right upper abdomen) | organ |
| `musculoskeletal` | quadriceps (representative muscle) | organ |
| `sleep_recovery` | head/rest halo | **system** (inferred) |
| `stress_autonomic` | throat–chest vagal axis | **system** (inferred) |
| `immune_inflammation` | torso lymphatic core | **system** (inferred) |

`kind: "system"` regions are inferred proxies → rendered **dashed** and the
tooltip carries an "inferred" tag. Edit geometry in
`components/Avatar/regions.ts` (`REGIONS`, `BODY_SILHOUETTE`).

### Behavior

- **Heatmap:** each region glows in its status color. `alert` gently **pulses**
  (2.2s) until hovered/selected. `unknown` is dashed + desaturated.
- **Hover/focus:** tooltip with domain, score, status text, and inferred tag.
- **Keyboard:** every region is `tabIndex=0`, `role="button"`, with an
  `aria-label` combining domain + status + score. Activated with Enter/Space.
- **Reduced motion:** pulses disabled via `prefers-reduced-motion`.

---

## 5. Layout chrome

```tsx
import { AppFrame, type RailItem } from "@/components/layout";

<AppFrame
  navItems={navItems}            // RailItem[] — visual rail; you own routing
  activeNavId={active}
  onNavSelect={setActive}
  statusLine="Last sync 2h ago"
  rightRail={<EvidencePanel … />} // optional right column (hidden < xl)
>
  {/* your routed page */}
</AppFrame>
```

`AppFrame` = `CockpitHeader` + `SideRail` + scrollable `<main>` + optional right
`<aside>`. Chrome is **visual only**; wire routing/state in the FRONTEND layer.

---

## 6. Notes for the FRONTEND agent

- `App.tsx` is a **demo** with static data — replace it with your router + pages,
  but reuse every primitive and the `AppFrame`/`Avatar`. Feel free to lift the
  `DomainCard` / `RightRail` patterns from it.
- Map API `DomainStatus[]` → `AvatarRegion[]` with `scoreToStatus(status.score)`;
  pass `status.score` through for the tooltip/ring value.
- Use `domainLabel` / `domainLabelShort` for display names (don't hardcode).
- Keep the **measured vs inferred** and **uncertainty** conventions: show
  `unknown` regions, dashed inferred data, `missing_data`, `ConfidenceMeter`, and
  `EvidenceBadge` on every interpretation surface.
- Do not edit `src/api/types.ts` (shared contract) or `src/design/*` /
  `src/components/{Avatar,layout}/*` (DESIGN-owned) — extend in your own subtree.

## 7. Build / run

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (proxies /api → :8000)
npm run build    # tsc -b (strict) + vite build — must pass
```
