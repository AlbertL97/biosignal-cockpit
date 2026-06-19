import { cn } from "@/design";

export interface CockpitHeaderProps {
  statusLine?: string;
  className?: string;
}

/** CockpitHeader — slim top bar with brand mark, title and a live status line. */
export function CockpitHeader({ statusLine, className }: CockpitHeaderProps) {
  return (
    <header
      className={cn(
        "relative z-10 flex h-14 shrink-0 items-center gap-4 border-b border-[var(--hairline)] px-5",
        "bg-base-900/70 backdrop-blur",
        className,
      )}
    >
      <div className="flex items-center gap-2.5">
        <BrandMark />
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-tight text-slate-100">
            HEALTH<span className="text-cyan">·</span>INTELLIGENCE
          </div>
          <div className="tnum text-[10px] uppercase tracking-[0.25em] text-slate-500">
            Personal Cockpit
          </div>
        </div>
      </div>

      <div className="ml-auto flex items-center gap-4">
        {statusLine && (
          <span className="tnum hidden text-xs text-slate-400 sm:inline">
            {statusLine}
          </span>
        )}
        <span className="inline-flex items-center gap-1.5 text-xs text-ok">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ok opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-ok" />
          </span>
          live
        </span>
      </div>
    </header>
  );
}

function BrandMark() {
  return (
    <svg width={26} height={26} viewBox="0 0 24 24" aria-hidden className="text-cyan">
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.2" opacity="0.4" />
      <path
        d="M3 12 h4 l2 -5 l3 11 l2 -6 h7"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
