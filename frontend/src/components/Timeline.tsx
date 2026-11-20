import type { RunEvent } from "../api/types";

export const NODE_LABEL: Record<string, string> = {
  load_context: "Loading your subscriptions & preferences",
  parse_intent: "Understanding your request",
  clarify: "Asking you a question",
  plan_research: "Planning research",
  research: "Fetching prices from providers",
  validate: "Validating price evidence",
  decide: "Deciding whether data is sufficient",
  optimize: "Optimizing (OAVOE)",
  explain: "Writing the explanation",
  check_numbers: "Checking every number",
  approval: "Waiting for your approval",
  save_and_learn: "Saving your decision",
};

const ICON: Record<string, { mark: string; cls: string }> = {
  node_start: { mark: "●", cls: "text-indigo-500" },
  node_end: { mark: "✓", cls: "text-emerald-600" },
  tool_call: { mark: "↗", cls: "text-sky-600" },
  tool_error: { mark: "!", cls: "text-rose-600" },
  decision: { mark: "◆", cls: "text-violet-600" },
  fallback: { mark: "↺", cls: "text-amber-600" },
  interrupt: { mark: "❚❚", cls: "text-amber-600" },
};

/** Live agent timeline — every row is an event the backend recorded. */
export function Timeline({ events, live }: { events: RunEvent[]; live: boolean }) {
  if (events.length === 0) {
    return <p className="text-sm text-slate-500">{live ? "Waiting for the agent to start…" : "No events recorded."}</p>;
  }
  return (
    <ol className="relative space-y-3 border-l border-slate-200 pl-5" aria-live="polite">
      {events.map((e) => {
        const icon = ICON[e.event_type] ?? { mark: "·", cls: "text-slate-400" };
        return (
          <li key={e.seq} className="relative">
            <span className={`absolute -left-[27px] top-0.5 grid h-4 w-4 place-items-center rounded-full bg-white text-[10px] font-bold ${icon.cls}`}>{icon.mark}</span>
            <div className="flex flex-wrap items-baseline justify-between gap-x-3">
              <p className="text-sm text-slate-800">
                {e.node && e.event_type === "node_start" ? <span className="font-medium">{NODE_LABEL[e.node] ?? e.node}</span> : e.message}
              </p>
              <span className="text-xs tabular-nums text-slate-400">
                {e.duration_ms != null && `${(e.duration_ms / 1000).toFixed(1)}s · `}
                {new Date(e.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
            </div>
            {e.node && e.event_type === "node_start" && e.message && e.message !== NODE_LABEL[e.node] && <p className="text-xs text-slate-500">{e.message}</p>}
            {e.event_type === "tool_error" && e.payload && "error" in e.payload && <p className="text-xs text-rose-700">{String(e.payload.error)}</p>}
          </li>
        );
      })}
      {live && (
        <li className="relative">
          <span className="absolute -left-[25px] top-1.5 h-3 w-3 animate-ping rounded-full bg-indigo-400" />
          <p className="text-sm text-slate-500">Working…</p>
        </li>
      )}
    </ol>
  );
}
