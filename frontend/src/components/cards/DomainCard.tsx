import { motion, useReducedMotion } from "framer-motion";
import {
  Badge,
  ConfidenceMeter,
  EvidenceBadge,
  Panel,
  StatRing,
  StatusBadge,
  TrendIndicator,
  cn,
  domainLabel,
  motion as motionTokens,
  scoreToStatus,
} from "@/design";
import type { Domain } from "@/api/types";
import type { DomainStatus } from "@/api/types";

export interface DomainCardProps {
  status: DomainStatus;
  selected?: boolean;
  onSelect?: (id: Domain) => void;
}

/** Distinct top contributing sources, in first-seen order. */
function topSources(status: DomainStatus, limit = 3): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const c of status.contributions) {
    if (!seen.has(c.source)) {
      seen.add(c.source);
      out.push(c.source);
    }
    if (out.length >= limit) break;
  }
  return out;
}

/**
 * DomainCard — overview tile for one body-system domain. Surfaces score ring,
 * status, trend, confidence, evidence grade and the top contributing sources.
 * Selecting it opens the full domain report.
 */
export function DomainCard({ status, selected = false, onSelect }: DomainCardProps) {
  const st = scoreToStatus(status.score);
  const id = status.domain as Domain;
  const sources = topSources(status);
  const reduce = useReducedMotion();

  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: motionTokens.base }}
    >
      <Panel
        glow={selected}
        className={cn(
          "focusable cursor-pointer p-3 transition-transform hover:-translate-y-0.5",
          selected && "ring-1 ring-cyan/40",
        )}
      >
        <button
          type="button"
          onClick={() => onSelect?.(id)}
          className="block w-full text-left outline-none"
          aria-pressed={selected}
          aria-label={`Open ${domainLabel[status.domain] ?? status.domain} report`}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-slate-100">
                {domainLabel[status.domain] ?? status.domain}
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <StatusBadge status={st} />
                <TrendIndicator trend={status.trend} />
              </div>
            </div>
            <StatRing score={status.score} size={56} thickness={6} />
          </div>

          <div className="mt-2.5 flex items-center justify-between gap-2">
            <ConfidenceMeter confidence={status.confidence} showLabel={false} />
            <EvidenceBadge grade={status.evidence_grade} compact />
          </div>

          {sources.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-1">
              {sources.map((s) => (
                <Badge key={s} tone="neutral">
                  {s}
                </Badge>
              ))}
            </div>
          )}
        </button>
      </Panel>
    </motion.div>
  );
}
