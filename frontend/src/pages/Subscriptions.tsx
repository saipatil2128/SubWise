import { type FormEvent, useMemo, useState } from "react";

import { api } from "../api/client";
import type { Subscription, SubscriptionIn } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { Button, Card, EmptyState, ErrorNote, Field, Input, Loading, Modal, PageHeader, Select, Tag } from "../components/ui";
import { keys, usePlans, useProviders, useSubscriptions, useInvalidatingMutation } from "../hooks/queries";
import { CYCLE_LABEL, formatDate, paiseToRupeesInput, rupeesToPaise, USAGE_LABEL } from "../lib/format";

type Cycle = SubscriptionIn["billing_cycle"];
type Usage = SubscriptionIn["usage_frequency"];

interface FormState {
  provider_id: string; // "" = custom
  plan_id: string; // "" = not listed
  custom_name: string;
  price: string;
  billing_cycle: Cycle;
  renewal_date: string;
  usage_frequency: Usage;
  is_mandatory: boolean;
  notes: string;
}

const EMPTY: FormState = {
  provider_id: "",
  plan_id: "",
  custom_name: "",
  price: "",
  billing_cycle: 1,
  renewal_date: "",
  usage_frequency: "weekly",
  is_mandatory: false,
  notes: "",
};

const INVALIDATE = [keys.subscriptions, keys.dashboard];

