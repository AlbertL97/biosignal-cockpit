import { useId, useMemo, useState, type KeyboardEvent } from "react";
import { motion } from "framer-motion";
import type { Domain } from "@/api/types";
import {
  cn,
  domainLabelShort,
  statusColor,
  statusLabel,
  type Status,
} from "@/design";
import {
  AVATAR_VIEWBOX,
  BODY_SILHOUETTE,
  REGIONS,
  type RegionDef,
} from "./regions";

/** One region's status payload (provided by the FRONTEND agent from API data). */
export interface AvatarRegion {
  id: Domain;
  status: Status; // "ok" | "watch" | "alert" | "unknown"
  /** 0..100 domain score, or null when insufficient data. */
  score?: number | null;
}

export interface AvatarProps {
  /** Status per domain. Missing domains default to "unknown". */
  regions: AvatarRegion[];
  /** Fired when a region is activated (click / Enter / Space). */
  onSelectRegion?: (id: Domain) => void;
  /** Currently selected domain (controlled highlight). */
  selected?: Domain | null;
  /**
   * View mode. "overview" shows all regions; a system name dims regions outside
   * that system to support the system-view switch (task §7). Reserved for the
   * FRONTEND agent — defaults to "overview".
   */
  view?: AvatarView;
  /** Pixel width; height scales to the viewBox aspect ratio. Default 320. */
  width?: number;
  className?: string;
}

export type AvatarView =
  | "overview"
  | "digestive"
  | "nervous"
  | "cardiovascular"
  | "musculoskeletal"
  | "immune"
  | "metabolic"
  | "oral";

/** Which domains belong to each system view (for dimming non-members). */
const VIEW_MEMBERS: Record<AvatarView, Domain[] | "all"> = {
  overview: "all",
  digestive: ["gut", "metabolic"],
  nervous: ["brain", "stress_autonomic", "sleep_recovery"],
  cardiovascular: ["cardiovascular"],
  musculoskeletal: ["musculoskeletal"],
  immune: ["immune_inflammation"],
  metabolic: ["metabolic", "gut"],
  oral: ["oral_dental"],
};

interface TooltipState {
  region: RegionDef;
  status: Status;
  score?: number | null;
  x: number;
  y: number;
}

/**
 * Avatar — interactive front-view human body. Regions glow/heatmap by status,
 * hovering shows a tooltip, the selected region is highlighted, and "unknown"
 * regions render dashed + desaturated so uncertainty stays visible.
 *
 * Accessibility: each region is a keyboard-focusable button with an aria-label
 * combining domain, status and score. Status is never conveyed by color alone —
 * the tooltip and aria-label always carry the text status.
 *
 * Measured vs inferred: "system" hotspots (sleep, stress, immune) are inferred
 * proxies and are rendered with a dashed outline + an "inferred" tooltip note;
 * "organ" hotspots map to directly-measured-adjacent regions.
 */
