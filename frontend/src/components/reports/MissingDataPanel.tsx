import { Panel, SectionHeader } from "@/design";

export interface MissingDataPanelProps {
  missingData: string[];
}

/**
 * MissingDataPanel — explicit list of data gaps for the domain. Surfacing gaps
 * is mandatory (ARCHITECTURE.md §8): never imply completeness we don't have.
 */
export function MissingDataPanel({ missingData }: MissingDataPanelProps) {
  return (
    <Panel className="p-4">
      <SectionHeader kicker="Coverage" title="Missing data" />
      {missingData.length === 0 ? (
        <p className="mt-3 text-sm text-slate-400">
          No significant data gaps flagged for this domain.
        </p>
      ) : (
        <ul className="mt-3 space-y-2">
          {missingData.map((gap, i) => (
            <li
              key={i}
              className="flex items-start gap-2 text-sm leading-relaxed text-slate-300"
            >
              <span
                aria-hidden
                className="mt-0.5 text-watch"
                title="Data gap"
              >
                ⚠
              </span>
              <span>{gap}</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
