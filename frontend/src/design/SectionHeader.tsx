import type { ReactNode } from "react";
import { cn } from "./cn";

export interface SectionHeaderProps {
  title: string;
  /** Small monospaced eyebrow above the title (e.g. "DOMAIN", "SYSTEM"). */
  kicker?: string;
  /** Optional right-aligned content (badges, controls). */
  trailing?: ReactNode;
  className?: string;
}

/**
 * SectionHeader — labelled header used on panels and page sections.
 * Monospaced kicker + bold title + optional trailing slot.
 */
export function SectionHeader({
  title,
  kicker,
  trailing,
  className,
}: SectionHeaderProps) {
  return (
    <div className={cn("flex items-end justify-between gap-3", className)}>
      <div className="min-w-0">
        {kicker && (
          <div className="tnum text-[10px] uppercase tracking-[0.22em] text-cyan/70">
            {kicker}
          </div>
        )}
        <h2 className="truncate text-base font-semibold text-slate-100">
          {title}
        </h2>
      </div>
      {trailing && <div className="shrink-0">{trailing}</div>}
    </div>
  );
}
