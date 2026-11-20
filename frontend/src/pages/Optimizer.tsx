import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router";

import { api } from "../api/client";
import { Button, Card, ErrorNote, Notice, PageHeader } from "../components/ui";
import { keys, useInvalidatingMutation, useMe, useSubscriptions } from "../hooks/queries";

const MODES = [
  { value: "auto", label: "Let SubWise decide", hint: "Uses the wording of your request." },
  { value: "savings", label: "Maximum savings", hint: "Cheapest set that keeps your must-haves." },
  { value: "balanced", label: "Balanced", hint: "Trades a little cost for nice-to-have features." },
  { value: "best", label: "Best coverage", hint: "Keeps as many features as the budget allows." },
] as const;

const EXAMPLES = [
  "Cut my bill but keep cricket and ad-free music.",
  "I want to spend under ₹600 a month. I mostly watch movies and listen to music daily.",
  "Which of my subscriptions overlap? Keep Netflix.",
];

export function OptimizerPage() {
  const navigate = useNavigate();
  const subs = useSubscriptions();
  const me = useMe();
  const [message, setMessage] = useState("");
  const [mode, setMode] = useState<(typeof MODES)[number]["value"]>("auto");
  const start = useInvalidatingMutation(api.startRun, [keys.runs, keys.dashboard]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    const run = await start.mutateAsync({ message: message.trim(), mode });
    navigate(`/app/runs/${run.run_id}`);
  };

  const activeSubs = (subs.data ?? []).filter((s) => s.active);

  return (
    <>
      <PageHeader title="Optimizer" subtitle="Describe what you want in plain language. SubWise fetches current prices, optimizes, and shows every step." />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="New optimization" className="lg:col-span-2">
          <form onSubmit={submit} className="space-y-5">
            <div>
              <label htmlFor="msg" className="block text-sm font-medium text-slate-700">What would you like?</label>
              <textarea
                id="msg"
                rows={4}
                maxLength={2000}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="e.g. Keep live cricket, I don't need 4K, and stay under ₹500 a month."
                className="mt-1.5 block w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-indigo-500"
              />
              <div className="mt-2 flex flex-wrap gap-2">
                {EXAMPLES.map((ex) => (
                  <button key={ex} type="button" onClick={() => setMessage(ex)} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700 hover:bg-slate-200">
                    {ex}
                  </button>
                ))}
              </div>
            </div>
            <fieldset>
              <legend className="text-sm font-medium text-slate-700">Optimization mode</legend>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                {MODES.map((m) => (
                  <label key={m.value} className={`cursor-pointer rounded-lg p-3 ring-1 ring-inset ${mode === m.value ? "bg-indigo-50 ring-indigo-500" : "ring-slate-200 hover:bg-slate-50"}`}>
                    <input type="radio" name="mode" value={m.value} checked={mode === m.value} onChange={() => setMode(m.value)} className="sr-only" />
                    <p className="text-sm font-medium text-slate-900">{m.label}</p>
                    <p className="text-xs text-slate-500">{m.hint}</p>
                  </label>
                ))}
              </div>
            </fieldset>
            <ErrorNote error={start.error} />
            <div className="flex justify-end">
              <Button type="submit" busy={start.isPending} disabled={!message.trim()}>Start optimization</Button>
            </div>
          </form>
        </Card>
        <div className="space-y-4">
          <Card title="What will be used">
            <ul className="space-y-2 text-sm text-slate-700">
              <li>
                <span className="font-medium">{activeSubs.length}</span> active subscription{activeSubs.length === 1 ? "" : "s"} as your baseline.{" "}
                <Link to="/app/subscriptions" className="text-indigo-600 hover:underline">Edit</Link>
              </li>
              <li>
                Budget: <span className="font-medium">{me.data?.profile.monthly_budget?.display ?? "not set"}</span>
                {me.data?.profile.monthly_budget && " per month"}.{" "}
                <Link to="/app/settings" className="text-indigo-600 hover:underline">Change</Link>
              </li>
              <li>Prices are fetched from each provider’s official page during the run.</li>
            </ul>
          </Card>
          {activeSubs.length === 0 && (
            <Notice tone="warn">You haven’t added any subscriptions. The optimizer can still suggest plans, but it can’t calculate savings.</Notice>
          )}
        </div>
      </div>
    </>
  );
}
