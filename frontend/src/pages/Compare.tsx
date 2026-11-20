import { useSearchParams } from "react-router";

import type { PlanPrice } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { Card, EmptyState, Loading, PageHeader, Select } from "../components/ui";
import { useFeatures, usePlans } from "../hooks/queries";
import { CYCLE_LABEL, formatDateTime } from "../lib/format";

const MAX = 3;

function Cell({ value }: { value: string | undefined }) {
  if (value === "yes") return <span className="font-medium text-emerald-700">✓ Yes</span>;
  if (value === "no") return <span className="text-rose-700">✕ No</span>;
  return <span className="text-slate-400" title="Not stated on the provider's page">Not stated</span>;
}

export function ComparePage() {
  const plans = usePlans();
  const features = useFeatures();
  const [params, setParams] = useSearchParams();
  const ids = (params.get("plans") ?? "").split(",").filter(Boolean).slice(0, MAX);
  const byId = new Map((plans.data ?? []).map((p) => [p.plan_id, p]));
  const chosen = ids.map((id) => byId.get(id)).filter((p): p is PlanPrice => !!p);

  const setIds = (next: string[]) => {
    const p = new URLSearchParams(params);
    if (next.length) p.set("plans", next.join(","));
    else p.delete("plans");
    setParams(p, { replace: true });
  };

  if (plans.isLoading) return <Loading />;
  const all = [...(plans.data ?? [])].sort((a, b) => a.provider_name.localeCompare(b.provider_name) || a.monthly.paise - b.monthly.paise);
  const cheapest = chosen.length > 1 ? Math.min(...chosen.map((p) => p.monthly.paise)) : null;

  const featureRows = (features.data ?? []).filter((f) => chosen.some((p) => p.features[f.code] !== undefined));

  return (
    <>
      <PageHeader title="Compare plans" subtitle={`Pick up to ${MAX} plans to compare cost, data quality and stated features side by side.`} />
      <Card className="mb-6">
        <div className="grid gap-3 sm:grid-cols-3">
          {Array.from({ length: MAX }, (_, i) => (
            <Select
              key={i}
              aria-label={`Plan ${i + 1}`}
              value={ids[i] ?? ""}
              onChange={(e) => {
                const next = [...ids];
                if (e.target.value) next[i] = e.target.value;
                else next.splice(i, 1);
                setIds(next.filter(Boolean));
              }}
              disabled={i > ids.length}
            >
              <option value="">{i > ids.length ? "—" : "Choose a plan…"}</option>
              {all.map((p) => (
                <option key={p.plan_id} value={p.plan_id} disabled={ids.includes(p.plan_id) && ids[i] !== p.plan_id}>
                  {p.provider_name} · {p.plan_name} ({CYCLE_LABEL[p.billing_cycle]})
                </option>
              ))}
            </Select>
          ))}
        </div>
      </Card>

      {(plans.data ?? []).length === 0 ? (
        <EmptyState title="No plans available">Fetch prices on the Plans & prices page first.</EmptyState>
      ) : chosen.length === 0 ? (
        <EmptyState title="Choose plans to compare" />
      ) : (
        <Card>
          <div className="-m-5 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="w-48 px-5 py-4" />
                  {chosen.map((p) => (
                    <th key={p.plan_id} className="px-4 py-4 text-left align-top">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{p.provider_name}</p>
                      <p className="text-base font-semibold text-slate-900">{p.plan_name}</p>
                      <button type="button" onClick={() => setIds(ids.filter((x) => x !== p.plan_id))} className="mt-1 text-xs font-normal text-slate-400 hover:text-rose-600">Remove</button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr><td className="px-5 py-3 text-slate-500">Price</td>{chosen.map((p) => <td key={p.plan_id} className="px-4 py-3 tabular-nums">{p.price.display} · {CYCLE_LABEL[p.billing_cycle]}</td>)}</tr>
                <tr>
                  <td className="px-5 py-3 text-slate-500">Per month</td>
                  {chosen.map((p) => (
                    <td key={p.plan_id} className="px-4 py-3 font-semibold tabular-nums">
                      {p.monthly.display}
                      {cheapest !== null && p.monthly.paise === cheapest && <span className="ml-2 rounded bg-emerald-50 px-1.5 py-0.5 text-xs font-medium text-emerald-700">Lowest</span>}
                    </td>
                  ))}
                </tr>
                <tr><td className="px-5 py-3 text-slate-500">Per year</td>{chosen.map((p) => <td key={p.plan_id} className="px-4 py-3 tabular-nums">{p.annual.display}</td>)}</tr>
                <tr><td className="px-5 py-3 text-slate-500">Intro offer</td>{chosen.map((p) => <td key={p.plan_id} className="px-4 py-3">{p.intro ? `${String(p.intro.price_display ?? "")} for ${String(p.intro.months ?? "?")} mo` : "—"}</td>)}</tr>
                <tr><td className="px-5 py-3 text-slate-500">Price status</td>{chosen.map((p) => <td key={p.plan_id} className="px-4 py-3"><StatusBadge status={p.label} /><p className="mt-1 text-xs text-slate-500">{formatDateTime(p.observed_at)}</p></td>)}</tr>
                {featureRows.map((f) => (
                  <tr key={f.code}><td className="px-5 py-3 text-slate-500">{f.label}</td>{chosen.map((p) => <td key={p.plan_id} className="px-4 py-3"><Cell value={p.features[f.code]} /></td>)}</tr>
                ))}
                <tr>
                  <td className="px-5 py-3 text-slate-500">Source</td>
                  {chosen.map((p) => (
                    <td key={p.plan_id} className="px-4 py-3 text-xs">
                      {p.source_url ? <a href={p.source_url} target="_blank" rel="noreferrer noopener" className="break-all text-indigo-600 hover:underline">Official page</a> : "—"}
                      <p className="mt-1 italic text-slate-500">“{p.evidence}”</p>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
          {chosen.length > 1 && cheapest !== null && (
            <p className="mt-4 text-xs text-slate-500">Features marked “Not stated” were not found in the text of the provider’s page; they may still be included.</p>
          )}
        </Card>
      )}
    </>
  );
}
