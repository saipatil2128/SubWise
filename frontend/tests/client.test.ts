import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, apiFetch, CSRF_HEADER } from "../src/api/client";

const envelope = {
  error: { code: "CONFLICT", message: "Not waiting.", retryable: false, details: { run: "x" }, request_id: "req_1" },
};

describe("apiFetch", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns parsed JSON on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: 1 }), { status: 200 })));
    await expect(apiFetch<{ ok: number }>("/health")).resolves.toEqual({ ok: 1 });
  });

  it("sends the session cookie and the CSRF header on every request", async () => {
    const f = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", f);
    await api.deleteSubscription("sub_1");
    const [url, init] = f.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/subscriptions/sub_1");
    expect(init.method).toBe("DELETE");
    expect(init.credentials).toBe("include");
    expect((init.headers as Record<string, string>)[CSRF_HEADER]).toBe("1");
  });

  it("turns the backend error envelope into ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(envelope), { status: 409 })));
    const err = await apiFetch("/runs").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(409);
    expect((err as ApiError).message).toBe("Not waiting.");
    expect((err as ApiError).body.details).toEqual({ run: "x" });
  });

  it("wraps non-envelope failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("oops", { status: 502 })));
    const err = (await apiFetch("/x").catch((e: unknown) => e)) as ApiError;
    expect(err.body.code).toBe("INTERNAL_ERROR");
  });

  it("encodes query parameters", async () => {
    const f = vi.fn().mockResolvedValue(new Response("[]", { status: 200 }));
    vi.stubGlobal("fetch", f);
    await api.plans("sony liv");
    expect(f.mock.calls[0]![0]).toBe("/api/v1/catalog/plans?provider_id=sony%20liv");
  });
});