function SubscriptionForm({ initial, editing, onDone }: { initial: FormState; editing: Subscription | null; onDone: () => void }) {
  const [f, setF] = useState<FormState>(initial);
  const [error, setError] = useState<unknown>(null);
  const providers = useProviders();
  const plans = usePlans();
  const create = useInvalidatingMutation(api.createSubscription, INVALIDATE);
  const update = useInvalidatingMutation(({ id, body }: { id: string; body: Parameters<typeof api.updateSubscription>[1] }) => api.updateSubscription(id, body), INVALIDATE);

  const providerPlans = useMemo(
    () => (plans.data ?? []).filter((p) => p.provider_id === f.provider_id),
    [plans.data, f.provider_id],
  );
  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setF((prev) => ({ ...prev, [k]: v }));

  const pickPlan = (planId: string) => {
    const plan = providerPlans.find((p) => p.plan_id === planId);
    setF((prev) => ({
      ...prev,
      plan_id: planId,
      billing_cycle: plan ? (plan.billing_cycle as Cycle) : prev.billing_cycle,
      price: prev.price || (plan ? paiseToRupeesInput(plan.price.paise) : ""),
    }));
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const price = rupeesToPaise(f.price);
    if (price === null || price <= 0) {
      setError(new Error("Enter the price you pay, in rupees (for example 149 or 149.50)."));
      return;
    }
    if (!f.provider_id && !f.custom_name.trim()) {
      setError(new Error("Give the subscription a name."));
      return;
    }
    try {
      if (editing) {
        await update.mutateAsync({
          id: editing.id,
          body: {
            plan_id: f.plan_id || null,
            price_paise: price,
            billing_cycle: f.billing_cycle,
            renewal_date: f.renewal_date || null,
            usage_frequency: f.usage_frequency,
            is_mandatory: f.is_mandatory,
            notes: f.notes.trim() || null,
          },
        });
      } else {
        await create.mutateAsync({
          provider_id: f.provider_id || null,
          plan_id: f.plan_id || null,
          custom_name: f.plan_id ? null : f.custom_name.trim() || null,
          price_paise: price,
          billing_cycle: f.billing_cycle,
          renewal_date: f.renewal_date || null,
          usage_frequency: f.usage_frequency,
          is_mandatory: f.is_mandatory,
          notes: f.notes.trim() || null,
        });
      }
      onDone();
    } catch (err) {
      setError(err);
    }
  };

  const selectedPlan = providerPlans.find((p) => p.plan_id === f.plan_id);

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Service" htmlFor="provider">
        <Select
          id="provider"
          value={f.provider_id}
          disabled={!!editing}
          onChange={(e) => setF((prev) => ({ ...prev, provider_id: e.target.value, plan_id: "" }))}
        >
          <option value="">Other (not in the catalog)</option>
          {(providers.data ?? []).map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </Select>
      </Field>

      {f.provider_id && (
        <Field
          label="Plan"
          htmlFor="plan"
          hint={
            providerPlans.length === 0
              ? "No plans have been fetched for this service yet — refresh prices on the Plans page, or name your plan below."
              : selectedPlan
                ? <>Listed price {selectedPlan.price.display} · <StatusBadge status={selectedPlan.label} /></>
                : "Pick your plan so the optimizer knows its features."
          }
        >
          <Select id="plan" value={f.plan_id} onChange={(e) => pickPlan(e.target.value)}>
            <option value="">My plan isn’t listed</option>
            {providerPlans.map((p) => (
              <option key={p.plan_id} value={p.plan_id}>
                {p.plan_name} · {CYCLE_LABEL[p.billing_cycle] ?? `${p.billing_cycle} months`}
              </option>
            ))}
          </Select>
        </Field>
      )}

      {!f.plan_id && !editing && (
        <Field label={f.provider_id ? "Plan name" : "Subscription name"} htmlFor="custom_name">
          <Input id="custom_name" maxLength={80} value={f.custom_name} placeholder={f.provider_id ? "e.g. Premium" : "e.g. Local cable"} onChange={(e) => set("custom_name", e.target.value)} />
        </Field>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Price you pay (₹)" htmlFor="price" hint="Including any discount you get.">
          <Input id="price" inputMode="decimal" required value={f.price} onChange={(e) => set("price", e.target.value)} />
        </Field>
        <Field label="Billed" htmlFor="cycle">
          <Select id="cycle" value={f.billing_cycle} onChange={(e) => set("billing_cycle", Number(e.target.value) as Cycle)}>
            {Object.entries(CYCLE_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
        </Field>
        <Field label="Next renewal" htmlFor="renewal">
          <Input id="renewal" type="date" value={f.renewal_date} onChange={(e) => set("renewal_date", e.target.value)} />
        </Field>
        <Field label="How often you use it" htmlFor="usage">
          <Select id="usage" value={f.usage_frequency} onChange={(e) => set("usage_frequency", e.target.value as Usage)}>
            {Object.entries(USAGE_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
        </Field>
      </div>

      <label className="flex items-start gap-3 text-sm text-slate-700">
        <input type="checkbox" className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600" checked={f.is_mandatory} onChange={(e) => set("is_mandatory", e.target.checked)} />
        <span><span className="font-medium">Must keep</span> — the optimizer will never drop this subscription.</span>
      </label>

      <Field label="Notes" htmlFor="notes">
        <Input id="notes" maxLength={300} value={f.notes} onChange={(e) => set("notes", e.target.value)} />
      </Field>

      <ErrorNote error={error} />
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onDone}>Cancel</Button>
        <Button type="submit" busy={create.isPending || update.isPending}>{editing ? "Save changes" : "Add subscription"}</Button>
      </div>
    </form>
  );
}

export function SubscriptionsPage() {
  const { data, isLoading, error } = useSubscriptions();
  const [modal, setModal] = useState<{ editing: Subscription | null } | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Subscription | null>(null);
  const remove = useInvalidatingMutation(api.deleteSubscription, INVALIDATE);
  const toggle = useInvalidatingMutation((s: Subscription) => api.updateSubscription(s.id, { active: !s.active }), INVALIDATE);

  const initialFor = (s: Subscription | null): FormState =>
    s
      ? {
          provider_id: s.provider_id ?? "",
          plan_id: s.plan_id ?? "",
          custom_name: s.display_name,
          price: paiseToRupeesInput(s.price.paise),
          billing_cycle: s.billing_cycle,
          renewal_date: s.renewal_date ?? "",
          usage_frequency: s.usage_frequency,
          is_mandatory: s.is_mandatory,
          notes: s.notes ?? "",
        }
      : EMPTY;

  return (
    <>
      <PageHeader
        title="Subscriptions"
        subtitle="What you pay today. These prices are yours — they are never replaced by fetched prices."
        actions={<Button onClick={() => setModal({ editing: null })}>Add subscription</Button>}
      />
      {isLoading && <Loading />}
      <ErrorNote error={error} />
      {data && data.length === 0 && (
        <EmptyState title="No subscriptions yet" action={<Button onClick={() => setModal({ editing: null })}>Add your first subscription</Button>}>
          Add every streaming or music service you pay for. The optimizer compares them against current plans.
        </EmptyState>
      )}
      {data && data.length > 0 && (
        <Card>
          <div className="-m-5 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3">Subscription</th>
                  <th className="px-3 py-3">Price</th>
                  <th className="px-3 py-3">Per month</th>
                  <th className="px-3 py-3">Per year</th>
                  <th className="px-3 py-3">Renews</th>
                  <th className="px-3 py-3">Usage</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.map((s) => (
                  <tr key={s.id} className={s.active ? "" : "opacity-50"}>
                    <td className="px-5 py-3">
                      <p className="font-medium text-slate-900">{s.display_name}</p>
                      <p className="flex flex-wrap gap-1.5 pt-1 text-xs text-slate-500">
                        {s.provider_name ?? "Custom"}
                        {s.is_mandatory && <Tag tone="indigo">Must keep</Tag>}
                        {!s.active && <Tag>Paused</Tag>}
                        {!s.plan_id && s.provider_id && <Tag tone="amber">Plan not linked</Tag>}
                      </p>
                    </td>
                    <td className="px-3 py-3 tabular-nums">{s.price.display}<span className="text-xs text-slate-500"> · {CYCLE_LABEL[s.billing_cycle]}</span></td>
                    <td className="px-3 py-3 tabular-nums">{s.monthly_equivalent.display}</td>
                    <td className="px-3 py-3 tabular-nums">{s.annual_cost.display}</td>
                    <td className="px-3 py-3">
                      {formatDate(s.renewal_date)}
                      {s.days_to_renewal !== null && s.days_to_renewal >= 0 && s.days_to_renewal <= 7 && <span className="ml-1 text-xs text-amber-700">({s.days_to_renewal}d)</span>}
                    </td>
                    <td className="px-3 py-3">{USAGE_LABEL[s.usage_frequency]}</td>
                    <td className="whitespace-nowrap px-5 py-3 text-right">
                      <Button variant="ghost" onClick={() => setModal({ editing: s })}>Edit</Button>
                      <Button variant="ghost" onClick={() => toggle.mutate(s)}>{s.active ? "Pause" : "Resume"}</Button>
                      <Button variant="ghost" className="text-rose-600 hover:text-rose-700" onClick={() => setConfirmDelete(s)}>Delete</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Modal open={!!modal} title={modal?.editing ? `Edit ${modal.editing.display_name}` : "Add subscription"} onClose={() => setModal(null)}>
        {modal && <SubscriptionForm key={modal.editing?.id ?? "new"} initial={initialFor(modal.editing)} editing={modal.editing} onDone={() => setModal(null)} />}
      </Modal>
      <Modal open={!!confirmDelete} title="Delete subscription?" onClose={() => setConfirmDelete(null)}>
        <p className="text-sm text-slate-600">“{confirmDelete?.display_name}” will be removed from SubWise. This does not cancel it with the provider.</p>
        <ErrorNote error={remove.error} />
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setConfirmDelete(null)}>Keep it</Button>
          <Button
            variant="danger"
            busy={remove.isPending}
            onClick={async () => {
              if (!confirmDelete) return;
              await remove.mutateAsync(confirmDelete.id);
              setConfirmDelete(null);
            }}
          >
            Delete
          </Button>
        </div>
      </Modal>
    </>
  );
}
