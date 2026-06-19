import { cn } from "./cn";
import type { Trend } from "@/api/types";
import { trendMeta } from "./tokens";

const toneClass: Record<Trend, string> = {
  improving: "text-ok",
  declining: "text-alert",
  stable: "text-slate-300",
  unknown: "text-slate-500",
};

/** TrendIndicator — directional glyph + optional label for a Trend. */
export function TrendIndicator({
  trend,
  showLabel = false,
  className,
}: {
  trend: Trend;
  showLabel?: boolean;
  className?: string;
}) {
  const meta = trendMeta[trend];
  return (
    <span
      className={cn("inline-flex items-center gap-1 text-xs", toneClass[trend], className)}
      title={meta.label}
    >
      <span aria-hidden className="text-[10px] leading-none">
        {meta.glyph}
      </span>
      {showLabel ? <span>{meta.label}</span> : <span className="sr-only">{meta.label}</span>}
    </span>
  );
}
