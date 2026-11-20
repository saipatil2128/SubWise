const STYLES: Record<string, { label: string; className: string; help: string }> = {
  live_verified: {
    label: "Live · verified",
    className: "bg-emerald-100 text-emerald-800 ring-emerald-200",
    help: "Fetched from the provider's official page in the latest attempt (under 24 h ago) and bound to this plan by evidence.",
  },
  cached_verified: {
    label: "Cached · verified",
    className: "bg-teal-50 text-teal-800 ring-teal-200",
    help: "Verified on an earlier fetch. The latest fetch did not re-confirm it, or it is older than 24 h.",
  },
  partial: {
    label: "Partial",
    className: "bg-sky-50 text-sky-800 ring-sky-200",
    help: "A price was found on the official page but not every dimension (plan, cycle, region) could be bound.",
  },
  unverified: {
    label: "Unverified",
    className: "bg-amber-50 text-amber-800 ring-amber-200",
    help: "The price could not be tied to this plan with enough evidence.",
  },
  conflict: {
    label: "Conflict",
    className: "bg-rose-50 text-rose-800 ring-rose-200",
    help: "Sources disagree about this price.",
  },
  unavailable: {
    label: "Unavailable",
    className: "bg-slate-100 text-slate-600 ring-slate-200",
    help: "No usable price could be retrieved.",
  },
  user_entered: {
    label: "You entered",
    className: "bg-violet-50 text-violet-800 ring-violet-200",
    help: "The price you entered for your own subscription.",
  },
  // Raw observation statuses (price history)
  verified: { label: "Verified", className: "bg-emerald-100 text-emerald-800 ring-emerald-200", help: "Verified observation." },
};

export function statusHelp(label: string): string {
  return STYLES[label]?.help ?? label;
}

/** Every price in the UI carries one of these badges (blueprint I.1). */
export function StatusBadge({ status, title }: { status: string; title?: string }) {
  const style = STYLES[status] ?? { label: status, className: "bg-slate-100 text-slate-700 ring-slate-200", help: status };
  return (
    <span
      title={title ?? style.help}
      className={`inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${style.className}`}
    >
      {style.label}
    </span>
  );
}

const OUTCOME: Record<string, string> = {
  success: "bg-emerald-100 text-emerald-800",
  running: "bg-indigo-100 text-indigo-800",
  no_prices: "bg-amber-100 text-amber-800",
  needs_js: "bg-amber-100 text-amber-800",
  disallowed: "bg-rose-100 text-rose-800",
  failed: "bg-rose-100 text-rose-800",
};

export function OutcomeBadge({ outcome }: { outcome: string }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${OUTCOME[outcome] ?? "bg-slate-100 text-slate-700"}`}>
      {outcome.replace(/_/g, " ")}
    </span>
  );
}

const RUN: Record<string, string> = {
  queued: "bg-slate-100 text-slate-700",
  running: "bg-indigo-100 text-indigo-800",
  waiting_clarification: "bg-amber-100 text-amber-800",
  waiting_approval: "bg-amber-100 text-amber-800",
  completed: "bg-emerald-100 text-emerald-800",
  failed: "bg-rose-100 text-rose-800",
  cancelled: "bg-slate-200 text-slate-600",
};

export function RunStatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${RUN[status] ?? "bg-slate-100"}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
