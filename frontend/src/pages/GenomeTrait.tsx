import { Link, useParams } from "react-router-dom";
import { Badge, Panel, SectionHeader, StatRing } from "@/design";
import { useGenomeTrait } from "@/api/hooks";
import { ErrorState, LoadingState } from "@/components/cards/States";
import { PercentileBar } from "@/components/genome/PercentileBar";
import { VariantTable } from "@/components/genome/VariantTable";

export function GenomeTrait() {
  const { id } = useParams<{ id: string }>();
  const traitQuery = useGenomeTrait(id);

  if (traitQuery.isLoading) return <LoadingState label="Loading trait…" />;
  if (traitQuery.isError)
    return <ErrorState error={traitQuery.error} onRetry={() => traitQuery.refetch()} />;
  if (!traitQuery.data) return <ErrorState error={new Error("Trait not found.")} />;

  const trait = traitQuery.data;
  const highlighted = trait.variants.filter((v) => v.highlighted).length;

  return (
    <div className="mx-auto max-w-[1100px] space-y-4">
      <Link
        to="/genome"
        className="focusable text-sm text-slate-400 underline-offset-2 hover:text-cyan hover:underline"
      >
        ← All traits
      </Link>

      <Panel className="p-5" glow>
        <SectionHeader
          kicker="Polygenic trait"
          title={trait.trait}
          trailing={trait.category ? <Badge tone="neutral">{trait.category}</Badge> : undefined}
        />
        <div className="mt-4 flex flex-col gap-5 sm:flex-row sm:items-center">
          <StatRing score={trait.score} caption="score" size={104} />
          <div className="flex-1 space-y-3">
            {trait.score_label && (
              <div className="text-sm font-medium text-cyan/90">{trait.score_label}</div>
            )}
            <PercentileBar percentile={trait.percentile} />
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500">
              <span>
                {trait.variants.length} variant{trait.variants.length === 1 ? "" : "s"}
              </span>
              {highlighted > 0 && (
                <span className="text-cyan/80">{highlighted} highlighted</span>
              )}
            </div>
            {trait.citation && (
              <p className="text-xs leading-relaxed text-slate-500">
                Source: {trait.citation}
              </p>
            )}
          </div>
        </div>
      </Panel>

      {(trait.description || trait.interpretation) && (
        <Panel className="p-5">
          <SectionHeader kicker="What this means" title="Reading this report" />
          {trait.description && (
            <p className="mt-3 text-sm leading-relaxed text-slate-300">
              {trait.description}
            </p>
          )}
          {trait.interpretation && (
            <p className="mt-3 text-sm leading-relaxed text-slate-400">
              {trait.interpretation}
            </p>
          )}
        </Panel>
      )}

      <VariantTable variants={trait.variants} />

      <p className="px-1 pb-6 text-xs leading-relaxed text-slate-600">
        This percentile reflects polygenic predisposition relative to a reference
        population. It is non-deterministic and not a diagnosis — environment,
        lifestyle and unmeasured variants all matter. Discuss any concerns with a
        qualified clinician or genetic counselor.
      </p>
    </div>
  );
}
