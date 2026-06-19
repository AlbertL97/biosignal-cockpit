import { cn } from "./cn";
import type { EvidenceGrade } from "@/api/types";
import { evidenceColor, evidenceLabel } from "./tokens";

export interface EvidenceBadgeProps {
  grade: EvidenceGrade;
  /** Compact mode: dot + short label only. Default false. */
  compact?: boolean;
  className?: string;
}

/**
 * EvidenceBadge — grades the scientific support behind an interpretation
 * (distinct from ConfidenceMeter, which grades data-driven certainty). The
 * "exploratory" grade is violet to clearly mark research-only claims, and
 * "unsupported" is red per the project's evidence policy (task §5).
 */
export function EvidenceBadge({ grade, compact, className }: EvidenceBadgeProps) {
  const color = evidenceColor[grade];
  const label = evidenceLabel[grade];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5",
        "text-[11px] font-medium leading-none",
        className,
      )}
      style={{
        color,
        borderColor: `${color}55`,
        backgroundColor: `${color}1a`,
      }}
      title={`Evidence: ${label}`}
    >
      <span
        aria-hidden
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: color }}
      />
      {compact ? label.replace(/ evidence$/i, "") : label}
    </span>
  );
}