export function Avatar({
  regions,
  onSelectRegion,
  selected = null,
  view = "overview",
  width = 320,
  className,
}: AvatarProps) {
  const gradId = useId();
  const [hovered, setHovered] = useState<Domain | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const statusById = useMemo(() => {
    const m = new Map<Domain, AvatarRegion>();
    for (const r of regions) m.set(r.id, r);
    return m;
  }, [regions]);

  const members = VIEW_MEMBERS[view];
  const inView = (id: Domain) => members === "all" || members.includes(id);

  const { w, h } = AVATAR_VIEWBOX;
  const height = (width / w) * h;

  const handleKey = (e: KeyboardEvent, id: Domain) => {
    if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
      e.preventDefault();
      onSelectRegion?.(id);
    }
  };

  return (
    <div
      className={cn("relative select-none", className)}
      style={{ width }}
      onMouseLeave={() => {
        setHovered(null);
        setTooltip(null);
      }}
    >
      <svg
        viewBox={`0 0 ${w} ${h}`}
        width={width}
        height={height}
        role="group"
        aria-label="Interactive body map. Select a region to open its report."
        className="overflow-visible"
      >
        <defs>
          <radialGradient id={`bodyfill-${gradId}`} cx="50%" cy="30%" r="80%">
            <stop offset="0%" stopColor="#16243a" />
            <stop offset="100%" stopColor="#0a1018" />
          </radialGradient>
          <filter id={`soft-${gradId}`} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="3" />
          </filter>
        </defs>

        {/* base silhouette */}
        <path
          d={BODY_SILHOUETTE}
          fill={`url(#bodyfill-${gradId})`}
          stroke="rgba(34,211,238,0.25)"
          strokeWidth={1.2}
        />
        {/* faint centerline + scan accent */}
        <line
          x1={w / 2}
          y1={20}
          x2={w / 2}
          y2={h - 30}
          stroke="rgba(34,211,238,0.10)"
          strokeWidth={1}
          strokeDasharray="2 6"
        />

        {REGIONS.map((region) => {
          const data = statusById.get(region.id);
          const status: Status = data?.status ?? "unknown";
          const color = statusColor[status];
          const isSelected = selected === region.id;
          const isHover = hovered === region.id;
          const dim = !inView(region.id);
          const inferred = region.kind === "system" || status === "unknown";
          const active = isSelected || isHover;

          return (
            <g
              key={region.id}
              opacity={dim ? 0.18 : 1}
              style={{ transition: "opacity 0.28s ease" }}
              tabIndex={dim ? -1 : 0}
              role="button"
              aria-label={`${region.label}: ${statusLabel[status]}${
                data?.score != null ? `, score ${Math.round(data.score)} of 100` : ""
              }. ${region.note}`}
              aria-pressed={isSelected}
              className="focusable cursor-pointer outline-none"
              onClick={() => !dim && onSelectRegion?.(region.id)}
              onKeyDown={(e) => !dim && handleKey(e, region.id)}
              onMouseEnter={() => {
                if (dim) return;
                setHovered(region.id);
                setTooltip({
                  region,
                  status,
                  score: data?.score,
                  x: region.center.x,
                  y: region.center.y,
                });
              }}
              onFocus={() => {
                if (dim) return;
                setHovered(region.id);
                setTooltip({
                  region,
                  status,
                  score: data?.score,
                  x: region.center.x,
                  y: region.center.y,
                });
              }}
              onBlur={() => {
                setHovered(null);
                setTooltip(null);
              }}
            >
              {/* glow halo (pulses on alert) */}
              <motion.path
                d={region.path}
                fill={color}
                filter={`url(#soft-${gradId})`}
                initial={false}
                animate={{
                  opacity:
                    status === "alert"
                      ? active
                        ? 0.85
                        : [0.35, 0.7, 0.35]
                      : active
                        ? 0.7
                        : 0.32,
                }}
                transition={
                  status === "alert" && !active
                    ? { duration: 2.2, repeat: Infinity, ease: "easeInOut" }
                    : { duration: 0.28 }
                }
              />
              {/* crisp region outline */}
              <path
                d={region.path}
                fill={active ? `${color}33` : `${color}14`}
                stroke={color}
                strokeWidth={isSelected ? 2 : 1.2}
                strokeDasharray={inferred ? "3 3" : undefined}
                strokeOpacity={status === "unknown" ? 0.6 : 0.95}
                strokeLinejoin="round"
                style={{ transition: "all 0.2s ease" }}
              />
              {/* anatomical inner detail (gyri, vessels, striations) */}
              {region.detail && (
                <path
                  d={region.detail}
                  fill="none"
                  stroke={color}
                  strokeWidth={0.8}
                  strokeOpacity={active ? 0.8 : 0.45}
                  strokeLinecap="round"
                  style={{ transition: "all 0.2s ease" }}
                />
              )}
            </g>
          );
        })}
      </svg>

      {tooltip && (
        <RegionTooltip
          tooltip={tooltip}
          containerWidth={width}
          viewBox={AVATAR_VIEWBOX}
        />
      )}
    </div>
  );
}

function RegionTooltip({
  tooltip,
  containerWidth,
  viewBox,
}: {
  tooltip: TooltipState;
  containerWidth: number;
  viewBox: { w: number; h: number };
}) {
  const scale = containerWidth / viewBox.w;
  const left = tooltip.x * scale;
  const top = tooltip.y * scale;
  const right = tooltip.region.labelSide === "right";
  const color = statusColor[tooltip.status];
  const inferred = tooltip.region.kind === "system";

  return (
    <div
      role="tooltip"
      className={cn(
        "pointer-events-none absolute z-10 w-44 -translate-y-1/2 rounded-md panel-surface px-3 py-2 text-xs shadow-xl",
        right ? "translate-x-3" : "-translate-x-[calc(100%+0.75rem)]",
      )}
      style={{ left, top, borderColor: `${color}55` }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-slate-100">
          {domainLabelShort[tooltip.region.id] ?? tooltip.region.label}
        </span>
        <span
          className="tnum text-sm font-semibold"
          style={{ color }}
        >
          {tooltip.score == null ? "—" : Math.round(tooltip.score)}
        </span>
      </div>
      <div className="mt-0.5 flex items-center gap-1.5">
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{ backgroundColor: color }}
        />
        <span className="text-slate-300">{statusLabel[tooltip.status]}</span>
        {inferred && (
          <span className="ml-auto rounded border border-dashed border-slate-500/60 px-1 text-[9px] uppercase tracking-wide text-slate-400">
            inferred
          </span>
        )}
      </div>
      <p className="mt-1 leading-snug text-slate-500">{tooltip.region.note}</p>
    </div>
  );
}
