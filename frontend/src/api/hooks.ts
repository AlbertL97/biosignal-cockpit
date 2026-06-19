// React Query hooks over the typed API client. All read-only GETs.
import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { apiGet } from "./client";
import type {
  DomainStatus,
  EvidenceRef,
  MetricSeries,
  NebulaTrait,
  Profile,
} from "./types";

/** Window granularity accepted by the metrics endpoint. */
export type MetricWindow = "day" | "week" | "month";

const STALE = 5 * 60 * 1000; // 5 minutes — local single-user data changes rarely.

export function useProfile(): UseQueryResult<Profile> {
  return useQuery({
    queryKey: ["profile"],
    queryFn: ({ signal }) => apiGet<Profile>("/profile", undefined, signal),
    staleTime: STALE,
  });
}

export function useDomains(): UseQueryResult<DomainStatus[]> {
  return useQuery({
    queryKey: ["domains"],
    queryFn: ({ signal }) => apiGet<DomainStatus[]>("/domains", undefined, signal),
    staleTime: STALE,
  });
}

export function useDomain(domain: string | undefined): UseQueryResult<DomainStatus> {
  return useQuery({
    queryKey: ["domain", domain],
    queryFn: ({ signal }) =>
      apiGet<DomainStatus>(`/domains/${domain}`, undefined, signal),
    enabled: !!domain,
    staleTime: STALE,
  });
}

export function useMetric(
  metric: string | undefined,
  window: MetricWindow = "day",
): UseQueryResult<MetricSeries> {
  return useQuery({
    queryKey: ["metric", metric, window],
    queryFn: ({ signal }) =>
      apiGet<MetricSeries>(`/metrics/${metric}`, { window }, signal),
    enabled: !!metric,
    staleTime: STALE,
  });
}

export function useGenomeTraits(category?: string): UseQueryResult<NebulaTrait[]> {
  return useQuery({
    queryKey: ["genome-traits", category ?? "all"],
    queryFn: ({ signal }) =>
      apiGet<NebulaTrait[]>("/genome/traits", { category }, signal),
    staleTime: STALE,
  });
}

export function useGenomeTrait(
  id: number | string | undefined,
): UseQueryResult<NebulaTrait> {
  return useQuery({
    queryKey: ["genome-trait", String(id)],
    queryFn: ({ signal }) =>
      apiGet<NebulaTrait>(`/genome/traits/${id}`, undefined, signal),
    enabled: id !== undefined && id !== "",
    staleTime: STALE,
  });
}

export function useEvidence(domain: string | undefined): UseQueryResult<EvidenceRef[]> {
  return useQuery({
    queryKey: ["evidence", domain],
    queryFn: ({ signal }) =>
      apiGet<EvidenceRef[]>("/evidence", { domain }, signal),
    enabled: !!domain,
    staleTime: STALE,
  });
}
