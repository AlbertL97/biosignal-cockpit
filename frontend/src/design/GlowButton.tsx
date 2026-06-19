import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "./cn";

type Variant = "solid" | "outline" | "ghost";
type Size = "sm" | "md";

export interface GlowButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  /** Optional leading icon/glyph. */
  leading?: ReactNode;
}

const base =
  "focusable inline-flex items-center justify-center gap-2 rounded-md font-medium " +
  "transition-colors disabled:opacity-50 disabled:pointer-events-none select-none";

const variants: Record<Variant, string> = {
  solid:
    "bg-cyan/15 text-cyan border border-cyan/40 hover:bg-cyan/25 " +
    "hover:shadow-[0_0_18px_-4px_rgba(34,211,238,0.6)]",
  outline:
    "bg-transparent text-slate-200 border border-slate-500/40 hover:border-cyan/50 hover:text-cyan",
  ghost: "bg-transparent text-slate-300 hover:bg-slate-500/10",
};

const sizes: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs",
  md: "h-9 px-4 text-sm",
};

/** GlowButton — primary cockpit button with a subtle cyan glow on hover. */
export function GlowButton({
  children,
  variant = "solid",
  size = "md",
  leading,
  className,
  type = "button",
  ...rest
}: GlowButtonProps) {
  return (
    <button
      type={type}
      className={cn(base, variants[variant], sizes[size], className)}
      {...rest}
    >
      {leading && <span className="shrink-0">{leading}</span>}
      {children}
    </button>
  );
}
