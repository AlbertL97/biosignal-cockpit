import type { ReactNode } from "react";
import { cn } from "@/design";
import { CockpitHeader } from "./CockpitHeader";
import { SideRail, type RailItem } from "./SideRail";

export interface AppFrameProps {
  children: ReactNode;
  /** Left navigation rail items (visual only — FRONTEND agent wires routing). */
  navItems?: RailItem[];
  activeNavId?: string;
  onNavSelect?: (id: string) => void;
  /** Optional right-side rail content (e.g. evidence/uncertainty panels). */
  rightRail?: ReactNode;
  /** Header status line text (e.g. "Last sync 2h ago"). */
  statusLine?: string;
  className?: string;
}

/**
 * AppFrame — top-level cockpit chrome: fixed header, left navigation rail,
 * scrollable main, and an optional right rail. Visual-only shell; the FRONTEND
 * agent renders pages into `children` and supplies nav/state.
 */
export function AppFrame({
  children,
  navItems = [],
  activeNavId,
  onNavSelect,
  rightRail,
  statusLine,
  className,
}: AppFrameProps) {
  return (
    <div className={cn("cockpit-bg flex h-screen flex-col text-slate-200", className)}>
      <CockpitHeader statusLine={statusLine} />
      <div className="flex min-h-0 flex-1">
        {navItems.length > 0 && (
          <SideRail
            items={navItems}
            activeId={activeNavId}
            onSelect={onNavSelect}
          />
        )}
        <main className="scroll-thin min-w-0 flex-1 overflow-y-auto px-5 py-5">
          {children}
        </main>
        {rightRail && (
          <aside className="scroll-thin hidden w-80 shrink-0 overflow-y-auto border-l border-[var(--hairline)] px-4 py-5 xl:block">
            {rightRail}
          </aside>
        )}
      </div>
    </div>
  );
}
