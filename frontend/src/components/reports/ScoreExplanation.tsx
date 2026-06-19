import { Panel, SectionHeader } from "@/design";
import type { Driver } from "@/api/types";

/** Why the score is what it is (drivers) + research-informed ways to improve it. */
export function ScoreExplanation({
  drivers,
  levers,
}: {
  drivers: Driver[];
  levers: string[];
}) {
  if (drivers.length === 0 && levers.length === 0) return null;

  const raising = drivers.filter((d) => d.direction === "raising");
  const lowering = drivers.filter((d) => d.direction === "lowering");
  const neutral = drivers.filter(
    (d) => d.direction !== "raising" && d.direction !== "lowering",
  );

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Panel className="p-4">
        <SectionHeader
          kicker="Explanation"
          title="What's shaping this score"
        />
        <div className="mt-3 space-y-3">
          <DriverGroup
            title="Lowering it"
            color="text-rose-300"
            mark="▼"
            markColor="text-rose-400"
            drivers={lowering}
          />
          <DriverGroup
            title="Supporting it"
            color="text-emerald-300"
            mark="▲"
            markColor="text-emerald-400"
            drivers={raising}
          />
          <DriverGroup
            title="Mixed / uncertain"
            color="text-slate-300"
            mark="•"
            markColor="text-slate-500"
            drivers={neutral}
          />
          {drivers.length === 0 && (
            <p className="text-sm text-slate-500">
              Not enough data to attribute drivers for this domain yet.
            </p>
          )}
        </div>
      </Panel>

      <Panel className="p-4">
        <SectionHeader
          kicker="Improve"
          title="Evidence-based ways to raise it"
        />
        {levers.length > 0 ? (
          <ul className="mt-3 space-y-2">
            {levers.map((l, i) => (
              <li key={i} className="flex gap-2 text-sm leading-relaxed text-slate-300">
                <span className="mt-1 text-cyan">↗</span>
                <span>{l}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-slate-500">No levers listed.</p>
        )}
        <p className="mt-3 text-xs leading-relaxed text-slate-600">
          General, research-informed lifestyle levers — not personalised medical
          advice. See the Evidence panel for sources.
        </p>
      </Panel>
    </div>
  );
}

function DriverGroup({
  title,
  color,
  mark,
  markColor,
  drivers,
}: {
  title: string;
  color: string;
  mark: string;
  markColor: string;
  drivers: Driver[];
}) {
  if (drivers.length === 0) return null;
  return (
    <div>
      <h4 className={`text-[11px] uppercase tracking-wider ${color}`}>{title}</h4>
      <ul className="mt-1 space-y-1">
        {drivers.map((d, i) => (
          <li key={i} className="flex gap-2 text-sm leading-relaxed text-slate-300">
            <span className={`mt-0.5 ${markColor}`}>{mark}</span>
            <span>{d.detail}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
