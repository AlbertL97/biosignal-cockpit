import { useId } from "react";
import { cn } from "./cn";
import { type Status, statusColor } from "./tokens";

export interface SparklineProps {
  /** Series values (oldest → newest). Empty/short series renders a flat hint. */
  data: number[];
  width?: number;
  height?: number;
  status?: Status;
  /** Override stroke color (otherwise derived from status / cyan). */
  color?: string;
  /** Render dashed to indicate inferred/uncertain data. Default false. */
  inferred?: boolean;
  className?: string;
  ariaLabel?: string;
}

/**
 * Sparkline — lightweight inline trend line (placeholder/utility). The data-
 * heavy charts live in the FRONTEND agent's charts/ using Recharts; this is for
 * compact in-card trends and avatar callouts.
 */
export function Sparkline({
  data,
  width = 120,
  height = 32,
  status,
  color,
  inferred = false,
  className,
  ariaLabel,
}: SparklineProps) {
  const id = useId();
  const stroke = color ?? (status ? statusColor[status] : "var(--cyan)");
  const pad = 2;

  if (data.length < 2) {
    return (
      <svg
        width={width}
        height={height}
        className={cn("overflow-visible", className)}
        role="img"
        aria-label={ariaLabel ?? "No trend data"}
      >
        <line
          x1={pad}
          y1={height / 2}
          x2={width - pad}
          y2={height / 2}
          stroke="var(--text-muted)"
          strokeWidth={1}
          strokeDasharray="2 4"
        />
      </svg>
    );
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const stepX = (width - pad * 2) / (data.length - 1);
  const pts = data.map((v, i) => {
    const x = pad + i * stepX;
    const y = pad + (height - pad * 2) * (1 - (v - min) / span);
    return [x, y] as const;
  });
  const line = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x},${y}`).join(" ");
  const area = `${line} L${pts[pts.length - 1][0]},${height - pad} L${pts[0][0]},${
    height - pad
  } Z`;
  const [lastX, lastY] = pts[pts.length - 1];

  return (
    <svg
      width={width}
      height={height}
      className={cn("overflow-visible", className)}
      role="img"
      aria-label={ariaLabel ?? "Trend"}
    >
      <defs>
        <linearGradient id={`spark-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity={0.28} />
          <stop offset="100%" stopColor={stroke} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#spark-${id})`} />
      <path
        d={line}
        fill="none"
        stroke={stroke}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={inferred ? "3 3" : undefined}
        opacity={inferred ? 0.8 : 1}
      />
      <circle cx={lastX} cy={lastY} r={2} fill={stroke} />
    </svg>
  );
}
