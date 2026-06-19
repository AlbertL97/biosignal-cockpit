import { cn } from "@/design";

export interface PercentileBarProps {
  /** Percentile 0..100, or null when unknown. */
  percentile: number | null;
  /** Compact height for cards. Default false. */
  compact?: boolean;
  className?: string;
}

/**
 * PercentileBar — horizontal gauge for a polygenic percentile. Percentiles are
 * population-relative and non-deterministic, so the scale is labelled and the
 * marker is a position, not a verdict.
 */
export function PercentileBar({ percentile, compact = false, className }: PercentileBarProps) {
  const known = percentile != null && !Number.isNaN(percentile);
  const clamped = known ? Math.max(0, Math.min(100, percentile)) : 0;

  return (
    <div className={cn("w-full", className)}>
      <div className="mb-1 flex items-center justify-between text-[11px] text-slate-500">
        <span>Percentile</span>
        <span className="tnum font-semibold text-slate-300">
          {known ? `${Math.round(clamped)}th` : "—"}
        </span>
      </div>
      <div
        className={cn(
          "relative w-full overflow-hidden rounded-full bg-slate-600/40",
          compact ? "h-1.5" : "h-2.5",
        )}
        role="img"
        aria-label={
          known
            ? `${Math.round(clamped)}th percentile (population-relative, non-deterministic)`
            : "Percentile unknown"
        }
      >
        {known ? (
          <>
            <div
              className="h-full rounded-full bg-gradient-to-r from-cyan/40 to-cyan"
              style={{ width: `${clamped}%` }}
            />
            <span
              aria-hidden
              className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 rounded bg-white/90"
              style={{ left: `calc(${clamped}% - 1px)` }}
            />
          </>
        ) : (
          <div className="h-full w-full bg-[repeating-linear-gradient(45deg,rgba(100,116,139,0.3)_0,rgba(100,116,139,0.3)_4px,transparent_4px,transparent_8px)]" />
        )}
      </div>
    </div>
  );
}
