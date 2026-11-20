import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CSRF_HEADER } from "../src/api/client";
import { fakeApi, HEALTH, makeReport, ME, money, renderAt, unauthorized } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  url: string;
  listeners: Record<string, ((e: MessageEvent) => void)[]> = {};
  onerror: (() => void) | null = null;
  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }
  addEventListener(type: string, fn: (e: MessageEvent) => void) {
    (this.listeners[type] ??= []).push(fn);
  }
  emit(type: string, data: unknown) {
    for (const fn of this.listeners[type] ?? []) fn(new MessageEvent(type, { data: JSON.stringify(data) }));
  }
  close() {}
}

describe("auth", () => {
  it("redirects to sign-in when there is no session", async () => {
    fakeApi({ "GET /me": () => unauthorized(), "GET /health": HEALTH });
    const router = renderAt("/app");
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("signs in with the CSRF header and goes to the dashboard", async () => {
    let signedIn = false;
    const api = fakeApi({
      "GET /me": () => (signedIn ? ME : unauthorized()),
      "POST /auth/login": () => {
        signedIn = true;
        return ME.user;
      },
      "GET /health": HEALTH,
      "GET /dashboard": {
        monthly_spend: money(0), annual_spend: money(0), active_subscriptions: 0, renewals_next_30_days: [],
        spend_by_subscription: [], spend_by_category: [], latest_report: null, recent_runs: [], budget_monthly: null, over_budget: null,
      },
    });
    const router = renderAt("/login");
    fireEvent.change(await screen.findByLabelText("Email"), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-horse" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/app"));
    const login = api.calls.find((c) => c.path === "/auth/login")!;
    expect(login.body).toEqual({ email: "test@example.com", password: "correct-horse" });
    expect(login.headers[CSRF_HEADER]).toBe("1");
    expect(await screen.findByText("No subscriptions yet")).toBeInTheDocument();
  });

  it("checks that passwords match on registration", async () => {
    const api = fakeApi({ "GET /me": () => unauthorized() });
    renderAt("/register");
    fireEvent.change(await screen.findByLabelText("Name"), { target: { value: "A" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "abcdefghij" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "abcdefghik" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("Passwords do not match.")).toBeInTheDocument();
    expect(api.calls.some((c) => c.path === "/auth/register")).toBe(false);
  });
});

describe("subscriptions", () => {
  it("adds a custom subscription with the price in paise", async () => {
    const api = fakeApi({
      "GET /me": ME,
      "GET /health": HEALTH,
      "GET /subscriptions": [],
      "GET /catalog/providers": [],
      "GET /catalog/plans": [],
      "POST /subscriptions": { id: "sub_1" },
    });
    renderAt("/app/subscriptions");
    fireEvent.click(await screen.findByRole("button", { name: "Add your first subscription" }));
    fireEvent.change(screen.getByLabelText("Subscription name"), { target: { value: "Local cable" } });
    fireEvent.change(screen.getByLabelText("Price you pay (₹)"), { target: { value: "249.50" } });
    fireEvent.change(screen.getByLabelText("How often you use it"), { target: { value: "daily" } });
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Add subscription" }));
    await waitFor(() => expect(api.calls.some((c) => c.method === "POST" && c.path === "/subscriptions")).toBe(true));
    const post = api.calls.find((c) => c.method === "POST")!;
    expect(post.body).toMatchObject({ custom_name: "Local cable", price_paise: 24950, billing_cycle: 1, usage_frequency: "daily", provider_id: null, plan_id: null });
  });

  it("rejects an invalid price without calling the API", async () => {
    const api = fakeApi({ "GET /me": ME, "GET /health": HEALTH, "GET /subscriptions": [], "GET /catalog/providers": [], "GET /catalog/plans": [] });
    renderAt("/app/subscriptions");
    fireEvent.click(await screen.findByRole("button", { name: "Add your first subscription" }));
    fireEvent.change(screen.getByLabelText("Subscription name"), { target: { value: "X" } });
    fireEvent.change(screen.getByLabelText("Price you pay (₹)"), { target: { value: "abc" } });
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Add subscription" }));
    expect(await screen.findByText(/Enter the price you pay/)).toBeInTheDocument();
    expect(api.calls.some((c) => c.method === "POST")).toBe(false);
  });
});

describe("optimizer run", () => {
  it("starts a run and navigates to its page", async () => {
    const api = fakeApi({
      "GET /me": ME,
      "GET /health": HEALTH,
      "GET /subscriptions": [],
      "POST /runs": { run_id: "run_1", thread_id: "thr_1", status: "queued" },
      "GET /runs/run_1": { run_id: "run_1", thread_id: "thr_1", status: "queued", request_message: "save money", mode: "savings", revision: 0, created_at: "2026-11-01T10:00:00Z", resumable: false },
      "GET /runs/run_1/reports": [],
    });
    vi.stubGlobal("EventSource", FakeEventSource);
    const router = renderAt("/app/optimize");
    fireEvent.change(await screen.findByLabelText("What would you like?"), { target: { value: "save money" } });
    fireEvent.click(screen.getByText("Maximum savings"));
    fireEvent.click(screen.getByRole("button", { name: "Start optimization" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/app/runs/run_1"));
    expect(api.calls.find((c) => c.path === "/runs" && c.method === "POST")!.body).toEqual({ message: "save money", mode: "savings" });
  });

  it("streams events and sends the approval for the pending report", async () => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
    const report = makeReport();
    const api = fakeApi({
      "GET /me": ME,
      "GET /health": HEALTH,
      "GET /features": [{ code: "movies", label: "Movies", category: "video", description: "" }],
      "GET /runs/run_1": {
        run_id: "run_1", thread_id: "thr_1", status: "waiting_approval", request_message: "save money", mode: "savings", revision: 0,
        created_at: "2026-11-01T10:00:00Z", resumable: false, pending_interrupt: { kind: "approval", report_id: report.id },
      },
      "GET /runs/run_1/reports": [report],
      "POST /runs/run_1/approval": { status: "accepted" },
    });
    renderAt("/app/runs/run_1");
    expect(await screen.findByText("Your decision")).toBeInTheDocument();
    await waitFor(() => expect(FakeEventSource.instances.length).toBeGreaterThan(0));
    expect(FakeEventSource.instances[0]!.url).toBe("/api/v1/runs/run_1/events?after_seq=0");
    FakeEventSource.instances[0]!.emit("run_event", { seq: 1, node: "optimize", event_type: "node_start", message: "Solving", payload: {}, duration_ms: null, created_at: "2026-11-01T10:00:00Z" });
    expect(await screen.findByText("Optimizing (OAVOE)")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Movies"));
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(api.calls.some((c) => c.path === "/runs/run_1/approval")).toBe(true));
    expect(api.calls.find((c) => c.path === "/runs/run_1/approval")!.body).toEqual({ report_id: "rep_1", decision: "approved", remember: ["movies"] });
  });

  it("asks clarification questions from the interrupt and posts the answers", async () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    const api = fakeApi({
      "GET /me": ME,
      "GET /health": HEALTH,
      "GET /runs/run_2": {
        run_id: "run_2", thread_id: "thr_1", status: "waiting_clarification", request_message: "help", mode: "auto", revision: 0,
        created_at: "2026-11-01T10:00:00Z", resumable: false,
        pending_interrupt: { kind: "clarify", questions: [{ field: "budget", question: "What monthly budget (₹)?" }] },
      },
      "GET /runs/run_2/reports": [],
      "POST /runs/run_2/clarification": { status: "accepted" },
    });
    renderAt("/app/runs/run_2");
    fireEvent.change(await screen.findByLabelText("What monthly budget (₹)?"), { target: { value: "500" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(api.calls.find((c) => c.path === "/runs/run_2/clarification")?.body).toEqual({ answers: { budget: "500" } }));
  });

  it("offers resume for a run lost to a server restart", async () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    const api = fakeApi({
      "GET /me": ME,
      "GET /health": HEALTH,
      "GET /runs/run_3": {
        run_id: "run_3", thread_id: "thr_1", status: "failed", request_message: "x", mode: "auto", revision: 0,
        created_at: "2026-11-01T10:00:00Z", resumable: true, error_code: "WORKER_LOST", error_message: "The server restarted during this run.",
      },
      "GET /runs/run_3/reports": [],
      "POST /runs/run_3/resume": { status: "accepted" },
    });
    renderAt("/app/runs/run_3");
    fireEvent.click(await screen.findByRole("button", { name: "Resume from checkpoint" }));
    await waitFor(() => expect(api.calls.some((c) => c.method === "POST" && c.path === "/runs/run_3/resume")).toBe(true));
  });
});

describe("plans and comparison", () => {
  const plan = (id: string, name: string, paise: number, features: Record<string, string>) => ({
    plan_id: id, provider_id: "testprov", provider_name: "TestProv", plan_name: name, billing_cycle: 1,
    price: money(paise), monthly: money(paise), annual: money(paise * 12), status: "verified", label: "live_verified",
    observed_at: "2026-11-01T10:00:00Z", age_days: 0, source_url: "https://example.test/p", evidence: `${name} ₹${paise / 100}`, features, intro: null,
  });

  it("compares the plans named in the URL", async () => {
    fakeApi({
      "GET /me": ME,
      "GET /health": HEALTH,
      "GET /catalog/plans": [plan("t:a:1m", "Alpha", 19900, { uhd_4k: "yes" }), plan("t:b:1m", "Beta", 14900, { uhd_4k: "no" })],
      "GET /features": [{ code: "uhd_4k", label: "4K Ultra HD", category: "video", description: "" }],
    });
    renderAt("/app/compare?plans=t:a:1m,t:b:1m");
    expect(await screen.findByText("Alpha", { selector: "p" })).toBeInTheDocument();
    expect(screen.getByText("Lowest")).toBeInTheDocument();
    expect(await screen.findByText("4K Ultra HD")).toBeInTheDocument();
    expect(screen.getByText("✓ Yes")).toBeInTheDocument();
    expect(screen.getByText("✕ No")).toBeInTheDocument();
  });

  it("refreshes one provider and reports the outcome honestly", async () => {
    const api = fakeApi({
      "GET /me": ME,
      "GET /health": HEALTH,
      "GET /catalog/plans": [],
      "GET /catalog/providers": [{ id: "testprov", name: "TestProv", category: "video", pricing_url: "https://example.test/p", needs_js: false, latest_attempt: null }],
      "POST /prices/refresh": [{ provider_id: "testprov", outcome: "failed", prices_found: 0, verified: 0, error: "DNS failure", warnings: [] }],
    });
    renderAt("/app/plans");
    fireEvent.click(await screen.findByRole("button", { name: "Refresh" }));
    expect(await screen.findByText(/0 succeeded/)).toBeInTheDocument();
    expect(screen.getByText(/nothing is filled in/)).toBeInTheDocument();
    expect(api.calls.find((c) => c.path === "/prices/refresh")!.body).toEqual({ provider_ids: ["testprov"] });
  });
});

describe("preferences", () => {
  it("saves feature requirements", async () => {
    const api = fakeApi({
      "GET /me": ME,
      "GET /health": HEALTH,
      "GET /features": [{ code: "live_sports", label: "Live sports", category: "video", description: "Live matches" }],
      "GET /me/requirements": { requirements: [] },
      "GET /me/memory": [{ kind: "rejections", key: "t:a:1m", value: { plan: "Alpha", reason: "too pricey" }, created_at: "2026-11-01T10:00:00Z" }],
      "PUT /me/requirements": (init: RequestInit) => JSON.parse(String(init.body)),
      "DELETE /me/memory/rejections/t%3Aa%3A1m": undefined,
    });
    renderAt("/app/settings");
    fireEvent.click(await screen.findByRole("radio", { name: "Must have" }));
    fireEvent.click(screen.getByRole("button", { name: "Save features" }));
    await waitFor(() => expect(api.calls.find((c) => c.method === "PUT")?.body).toEqual({ requirements: [{ feature_code: "live_sports", level: "must", weight: 0.5 }] }));

    expect(await screen.findByText(/too pricey/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Forget" }));
    await waitFor(() => expect(api.calls.some((c) => c.method === "DELETE")).toBe(true));
  });
});
