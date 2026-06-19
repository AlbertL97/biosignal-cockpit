// Typed fetch wrapper for the same-origin /api surface (proxied to :8000 in dev).
// Throws ApiError on non-2xx responses so React Query can surface failures.

export class ApiError extends Error {
  readonly status: number;
  readonly url: string;
  constructor(status: number, url: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.url = url;
  }
}

/** Build a same-origin /api URL with optional query params. */
function buildUrl(path: string, params?: Record<string, string | undefined>): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  const base = `/api${clean}`;
  if (!params) return base;
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") search.set(k, v);
  }
  const qs = search.toString();
  return qs ? `${base}?${qs}` : base;
}

// ---------------------------------------------------------------------------
// Static demo mode: when built with VITE_DEMO=1 (GitHub Pages), there is no
// backend — every request is resolved from a single bundled JSON file.
// ---------------------------------------------------------------------------
export const IS_DEMO = import.meta.env.VITE_DEMO === "1";

interface DemoBundle {
  profile: unknown;
  domains: Array<{ domain: string }>;
  metrics: Record<string, unknown>;
  genomeTraits: Array<{ category: string | null }>;
  genomeTraitDetails: Record<string, unknown>;
  evidence: Record<string, unknown>;
}

let bundlePromise: Promise<DemoBundle> | null = null;
function loadBundle(): Promise<DemoBundle> {
  if (!bundlePromise) {
    const url = `${import.meta.env.BASE_URL}demo/bundle.json`;
    bundlePromise = fetch(url).then((r) => {
      if (!r.ok) throw new ApiError(r.status, url, "demo bundle unavailable");
      return r.json() as Promise<DemoBundle>;
    });
  }
  return bundlePromise;
}

async function demoGet<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const b = await loadBundle();
  const clean = path.replace(/^\//, "");
  const seg = clean.split("/");
  const notFound = (what: string): never => {
    throw new ApiError(404, path, `demo: ${what} not found`);
  };

  if (clean === "health") return { status: "ok" } as unknown as T;
  if (clean === "profile") return b.profile as T;
  if (clean === "domains") return b.domains as unknown as T;
  if (seg[0] === "domains" && seg[1]) {
    const d = b.domains.find((x) => x.domain === decodeURIComponent(seg[1]));
    return (d ?? notFound(`domain ${seg[1]}`)) as T;
  }
  if (seg[0] === "metrics" && seg[1]) {
    const m = b.metrics[decodeURIComponent(seg[1])];
    return (m ?? notFound(`metric ${seg[1]}`)) as T;
  }
  if (clean === "genome/traits") {
    const cat = params?.category;
    const list = cat ? b.genomeTraits.filter((t) => t.category === cat) : b.genomeTraits;
    return list as unknown as T;
  }
  if (seg[0] === "genome" && seg[1] === "traits" && seg[2]) {
    const t = b.genomeTraitDetails[decodeURIComponent(seg[2])];
    return (t ?? notFound(`trait ${seg[2]}`)) as T;
  }
  if (clean === "evidence") {
    const dom = params?.domain ?? "";
    return ((b.evidence[dom] as unknown) ?? []) as T;
  }
  return notFound(path);
}

/**
 * Typed GET against the API. Throws ApiError on !ok and on JSON parse errors.
 * In demo mode, resolves from the bundled JSON instead of the network.
 */
export async function apiGet<T>(
  path: string,
  params?: Record<string, string | undefined>,
  signal?: AbortSignal,
): Promise<T> {
  if (IS_DEMO) return demoGet<T>(path, params);
  const url = buildUrl(path, params);
  const res = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    signal,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string; message?: string };
      detail = body.detail ?? body.message ?? detail;
    } catch {
      // non-JSON error body — keep statusText
    }
    throw new ApiError(res.status, url, `Request failed (${res.status}): ${detail}`);
  }

  return (await res.json()) as T;
}
