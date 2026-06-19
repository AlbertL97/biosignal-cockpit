import { EvidenceBadge, Panel, SectionHeader } from "@/design";
import type { EvidenceRef } from "@/api/types";

export interface EvidenceListProps {
  evidence: EvidenceRef[];
  title?: string;
}

/** Resolve the best external link for a reference (PubMed if a PMID exists). */
function refUrl(ref: EvidenceRef): string | null {
  if (ref.pmid) return `https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}/`;
  return ref.url ?? null;
}

/**
 * EvidenceList — graded scientific references behind the interpretation. Each
 * row shows the claim, its evidence grade, source and a PubMed link when a PMID
 * is present.
 */
export function EvidenceList({ evidence, title = "Evidence" }: EvidenceListProps) {
  return (
    <Panel className="p-4">
      <SectionHeader kicker="Science" title={title} />
      {evidence.length === 0 ? (
        <p className="mt-3 text-sm italic text-slate-500">
          No graded evidence references attached.
        </p>
      ) : (
        <ul className="mt-3 space-y-3">
          {evidence.map((ref, i) => {
            const url = refUrl(ref);
            return (
              <li
                key={`${ref.claim}-${i}`}
                className="border-t border-[var(--hairline)] pt-3 first:border-t-0 first:pt-0"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm leading-relaxed text-slate-200">{ref.claim}</p>
                  <EvidenceBadge grade={ref.grade} compact className="shrink-0" />
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                  {ref.title && <span className="text-slate-400">{ref.title}</span>}
                  {ref.year != null && <span className="tnum">{ref.year}</span>}
                  <span className="uppercase tracking-wide">{ref.source}</span>
                  {url && (
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="focusable text-cyan underline-offset-2 hover:underline"
                    >
                      {ref.pmid ? `PubMed ${ref.pmid}` : "Source"} ↗
                    </a>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}
