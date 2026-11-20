/**
 * Test-only helpers. All data built here is synthetic test data for exercising the UI;
 * it is never shown to users and never written to any database.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { vi } from "vitest";

import type { Report } from "../src/api/types";
import { routes } from "../src/router";

export type Handler = (init: RequestInit & { url: string }) => unknown;

export interface FakeApi {
  calls: { method: string; path: string; body: unknown; headers: Record<string, string> }[];
  fetch: ReturnType<typeof vi.fn>;
}

/** Route `METHOD /path` (path without /api/v1 and without query) to a handler result. */
export function fakeApi(handlers: Record<string, unknown | Handler>): FakeApi {
  const calls: FakeApi["calls"] = [];
  const fetchFn = vi.fn(async (input: string, init: RequestInit = {}) => {
    const url = new URL(input, "http://localhost");
    const path = url.pathname.replace(/^\/api\/v1/, "");
    const method = (init.method ?? "GET").toUpperCase();
    const body = init.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path, body, headers: (init.headers ?? {}) as Record<string, string> });
    const key = `${method} ${path}`;
    if (!(key in handlers)) {
      return new Response(JSON.stringify({ error: { code: "NOT_FOUND", message: `No fake for ${key}`, retryable: false, details: {}, request_id: null } }), { status: 404 });
    }
    const h = handlers[key];
    const result = typeof h === "function" ? (h as Handler)({ ...init, url: input }) : h;
    if (result instanceof Response) return result;
    if (result === undefined) return new Response(null, { status: 204 });
    return new Response(JSON.stringify(result), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchFn);
  return { calls, fetch: fetchFn };
}

export const money = (paise: number) => ({ paise, display: `₹${(paise / 100).toFixed(2)}` });

export const ME = {
  user: { id: "usr_test", email: "test@example.com", display_name: "Test User", created_at: "2026-01-01T00:00:00Z" },
  profile: {
    user_id: "usr_test",
    country: "IN",
    currency: "INR",
    budget_paise: 50000,
    budget_period: "monthly",
    billing_preference: "any",
    ads_tolerance: "ok",
    allow_cached_prices: true,
    allow_partial_prices: false,
    allow_unverified_prices: false,
    eligibility: [],
    monthly_budget: money(50000),
  },
};

export const HEALTH = { status: "ok", version: "test", environment: "test", database: "ok", llm: { reachable: false }, search: "disabled", playwright: "disabled" };

export function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

export function unauthorized() {
  return new Response(JSON.stringify({ error: { code: "UNAUTHENTICATED", message: "Sign in.", retryable: false, details: {}, request_id: null } }), { status: 401 });
}

// Synthetic test data only.
export function makeReport(overrides: Partial<Record<string, unknown>> = {}): Report {
  const facts = {
    status: "optimal",
    budget_display: "₹500.00",
    within_budget: true,
    current_total_display: "₹800.00",
    current_items: [],
    recommended: [
      {
        plan_id: "testprov:basic:1m",
        name: "Test Basic",
        provider_name: "TestProv",
        monthly_display: "₹300.00",
        price_display: "₹300.00",
        billing_cycle_months: 1,
        label: "live_verified",
        observed_at: "2026-11-01T10:00:00Z",
        source_url: "https://example.test/pricing",
        evidence: "Basic ₹300/month",
        is_current: false,
      },
    ],
    fixed_items: [{ name: "Local cable", monthly_display: "₹100.00" }],
    recommended_total_display: "₹400.00",
    monthly_saving_paise: 40000,
    monthly_saving_display: "₹400.00",
    annual_saving_display: "₹4,800.00",
    keep: [],
    add: ["Test Basic"],
    drop: ["Old Plan"],
    features_covered: ["Movies"],
    features_lost: ["4K Ultra HD"],
    missing_must_have: [],
    missing_nice_to_have: [],
    current_overlaps: { Movies: ["Old Plan", "Other Plan"] },
    rejected: [{ name: "Pricey Plan", reason: "Costs more than the budget" }],
    alternatives: [{ plans: ["Alt Plan"], total_display: "₹450.00", missing_nice_to_have: [] }],
    data_issues: ["OtherProv: page could not be reached (DNS failure)."],
    diagnosis: null,
    diagnosis_amounts: {},
    ...overrides,
  };
  return {
    id: "rep_1",
    run_id: "run_1",
    version: 1,
    status: "pending",
    markdown: "# Report\n\n## Summary\nSwitch to Test Basic to save ₹400.00 a month.\n",
    generated_by: "template",
    current_monthly: money(80000),
    recommended_monthly: facts.status === "optimal" ? money(40000) : null,
    result: {},
    facts,
    evidence: [
      {
        plan_id: "testprov:basic:1m",
        plan_name: "Test Basic",
        price: money(30000),
        billing_cycle: 1,
        status: "verified",
        source_url: "https://example.test/pricing",
        observed_at: "2026-11-01T10:00:00Z",
        evidence_snippet: "Basic ₹300/month",
      },
    ],
    created_at: "2026-11-01T10:00:00Z",
  } as Report;
}

