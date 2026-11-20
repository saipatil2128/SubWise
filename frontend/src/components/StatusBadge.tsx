import type { Freshness, ObservationStatus } from "../api/types";

type BadgeKind = ObservationStatus | Extract<Freshness, "stale">;

const STYLES: Record<BadgeKind, { label: string; className: string }> = {
  verified: { label: "Verified", className: "bg-emerald-100 text-emerald-800" },
  partial: { label: "Partial", className: "bg-sky-100 text-sky-800" },
  unverified: { label: "Unverified", className: "bg-amber-100 text-amber-800" },
  conflict: { label: "Conflict", className: "bg-rose-100 text-rose-800" },
  stale: { label: "Stale", className: "bg-slate-200 text-slate-700" },
};

/** Every price in the UI carries one of these badges (blueprint I.1). */
export function StatusBadge({ status, title }: { status: BadgeKind; title?: string }) {
  const style = STYLES[status];
  return (
    <span
      title={title}
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${style.className}`}
    >
      {style.label}
    </span>
  );
}
