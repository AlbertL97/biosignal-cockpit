import { Panel, SectionHeader, cn, statusColor } from "@/design";
import type { Contribution } from "@/api/types";

export interface ContributionsPanelProps {
  contributions: Contribution[];
}

const DIRECTION_META: Record<
  Contribution["direction"],
  { label: string; status: "ok" | "watch" | "alert" | "unknown" }
> = {
  supportive: { label: "Supportive", status: "ok" },
  adverse: { label: "Adverse", status: "alert" },
  neutral: { label: "Neutral", status: "unknown" },
  uncertain: { label: "Uncertain", status: "watch" },
};

function formatValue(value: Contribution["value"]): string {
  if (value == null) return "—";
  if (typeof value === "number") return value.toLocaleString();
  return value;
}

/**
 * ContributionsPanel — breaks down how each source/metric contributes to the
 * domain score: weight (relative influence) and direction. Makes the scoring
 * legible rather than a black box.
 */
export function ContributionsPanel({ contributions }: ContributionsPanelProps) {
  return (
    <Panel className="p-4">
      <SectionHeader kicker="Scoring" title="Contributions breakdown" />
      {contributions.length === 0 ? (
        <p className="mt-3 text-sm italic text-slate-500">
          No contributing factors recorded for this domain.
        </p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">
              Source, metric, relative weight and direction for each contribution.
            </caption>
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-slate-500">
                <th scope="col" className="pb-2 pr-3 font-medium">Source</th>
                <th scope="col" className="pb-2 pr-3 font-medium">Metric</th>
                <th scope="col" className="pb-2 pr-3 font-medium">Value</th>
                <th scope="col" className="pb-2 pr-3 font-medium">Weight</th>
                <th scope="col" className="pb-2 font-medium">Direction</th>
              </tr>
            </thead>
            <tbody>
              {contributions.map((c, i) => {
                const dir = DIRECTION_META[c.direction] ?? DIRECTION_META.neutral;
                const color = statusColor[dir.status];
                const pct = Math.round(Math.max(0, Math.min(1, c.weight)) * 100);
                return (
                  <tr
                    key={`${c.source}-${c.metric}-${i}`}
                    className="border-t border-[var(--hairline)]"
                  >
                    <td className="py-2 pr-3 text-slate-400">{c.source}</td>
                    <td className="py-2 pr-3 font-medium text-slate-200">{c.metric}</td>
                    <td className="tnum py-2 pr-3 text-slate-300">
                      {formatValue(c.value)}
                    </td>
                    <td className="py-2 pr-3">
                      <div className="flex items-center gap-2">
                        <div
                          className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-600/40"
                          role="img"
                          aria-label={`Weight ${pct} percent`}
                        >
                          <div
                            className="h-full rounded-full bg-cyan"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="tnum text-xs text-slate-400">{pct}%</span>
                      </div>
                    </td>
                    <td className="py-2">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1.5 text-xs font-medium",
                        )}
                        style={{ color }}
                      >
                        <span
                          aria-hidden
                          className="h-1.5 w-1.5 rounded-full"
                          style={{ backgroundColor: color }}
                        />
                        {dir.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
