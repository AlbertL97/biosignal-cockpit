import type { ReactNode } from "react";
import { cn } from "./cn";

export interface PanelProps {
  children: ReactNode;
  className?: string;
  /** Show instrumentation corner brackets. Default true. */
  ticks?: boolean;
  /** Apply a cyan glow ring (use sparingly, e.g. focused/selected panels). */
  glow?: boolean;
  /** Render as a focusable region with the given aria-label. */
  as?: "div" | "section" | "article";
  ariaLabel?: string;
}

/**
 * Panel — the base cockpit surface. Frosted dark glass with a hairline border
 * and optional instrumentation corner brackets. Compose everything on top.
 */
export function Panel({
  children,
  className,
  ticks = true,
  glow = false,
  as: Tag = "div",
  ariaLabel,
}: PanelProps) {
  return (
    <Tag
      aria-label={ariaLabel}
      className={cn(
        "relative rounded-lg panel-surface",
        ticks && "panel-ticks",
        glow && "glow-cyan",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
