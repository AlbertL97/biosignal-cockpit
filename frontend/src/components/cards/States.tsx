import { GlowButton, Panel } from "@/design";

/** Centered loading indicator for page-level fetches. */
export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div
      className="grid place-items-center py-16 text-sm text-slate-400"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-3">
        <span
          aria-hidden
          className="h-4 w-4 animate-spin rounded-full border-2 border-cyan/30 border-t-cyan"
        />
        {label}
      </div>
    </div>
  );
}

/** Page-level error panel with optional retry. */
export function ErrorState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  const message =
    error instanceof Error ? error.message : "Something went wrong loading this view.";
  return (
    <Panel className="mx-auto mt-10 max-w-md p-6 text-center" glow>
      <div className="text-sm font-semibold text-alert">Unable to load data</div>
      <p className="mt-2 text-sm text-slate-400">{message}</p>
      {onRetry && (
        <div className="mt-4">
          <GlowButton variant="outline" size="sm" onClick={onRetry}>
            Retry
          </GlowButton>
        </div>
      )}
    </Panel>
  );
}

/** Neutral empty-state message. */
export function EmptyState({ label }: { label: string }) {
  return (
    <div className="grid place-items-center py-16 text-sm text-slate-500">{label}</div>
  );
}
