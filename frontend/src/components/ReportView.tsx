import { Fragment, useState } from "react";
import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts";

import type { Evidence, PlanFact, Report, ReportFacts } from "../api/types";
import { CYCLE_LABEL, formatDateTime, reportSummary } from "../lib/format";
import { StatusBadge } from "./StatusBadge";
import { Card, Notice, Stat, Tag } from "./ui";

function EvidenceBlock({ plan, evidence }: { plan: PlanFact; evidence: Evidence[] }) {
  const ev = evidence.filter((e) => e.plan_id === plan.plan_id);
  return (
    <div className="space-y-2 rounded-lg bg-slate-50 p-3 text-xs text-slate-700">
      {plan.evidence && (
        <p>
          <span className="font-medium text-slate-900">Text on the page: </span>
          <q className="italic">{plan.evidence}</q>
        </p>
      )}
      {ev.map((e, i) => (
        <div key={i} className="border-t border-slate-200 pt-2">
          <p>
            <StatusBadge status={e.status} /> <span className="tabular-nums">{e.price.display}</span> · {CYCLE_LABEL[e.billing_cycle] ?? `${e.billing_cycle} months`} · observed {formatDateTime(e.observed_at)}
          </p>
          <p className="mt-1 italic">“{e.evidence_snippet}”</p>
          {e.source_url && (
            <a href={e.source_url} target="_blank" rel="noreferrer noopener" className="mt-1 inline-block break-all text-indigo-600 hover:underline">
              {e.source_url}
            </a>
          )}
        </div>
      ))}
      {!plan.evidence && ev.length === 0 && <p>{plan.is_current ? "This is your current subscription; the price is the one you entered." : "No evidence recorded."}</p>}
    </div>
  );
}

