# ADR-010: Decisions taken while building the full application (M0–M14)

Date: 2026-11-21 · Status: Accepted

## Context

The full-application directive changed one premise of the blueprint and the build surfaced several
implementation choices. They are recorded here; the blueprint stays the design reference and this
ADR wins where they differ.

## Decisions

1. **No seeded prices (supersedes the curated-catalog seed in blueprint §A.2, §G and roadmap M4).**
   The directive forbids fabricated or hardcoded prices. The provider registry
   (`research/registry.py`) holds only identities: official domains, the India pricing URL, tier
   names/aliases, region markers and defining features. Plans and prices come into existence only
   from live retrieval (`PriceService.refresh`) with evidence. A provider that cannot be retrieved
   has no prices; a price verified earlier is shown as *cached · verified* and is used by the
   optimizer only within 30 days and only if the user allows cached prices.
2. **Price labels.** `live_verified` requires that the latest fetch attempt for the provider
   succeeded, that the observation came from that fetch, and that it is under 24 h old. Otherwise a
   verified observation is `cached_verified`. `partial`, `unverified` and `conflict` are usable only
   via explicit profile flags. The user's own subscriptions use the price the user entered
   (`user_entered`).
3. **Tavily's role is URL recovery only.** With a key, if a provider's registered page fails, search
   restricted to the official domains may find the moved pricing page; extraction rules are
   unchanged. Search results are never used as prices.
4. **Agent nodes live in `agent/graph.py`** (one `Nodes` class) instead of one module per node;
   **database models and repositories are single modules** (`db/models.py`, `db/repositories.py`).
5. **No import-time side effects:** uvicorn runs in factory mode
   (`subwise.main:create_app --factory`); `main.py` exposes no module-level `app`.
6. **SSE without a library:** `StreamingResponse` polls the `run_events` table every 0.5 s, sends
   `run_event` (with `id:` = seq for replay) and a final `run_status` when the run pauses or ends.
   `sse-starlette` was removed from the dependencies. The browser reconnects from the last seq
   whenever the run status changes.
7. **Single background worker thread** (`ThreadPoolExecutor(max_workers=1)`) executes runs; runs
   left `running` by a crash are marked `WORKER_LOST` at start-up and can be resumed from their
   LangGraph checkpoint via `POST /runs/{id}/resume`.
8. **Subscriptions** may reference a catalog plan, a catalog provider with a free-text plan label
   (when that provider's plans have not been fetched yet), or a custom non-catalog service. A
   provider-level subscription without a plan is treated as a fixed cost the optimizer may keep or
   drop by service line; a custom subscription is a fixed cost.
9. **Frontend money rendering:** the client renders the server's `Money.display` strings and never
   does money arithmetic. Charts use `paise / 100` only for bar/line geometry; every label and
   tooltip shows the server string.
10. **Browser E2E** (`pytest -m e2e`) serves the built frontend from the real FastAPI app over HTTP
    and drives Chromium with Playwright. Provider pages are the synthetic test fixtures served via
    the test-only mock transport, so the test is deterministic and never presents fixture prices as
    real; it runs in a temporary data directory.
11. **Phase 1 stubs removed:** `NotImplementedYet` / `NOT_IMPLEMENTED` no longer exist.

## Consequences

+ The app never shows a price that was not read from an official page with evidence.
− On a fresh install, there are no plans until the first successful refresh; if a provider blocks
  automated access or changes its markup, that provider has no prices until the extractor is fixed.
