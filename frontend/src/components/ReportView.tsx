import { Fragment, type ReactNode, useState } from "react";
import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts";

import type { Evidence, PlanFact, Report, ReportFacts } from "../api/types";
import { CYCLE_LABEL, formatDate, formatDateTime, reportSummary } from "../lib/format";
import { StatusBadge } from "./StatusBadge";
import { Button } from "./ui";

/** Feature codes and other snake_case identifiers -> readable words ("ad_free_music" -> "Ad-free music"). */
export function humanize(text: string, labels?: Map<string, string>): string {
  return text.replace(/\b[a-z0-9]+(?:_[a-z0-9]+)+\b/g, (code) => labels?.get(code) ?? code.replace(/_/g, " "));
}

const STATUS_TEXT: Record<string, { label: string; className: string }> = {
  pending: { label: "Awaiting your decision", className: "bg-amber-50 text-amber-800 ring-amber-200" },
  approved: { label: "Approved", className: "bg-emerald-50 text-emerald-800 ring-emerald-200" },
  rejected: { label: "Rejected", className: "bg-rose-50 text-rose-800 ring-rose-200" },
  superseded: { label: "Superseded", className: "bg-slate-100 text-slate-600 ring-slate-200" },
};

function Section({ n, title, children, lead }: { n: number; title: string; children: ReactNode; lead?: ReactNode }) {
  return (
    <section className="break-inside-avoid border-t border-slate-200 px-8 py-6">
      <h3 className="flex items-baseline gap-3 text-base font-semibold text-slate-900">
        <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-indigo-50 text-xs font-semibold text-indigo-700">{n}</span>
        <span>{title}</span>
      </h3>
      {lead && <p className="mt-1 pl-9 text-sm text-slate-500">{lead}</p>}
      <div className="mt-4 pl-9">{children}</div>
    </section>
  );
}

