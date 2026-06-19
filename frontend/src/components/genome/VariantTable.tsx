import { Panel, SectionHeader, cn } from "@/design";
import type { TraitVariant } from "@/api/types";

export interface VariantTableProps {
  variants: TraitVariant[];
}

function fmtNum(value: number | null, digits = 3): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function fmtP(value: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (value !== 0 && Math.abs(value) < 1e-3) return value.toExponential(1);
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

/**
 * VariantTable — the per-trait variant table (rsID, your genotype, gene, effect
 * size, frequency, p-value). Highlighted rows (variants you carry that drive the
 * trait) are emphasized.
 */
export function VariantTable({ variants }: VariantTableProps) {
  return (
    <Panel className="p-4">
      <SectionHeader kicker="Genotype" title="Variant table" />
      {variants.length === 0 ? (
        <p className="mt-3 text-sm italic text-slate-500">
          No variant rows available for this trait.
        </p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">
              Variants for this trait: rsID, your genotype, gene, effect size,
              frequency and p-value. Highlighted rows are emphasized.
            </caption>
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-slate-500">
                <th scope="col" className="pb-2 pr-3 font-medium">rsID</th>
                <th scope="col" className="pb-2 pr-3 font-medium">Genotype</th>
                <th scope="col" className="pb-2 pr-3 font-medium">Gene</th>
                <th scope="col" className="pb-2 pr-3 font-medium">Effect size</th>
                <th scope="col" className="pb-2 pr-3 font-medium">Frequency</th>
                <th scope="col" className="pb-2 font-medium">p-value</th>
              </tr>
            </thead>
            <tbody>
              {variants.map((v, i) => (
                <tr
                  key={`${v.rsid}-${i}`}
                  className={cn(
                    "border-t border-[var(--hairline)]",
                    v.highlighted && "bg-cyan/5",
                  )}
                >
                  <th
                    scope="row"
                    className="py-2 pr-3 text-left font-normal"
                  >
                    <span className="inline-flex items-center gap-1.5">
                      {v.highlighted && (
                        <span
                          aria-label="Highlighted variant"
                          title="Highlighted variant"
                          className="h-1.5 w-1.5 shrink-0 rounded-full bg-cyan"
                        />
                      )}
                      <span
                        className={cn(
                          "tnum",
                          v.highlighted ? "font-semibold text-cyan" : "text-slate-300",
                        )}
                      >
                        {v.rsid}
                      </span>
                    </span>
                  </th>
                  <td className="tnum py-2 pr-3 text-slate-200">{v.genotype ?? "—"}</td>
                  <td className="py-2 pr-3 text-slate-300">{v.gene ?? "—"}</td>
                  <td className="tnum py-2 pr-3 text-slate-300">{fmtNum(v.effect_size)}</td>
                  <td className="tnum py-2 pr-3 text-slate-300">{fmtNum(v.frequency)}</td>
                  <td className="tnum py-2 text-slate-300">{fmtP(v.p_value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
