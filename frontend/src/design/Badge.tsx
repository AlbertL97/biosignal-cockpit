import type { ReactNode } from "react";
import { cn } from "./cn";
import { type Status, statusColor, statusLabel } from "./tokens";

type Tone = Status | "neutral" | "accent";

export interface BadgeProps {
  children?: ReactNode;
  tone?: Tone;
  /** Show a small leading dot in the tone color. */
  dot?: boolean;
  className?: string;
}

const toneClasses: Record<Tone, string> = {
  ok: "text-ok/90 border-ok/30 bg-ok/10",
  watch: "text-watch/90 border-watch/30 bg-watch/10",
  alert: "text-alert/90 border-alert/30 bg-alert/10",
  unknown: "text-slate-400 border-slate-500/30 bg-slate-500/10",
  neutral: "text-slate-300 border-slate-500/25 bg-slate-500/10",
  accent: "text-cyan border-cyan/30 bg-cyan/10",
};

/** Badge — compact pill for statuses, tags and counts. */
export function Badge({ children, tone = "neutral", dot, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5",
        "text-[11px] font-medium leading-none",
        toneClasses[tone],
        className,
      )}
    >
      {dot && (
        <span
          aria-hidden
          className="h-1.5 w-1.5 rounded-full"
          style={{
            backgroundColor:
              tone === "neutral" || tone === "accent"
                ? "currentColor"
                : statusColor[tone],
          }}
        />
      )}
      {children}
    </span>
  );
}

/** StatusBadge — convenience wrapper that renders a Status with its label. */
export function StatusBadge({
  status,
  label,
  className,
}: {
  status: Status;
  label?: string;
  className?: string;
}) {
  return (
    <Badge tone={status} dot className={className}>
      {label ?? statusLabel[status]}
    </Badge>
  );
}
