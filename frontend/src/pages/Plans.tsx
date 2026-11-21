import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api } from "../api/client";
import type { PlanPrice, RefreshResult } from "../api/types";
import { OutcomeBadge, StatusBadge, statusHelp } from "../components/StatusBadge";
import { Button, Card, EmptyState, ErrorNote, Loading, Modal, Notice, PageHeader, Select, Tag } from "../components/ui";
import { keys, useFeatures, usePlans, usePriceHistory, useProviders } from "../hooks/queries";
import { CYCLE_LABEL, formatDate, formatDateTime } from "../lib/format";

function HistoryModal({ plan, onClose }: { plan: PlanPrice | null; onClose: () => void }) {
  const history = usePriceHistory(plan?.plan_id ?? null);
  const features = useFeatures();
  const labels = new Map((features.data ?? []).map((f) => [f.code, f.label]));
  const points = (history.data ?? []).map((h) => ({
    when: formatDate(h.observed_at),
    value: h.price.paise / 100,
    display: h.price.display,
    status: h.status,
    kind: h.kind,
  }));
  return (
    <Modal open={!!plan} title={plan ? `${plan.provider_name} · ${plan.plan_name}` : ""} onClose={onClose}>
      {plan && (
        <div className="space-y-5 text-sm">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xl font-semibold tabular-nums">{plan.price.display}</span>
            <span className="text-slate-500">{CYCLE_LABEL[plan.billing_cycle]} · {plan.monthly.display}/mo · {plan.annual.display}/yr</span>
            <StatusBadge status={plan.label} />
          </div>
          <p className="text-xs text-slate-500">{statusHelp(plan.label)}</p>
          <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-700">
            <p className="font-medium text-slate-900">Evidence</p>
            <p className="mt-1 italic">“{plan.evidence}”</p>
            <p className="mt-2">Observed {formatDateTime(plan.observed_at)} ({plan.age_days} day{plan.age_days === 1 ? "" : "s"} ago)</p>
            {plan.source_url && <a className="mt-1 inline-block break-all text-indigo-600 hover:underline" href={plan.source_url} target="_blank" rel="noreferrer noopener">{plan.source_url}</a>}
          </div>
          {plan.intro && (
            <Notice tone="info">
              Introductory offer: {String(plan.intro.price_display ?? "")} for {String(plan.intro.months ?? "?")} month(s), then the regular price above.
              {plan.intro.evidence ? <span className="block italic">“{String(plan.intro.evidence)}”</span> : null}
            </Notice>
          )}
          <div>
            <p className="mb-1.5 font-medium text-slate-900">Features stated on the page</p>
            {Object.keys(plan.features).length === 0 ? (
              <p className="text-xs text-slate-500">None could be read from the page.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(plan.features).map(([code, v]) => (
                  <Tag key={code} tone={v === "yes" ? "green" : v === "no" ? "red" : "slate"}>{v === "no" ? "No " : ""}{labels.get(code) ?? code}</Tag>
                ))}
              </div>
            )}
          </div>
          <div>
            <p className="mb-1.5 font-medium text-slate-900">Price history</p>
            {history.isLoading ? <Loading /> : points.length < 2 ? (
              <p className="text-xs text-slate-500">{points.length === 1 ? "Only one observation so far." : "No history."} History builds up each time prices are refreshed.</p>
            ) : (
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={points}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="when" fontSize={11} />
                    <YAxis fontSize={11} tickFormatter={(v: number) => `₹${v}`} width={60} />
                    <Tooltip formatter={(_v, _n, item) => [(item.payload as { display: string }).display, "Price"]} />
                    <Line type="stepAfter" dataKey="value" stroke="#4f46e5" strokeWidth={2} dot />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}

export function PlansPage() {
  const qc = useQueryClient();
  const providers = useProviders();
  const plans = usePlans();
  const [provider, setProvider] = useState("");
  const [category, setCategory] = useState("");
  const [cycle, setCycle] = useState("");
  const [selected, setSelected] = useState<PlanPrice | null>(null);
  const [refreshing, setRefreshing] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<unknown>(null);
  const [lastRefresh, setLastRefresh] = useState<RefreshResult[] | null>(null);

  const categoryOf = useMemo(() => new Map((providers.data ?? []).map((p) => [p.id, p.category])), [providers.data]);
  const filtered = (plans.data ?? [])
    .filter((p) => (!provider || p.provider_id === provider) && (!category || categoryOf.get(p.provider_id) === category) && (!cycle || String(p.billing_cycle) === cycle))
    .sort((a, b) => a.provider_name.localeCompare(b.provider_name) || a.monthly.paise - b.monthly.paise);

  const refresh = async (ids?: string[]) => {
    setRefreshing(ids?.[0] ?? "all");
    setRefreshError(null);
    try {
      const res = await api.refreshPrices(ids);
      setLastRefresh(res);
      await Promise.all([qc.invalidateQueries({ queryKey: keys.providers }), qc.invalidateQueries({ queryKey: keys.plans })]);
    } catch (err) {
      setRefreshError(err);
    } finally {
      setRefreshing(null);
    }
  };

  return (
    <>
      <PageHeader
        title="Plans & prices"
        subtitle="Prices read from each provider's official Indian pricing page. Nothing here is typed in by hand."
        actions={<Button busy={refreshing === "all"} disabled={!!refreshing} onClick={() => refresh()}>Refresh all prices</Button>}
      />
      <ErrorNote error={refreshError} />
      {refreshing === "all" && <div className="mb-4"><Notice>Fetching every provider's official page. This can take a minute; pages that need a browser take longer.</Notice></div>}
      {lastRefresh && !refreshing && (
        <div className="mb-4">
          <Notice tone={lastRefresh.every((r) => r.outcome === "success") ? "success" : "warn"}>
            Refreshed {lastRefresh.length} provider{lastRefresh.length === 1 ? "" : "s"}: {lastRefresh.filter((r) => r.outcome === "success").length} succeeded,{" "}
            {lastRefresh.reduce((n, r) => n + r.verified, 0)} verified prices found.
            {lastRefresh.some((r) => r.outcome !== "success") && " Providers that failed keep their earlier verified prices (shown as cached) — nothing is filled in."}
          </Notice>
        </div>
      )}

      <Card title="Providers" className="mb-6">
        {providers.isLoading ? <Loading /> : (
          <div className="-mx-5 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr><th className="px-5 py-2.5">Provider</th><th className="px-3 py-2.5">Last fetch</th><th className="px-3 py-2.5">Result</th><th className="px-3 py-2.5">Prices</th><th className="px-5 py-2.5 text-right" /></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(providers.data ?? []).map((p) => {
                  const a = p.latest_attempt;
                  return (
                    <tr key={p.id}>
                      <td className="px-5 py-3">
                        <p className="font-medium text-slate-900">{p.name}</p>
                        <a href={p.pricing_url} target="_blank" rel="noreferrer noopener" className="break-all text-xs text-indigo-600 hover:underline">{p.pricing_url}</a>
                      </td>
                      <td className="px-3 py-3 text-slate-600">{a ? formatDateTime(a.finished_at ?? a.started_at) : "Never"}</td>
                      <td className="px-3 py-3">
                        {a ? <OutcomeBadge outcome={a.outcome} /> : <span className="text-xs text-slate-400">—</span>}
                        {a?.error && <p className="mt-1 max-w-xs text-xs text-rose-700">{a.error}</p>}
                        {a?.warnings.slice(0, 2).map((w, i) => <p key={i} className="mt-1 max-w-xs text-xs text-amber-700">{w}</p>)}
                      </td>
                      <td className="px-3 py-3 tabular-nums text-slate-600">{a ? `${a.verified_found} verified / ${a.prices_found}` : "—"}</td>
                      <td className="px-5 py-3 text-right">
                        <Button variant="secondary" busy={refreshing === p.id} disabled={!!refreshing} onClick={() => refresh([p.id])}>Refresh</Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card
        title="Plans"
        actions={
          <>
            <Select aria-label="Filter by provider" value={provider} onChange={(e) => setProvider(e.target.value)} className="w-40">
              <option value="">All providers</option>
              {(providers.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </Select>
            <Select aria-label="Filter by category" value={category} onChange={(e) => setCategory(e.target.value)} className="w-32">
              <option value="">All types</option>
              <option value="video">Video</option>
              <option value="music">Music</option>
            </Select>
            <Select aria-label="Filter by billing" value={cycle} onChange={(e) => setCycle(e.target.value)} className="w-36">
              <option value="">Any billing</option>
              {Object.entries(CYCLE_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </Select>
          </>
        }
      >
        {plans.isLoading && <Loading />}
        <ErrorNote error={plans.error} />
        {plans.data && plans.data.length === 0 && (
          <EmptyState title="No prices fetched yet" action={<Button busy={refreshing === "all"} onClick={() => refresh()}>Fetch prices now</Button>}>
            Prices are fetched live from each provider. They are also fetched automatically when you run the optimizer.
          </EmptyState>
        )}
        {filtered.length > 0 && (
          <div className="-mx-5 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr><th className="px-5 py-2.5">Plan</th><th className="px-3 py-2.5">Price</th><th className="px-3 py-2.5">Per month</th><th className="px-3 py-2.5">Per year</th><th className="px-3 py-2.5">Status</th><th className="px-5 py-2.5 text-right" /></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((p) => (
                  <tr key={p.plan_id} className="hover:bg-slate-50">
                    <td className="px-5 py-3">
                      <p className="font-medium text-slate-900">{p.plan_name}</p>
                      <p className="text-xs text-slate-500">{p.provider_name}{p.intro && " · intro offer"}</p>
                    </td>
                    <td className="px-3 py-3 tabular-nums">{p.price.display}<span className="text-xs text-slate-500"> · {CYCLE_LABEL[p.billing_cycle]}</span></td>
                    <td className="px-3 py-3 font-medium tabular-nums">{p.monthly.display}</td>
                    <td className="px-3 py-3 tabular-nums">{p.annual.display}</td>
                    <td className="px-3 py-3"><StatusBadge status={p.label} /><p className="mt-1 text-xs text-slate-500">{p.age_days === 0 ? "today" : `${p.age_days}d ago`}</p></td>
                    <td className="whitespace-nowrap px-5 py-3 text-right">
                      <Button variant="ghost" onClick={() => setSelected(p)}>Evidence & history</Button>
                      <Link to={`/app/compare?plans=${encodeURIComponent(p.plan_id)}`} className="ml-1 text-xs font-medium text-indigo-600 hover:underline">Compare</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {plans.data && plans.data.length > 0 && filtered.length === 0 && <p className="text-sm text-slate-500">No plans match these filters.</p>}
      </Card>
      <HistoryModal plan={selected} onClose={() => setSelected(null)} />
    </>
  );
}
