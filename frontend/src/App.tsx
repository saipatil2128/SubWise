import { NavLink, Outlet } from "react-router";

import { useHealth } from "./hooks/useHealth";

const NAV = [
  { to: "/", label: "Dashboard" },
  { to: "/subscriptions", label: "My Subscriptions" },
  { to: "/optimizer", label: "AI Optimizer" },
  { to: "/prices", label: "Price Intelligence" },
  { to: "/history", label: "History" },
  { to: "/profile", label: "Profile" },
];

function BackendIndicator() {
  const health = useHealth();
  const label = health.isSuccess ? `API ${health.data.version}` : health.isError ? "API offline" : "API…";
  const color = health.isSuccess ? "bg-emerald-500" : health.isError ? "bg-rose-500" : "bg-slate-400";
  return (
    <span className="flex items-center gap-2 text-sm text-slate-600" data-testid="backend-indicator">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      {label}
    </span>
  );
}

export function Layout() {
  return (
    <div className="min-h-screen">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <span className="text-lg font-semibold">SubWise</span>
          <BackendIndicator />
        </div>
        <nav className="mx-auto flex max-w-6xl gap-4 px-4 pb-2 text-sm">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => (isActive ? "font-semibold text-slate-900" : "text-slate-500")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
