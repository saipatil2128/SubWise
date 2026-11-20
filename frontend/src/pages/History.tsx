import { Link } from "react-router";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { RunStatusBadge } from "../components/StatusBadge";
import { Card, EmptyState, ErrorNote, Loading, PageHeader } from "../components/ui";
import { useRuns } from "../hooks/queries";
import { formatDateTime } from "../lib/format";

export function HistoryPage() {
  const { data, isLoading, error } = useRuns();
  const withReports = (data ?? []).filter((r) => r.current_monthly && r.recommended_monthly).reverse();
  const chart = withReports.map((r) => ({
    when: formatDateTime(r.created_at),
    current: r.current_monthly!.paise / 100,
    recommended: r.recommended_monthly!.paise / 100,
    currentDisplay: r.current_monthly!.display,
    recommendedDisplay: r.recommended_monthly!.display,
  }));

  return (
    <>
      <PageHeader title="History" subtitle="Every optimization you've run, with its outcome." />
      {isLoading && <Loading />}
      <ErrorNote error={error} />
      {data && data.length === 0 && (
        <EmptyState title="No optimizations yet" action={<Link to="/app/optimize" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">Run the optimizer</Link>} />
      )}
      {chart.length > 0 && (
        <Card title="Current vs recommended monthly cost" className="mb-6">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="when" fontSize={11} />
                <YAxis fontSize={11} tickFormatter={(v: number) => `₹${v}`} width={60} />
                <Tooltip
                  formatter={(_v, name, item) => {
                    const p = item.payload as { currentDisplay: string; recommendedDisplay: string };
                    return [name === "Current" ? p.currentDisplay : p.recommendedDisplay, name];
                  }}
                />
                <Legend />
                <Bar dataKey="current" name="Current" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="recommended" name="Recommended" fill="#4f46e5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}
      {data && data.length > 0 && (
        <Card>
          <ul className="-my-5 divide-y divide-slate-100">
            {data.map((r) => (
              <li key={r.run_id} className="flex flex-wrap items-center gap-4 py-4">
                <div className="min-w-0 flex-1">
                  <Link to={`/app/runs/${r.run_id}`} className="font-medium text-slate-900 hover:text-indigo-700">{r.request_message}</Link>
                  <p className="text-xs text-slate-500">
                    {formatDateTime(r.created_at)} · mode {r.mode}{r.revision > 0 && ` · ${r.revision} revision${r.revision === 1 ? "" : "s"}`}
                    {r.error_message && <span className="text-rose-600"> · {r.error_message}</span>}
                  </p>
                </div>
                {r.current_monthly && r.recommended_monthly && (
                  <p className="text-sm tabular-nums text-slate-700">{r.current_monthly.display} → <span className="font-semibold">{r.recommended_monthly.display}</span>/mo</p>
                )}
                {r.latest_report_status && <span className="text-xs text-slate-500">report {r.latest_report_status}</span>}
                <RunStatusBadge status={r.status} />
                {r.latest_report_id && <Link to={`/app/reports/${r.latest_report_id}`} className="text-xs font-medium text-indigo-600 hover:underline">Report</Link>}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
