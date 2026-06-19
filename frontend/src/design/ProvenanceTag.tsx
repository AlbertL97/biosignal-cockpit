import { cn } from "./cn";
import type { Provenance } from "./tokens";

/**
 * ProvenanceTag — explicit "Measured" vs "Inferred" marker. Required to keep the
 * directly-measured / cautiously-inferred distinction visible everywhere
 * (ARCHITECTURE.md §8). Measured = solid cyan; Inferred = dashed, desaturated.
 */
export function ProvenanceTag({
  provenance,
  className,
}: {
  provenance: Provenance;
  className?: string;
}) {
  const measured = provenance === "measured";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        measured
          ? "border border-cyan/30 bg-cyan/10 text-cyan"
          : "border border-dashed border-slate-500/50 bg-transparent text-slate-400",
        className,
      )}
      title={measured ? "Directly measured value" : "Cautiously inferred — not directly measured"}
    >
      {measured ? "Measured" : "Inferred"}
    </span>
  );
}
