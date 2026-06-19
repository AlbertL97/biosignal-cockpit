import type { ReactNode } from "react";
import { cn } from "@/design";

export interface RailItem {
  id: string;
  label: string;
  /** Optional glyph/icon node. */
  icon?: ReactNode;
}

export interface SideRailProps {
  items: RailItem[];
  activeId?: string;
  onSelect?: (id: string) => void;
  className?: string;
}

/**
 * SideRail — compact left navigation rail. Visual chrome only; routing/state is
 * owned by the FRONTEND agent. Labels appear on hover/focus (icon rail).
 */
export function SideRail({ items, activeId, onSelect, className }: SideRailProps) {
  return (
    <nav
      aria-label="Primary"
      className={cn(
        "flex w-16 shrink-0 flex-col items-center gap-1 border-r border-[var(--hairline)] py-4",
        "bg-base-900/40",
        className,
      )}
    >
      {items.map((item) => {
        const active = item.id === activeId;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelect?.(item.id)}
            aria-current={active ? "page" : undefined}
            title={item.label}
            className={cn(
              "focusable group relative grid h-11 w-11 place-items-center rounded-lg transition-colors",
              active
                ? "bg-cyan/15 text-cyan"
                : "text-slate-400 hover:bg-slate-500/10 hover:text-slate-200",
            )}
          >
            {active && (
              <span className="absolute left-0 top-1/2 h-5 -translate-y-1/2 rounded-r bg-cyan" style={{ width: 2 }} />
            )}
            <span className="text-base" aria-hidden>
              {item.icon ?? item.label.charAt(0)}
            </span>
            <span className="sr-only">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
