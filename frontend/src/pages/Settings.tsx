import { useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router";

import { api } from "../api/client";
import type { FeatureRequirement, MemoryItem, ProfileIn } from "../api/types";
import { Button, Card, ErrorNote, Field, Input, Loading, Notice, PageHeader, Select, Tag } from "../components/ui";
import { keys, useFeatures, useInvalidatingMutation, useMe, useMemory, useRequirements } from "../hooks/queries";
import { formatDateTime, paiseToRupeesInput, rupeesToPaise } from "../lib/format";

type Eligibility = NonNullable<ProfileIn["eligibility"]>[number];
const ELIGIBILITY: { value: Eligibility; label: string }[] = [
  { value: "student", label: "I'm a student (student plans)" },
  { value: "new_customer", label: "New customer offers" },
  { value: "telecom_customer", label: "Telecom bundle offers" },
];

function Toggle({ checked, onChange, label, hint }: { checked: boolean; onChange: (v: boolean) => void; label: string; hint: string }) {
  return (
    <label className="flex items-start gap-3 text-sm">
      <input type="checkbox" className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>
        <span className="font-medium text-slate-800">{label}</span>
        <span className="block text-xs text-slate-500">{hint}</span>
      </span>
    </label>
  );
}

function ProfileCard() {
  const me = useMe();
  const qc = useQueryClient();
  const [form, setForm] = useState<ProfileIn | null>(null);
  const [budget, setBudget] = useState("");
  const [saved, setSaved] = useState(false);
  const save = useInvalidatingMutation(api.putProfile, [keys.me, keys.dashboard]);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (me.data && !form) {
      const p = me.data.profile;
      setForm({
        country: p.country,
        currency: p.currency,
        budget_paise: p.budget_paise ?? null,
        budget_period: p.budget_period,
        billing_preference: p.billing_preference,
        ads_tolerance: p.ads_tolerance,
        allow_cached_prices: p.allow_cached_prices,
        allow_partial_prices: p.allow_partial_prices,
        allow_unverified_prices: p.allow_unverified_prices,
        eligibility: p.eligibility ?? [],
      });
      setBudget(paiseToRupeesInput(p.budget_paise));
    }
  }, [me.data, form]);

  if (!form) return <Loading />;
  const set = <K extends keyof ProfileIn>(k: K, v: ProfileIn[K]) => {
    setSaved(false);
    setForm({ ...form, [k]: v });
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    let budget_paise: number | null = null;
    if (budget.trim()) {
      budget_paise = rupeesToPaise(budget);
      if (budget_paise === null) {
        setError(new Error("Budget must be an amount in rupees, e.g. 500."));
        return;
      }
    }
    try {
      await save.mutateAsync({ ...form, budget_paise });
      await qc.invalidateQueries({ queryKey: keys.me });
      setSaved(true);
    } catch (err) {
      setError(err);
    }
  };

  const elig = new Set(form.eligibility ?? []);

  return (
    <Card title="Budget & plan preferences">
      <form onSubmit={submit} className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Budget (₹)" htmlFor="budget" hint="Leave empty for no limit.">
            <Input id="budget" inputMode="decimal" value={budget} onChange={(e) => { setSaved(false); setBudget(e.target.value); }} />
          </Field>
          <Field label="Budget period" htmlFor="period">
            <Select id="period" value={form.budget_period} onChange={(e) => set("budget_period", e.target.value as ProfileIn["budget_period"])}>
              <option value="monthly">Per month</option>
              <option value="annual">Per year</option>
            </Select>
          </Field>
          <Field label="Country / currency" htmlFor="country" hint="SubWise currently supports India.">
            <Input id="country" value="India · INR (₹)" disabled readOnly />
          </Field>
          <Field label="Billing preference" htmlFor="billing">
            <Select id="billing" value={form.billing_preference} onChange={(e) => set("billing_preference", e.target.value as ProfileIn["billing_preference"])}>
              <option value="any">Any — whichever is cheaper</option>
              <option value="monthly">Monthly only</option>
              <option value="annual">Annual is fine / preferred</option>
            </Select>
          </Field>
          <Field label="Ads in video plans" htmlFor="ads">
            <Select id="ads" value={form.ads_tolerance} onChange={(e) => set("ads_tolerance", e.target.value as ProfileIn["ads_tolerance"])}>
              <option value="ok">Ads are fine</option>
              <option value="avoid">Prefer ad-free</option>
              <option value="never">Never — ad-free only</option>
            </Select>
          </Field>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-slate-700">Eligibility for special plans</p>
          <div className="flex flex-wrap gap-4">
            {ELIGIBILITY.map((o) => (
              <label key={o.value} className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                  checked={elig.has(o.value)}
                  onChange={(e) => {
                    const next = new Set(elig);
                    if (e.target.checked) next.add(o.value);
                    else next.delete(o.value);
                    set("eligibility", [...next]);
                  }}
                />
                {o.label}
              </label>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-700">Which prices may the optimizer use?</p>
          <p className="text-xs text-slate-500">Live, verified prices are always used. Your own subscriptions always use the price you entered.</p>
          <Toggle checked={form.allow_cached_prices} onChange={(v) => set("allow_cached_prices", v)} label="Cached, previously verified prices (up to 30 days old)" hint="Used when a provider's page can't be reached right now." />
          <Toggle checked={form.allow_partial_prices} onChange={(v) => set("allow_partial_prices", v)} label="Partially verified prices" hint="Found on the official page, but not every detail could be bound to the plan." />
          <Toggle checked={form.allow_unverified_prices} onChange={(v) => set("allow_unverified_prices", v)} label="Unverified prices" hint="Not recommended. They are clearly labelled in reports." />
        </div>

        <ErrorNote error={error} />
        <div className="flex items-center justify-end gap-3">
          {saved && <span className="text-sm text-emerald-700">Saved</span>}
          <Button type="submit" busy={save.isPending}>Save preferences</Button>
        </div>
      </form>
    </Card>
  );
}

const LEVELS = [
  { value: "must", label: "Must have" },
  { value: "nice", label: "Nice to have" },
  { value: "none", label: "Don't care" },
] as const;

function RequirementsCard() {
  const features = useFeatures();
  const reqs = useRequirements();
  const [rows, setRows] = useState<Record<string, FeatureRequirement> | null>(null);
  const [saved, setSaved] = useState(false);
  const save = useInvalidatingMutation(api.putRequirements, [keys.requirements]);

  useEffect(() => {
    if (features.data && reqs.data && !rows) {
      const map: Record<string, FeatureRequirement> = {};
      for (const f of features.data) map[f.code] = { feature_code: f.code, level: "none", weight: 0.5 };
      for (const r of reqs.data.requirements) map[r.feature_code] = r;
      setRows(map);
    }
  }, [features.data, reqs.data, rows]);

  if (!rows || !features.data) return <Card title="Features you need"><Loading /></Card>;

  const groups: Record<string, typeof features.data> = {};
  for (const f of features.data) (groups[f.category ?? "general"] ??= []).push(f);

  const update = (code: string, patch: Partial<FeatureRequirement>) => {
    setSaved(false);
    setRows({ ...rows, [code]: { ...rows[code]!, ...patch } });
  };

  const submit = async () => {
    await save.mutateAsync(Object.values(rows).filter((r) => r.level !== "none"));
    setSaved(true);
  };

  return (
    <Card title="Features you need" actions={<>{saved && <span className="text-sm text-emerald-700">Saved</span>}<Button busy={save.isPending} onClick={submit}>Save features</Button></>}>
      <p className="mb-4 text-sm text-slate-500">
        “Must have” features are hard constraints: a recommendation that loses one is never made. “Nice to have” features are traded off against price using their importance.
      </p>
      <ErrorNote error={save.error} />
      <div className="space-y-6">
        {Object.entries(groups).map(([cat, list]) => (
          <div key={cat}>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{cat === "video" ? "Video" : cat === "music" ? "Music" : "General"}</p>
            <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
              {list.map((f) => {
                const r = rows[f.code]!;
                return (
                  <div key={f.code} className="flex flex-wrap items-center gap-3 px-4 py-3">
                    <div className="min-w-48 flex-1">
                      <p className="text-sm font-medium text-slate-800">{f.label}</p>
                      <p className="text-xs text-slate-500">{f.description}</p>
                    </div>
                    <div className="flex rounded-lg bg-slate-100 p-0.5" role="radiogroup" aria-label={`${f.label} requirement`}>
                      {LEVELS.map((l) => (
                        <button
                          key={l.value}
                          type="button"
                          role="radio"
                          aria-checked={r.level === l.value}
                          onClick={() => update(f.code, { level: l.value })}
                          className={`rounded-md px-2.5 py-1 text-xs font-medium ${r.level === l.value ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
                        >
                          {l.label}
                        </button>
                      ))}
                    </div>
                    {r.level === "nice" && (
                      <label className="flex items-center gap-2 text-xs text-slate-600">
                        Importance
                        <input type="range" min={0.1} max={1} step={0.1} value={r.weight} onChange={(e) => update(f.code, { weight: Number(e.target.value) })} aria-label={`${f.label} importance`} />
                        <span className="w-6 tabular-nums">{r.weight.toFixed(1)}</span>
                      </label>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function describeMemory(m: MemoryItem): { kind: string; text: string } {
  const v = m.value as Record<string, string | undefined>;
  if (m.kind === "rejections") return { kind: "Rejected plan", text: `${v.plan ?? m.key}${v.reason ? ` — “${v.reason}”` : ""}` };
  if (m.kind === "stated_priorities") return { kind: "Priority", text: v.text ?? m.key };
  if (m.kind === "provider_attitudes") return { kind: "Provider", text: `${v.provider ?? m.key}: ${v.attitude ?? ""}` };
  return { kind: m.kind, text: m.key };
}

function MemoryCard() {
  const memory = useMemory();
  const forget = useInvalidatingMutation(({ kind, key }: { kind: string; key: string }) => api.forget(kind, key), [keys.memory]);
  return (
    <Card title="What SubWise has learned">
      <p className="mb-4 text-sm text-slate-500">
        Learned only when you approve or reject a recommendation. It shapes future recommendations. Delete anything you don’t want used.
      </p>
      {memory.isLoading && <Loading />}
      <ErrorNote error={memory.error ?? forget.error} />
      {memory.data?.length === 0 && <p className="text-sm text-slate-500">Nothing learned yet.</p>}
      <ul className="divide-y divide-slate-100">
        {memory.data?.map((m) => {
          const d = describeMemory(m);
          return (
            <li key={`${m.kind}/${m.key}`} className="flex items-center justify-between gap-3 py-2.5 text-sm">
              <div className="min-w-0">
                <Tag tone={m.kind === "rejections" ? "red" : "indigo"}>{d.kind}</Tag>
                <span className="ml-2 text-slate-800">{d.text}</span>
                <span className="ml-2 text-xs text-slate-400">{formatDateTime(m.created_at)}</span>
              </div>
              <Button variant="ghost" busy={forget.isPending && forget.variables?.key === m.key} onClick={() => forget.mutate({ kind: m.kind, key: m.key })}>
                Forget
              </Button>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function AccountCard() {
  const me = useMe();
  const qc = useQueryClient();
  const navigate = useNavigate();
  return (
    <Card title="Account">
      <div className="flex flex-wrap items-center justify-between gap-4 text-sm">
        <div>
          <p className="font-medium text-slate-800">{me.data?.user.display_name}</p>
          <p className="text-slate-500">{me.data?.user.email} · member since {formatDateTime(me.data?.user.created_at)}</p>
        </div>
        <Button
          variant="secondary"
          onClick={async () => {
            await api.logout().catch(() => undefined);
            qc.clear();
            navigate("/login");
          }}
        >
          Sign out
        </Button>
      </div>
    </Card>
  );
}

export function SettingsPage() {
  return (
    <>
      <PageHeader title="Preferences" subtitle="Budget, features and the data the optimizer may rely on." />
      <div className="space-y-6">
        <Notice>These settings are saved to your account and used by every optimization. You can also state a budget or needs in plain language on the Optimizer page; that applies to that run only.</Notice>
        <ProfileCard />
        <RequirementsCard />
        <MemoryCard />
        <AccountCard />
      </div>
    </>
  );
}