function Figure({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "good" | "bad" }) {
  const color = tone === "good" ? "text-emerald-700" : tone === "bad" ? "text-rose-700" : "text-slate-900";
  return (
    <div className="px-6 py-5">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${color}`}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

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
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-2.5">Plan</th>
            <th className="px-3 py-2.5">Price</th>
            <th className="px-3 py-2.5 text-right">Per month</th>
            <th className="px-3 py-2.5">Price status</th>
            <th className="px-4 py-2.5 text-right print:hidden">Evidence</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {plans.map((p) => (
            <Fragment key={p.plan_id}>
              <tr>
                <td className="px-4 py-3">
                  <p className="font-medium text-slate-900">{p.name}</p>
                  <p className="text-xs text-slate-500">{p.provider_name}{p.is_current && " · you already have this"}</p>
                </td>
                <td className="px-3 py-3 tabular-nums">{p.price_display}<span className="text-xs text-slate-500"> · {CYCLE_LABEL[p.billing_cycle_months] ?? `${p.billing_cycle_months} mo`}</span></td>
                <td className="px-3 py-3 text-right font-semibold tabular-nums">{p.monthly_display}</td>
                <td className="px-3 py-3">
                  <StatusBadge status={p.label} />
                  {p.observed_at && <p className="mt-1 text-xs text-slate-500">{formatDateTime(p.observed_at)}</p>}
                </td>
                <td className="px-4 py-3 text-right print:hidden">
                  <button type="button" onClick={() => setOpen(open === p.plan_id ? null : p.plan_id)} className="text-xs font-medium text-indigo-600 hover:underline" aria-expanded={open === p.plan_id}>
                    {open === p.plan_id ? "Hide" : "Show"}
                  </button>
                </td>
              </tr>
              {open === p.plan_id && (
                <tr>
                  <td colSpan={5} className="px-4 pb-4"><EvidenceBlock plan={p} evidence={evidence} /></td>
                </tr>
              )}
            </Fragment>
          ))}
          {fixed.map((f) => (
            <tr key={`fixed-${f.name}`}>
              <td className="px-4 py-3"><p className="font-medium text-slate-900">{f.name}</p><p className="text-xs text-slate-500">Kept — not in the catalog</p></td>
              <td className="px-3 py-3">—</td>
              <td className="px-3 py-3 text-right font-semibold tabular-nums">{f.monthly_display}</td>
              <td className="px-3 py-3"><StatusBadge status="user_entered" /></td>
              <td className="px-4 py-3 print:hidden" />
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
    { name: "You pay now", value: report.current_monthly.paise / 100, display: report.current_monthly.display },
    { name: "Recommended", value: report.recommended_monthly.paise / 100, display: report.recommended_monthly.display },
  ];
  return (
    <div className="mt-5 h-32" data-testid="savings-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 90 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" width={110} fontSize={12} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={26} isAnimationActive={false}>
            <Cell fill="#94a3b8" />
            <Cell fill="#4f46e5" />
            <LabelList dataKey="display" position="right" fontSize={12} fill="#334155" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function ChangeColumn({ title, items, tone, empty }: { title: string; items: string[]; tone: string; empty: string }) {
  return (
    <div className={`rounded-lg border p-4 ${tone}`}>
      <p className="text-xs font-semibold uppercase tracking-wide">{title}</p>
      {items.length ? (
        <ul className="mt-2 space-y-1 text-sm text-slate-800">
          {items.map((i) => <li key={i}><span>{i}</span></li>)}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-slate-500">{empty}</p>
      )}
    </div>
  );
}

function FeatureRow({ title, items, mark, markClass }: { title: string; items: string[]; mark: string; markClass: string }) {
  if (!items.length) return null;
  return (
    <div className="grid gap-2 py-2 sm:grid-cols-[180px_1fr]">
      <p className="text-sm font-medium text-slate-600">{title}</p>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-800">
        {items.map((i) => (
          <li key={i} className="flex items-center gap-1.5"><span className={`font-bold ${markClass}`}>{mark}</span><span>{i}</span></li>
        ))}
      </ul>
    </div>
  );
}

/** A recommendation laid out as a readable, printable report. */
export function ReportView({ report, featureLabels }: { report: Report; featureLabels?: Map<string, string> }) {
  const f = report.facts as unknown as ReportFacts;
  const h = (t: string) => humanize(t, featureLabels);
  const summary = h(reportSummary(report.markdown));
  const feasible = f.status === "optimal";
  const saving = f.monthly_saving_paise ?? 0;
  const status = STATUS_TEXT[report.status] ?? { label: report.status, className: "bg-slate-100 text-slate-700 ring-slate-200" };
  const headline = !feasible
    ? "No plan combination fits your constraints"
    : saving > 0
      ? `Save ${f.monthly_saving_display} a month`
      : saving < 0
        ? `Covers your needs for ${f.monthly_saving_display?.replace(/^-/, "")} more a month`
        : "Your current plans are already the best fit";
  const withEvidence = feasible ? f.recommended.filter((p) => p.source_url || p.evidence) : [];

  let n = 0;
  const next = () => ++n;

  return (
    <article className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm print:rounded-none print:border-0 print:shadow-none">
      <header className="flex flex-wrap items-start justify-between gap-4 bg-gradient-to-b from-indigo-50/70 to-white px-8 pb-6 pt-7">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">SubWise · Recommendation report</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{headline}</h2>
          <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
            <span>{formatDateTime(report.created_at)}</span>
            <span aria-hidden>·</span>
            <span>Version {report.version}</span>
            <span aria-hidden>·</span>
            <span className={`rounded-full px-2 py-0.5 font-medium ring-1 ring-inset ${status.className}`}>{status.label}</span>
            <span aria-hidden>·</span>
            <span>{report.generated_by === "llm" ? "Written by the local AI model, every number checked" : "Written from the optimizer's results"}</span>
          </p>
        </div>
        <Button variant="secondary" onClick={() => window.print()} className="print:hidden">Print / Save as PDF</Button>
      </header>

      <div className="grid divide-y divide-slate-200 border-t border-slate-200 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        <Figure label="You pay now" value={f.current_total_display} sub="per month" />
        <Figure
          label="Recommended"
          value={f.recommended_total_display ?? "—"}
          sub={f.budget_display ? `per month · budget ${f.budget_display}${f.within_budget === false ? " (over)" : ""}` : "per month · no budget set"}
          tone={f.within_budget === false ? "bad" : undefined}
        />
        <Figure
          label={saving >= 0 ? "Monthly saving" : "Extra per month"}
          value={f.monthly_saving_display ?? "—"}
          sub={f.annual_saving_display ? `${f.annual_saving_display} per year` : undefined}
          tone={saving > 0 ? "good" : saving < 0 ? "bad" : undefined}
        />
      </div>

      <Section n={next()} title="Summary">
        {summary ? <p className="whitespace-pre-line text-[15px] leading-7 text-slate-700">{summary}</p> : <p className="text-sm text-slate-500">No summary was written.</p>}
        {feasible && <SavingsChart report={report} />}
      </Section>

      {!feasible && (
        <Section n={next()} title="Why there is no recommendation">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <p className="font-medium">No plan combination satisfies all your constraints.</p>
            {f.diagnosis && <p className="mt-1">{h(f.diagnosis)}</p>}
            {Object.keys(f.diagnosis_amounts).length > 0 && (
              <ul className="mt-2 list-disc pl-5">
                {Object.entries(f.diagnosis_amounts).map(([k, v]) => <li key={k}>{k.replace(/_/g, " ")}: {v}</li>)}
              </ul>
            )}
            {f.missing_must_have.length > 0 && <p className="mt-2">Must-have features no available plan covers: {f.missing_must_have.join(", ")}.</p>}
          </div>
          <p className="mt-3 text-sm text-slate-600">
            What you can do: raise your budget, mark a feature as “Nice to have” instead of “Must have” in Preferences, or refresh prices if a provider failed below.
          </p>
        </Section>
      )}

      {feasible && (
        <Section n={next()} title="Recommended plans" lead="Every price is read from the provider's official page. Click Show to see the exact text it came from.">
          <PlanTable plans={f.recommended} evidence={report.evidence} fixed={f.fixed_items} />
        </Section>
      )}

      {feasible && (
        <Section n={next()} title="What changes">
          <div className="grid gap-3 sm:grid-cols-3">
            <ChangeColumn title="Keep" items={f.keep} tone="border-slate-200 bg-slate-50 text-slate-600" empty="Nothing" />
            <ChangeColumn title="Switch to / add" items={f.add} tone="border-indigo-200 bg-indigo-50/60 text-indigo-700" empty="Nothing new" />
            <ChangeColumn title="Cancel or replace" items={f.drop} tone="border-rose-200 bg-rose-50/60 text-rose-700" empty="Nothing" />
          </div>
        </Section>
      )}

      {feasible && (f.features_covered.length > 0 || f.features_lost.length > 0 || f.missing_nice_to_have.length > 0) && (
        <Section n={next()} title="Features">
          <div className="divide-y divide-slate-100">
            <FeatureRow title="Covered" items={f.features_covered} mark="✓" markClass="text-emerald-600" />
            <FeatureRow title="Lost compared with today" items={f.features_lost} mark="✕" markClass="text-rose-600" />
            <FeatureRow title="Nice-to-have not covered" items={f.missing_nice_to_have} mark="–" markClass="text-amber-600" />
            <FeatureRow title="Must-have not covered" items={f.missing_must_have} mark="!" markClass="text-rose-600" />
          </div>
        </Section>
      )}

      {Object.keys(f.current_overlaps).length > 0 && (
        <Section n={next()} title="Where you pay twice today" lead="The same feature is included in more than one of your current subscriptions.">
          <ul className="space-y-1.5 text-sm text-slate-700">
            {Object.entries(f.current_overlaps).map(([feat, names]) => (
              <li key={feat}><span className="font-medium text-slate-900">{h(feat)}</span> — in {names.join(", ")}</li>
            ))}
          </ul>
        </Section>
      )}

      {f.alternatives.length > 0 && (
        <Section n={next()} title="Alternatives considered" lead="The next-best combinations, in case you prefer a different trade-off.">
          <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200 text-sm">
            {f.alternatives.map((a, i) => (
              <li key={i} className="flex items-center justify-between gap-3 px-4 py-2.5">
                <span className="text-slate-800">
                  {a.plans.join(" + ") || "Nothing"}
                  {a.missing_nice_to_have.length > 0 && <span className="text-xs text-slate-500"> · misses {a.missing_nice_to_have.join(", ")}</span>}
                </span>
                <span className="whitespace-nowrap font-medium tabular-nums text-slate-900">{a.total_display}/mo</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {f.rejected.length > 0 && (
        <Section n={next()} title="Plans ruled out" lead="Why the optimizer did not pick these.">
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="min-w-full text-sm">
              <tbody className="divide-y divide-slate-100">
                {f.rejected.map((r, i) => (
                  <tr key={i}>
                    <td className="w-2/5 px-4 py-2 font-medium text-slate-800">{r.name}</td>
                    <td className="px-4 py-2 text-slate-600">{h(r.reason)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {f.data_issues.length > 0 && (
        <Section n={next()} title="Data limitations" lead="Providers whose prices could not be used. Nothing was filled in for them.">
          <ul className="space-y-1.5 text-sm text-amber-900">
            {f.data_issues.map((d, i) => (
              <li key={i} className="rounded-md bg-amber-50 px-3 py-2">{h(d)}</li>
            ))}
          </ul>
        </Section>
      )}

      {withEvidence.length > 0 && (
        <Section n={next()} title="Sources and evidence">
          <ol className="space-y-3 text-sm">
            {withEvidence.map((p, i) => (
              <li key={p.plan_id} className="flex gap-3">
                <span className="text-xs font-medium text-slate-400">[{i + 1}]</span>
                <div className="min-w-0">
                  <p className="font-medium text-slate-900">{p.name} — {p.price_display}</p>
                  {p.evidence && <p className="italic text-slate-600">“{p.evidence}”</p>}
                  <p className="text-xs text-slate-500">
                    {p.source_url && <a href={p.source_url} target="_blank" rel="noreferrer noopener" className="break-all text-indigo-600 hover:underline">{p.source_url}</a>}
                    {p.observed_at && <> · read {formatDate(p.observed_at)}</>}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </Section>
      )}

      <footer className="border-t border-slate-200 bg-slate-50 px-8 py-4 text-xs text-slate-500">
        Prices change often — confirm on the provider’s site before you subscribe or cancel. SubWise never subscribes or cancels anything for you.
      </footer>
    </article>
  );
}