function PlanTable({ plans, evidence, fixed }: { plans: PlanFact[]; evidence: Evidence[]; fixed: ReportFacts["fixed_items"] }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="-mx-5 overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-5 py-2.5">Plan</th>
            <th className="px-3 py-2.5">Price</th>
            <th className="px-3 py-2.5">Per month</th>
            <th className="px-3 py-2.5">Price status</th>
            <th className="px-5 py-2.5 text-right">Evidence</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {plans.map((p) => (
            <Fragment key={p.plan_id}>
              <tr>
                <td className="px-5 py-3">
                  <p className="font-medium text-slate-900">{p.name}</p>
                  <p className="text-xs text-slate-500">{p.provider_name}{p.is_current && " · you have this"}</p>
                </td>
                <td className="px-3 py-3 tabular-nums">{p.price_display}<span className="text-xs text-slate-500"> · {CYCLE_LABEL[p.billing_cycle_months] ?? `${p.billing_cycle_months} mo`}</span></td>
                <td className="px-3 py-3 font-medium tabular-nums">{p.monthly_display}</td>
                <td className="px-3 py-3">
                  <StatusBadge status={p.label} />
                  {p.observed_at && <p className="mt-1 text-xs text-slate-500">{formatDateTime(p.observed_at)}</p>}
                </td>
                <td className="px-5 py-3 text-right">
                  <button type="button" onClick={() => setOpen(open === p.plan_id ? null : p.plan_id)} className="text-xs font-medium text-indigo-600 hover:underline" aria-expanded={open === p.plan_id}>
                    {open === p.plan_id ? "Hide" : "Show"}
                  </button>
                </td>
              </tr>
              {open === p.plan_id && (
                <tr>
                  <td colSpan={5} className="px-5 pb-4"><EvidenceBlock plan={p} evidence={evidence} /></td>
                </tr>
              )}
            </Fragment>
          ))}
          {fixed.map((f) => (
            <tr key={`fixed-${f.name}`}>
              <td className="px-5 py-3"><p className="font-medium text-slate-900">{f.name}</p><p className="text-xs text-slate-500">Kept — not in the catalog</p></td>
              <td className="px-3 py-3">—</td>
              <td className="px-3 py-3 font-medium tabular-nums">{f.monthly_display}</td>
              <td className="px-3 py-3"><StatusBadge status="user_entered" /></td>
              <td className="px-5 py-3" />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SavingsChart({ report }: { report: Report }) {
  if (!report.recommended_monthly) return null;
  const data = [
    { name: "Current", value: report.current_monthly.paise / 100, display: report.current_monthly.display },
    { name: "Recommended", value: report.recommended_monthly.paise / 100, display: report.recommended_monthly.display },
  ];
  return (
    <div className="h-40" data-testid="savings-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 80 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" width={100} fontSize={12} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={28}>
            <Cell fill="#94a3b8" />
            <Cell fill="#4f46e5" />
            <LabelList dataKey="display" position="right" fontSize={12} fill="#334155" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function List({ title, items, tone }: { title: string; items: string[]; tone: "green" | "red" | "slate" | "amber" | "indigo" }) {
  if (!items.length) return null;
  return (
    <div>
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <div className="flex flex-wrap gap-1.5">{items.map((i) => <Tag key={i} tone={tone}>{i}</Tag>)}</div>
    </div>
  );
}

export function ReportView({ report }: { report: Report }) {
  const f = report.facts as unknown as ReportFacts;
  const summary = reportSummary(report.markdown);
  const feasible = f.status === "optimal";
  const saving = f.monthly_saving_paise ?? 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="You pay now" value={f.current_total_display} sub="per month" />
        <Stat label="Recommended" value={f.recommended_total_display ?? "No feasible set"} sub={f.budget_display ? `Budget ${f.budget_display}${f.within_budget === false ? " — over budget" : ""}` : "No budget set"} tone={f.within_budget === false ? "bad" : undefined} />
        <Stat
          label={saving >= 0 ? "Monthly saving" : "Extra per month"}
          value={f.monthly_saving_display ?? "—"}
          sub={f.annual_saving_display ? `${f.annual_saving_display} per year` : undefined}
          tone={saving > 0 ? "good" : saving < 0 ? "bad" : undefined}
        />
      </div>

      <Card title={<span className="flex items-center gap-2">Recommendation <Tag>{`v${report.version}`}</Tag> <Tag tone={report.status === "approved" ? "green" : report.status === "rejected" ? "red" : "amber"}>{report.status}</Tag></span>} actions={<span className="text-xs text-slate-500">Written by {report.generated_by === "llm" ? "the local LLM (numbers checked)" : "the template (LLM unavailable or failed checks)"}</span>}>
        {summary && <p className="whitespace-pre-line text-sm leading-6 text-slate-700">{summary}</p>}
        {!feasible && (
          <div className="mt-4">
            <Notice tone="warn">
              <p className="font-medium">No plan combination satisfies all your constraints.</p>
              {f.diagnosis && <p className="mt-1">{f.diagnosis}</p>}
              {Object.keys(f.diagnosis_amounts).length > 0 && (
                <ul className="mt-2 list-disc pl-5">
                  {Object.entries(f.diagnosis_amounts).map(([k, v]) => <li key={k}>{k.replace(/_/g, " ")}: {v}</li>)}
                </ul>
              )}
            </Notice>
          </div>
        )}
        {feasible && <div className="mt-5"><SavingsChart report={report} /></div>}
      </Card>

      {feasible && (
        <Card title="Recommended plans">
          <PlanTable plans={f.recommended} evidence={report.evidence} fixed={f.fixed_items} />
        </Card>
      )}

      {feasible && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="What changes">
            <div className="space-y-4">
              <List title="Keep" items={f.keep} tone="slate" />
              <List title="Add" items={f.add} tone="indigo" />
              <List title="Drop" items={f.drop} tone="red" />
              {!f.keep.length && !f.add.length && !f.drop.length && <p className="text-sm text-slate-500">No changes.</p>}
            </div>
          </Card>
          <Card title="Features">
            <div className="space-y-4">
              <List title="Covered" items={f.features_covered} tone="green" />
              <List title="Lost compared with today" items={f.features_lost} tone="red" />
              <List title="Nice-to-have not covered" items={f.missing_nice_to_have} tone="amber" />
              {f.missing_must_have.length > 0 && <List title="Must-have not covered" items={f.missing_must_have} tone="red" />}
            </div>
          </Card>
        </div>
      )}

      {Object.keys(f.current_overlaps).length > 0 && (
        <Card title="Overlaps in what you pay for today">
          <ul className="space-y-1 text-sm text-slate-700">
            {Object.entries(f.current_overlaps).map(([feat, names]) => (
              <li key={feat}><span className="font-medium">{feat}</span> — paid for in {names.join(", ")}</li>
            ))}
          </ul>
        </Card>
      )}

      {(f.alternatives.length > 0 || f.rejected.length > 0) && (
        <div className="grid gap-6 lg:grid-cols-2">
          {f.alternatives.length > 0 && (
            <Card title="Alternatives considered">
              <ul className="space-y-2 text-sm">
                {f.alternatives.map((a, i) => (
                  <li key={i} className="flex justify-between gap-3">
                    <span className="text-slate-700">{a.plans.join(" + ") || "Nothing"}{a.missing_nice_to_have.length > 0 && <span className="text-xs text-slate-500"> (misses {a.missing_nice_to_have.join(", ")})</span>}</span>
                    <span className="whitespace-nowrap tabular-nums text-slate-900">{a.total_display}/mo</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
          {f.rejected.length > 0 && (
            <Card title="Plans ruled out">
              <ul className="max-h-72 space-y-1.5 overflow-y-auto text-sm">
                {f.rejected.map((r, i) => (
                  <li key={i}><span className="font-medium text-slate-800">{r.name}</span> <span className="text-slate-500">— {r.reason}</span></li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}

      {f.data_issues.length > 0 && (
        <Notice tone="warn">
          <p className="font-medium">Data limitations</p>
          <ul className="mt-1 list-disc pl-5">{f.data_issues.map((d, i) => <li key={i}>{d}</li>)}</ul>
        </Notice>
      )}

      <details className="rounded-xl border border-slate-200 bg-white p-5 text-sm">
        <summary className="cursor-pointer font-medium text-slate-700">Full report text</summary>
        <pre className="mt-4 whitespace-pre-wrap font-sans text-slate-700">{report.markdown}</pre>
      </details>
    </div>
  );
}
