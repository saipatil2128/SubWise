# SubWise test report

Date: 2026-11-21 · Build environment: Linux sandbox, Python 3.12.13, Node 22.23.4, Chromium (Playwright 1.65.2).
This report states only what was actually run. Re-run everything on your Windows machine with
`.\scripts\test.ps1 -E2E`, then `pytest -m live -rA` and `pytest -m llm -rA` in `backend`.

## Summary

| Suite | Command | Result |
| --- | --- | --- |
| Backend lint/format/types | `ruff check`, `ruff format --check`, `mypy src` | clean (66 source files) |
| Backend unit + integration + workflow | `pytest` | **135 passed**, 0 failed · line coverage 87 % |
| Frontend types | `npm run typecheck` | clean |
| Frontend unit/component/page | `npm test` (Vitest) | **39 passed**, 0 failed |
| Frontend production build | `npm run build` | succeeds |
| Browser end-to-end | `pytest -m e2e` | **1 passed** (full journey, see below) |
| Live provider retrieval | `pytest -m live -rA` | **8 xfailed** — no internet access from the build sandbox (DNS failure for every provider); each failure was reported honestly and produced no price |
| Local LLM (Qwen 2.5 3B) | `pytest -m llm -rA` | quality test **skipped** — no Ollama in the build sandbox; guard test passed |

## What was tested

**Unit (backend, 104 tests)** — money in integer paise and Indian formatting, monthly/annual
normalisation and the equal-cost rule; price extraction from synthetic official-page HTML (plan
blocks, tables, intro vs renewal prices, foreign currency rejected, ambiguous prices unbound);
evidence binding, freshness and label rules; OAVOE optimizer (budget, must-haves, exclusion groups,
bundles, add-on prerequisites, eligibility, modes, infeasibility diagnosis, alternatives) including
a Hypothesis property test comparing the ILP to brute force on 200 random instances; report facts,
template report and the number checker; rule-based intent parser and decision fallback; identifier
rules and graph config; config and optional search; error envelope; architecture rules (pure
`core/`/`domain/`, only the gateway imports `ollama`, no import-time side effects).

**Integration (31 tests)**
- Auth and isolation: register/login/logout, duplicate email and weak password, CSRF header
  required, profile/requirements, subscriptions CRUD, one user cannot read or change another
  user's data (404), health, JSON 404 for unknown API routes.
- Price service: retrieval stores evidence and labels it live; a failed refresh turns earlier prices
  into *cached*, never live; an unavailable provider has no prices; robots.txt disallow respected;
  JS-only page without a browser reported as `needs_js`; wrong-region page yields only unverified;
  prices API exposes labels, evidence and attempts.
- Library contracts: LangGraph interrupt/checkpoint, resume in a fresh process, node re-execution on
  resume, SqliteStore persistence and per-user isolation, Ollama client schema/timeout/errors, PuLP
  bundled CBC.
- Workflow (LangGraph through the API): full journey with overlap detection, savings, evidence and
  approval; clarification when the budget is missing; rejection remembered and triggers a revision;
  infeasible budget reported (no fake recommendation); LLM path with the number-check guard
  (LLM-invented numbers rejected → template); a paused run survives a restart and completes; one
  active run per user and the SSE stream.

**Frontend (39 tests)** — API client (cookie + CSRF header, error envelope, validation details,
query encoding), formatting helpers, price/status badges, live timeline, report view (feasible and
infeasible), and page flows with a fake API: auth redirect, sign-in, registration validation,
adding a subscription (rupees → paise), invalid price rejected, starting a run, SSE events +
approval with remembered features, clarification answers, resume after server restart, plan
comparison, price refresh with honest failure message, saving feature requirements and forgetting a
learned item.

**Browser E2E (1 journey)** — real FastAPI server over HTTP serving the built UI, real Chromium:
landing → register → refresh all prices (3 synthetic official pages succeed, 5 fail and are shown as
failed) → evidence modal → add three subscriptions → set budget → dashboard spend → run the optimizer
→ live timeline → report with data limitations and evidence → approve → completed → history →
report page → sign out → protected route redirects to login. No JavaScript errors in the page.

## Integrations not available during this build

| Integration | Status here | What to do on your machine |
| --- | --- | --- |
| Real provider websites | Unreachable (sandbox has no internet DNS) | `pytest -m live -rA` and **Plans & prices → Refresh all prices** |
| Ollama + Qwen 2.5 3B | Not installed in the sandbox; LLM paths tested with a scripted fake | `ollama pull qwen2.5:3b`, then `pytest -m llm -rA` |
| Playwright rendering of JS-only pricing pages (JioHotstar, Sony LIV, ZEE5, YouTube Premium) | Not exercised against real sites | `setup.ps1 -Browser`, `SUBWISE_PLAYWRIGHT_ENABLED=true`, refresh |
| Tavily search (optional) | Not configured | Optional; set `SUBWISE_TAVILY_API_KEY` |
| Windows + PowerShell scripts | Not run (no Windows or PowerShell in the sandbox); `setup.ps1`, `dev.ps1`, `test.ps1` and the VS Code tasks were written for Windows PowerShell 5.1+ but not executed; CI matrix includes `windows-latest` | `.\scripts\setup.ps1`, `.\scripts\test.ps1 -E2E` |

## Needs attention

1. **Extractor accuracy on today's real pages is unverified.** The extraction rules were written
   against the structure of the official pages and tested on synthetic HTML. Provider markup changes
   often; run `pytest -m live -rA` and check each provider. A provider that comes back `no_prices`
   or with warnings needs its tier aliases/patterns in `research/registry.py` / `research/extract.py`
   updated — the app will show no prices for it until then, never invented ones.
2. **JS-rendered providers** will report `needs_js` until the browser extra is installed and enabled.
3. **Robots/terms review** per provider is recorded in `docs/data-sources.md` and still needs a human
   reading of each provider's terms of use.
4. **Qwen 2.5 3B quality** on intent parsing must be measured with `pytest -m llm`; the deterministic
   fallbacks cover failures, but quality should be confirmed.
