import { useMemo } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";
import { palette } from "@/design";
import type { MetricSeries } from "@/api/types";

export interface TrendChartProps {
  series: MetricSeries;
  /** Series stroke color (defaults to cyan instrumentation accent). */
  color?: string;
  height?: number;
  /** Label for the metric (defaults to the raw metric key). */
  label?: string;
}

interface ChartPoint {
  ts: number;
  value: number;
  /** Lower bound of the baseline band, repeated for the area fill. */
  bandLow: number | null;
  /** Height of the baseline band above bandLow (stacked area trick). */
  bandSpan: number | null;
}

function formatDate(ms: number): string {
  return new Date(ms).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

/**
 * TrendChart — recharts time-series for a single metric with a +/-1 SD baseline
 * band drawn behind the line. Dark-themed via design tokens. The baseline band
 * makes "within personal baseline" visible without implying clinical thresholds.
 */
export function TrendChart({
  series,
  color = palette.cyan.DEFAULT,
  height = 220,
  label,
}: TrendChartProps) {
  const { mean, sd } = {
    mean: series.baseline_mean,
    sd: series.baseline_sd,
  };

  const data = useMemo<ChartPoint[]>(() => {
    const low = mean != null && sd != null ? mean - sd : null;
    const span = sd != null ? sd * 2 : null;
    return series.points
      .map((p) => ({
        ts: new Date(p.ts).getTime(),
        value: p.value,
        bandLow: low,
        bandSpan: span,
      }))
      .filter((p) => !Number.isNaN(p.ts))
      .sort((a, b) => a.ts - b.ts);
  }, [series.points, mean, sd]);

  const unit = series.unit ?? "";
  const metricLabel = label ?? series.metric;

  if (data.length === 0) {
    return (
      <div
        className="grid place-items-center rounded-md border border-dashed border-slate-600/40 text-sm text-slate-500"
        style={{ height }}
      >
        No data points available for {metricLabel}.
      </div>
    );
  }

  const hasBand = mean != null && sd != null;

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="rgba(148,163,184,0.10)" vertical={false} />
          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tickFormatter={formatDate}
            tick={{ fill: palette.text.secondary, fontSize: 11 }}
            stroke="rgba(148,163,184,0.25)"
            minTickGap={28}
          />
          <YAxis
            tick={{ fill: palette.text.secondary, fontSize: 11 }}
            stroke="rgba(148,163,184,0.25)"
            width={44}
            domain={["auto", "auto"]}
          />
          {/* Baseline band: stacked transparent + visible area (mean ± 1 SD). */}
          {hasBand && (
            <>
              <Area
                dataKey="bandLow"
                stackId="band"
                stroke="none"
                fill="transparent"
                isAnimationActive={false}
                activeDot={false}
              />
              <Area
                dataKey="bandSpan"
                stackId="band"
                stroke="none"
                fill={color}
                fillOpacity={0.1}
                isAnimationActive={false}
                activeDot={false}
                name="Baseline ±1 SD"
              />
            </>
          )}
          {mean != null && (
            <ReferenceLine
              y={mean}
              stroke={palette.text.muted}
              strokeDasharray="4 4"
              ifOverflow="extendDomain"
            />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: color }}
            isAnimationActive={false}
            name={metricLabel}
          />
          <Tooltip
            content={(props: TooltipProps<number, string>) => (
              <ChartTooltip {...props} unit={unit} metricLabel={metricLabel} />
            )}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function ChartTooltip({
  active,
  payload,
  label,
  unit,
  metricLabel,
}: TooltipProps<number, string> & { unit: string; metricLabel: string }) {
  if (!active || !payload || payload.length === 0) return null;
  const valuePoint = payload.find((p) => p.dataKey === "value");
  if (!valuePoint || typeof valuePoint.value !== "number") return null;
  const ts = typeof label === "number" ? label : Number(label);
  return (
    <div className="rounded-md panel-surface px-3 py-2 text-xs shadow-xl">
      <div className="tnum text-slate-400">{formatDate(ts)}</div>
      <div className="mt-0.5 font-semibold text-slate-100">
        {metricLabel}:{" "}
        <span className="tnum text-cyan">
          {valuePoint.value.toLocaleString("en-US")} {unit}
        </span>
      </div>
    </div>
  );
}
