import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch } from "../src/api/client";

const envelope = {
  error: { code: "NOT_IMPLEMENTED", message: "Later (M3).", retryable: false, details: { module: "M3" }, request_id: null },
};

describe("apiFetch", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns parsed JSON on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: 1 }), { status: 200 })));
    await expect(apiFetch<{ ok: number }>("/health")).resolves.toEqual({ ok: 1 });
  });

  it("turns the backend error envelope into ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(envelope), { status: 501 })));
    const err = await apiFetch("/runs").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(501);
    expect((err as ApiError).notImplemented).toBe(true);
    expect((err as ApiError).body.details).toEqual({ module: "M3" });
  });

  it("wraps non-envelope failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("oops", { status: 502 })));
    const err = (await apiFetch("/x").catch((e: unknown) => e)) as ApiError;
    expect(err.body.code).toBe("INTERNAL_ERROR");
  });
});
