import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Badge,
  ConfidenceMeter,
  EvidenceBadge,
  Panel,
  ProvenanceTag,
  SectionHeader,
  StatRing,
  StatusBadge,
  TrendIndicator,
  domainLabel,
  domainLabelShort,
  scoreToStatus,
  statusColor,
  type Status,
} from "@/design";
import { Avatar, type AvatarRegion } from "@/components/Avatar";
import type { Domain, DomainStatus } from "@/api/types";
import { DOMAINS } from "@/api/types";
import { useDomains, useProfile } from "@/api/hooks";
import { DomainCard } from "@/components/cards/DomainCard";
import { ErrorState, LoadingState } from "@/components/cards/States";

/** Order domains canonically so the layout is stable regardless of API order. */
function orderDomains(domains: DomainStatus[]): DomainStatus[] {
  const byId = new Map(domains.map((d) => [d.domain, d]));
  const ordered: DomainStatus[] = [];
  for (const id of DOMAINS) {
    const d = byId.get(id);
    if (d) ordered.push(d);
  }
  // Append any unexpected domains the API may add later.
  for (const d of domains) {
    if (!DOMAINS.includes(d.domain as Domain)) ordered.push(d);
  }
  return ordered;
}

export function Dashboard() {
  const navigate = useNavigate();
  const domainsQuery = useDomains();
  const profileQuery = useProfile();
  const [selected, setSelected] = useState<Domain | null>(null);

  const domains = useMemo(
    () => (domainsQuery.data ? orderDomains(domainsQuery.data) : []),
    [domainsQuery.data],
  );

  const avatarRegions = useMemo<AvatarRegion[]>(
    () =>
      domains.map((d) => ({
        id: d.domain as Domain,
        status: scoreToStatus(d.score),
        score: d.score,
      })),
    [domains],
  );

  const open = (id: Domain) => navigate(`/domain/${id}`);

  if (domainsQuery.isLoading) return <LoadingState label="Loading body systems…" />;
  if (domainsQuery.isError)
    return <ErrorState error={domainsQuery.error} onRetry={() => domainsQuery.refetch()} />;

  const selectedStatus = selected
    ? domains.find((d) => d.domain === selected) ?? null
    : null;

  return (
    <div className="mx-auto max-w-[1500px]">
      <ProfileHeader
        profile={profileQuery.data}
        loading={profileQuery.isLoading}
        domainCount={domains.length}
      />

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_400px]">
        {/* All domain cards together on the left */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {domains.map((d) => (
            <DomainCard
              key={d.domain}
              status={d}
              selected={selected === d.domain}
              onSelect={(id) => setSelected(id)}
            />
          ))}
        </div>

        {/* Avatar on the right */}
        <Panel
          className="grid place-items-start justify-items-center px-6 py-6 lg:sticky lg:top-4 lg:self-start"
          glow
        >
          <div className="mb-2 text-center">
            <div className="tnum text-[10px] uppercase tracking-[0.25em] text-cyan/70">
              Digital twin
            </div>
            <div className="text-sm text-slate-400">
              Select a region to open its report
            </div>
          </div>
          <Avatar
            regions={avatarRegions}
            selected={selected}
            onSelectRegion={open}
            width={300}
          />
          <Legend />
        </Panel>
      </div>

      {selectedStatus && (
        <div className="mt-4 xl:hidden">
          <SelectedSummary status={selectedStatus} onOpen={() => open(selectedStatus.domain as Domain)} />
        </div>
      )}
    </div>
  );
}

function ProfileHeader({
  profile,
  loading,
  domainCount,
}: {
  profile: ReturnType<typeof useProfile>["data"];
  loading: boolean;
  domainCount: number;
}) {
  const highlights = profile?.highlights ?? [];
  return (
    <Panel className="p-4">
      <SectionHeader
        kicker="System status"
        title="Body Systems Overview"
        trailing={<Badge tone="accent" dot>{domainCount} domains</Badge>}
      />
      <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        {/* Only show characteristics that are actually set. */}
        <Fact label="Sex" value={profile?.biological_sex} loading={loading} />
        <Fact label="DOB" value={profile?.dob} loading={loading} />
      </div>
      {highlights.length > 0 && (
        <div className="mt-3 border-t border-[var(--hairline)] pt-3">
          <div className="mb-2 text-[11px] uppercase tracking-wider text-slate-500">
            Current signals
          </div>
          <div className="flex flex-wrap gap-2.5">
            {highlights.map((h) => (
              <HighlightPill key={h.label} label={h.label} value={h.value} detail={h.detail} />
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}

function Fact({
  label,
  value,
  loading,
}: {
  label: string;
  value: string | null | undefined;
  loading: boolean;
}) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-[11px] uppercase tracking-wider text-slate-500">{label}</span>
      <span className="tnum text-slate-200">
        {loading ? "…" : (value ?? "—")}
      </span>
    </div>
  );
}

function HighlightPill({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string | null;
}) {
  return (
    <div
      className="rounded-md border border-[var(--hairline)] bg-base-800/40 px-3 py-1.5"
      title={detail ?? undefined}
    >
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="tnum text-sm font-semibold text-slate-100">{value}</div>
    </div>
  );
}

function Legend() {
  const items: { status: Status; label: string }[] = [
    { status: "ok", label: "Supportive" },
    { status: "watch", label: "Monitor" },
    { status: "alert", label: "Attention" },
    { status: "unknown", label: "Insufficient" },
  ];
  return (
    <div className="mt-4 flex flex-wrap items-center justify-center gap-x-3 gap-y-1">
      {items.map((it) => (
        <span
          key={it.status}
          className="inline-flex items-center gap-1.5 text-[11px] text-slate-400"
        >
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: statusColor[it.status] }}
          />
          {it.label}
        </span>
      ))}
    </div>
  );
}

function SelectedSummary({
  status,
  onOpen,
}: {
  status: DomainStatus;
  onOpen: () => void;
}) {
  const st = scoreToStatus(status.score);
  return (
    <Panel className="p-4">
      <SectionHeader
        kicker="Domain"
        title={domainLabel[status.domain] ?? status.domain}
      />
      <div className="mt-3 flex items-center gap-4">
        <StatRing score={status.score} caption="score" />
        <div className="space-y-2">
          <StatusBadge status={st} />
          <TrendIndicator trend={status.trend} showLabel />
          <ConfidenceMeter confidence={status.confidence} />
          <div className="flex items-center gap-2">
            <EvidenceBadge grade={status.evidence_grade} />
            <ProvenanceTag provenance={status.score == null ? "inferred" : "measured"} />
          </div>
        </div>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-slate-400">{status.summary}</p>
      <button
        type="button"
        onClick={onOpen}
        className="focusable mt-3 text-sm text-cyan underline-offset-2 hover:underline"
      >
        Open full {domainLabelShort[status.domain] ?? status.domain} report →
      </button>
    </Panel>
  );
}
