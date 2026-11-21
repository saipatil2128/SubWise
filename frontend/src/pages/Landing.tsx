import { Link } from "react-router";

import { Logo } from "../components/Layout";
import { useMe } from "../hooks/queries";

const STEPS = [
  {
    title: "Add what you pay for",
    body: "Enter your current streaming and music subscriptions with the price you actually pay, how often you use them, and when they renew.",
  },
  {
    title: "Prices fetched from the source",
    body: "SubWise reads each provider's official Indian pricing page when you optimize, binds every price to a plan with evidence, and labels anything it could not verify.",
  },
  {
    title: "An optimizer, not a guess",
    body: "An integer-programming model (OAVOE) picks the cheapest combination that keeps the features you need, within your budget, without overlapping plans.",
  },
  {
    title: "You approve every change",
    body: "Each step of the agent is shown live. You review the recommendation with its sources, then approve or reject it — rejections teach it your priorities.",
  },
];

const PROVIDERS = ["Netflix", "Prime Video", "Sony LIV", "Spotify", "YouTube Premium", "Apple Music"];

export function LandingPage() {
  const me = useMe();
  const signedIn = !!me.data;
  return (
    <div className="min-h-screen bg-white">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Logo className="text-slate-900" />
        <nav className="flex items-center gap-3 text-sm">
          {signedIn ? (
            <Link to="/app" className="rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700">Open dashboard</Link>
          ) : (
            <>
              <Link to="/login" className="font-medium text-slate-700 hover:text-slate-900">Sign in</Link>
              <Link to="/register" className="rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700">Create account</Link>
            </>
          )}
        </nav>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-16 pt-12 sm:pt-20">
        <p className="text-sm font-semibold uppercase tracking-wider text-indigo-600">Subscription cost optimizer · India</p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
          Keep what you watch and listen to. Stop paying twice for it.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-slate-600">
          SubWise compares your OTT and music subscriptions against live, source-verified prices and recommends the
          cheapest set of plans that still covers what you actually use.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link to={signedIn ? "/app/optimize" : "/register"} className="rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700">
            {signedIn ? "Run an optimization" : "Get started — it runs on your machine"}
          </Link>
          {!signedIn && (
            <Link to="/login" className="rounded-lg px-5 py-3 text-sm font-semibold text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50">
              I already have an account
            </Link>
          )}
        </div>
        <div className="mt-10 flex flex-wrap gap-2">
          {PROVIDERS.map((p) => (
            <span key={p} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">{p}</span>
          ))}
        </div>
      </section>

      <section className="border-t border-slate-100 bg-slate-50">
        <div className="mx-auto grid max-w-6xl gap-6 px-6 py-16 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <div key={s.title} className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <p className="text-sm font-semibold text-indigo-600">0{i + 1}</p>
              <h3 className="mt-2 font-semibold text-slate-900">{s.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid gap-8 lg:grid-cols-3">
          <div>
            <h3 className="font-semibold text-slate-900">Honest about data</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Every price shows whether it is live and verified, cached from an earlier verification, partial or unverified,
              with the source page and the exact text it came from. If a provider can't be reached, you're told — nothing is filled in.
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">Local and private</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              The app, its database and the language model (Qwen 2.5 3B through Ollama) all run on your own computer.
              No paid APIs are required.
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">Learns your priorities</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Reject a recommendation and say why. SubWise remembers which features matter to you and which providers you want
              to keep — and you can review or delete what it remembers at any time.
            </p>
          </div>
        </div>
      </section>

      <footer className="border-t border-slate-100 py-8 text-center text-xs text-slate-500">
        SubWise · prices change often — always confirm on the provider’s site before you subscribe.
      </footer>
    </div>
  );
}
