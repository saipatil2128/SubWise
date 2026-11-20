# AGENTS.md — rules for AI coding tools (Antigravity, Claude, Copilot) and humans

Read this file and `docs/blueprint.md` before changing code. If a task conflicts with these rules,
stop and write the conflict into the PR description instead of working around it.

## How work is organised

- Work happens **one roadmap module at a time** (`docs/roadmap.md`, M1–M14). A task names its module.
  Do not implement code that belongs to another module, even if it looks easy.
- Stubs raise `NotImplementedYet("<module>")`. Implementing a module means removing *its* stubs, and
  only its stubs.
- A module is done only when: its acceptance items in `docs/roadmap.md` are met, its tests exist and
  pass, `ruff check`, `ruff format --check`, `mypy`, `pytest` (backend) and `npm run typecheck`,
  `npm test`, `npm run build` (frontend) pass, and the PR description pastes the test summary.
- Never claim something works without a passing test or a pasted command output that shows it.
- Architectural changes (new dependency, new storage, new LLM call, changed identifier rules) need a
  new ADR in `docs/decisions/` **before** the code.

## Non-negotiable architecture rules

1. **Money is integer paise.** Never `float` for money; never money arithmetic in the frontend
   (render `Money.display`). Never ask the LLM to compute, convert or compare prices.
2. **The LLM never produces a number the user sees.** It may: parse intent into `RequestSpec`, pick
   a guard-allowed `NextAction`, and verbalise `ReportFacts`. `check_numbers` must pass, else the
   template report is used.
3. **Only `subwise/llm/gateway.py` imports `ollama`.** Always pass a timeout (the client default is
   none). Every LLM call has a deterministic fallback.
4. **Identity:** `user_id` (`usr_…`) = account, `thread_id` (`thr_…`) = chat conversation,
   `run_id` (`run_…`) = one optimization. LangGraph's checkpoint key is **always** the run_id and is
   built **only** by `subwise.agent.config.graph_config`. `user_id` comes from the auth token,
   never from a request body or path.
5. **`core/` and `domain/` are pure**: no FastAPI, HTTP, SQL, LangGraph, Ollama or scraping imports
   (enforced by `tests/unit/test_architecture.py`).
6. **Only `subwise/memory/backends.py` opens `SqliteSaver` / `SqliteStore`** (enforced by ruff TID251).
   Long-term store namespace: `("users", user_id, kind)`. The agent writes to the store only after an
   approval action. Form-edited data (budget, requirements, subscriptions) lives in `app.db` only.
7. **No side effects before `interrupt()` in a node.** LangGraph re-runs the node from its start on
   resume (verified; see `tests/integration/test_library_contracts.py`).
8. **Price evidence:** a price is usable only if it is bound to provider, plan, billing cycle,
   currency and region in the same block of an official page (blueprint G.3). Unknown features are
   never treated as available. Never fabricate a price, feature or source.
9. **Exclusion groups, not providers:** only plans in the same `exclusion_group` exclude each other.
   Bundles and different service lines of one provider may be combined (blueprint H.2).
10. **Web access:** respect robots.txt and terms; honest User-Agent; never bypass CAPTCHAs, logins
    or rate limits; block private-IP URLs (SSRF).
11. **Free and local only:** no paid APIs required. Tavily is optional (`.[search]` extra); with no key
    the app must still run end to end on the curated catalog.
12. **Paths come from `Settings`** (`data_dir`), never relative to the current directory. Use
    `pathlib`. Code must run on Windows.

## Errors

Raise subclasses of `subwise.errors.SubWiseError`. HTTP responses always use the `ErrorEnvelope`
shape. Do not return raw exception text to clients.

## Dependencies

Versions are pinned exactly in `backend/pyproject.toml` and `frontend/package.json`. Changing a pin
requires re-running `tests/integration/test_library_contracts.py` and updating
`docs/verified-apis.md`. Do **not** upgrade PuLP to 4.x (ADR-005) or TypeScript to 7.x (ADR-008)
without a new ADR.

## Never

- Commit `.env`, anything under `data/`, or API keys.
- Modify the old repository `Sarthak0521/SubscriptionCostOptimitzer`.
- Copy code from the old repository without the review in `docs/ta2-migration.md`.
- Disable a failing test to make CI green.
