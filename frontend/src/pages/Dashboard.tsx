import { Link } from "react-router";
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Money } from "../api/types";
import { RunStatusBadge } from "../components/StatusBadge";
import { Card, EmptyState, ErrorNote, Loading, PageHeader, Stat } from "../components/ui";
import { useDashboard } from "../hooks/queries";
import { formatDateTime } from "../lib/format";

export const CHART_COLORS = ["#4f46e5", "#0891b2", "#059669", "#d97706", "#db2777", "#7c3aed", "#65a30d", "#475569"];

interface Renewal {
  name: string;
  date: string;
  days: number;
  amount: string;
}

interface LatestReport {
  id: string;
  run_id: string;
  status: string;
  created_at: string;
  current_monthly: string;
  recommended_monthly: string | null;
  monthly_saving: string | null;
}

/** Recharts needs numbers; rupees are used only for bar length. Labels always use the server's formatted string. */
const rupees = (m: Money) => m.paise / 100;

function MoneyTooltip({ active, payload }: { active?: boolean; payload?: { payload: { name: string; display: string } }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0]!.payload;
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow">
      <p className="font-medium text-slate-800">{p.name}</p>
      <p className="tabular-nums text-slate-600">{p.display} / month</p>
    </div>
  );
}

export function DashboardPage() {
  const { data, isLoading, error } = useDashboard();
  if (isLoading) return <Loading />;
  if (error || !data) return <ErrorNote error={error} title="Could not load the dashboard" />;

  const bySub = data.spend_by_subscription.map((s) => ({ name: s.name, value: rupees(s.monthly), display: s.monthly.display }));
  const byCat = data.spend_by_category.map((s) => ({
    name: s.name === "video" ? "Video" : s.name === "music" ? "Music" : s.name.charAt(0).toUpperCase() + s.name.slice(1),
    value: rupees(s.monthly),
    display: s.monthly.display,
  }));
  const renewals = data.renewals_next_30_days as unknown as Renewal[];
  const latest = data.latest_report as LatestReport | null;

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Your subscription spend at a glance."
        actions={
          <Link to="/app/optimize" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
            Optimize now
          </Link>
        }
      />

      {data.active_subscriptions === 0 ? (
        <EmptyState
          title="No subscriptions yet"
          action={<Link to="/app/subscriptions" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">Add your subscriptions</Link>}
        >
          Add the subscriptions you currently pay for, with the price you pay. SubWise uses them as the baseline for every optimization.
        </EmptyState>
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Monthly spend" value={data.monthly_spend.display} sub={`${data.active_subscriptions} active subscription${data.active_subscriptions === 1 ? "" : "s"}`} />
            <Stat label="Annual spend" value={data.annual_spend.display} sub="At current prices" />
            <Stat
              label="Monthly budget"
              value={data.budget_monthly?.display ?? "Not set"}
              sub={data.over_budget === null ? <Link className="text-indigo-600 hover:underline" to="/app/settings">Set a budget</Link> : data.over_budget ? "You are over budget" : "Within budget"}
              tone={data.over_budget ? "bad" : data.over_budget === false ? "good" : undefined}
            />
            <Stat
              label="Latest potential saving"
              value={latest?.monthly_saving ?? "—"}
              sub={latest ? `per month · ${formatDateTime(latest.created_at)}` : "Run the optimizer to find savings"}
              tone={latest?.monthly_saving ? "good" : undefined}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-5">
            <Card title="Monthly spend by subscription" className="lg:col-span-3">
              <div className="h-72" data-testid="spend-by-subscription">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={bySub} layout="vertical" margin={{ left: 8, right: 16 }}>
                    <XAxis type="number" tickFormatter={(v: number) => `₹${v}`} fontSize={12} />
                    <YAxis type="category" dataKey="name" width={130} fontSize={12} />
                    <Tooltip content={<MoneyTooltip />} cursor={{ fill: "#f1f5f9" }} />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                      {bySub.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card title="By category" className="lg:col-span-2">
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={byCat} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85} paddingAngle={2}>
                      {byCat.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    </Pie>
                    <Tooltip content={<MoneyTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="mt-2 space-y-1 text-sm">
                {byCat.map((c, i) => (
                  <li key={c.name} className="flex items-center justify-between">
                    <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />{c.name}</span>
                    <span className="tabular-nums text-slate-600">{c.display}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Renewals in the next 30 days">
              {renewals.length === 0 ? (
                <p className="text-sm text-slate-500">No renewals in the next 30 days{data.spend_by_subscription.length ? " (or no renewal dates entered)." : "."}</p>
              ) : (
                <ul className="divide-y divide-slate-100 text-sm">
                  {renewals.map((r) => (
                    <li key={`${r.name}-${r.date}`} className="flex items-center justify-between py-2">
                      <span className="font-medium text-slate-800">{r.name}</span>
                      <span className="text-slate-600">
                        <span className="tabular-nums">{r.amount}</span> · {r.days === 0 ? "today" : `in ${r.days} day${r.days === 1 ? "" : "s"}`}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card title="Recent optimizations" actions={<Link to="/app/history" className="text-xs font-medium text-indigo-600 hover:underline">View all</Link>}>
              {data.recent_runs.length === 0 ? (
                <p className="text-sm text-slate-500">No optimizations yet. <Link to="/app/optimize" className="text-indigo-600 hover:underline">Start one</Link>.</p>
              ) : (
                <ul className="divide-y divide-slate-100 text-sm">
                  {data.recent_runs.map((r) => (
                    <li key={r.run_id} className="flex items-center justify-between gap-3 py-2">
                      <Link to={`/app/runs/${r.run_id}`} className="min-w-0 flex-1 truncate text-slate-800 hover:text-indigo-700">{r.request_message}</Link>
                      {r.recommended_monthly && <span className="tabular-nums text-slate-600">{r.recommended_monthly.display}/mo</span>}
                      <RunStatusBadge status={r.status} />
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          {latest && (
            <Card title="Latest recommendation">
              <div className="flex flex-wrap items-center justify-between gap-4 text-sm">
                <p className="text-slate-700">
                  Current <span className="font-semibold tabular-nums">{latest.current_monthly}</span>
                  {latest.recommended_monthly && <> → recommended <span className="font-semibold tabular-nums">{latest.recommended_monthly}</span> per month</>}
                  {!latest.recommended_monthly && <> — no feasible plan combination was found.</>}
                </p>
                <Link to={`/app/reports/${latest.id}`} className="font-medium text-indigo-600 hover:underline">Open report →</Link>
              </div>
            </Card>
          )}
        </div>
      )}
    </>
  );
}
