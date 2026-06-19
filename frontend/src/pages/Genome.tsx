import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Badge, Panel, SectionHeader } from "@/design";
import type { NebulaTrait } from "@/api/types";
import { useGenomeTraits } from "@/api/hooks";
import { EmptyState, ErrorState, LoadingState } from "@/components/cards/States";
import { PercentileBar } from "@/components/genome/PercentileBar";

const ALL = "__all__";

export function Genome() {
  const navigate = useNavigate();
  const traitsQuery = useGenomeTraits();
  const [category, setCategory] = useState<string>(ALL);
  const [query, setQuery] = useState("");

  const traits = traitsQuery.data ?? [];

  const categories = useMemo(() => {
    const set = new Set<string>();
    for (const t of traits) if (t.category) set.add(t.category);
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [traits]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return traits.filter((t) => {
      if (category !== ALL && t.category !== category) return false;
      if (!q) return true;
      return (
        t.trait.toLowerCase().includes(q) ||
        (t.category?.toLowerCase().includes(q) ?? false) ||
        (t.score_label?.toLowerCase().includes(q) ?? false)
      );
    });
  }, [traits, category, query]);

  if (traitsQuery.isLoading) return <LoadingState label="Loading genome traits…" />;
  if (traitsQuery.isError)
    return <ErrorState error={traitsQuery.error} onRetry={() => traitsQuery.refetch()} />;

  return (
    <div className="mx-auto max-w-[1400px] space-y-4">
      <SectionHeader
        kicker="Genome"
        title="Polygenic trait reports"
        trailing={
          <Badge tone="neutral">
            {filtered.length} of {traits.length}
          </Badge>
        }
      />

      <Panel className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
        <label className="flex-1">
          <span className="sr-only">Search traits</span>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search traits, categories…"
            className="focusable w-full rounded-md border border-[var(--hairline)] bg-base-900/60 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500"
          />
        </label>
        <label className="sm:w-56">
          <span className="sr-only">Filter by category</span>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="focusable w-full rounded-md border border-[var(--hairline)] bg-base-900/60 px-3 py-2 text-sm text-slate-200"
          >
            <option value={ALL}>All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </Panel>

      <p className="px-1 text-xs leading-relaxed text-slate-500">
        Percentiles are polygenic and population-relative — they describe genetic
        predisposition, not a diagnosis or a deterministic outcome.
      </p>

      {filtered.length === 0 ? (
        <EmptyState label="No traits match your filters." />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((t) => (
            <TraitCard key={t.id} trait={t} onOpen={() => navigate(`/genome/${t.id}`)} />
          ))}
        </div>
      )}
    </div>
  );
}

function TraitCard({ trait, onOpen }: { trait: NebulaTrait; onOpen: () => void }) {
  return (
    <Panel className="focusable cursor-pointer p-4 transition-transform hover:-translate-y-0.5">
      <button
        type="button"
        onClick={onOpen}
        className="block w-full text-left outline-none"
        aria-label={`Open ${trait.trait} detail`}
      >
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold leading-snug text-slate-100">
            {trait.trait}
          </h3>
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          {trait.category && <Badge tone="neutral">{trait.category}</Badge>}
          {trait.score_label && (
            <span className="text-[11px] font-medium text-cyan/90">
              {trait.score_label}
            </span>
          )}
        </div>
        <div className="mt-3">
          <PercentileBar percentile={trait.percentile} compact />
        </div>
      </button>
    </Panel>
  );
}
