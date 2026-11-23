import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router";

import { api, ApiError } from "../api/client";
import { useHealth, useMe } from "../hooks/queries";
import { Loading } from "./ui";

const NAV = [
  { to: "/app", label: "Dashboard", icon: "◧", end: true },
  { to: "/app/subscriptions", label: "Subscriptions", icon: "☰" },
  { to: "/app/optimize", label: "Optimizer", icon: "✦" },
  { to: "/app/plans", label: "Plans & prices", icon: "₹" },
  { to: "/app/compare", label: "Compare plans", icon: "⇄" },
  { to: "/app/history", label: "History", icon: "↺" },
  { to: "/app/settings", label: "Preferences", icon: "⚙" },
];

export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-semibold tracking-tight ${className}`}>
      <span className="grid h-7 w-7 place-items-center rounded-lg bg-indigo-600 text-sm text-white">S</span>
      SubWise
    </span>
  );
}

function HealthDot() {
  const { data, isError } = useHealth();
  const llm = data?.llm as { reachable?: boolean; model_present?: boolean; model?: string } | undefined;
  const ok = data && !isError;
  const llmOk = !!(llm?.reachable && llm.model_present);
  return (
    <div className="space-y-1 text-xs text-slate-400">
      <p className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${ok ? "bg-emerald-400" : "bg-rose-400"}`} />
        Backend {ok ? "online" : "unreachable"}
      </p>
      {ok && (
        <p className="flex items-center gap-2" title={llmOk ? `Model ${llm?.model ?? ""}` : "Start Ollama: `ollama serve` and `ollama pull qwen2.5:3b`. Rule-based fallbacks are used meanwhile."}>
          <span className={`h-2 w-2 rounded-full ${llmOk ? "bg-emerald-400" : "bg-amber-400"}`} />
          LLM {llmOk ? (llm?.model ?? "ready") : llm?.reachable ? "model not pulled" : "offline (fallbacks)"}
        </p>
      )}
    </div>
  );
}

/** Authenticated application shell. Redirects to /login when the session cookie is missing. */
export function AppLayout() {
  const me = useMe();
  const location = useLocation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);

  if (me.isLoading) return <div className="p-10"><Loading /></div>;
  if (me.error instanceof ApiError && me.error.status === 401) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (me.error) {
    return (
      <div className="mx-auto max-w-lg p-10 text-sm text-slate-700">
        <p className="font-medium">Cannot reach the SubWise backend.</p>
        <p className="mt-2">Start it from VS Code (Run and Debug → “Backend”) or with <code>scripts\dev.ps1</code>, then reload.</p>
      </div>
    );
  }

  const logout = async () => {
    await api.logout().catch(() => undefined);
    qc.clear();
    navigate("/login");
  };

  const sidebar = (
    <nav className="flex h-full flex-col gap-1 p-4">
      <div className="mb-6 px-2 text-white"><Logo /></div>
      {NAV.map((n) => (
        <NavLink
          key={n.to}
          to={n.to}
          end={n.end}
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-white/10 text-white" : "text-slate-300 hover:bg-white/5 hover:text-white"}`
          }
        >
          <span className="w-4 text-center opacity-80">{n.icon}</span>
          {n.label}
        </NavLink>
      ))}
      <div className="mt-auto space-y-4 border-t border-white/10 px-2 pt-4">
        <HealthDot />
        <div className="text-xs text-slate-400">
          <p className="truncate text-slate-200">{me.data?.user.display_name}</p>
          <p className="truncate">{me.data?.user.email}</p>
        </div>
        <button type="button" onClick={logout} className="text-xs font-medium text-slate-300 hover:text-white">
          Sign out
        </button>
      </div>
    </nav>
  );

  return (
    <div className="min-h-screen bg-slate-50 print:bg-white">
      <aside className="fixed inset-y-0 left-0 hidden w-60 bg-slate-900 lg:block print:!hidden">{sidebar}</aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-slate-900/50" />
          <aside className="absolute inset-y-0 left-0 w-64 bg-slate-900" onClick={(e) => e.stopPropagation()}>{sidebar}</aside>
        </div>
      )}
      <div className="lg:pl-60 print:!pl-0">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden print:hidden">
          <button type="button" aria-label="Open menu" onClick={() => setOpen(true)} className="rounded p-1 text-slate-700 hover:bg-slate-100">☰</button>
          <Logo />
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
