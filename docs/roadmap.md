# Roadmap and module status

All modules are implemented. "Verified here" means covered by tests that pass in the build
environment (see [`test-report.md`](test-report.md)); items that need your machine (internet,
Ollama, Windows) are marked.

| # | Module | Status | Evidence |
| --- | --- | --- | --- |
| M0 | Scaffold, pins, CI (Windows + Ubuntu), VS Code configs, PowerShell scripts | ✅ | CI workflow; `scripts/*.ps1`; `.vscode/` |
| M1 | JSON logging with request IDs, error envelope, `/health` (DB, Ollama, search, Playwright) | ✅ | `test_health_reports_components`, `test_errors.py` |
| M2 | SQLAlchemy models, Alembic migration, user-scoped repositories | ✅ | migration runs on every test container; isolation tests |
| M3 | Auth (argon2, JWT HttpOnly cookie, CSRF header), profile, requirements, subscriptions | ✅ | `test_api_accounts.py` |
| M4 | Provider registry and feature vocabulary — **no seeded prices** (ADR-010) | ✅ | `registry.py`, `features.py` |
| M5 | Money, costing, validation (five-dimension binding, freshness, labels, conflicts) | ✅ | `test_money_costing.py`, `test_extract_validation.py` |
| M6 | OAVOE two-stage ILP, modes, exclusion groups, bundles, add-ons, eligibility, diagnosis, alternatives | ✅ | `test_optimizer.py` (incl. 200-instance brute-force property test) |
| M7 | Ollama gateway, prompts, rule fallbacks, template report, number checker | ✅ (LLM quality: run `pytest -m llm` locally) | `test_report_and_fallbacks.py`, `test_llm_path_with_number_check_guard` |
| M8 | Robots-aware fetcher with SSRF guard, extraction for 8 providers, optional Playwright and Tavily URL recovery | ✅ (real sites: run `pytest -m live` locally) | `test_price_service.py` |
| M9 | Checkpointer and long-term store, learned memory | ✅ | library contracts, rejection-memory workflow test |
| M10 | LangGraph agent: clarify, research, validate, decide, optimize, explain, check numbers, approval, learn | ✅ | `test_workflow.py` |
| M11 | Worker, runs API, SSE with replay, cancel, restart sweep + resume | ✅ | `test_paused_run_survives_restart_and_completes`, SSE test |
| M12 | Frontend: landing, auth, subscriptions, preferences, memory | ✅ | Vitest page tests |
| M13 | Frontend: optimizer with live timeline, clarification, report + evidence, approval, plans & prices, comparison, history, dashboard (Recharts) | ✅ | Vitest page tests, browser E2E |
| M14 | Browser E2E, live-source suite, LLM evaluation, test report | ✅ (live/LLM suites need your machine) | `tests/e2e`, `tests/live`, `tests/llm_eval`, `docs/test-report.md` |

## Possible next steps

- Run the live suite on Windows and tune extraction patterns for any provider that returns
  `no_prices` (see test report, "Needs attention").
- Scheduled background price refresh (e.g. daily) instead of on-demand only.
- More countries/currencies (the model already carries country and currency).
