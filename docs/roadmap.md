# Roadmap and module status

One module = one task (for Antigravity or a team member). Give the task: this module's row, the
matching blueprint sections, and `AGENTS.md`. Tick an item only when its test passes in CI.

## Phase 1 — scaffold (done, this commit)

- [x] Repository layout, `pyproject.toml` with verified exact pins, Vite app with pinned versions
- [x] Typed interfaces: domain models (catalog, evidence + `PriceBinding`, `RequestSpec`, optimizer I/O),
      `RunState`, `graph_config`, error hierarchy + envelope, 31 API operations as 501 stubs
- [x] Library contract tests (LangGraph checkpoint/interrupt/resume across processes, SqliteStore,
      Ollama client, PuLP/CBC); architecture-rule tests; frontend shell + tests
- [x] CI on Windows and Ubuntu (Python 3.12/3.13, Node 22); `check_env.py`; Windows PowerShell scripts
- [x] AGENTS.md, ADR-001…009, verified-APIs doc, TA2 migration notes

## Phase 2 — modules

Dependencies: M1→M2→M3; M5→M6; M4 needs M2; M7 needs M1; M8 needs M4+M5; M9 needs M2;
M10 needs M6+M7+M8+M9; M11 needs M3+M10; M12 needs M3; M13 needs M11+M12; M14 needs all.
Parallel tracks for 4 people: A: M2→M3→M12 · B: M5→M6 · C: M7→M9 · D: M4→M8.

| # | Module | Status | Acceptance (all must hold) |
| --- | --- | --- | --- |
| M1 | JSON logging (`logging_config.py`), request-ID middleware, real `/health` probes (DB, Ollama version + model, search) | ☐ | Logs carry request_id/user_id/run_id; `/health` reports Ollama down correctly; error envelope carries request_id |
| M2 | SQLAlchemy models for blueprint E (incl. v2 `service_lines`, `plan_entitlements`, `plan_prerequisites`, `plan_eligibility`, `exclusion_group`, `price_observations.binding`), first Alembic migration, user-scoped repositories, WAL + busy timeout | ☐ | `alembic upgrade head` on blank DB; cross-user repository reads return nothing |
| M3 | Auth (argon2 + JWT cookie + CSRF), profile, requirements, subscriptions API | ☐ | Register/login/logout; CRUD with monthly equivalent; cross-user access → 404 |
| M4 | Feature vocabulary + catalog seed YAML (providers, service lines, plans, entitlements, exclusion groups) + `seed_catalog.py` | ☐ | ≥ 12 plans in video + music; every price has official URL, date, `fetch_method=manual`, full `PriceBinding`; second person re-checked each against the page |
| M5 | `core/money`, `core/costing` (equal-cost rule), `core/validation` (five-dimension binding, freshness, conflicts) | ☐ | Blueprint K.2 cases 1, 2, 8, 9, 10 + the five binding-failure tests pass |
| M6 | OAVOE: two-stage ILP, modes, exclusion groups, add-ons, eligibility, retention via bundles, diagnosis, alternatives, brute-force checker | ☐ | K.2 cases 3–6; bundle + same-provider-other-line allowed; tiers exclusive; add-on needs base; ineligible excluded; ILP = brute force on 200 random instances; < 1 s for 40 plans |
| M7 | `OllamaGateway`, prompts, rule parser, template report, `check_numbers` | ☐ | With Ollama off all fallbacks valid; with Ollama on ≥ 80% of 30 eval requests parse to a valid `RequestSpec` |
| M8 | Fetcher, robots, SSRF guard, Tavily provider, ≥ 4 adapters, tier-3 extractor | ☐ | K.2 case 7; no-key run uses tiers 1–2 only; disallowed sources never fetched; live suite reports adapter status |
| M9 | `memory/backends.py`, `LearnedMemory` | ☐ | K.2 cases 11, 12 through SubWise code (contract tests already pass for the libraries) |
| M10 | Agent graph (blueprint D) | ☐ | K.2 cases 13, 14; trace records LLM vs rule per decision |
| M11 | Worker, runs API, SSE with replay, cancel, startup sweep | ☐ | Run survives page refresh; restart → `WORKER_LOST` + resume works |
| M12 | Frontend: auth, Subscriptions, Profile | ☐ | Forms validate; money only via `MoneyText` |
| M13 | Frontend: Optimizer (live timeline, evidence, approve/reject), History, Prices, Dashboard; add Recharts | ☐ | Journey steps visible in UI |
| M14 | Playwright end-to-end, LLM eval run, live-source check, demo script | ☐ | Blueprint section O |
