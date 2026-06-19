import { cn } from "./cn";
import type { Confidence } from "@/api/types";
import { confidenceLabel, confidenceLevel } from "./tokens";

export interface ConfidenceMeterProps {
  confidence: Confidence;
  /** Show the text label next to the bars. Default true. */
  showLabel?: boolean;
  className?: string;
}

/**
 * ConfidenceMeter — 4-segment stepped bar (exploratory → high). Communicates
 * how much the interpretation can be trusted, separate from evidence grade.
 */
export function ConfidenceMeter({
  confidence,
  showLabel = true,
  className,
}: ConfidenceMeterProps) {
  const level = confidenceLevel[confidence]; // 1..4
  return (
    <div
      className={cn("inline-flex items-center gap-2", className)}
      role="meter"
      aria-valuemin={1}
      aria-valuemax={4}
      aria-valuenow={level}
      aria-label={confidenceLabel[confidence]}
      title={confidenceLabel[confidence]}
    >
      <div className="flex items-end gap-0.5" aria-hidden>
        {[1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className={cn(
              "w-1.5 rounded-sm transition-colors",
              i <= level ? "bg-cyan" : "bg-slate-600/50",
            )}
            style={{ height: 4 + i * 3 }}
          />
        ))}
      </div>
      {showLabel && (
        <span className="text-[11px] text-slate-400">
          {confidenceLabel[confidence]}
        </span>
      )}
    </div>
  );
}
