import { Panel, ProvenanceTag, SectionHeader, cn } from "@/design";
import type { Provenance } from "@/design";
import type { DomainStatus } from "@/api/types";

interface LayerDef {
  key: keyof Pick<
    DomainStatus,
    "observations" | "derived" | "inferences" | "hypotheses" | "recommendations"
  >;
  kicker: string;
  title: string;
  provenance: Provenance;
  blurb: string;
}

/**
 * The five interpretation layers, ordered measured -> derived -> inferred. The
 * provenance tag on each header keeps MEASURED vs INFERRED explicit
 * (ARCHITECTURE.md §8); recommendations carry no provenance (they are guidance).
 */
const LAYERS: LayerDef[] = [
  {
    key: "observations",
    kicker: "Layer 1",
    title: "Observations",
    provenance: "measured",
    blurb: "Directly measured values from your data.",
  },
  {
    key: "derived",
    kicker: "Layer 2",
    title: "Derived metrics",
    provenance: "measured",
    blurb: "Computed from measured values (baselines, rolling means, deviations).",
  },
  {
    key: "inferences",
    kicker: "Layer 3",
    title: "Inferences",
    provenance: "inferred",
    blurb: "Cautious interpreted states — not directly measured.",
  },
  {
    key: "hypotheses",
    kicker: "Layer 4",
    title: "Hypotheses",
    provenance: "inferred",
    blurb: "Plausible but uncertain — for exploration, not conclusions.",
  },
  {
    key: "recommendations",
    kicker: "Layer 5",
    title: "Recommendations",
    provenance: "inferred",
    blurb: "Non-diagnostic, ranked suggestions. Discuss with a clinician.",
  },
];

export interface LayerStackProps {
  status: DomainStatus;
}

/** LayerStack — renders the five interpretation layers as visibly separated panels. */
export function LayerStack({ status }: LayerStackProps) {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {LAYERS.map((layer) => {
        const items = status[layer.key];
        const isRecommendation = layer.key === "recommendations";
        return (
          <Panel
            key={layer.key}
            className={cn("p-4", isRecommendation && "md:col-span-2")}
          >
            <SectionHeader
              kicker={layer.kicker}
              title={layer.title}
              trailing={<ProvenanceTag provenance={layer.provenance} />}
            />
            <p className="mt-1 text-xs text-slate-500">{layer.blurb}</p>
            {items.length === 0 ? (
              <p className="mt-3 text-sm italic text-slate-500">
                Nothing to report in this layer.
              </p>
            ) : isRecommendation ? (
              <ol className="mt-3 space-y-2">
                {items.map((text, i) => (
                  <li
                    key={i}
                    className="flex gap-2 text-sm leading-relaxed text-slate-200"
                  >
                    <span className="tnum mt-0.5 shrink-0 text-xs font-semibold text-cyan/80">
                      {i + 1}.
                    </span>
                    <span>{text}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <ul className="mt-3 space-y-2">
                {items.map((text, i) => (
                  <li
                    key={i}
                    className={cn(
                      "flex gap-2 text-sm leading-relaxed text-slate-200",
                      layer.provenance === "inferred" && "text-slate-300",
                    )}
                  >
                    <span
                      aria-hidden
                      className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-cyan/60"
                    />
                    <span>{text}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        );
      })}
    </div>
  );
}
