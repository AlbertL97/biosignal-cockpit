import { motion } from "framer-motion";
import { cn } from "./cn";
import {
  type Status,
  scoreToStatus,
  statusColor,
  statusLabel,
  motion as motionTokens,
} from "./tokens";

export interface StatRingProps {
  /** 0..100 score, or null for "insufficient data". */
  score: number | null | undefined;
  /** Override the derived status (otherwise computed from score). */
  status?: Status;
  /** Diameter in px. Default 96. */
  size?: number;
  /** Stroke thickness in px. Default 8. */
  thickness?: number;
  /** Center label. Defaults to the score (or "—"). */
  label?: string;
  /** Small caption under the value. */
  caption?: string;
  className?: string;
}

/**
 * StatRing — circular progress gauge colored by status. The track is always
 * visible; "unknown" renders a dashed, desaturated arc to make missing data
 * explicit rather than implying a real value.
 */
export function StatRing({
  score,
  status,
  size = 96,
  thickness = 8,
  label,
  caption,
  className,
}: StatRingProps) {
  const st: Status = status ?? scoreToStatus(score ?? null);
  const color = statusColor[st];
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const pct = st === "unknown" || score == null ? 0 : Math.max(0, Math.min(100, score));
  const dash = (pct / 100) * c;
  const display = label ?? (score == null ? "—" : Math.round(score).toString());

  return (
    <div
      className={cn("relative inline-grid place-items-center", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${caption ? caption + ": " : ""}${
        score == null ? statusLabel.unknown : `${Math.round(score)} of 100`
      }, ${statusLabel[st]}`}
    >
      <svg width={size} height={size} className="-rotate-90">
        {/* track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="rgba(148,163,184,0.16)"
          strokeWidth={thickness}
        />
        {st === "unknown" ? (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeOpacity={0.55}
            strokeWidth={thickness}
            strokeDasharray="3 7"
            strokeLinecap="round"
          />
        ) : (
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={thickness}
            strokeLinecap="round"
            strokeDasharray={c}
            initial={{ strokeDashoffset: c }}
            animate={{ strokeDashoffset: c - dash }}
            transition={{ duration: motionTokens.slow, ease: "easeOut" }}
            style={{ filter: `drop-shadow(0 0 6px ${color}66)` }}
          />
        )}
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div
          className="tnum text-lg font-semibold leading-none"
          style={{ color: st === "unknown" ? "var(--text-muted)" : "#e2e8f0" }}
        >
          {display}
        </div>
        {caption && (
          <div className="mt-1 text-[10px] uppercase tracking-wider text-slate-500">
            {caption}
          </div>
        )}
      </div>
    </div>
  );
}
