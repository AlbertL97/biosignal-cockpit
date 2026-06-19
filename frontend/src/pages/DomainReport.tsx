import { Link, useParams } from "react-router-dom";
import {
  ConfidenceMeter,
  EvidenceBadge,
  GlowButton,
  Panel,
  ProvenanceTag,
  SectionHeader,
  StatRing,
  StatusBadge,
  TrendIndicator,
  domainLabel,
  scoreToStatus,
} from "@/design";
import type { Domain, DomainStatus } from "@/api/types";
import { useDomain, useEvidence, useMetric } from "@/api/hooks";
import { ErrorState, LoadingState } from "@/components/cards/States";
import { LayerStack } from "@/components/reports/LayerStack";
import { ContributionsPanel } from "@/components/reports/ContributionsPanel";
import { ScoreExplanation } from "@/components/reports/ScoreExplanation";
import { MissingDataPanel } from "@/components/reports/MissingDataPanel";
import { EvidenceList } from "@/components/reports/EvidenceList";
import { TrendChart } from "@/components/charts/TrendChart";

/** A representative, directly-measured key metric per domain for the trend chart. */
const KEY_METRIC: Record<Domain, { metric: string; label: string }> = {
  cardiovascular: { metric: "RestingHeartRate", label: "Resting heart rate" },
  sleep_recovery: { metric: "HeartRateVariabilitySDNN", label: "HRV (SDNN)" },
  stress_autonomic: { metric: "HeartRateVariabilitySDNN", label: "HRV (SDNN)" },
  musculoskeletal: { metric: "StepCount", label: "Steps" },
  metabolic: { metric: "ActiveEnergyBurned", label: "Active energy" },
  immune_inflammation: { metric: "OxygenSaturation", label: "Blood oxygen" },
  brain: { metric: "HeartRateVariabilitySDNN", label: "HRV (SDNN)" },
  gut: { metric: "DietaryEnergyConsumed", label: "Dietary energy" },
  oral_dental: { metric: "DietarySugar", label: "Dietary sugar" },
};

export function DomainReport() {
  const { id } = useParams<{ id: string }>();
  const domainQuery = useDomain(id);
  const evidenceQuery = useEvidence(id);

  if (domainQuery.isLoading) return <LoadingState label="Loading report…" />;
  if (domainQuery.isError)
    return <ErrorState error={domainQuery.error} onRetry={() => domainQuery.refetch()} />;
  if (!domainQuery.data) return <ErrorState error={new Error("Domain not found.")} />;

  const status = domainQuery.data;
  // Prefer the API-attached evidence; fall back to the dedicated endpoint.
  const evidence =
    status.evidence.length > 0 ? status.evidence : evidenceQuery.data ?? [];

  return (
    <div className="mx-auto max-w-[1200px] space-y-4">
      <div className="flex items-center justify-between gap-3">
        <Link
          to="/"
          className="focusable text-sm text-slate-400 underline-offset-2 hover:text-cyan hover:underline"
        >
          ← Overview
        </Link>
        <span className="tnum text-xs text-slate-500">
          As of {new Date(status.as_of).toLocaleString()}
        </span>
      </div>

      <ReportHeader status={status} />

      <KeyTrend status={status} />

      <ScoreExplanation drivers={status.drivers} levers={status.levers} />

      <LayerStack status={status} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ContributionsPanel contributions={status.contributions} />
        <MissingDataPanel missingData={status.missing_data} />
      </div>

      <EvidenceList evidence={evidence} />

      <p className="px-1 pb-6 text-xs leading-relaxed text-slate-600">
        This report interprets your data within your personal baseline, not
        against population thresholds. It is informational and non-diagnostic —
        discuss any concerns with a qualified clinician.
      </p>
    </div>
  );
}

function ReportHeader({ status }: { status: DomainStatus }) {
  const st = scoreToStatus(status.score);
  return (
    <Panel className="p-5" glow>
      <SectionHeader
        kicker="Domain report"
        title={domainLabel[status.domain] ?? status.domain}
        trailing={
          <GlowButton variant="ghost" size="sm" disabled>
            {status.score_label}
          </GlowButton>
        }
      />
      <div className="mt-4 flex flex-col gap-5 sm:flex-row sm:items-center">
        <StatRing score={status.score} caption="score" size={120} />
        <div className="flex-1 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={st} />
            <TrendIndicator trend={status.trend} showLabel />
            <ProvenanceTag provenance={status.score == null ? "inferred" : "measured"} />
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <div className="flex items-center gap-2">
              <span className="text-[11px] uppercase tracking-wider text-slate-500">
                Confidence
              </span>
              <ConfidenceMeter confidence={status.confidence} />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] uppercase tracking-wider text-slate-500">
                Evidence
              </span>
              <EvidenceBadge grade={status.evidence_grade} />
            </div>
          </div>
          <p className="text-sm leading-relaxed text-slate-300">{status.summary}</p>
        </div>
      </div>
    </Panel>
  );
}

function KeyTrend({ status }: { status: DomainStatus }) {
  const key = KEY_METRIC[status.domain as Domain];
  // Hooks must run unconditionally; the hook is disabled when metric is absent.
  const metricQuery = useMetric(key?.metric, "day");

  if (!key) return null;

  return (
    <Panel className="p-4">
      <SectionHeader
        kicker="Key metric"
        title={key.label}
        trailing={<ProvenanceTag provenance="measured" />}
      />
      <div className="mt-3">
        {metricQuery.isLoading ? (
          <div className="grid h-[220px] place-items-center text-sm text-slate-500">
            Loading {key.label}…
          </div>
        ) : metricQuery.isError ? (
          <div className="grid h-[220px] place-items-center text-sm text-slate-500">
            Metric data unavailable.
          </div>
        ) : metricQuery.data ? (
          <TrendChart series={metricQuery.data} label={key.label} />
        ) : null}
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Shaded band shows your personal baseline (mean ±1 SD); dashed line is the
        baseline mean. Within-person, not a clinical threshold.
      </p>
    </Panel>
  );
}
