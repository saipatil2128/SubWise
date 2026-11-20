<!-- Exported from the living blueprint doc on 2026-11-21 (v2). The doc is the source of truth;
     re-export after changes. The two diagrams (architecture, run graph) render in the doc only. -->

# SubWise — Architecture Blueprint v2

Nov 4, 2026 · @Sai

SubWise should be built as a **deterministic research-and-optimization pipeline that a small local LLM steers and explains**, not as a free-roaming LLM agent. This blueprint was written after reading every source file in `Sarthak0521/SubscriptionCostOptimitzer` (commit `731edeb`). As of v2, only the Phase 1 scaffold is built (sections M and P); every feature module is still to be implemented.

## How to read this blueprint

Every claim carries one of four tags:

| Tag | Meaning |
| --- | --- |
| **\[CONFIRMED\]** | Verified by reading the existing repository's code |
| **\[PROPOSED\]** | New functionality this blueprint specifies for SubWise |
| **\[RECOMMENDATION\]** | An architectural choice, with reasons, that you can still overrule |
| **\[LATER\]** | Deliberately out of the MVP; planned for a later phase |

### The ten decisions that shape everything

1. **Keep the LLM off the critical path for numbers.** Qwen 2.5 3B parses the request into a typed `RequestSpec`, picks among a small fixed set of actions at two decision points, and writes the explanation. Prices, maths, validation and optimization are plain Python. \[RECOMMENDATION\]
2. **Use a curated catalog with live refresh, not open-web scraping at demo time.** Seed 12–15 real Indian OTT and music plans from official pages, each with a stored source URL and timestamp. Every run then tries a live refresh and falls back to cached data with an explicit "stale" label. \[RECOMMENDATION\]
3. **Accept no price without evidence.** An extracted price is used only if its exact text appears in the fetched page from an official domain. This one rule is the main defence against hallucinated prices. \[PROPOSED\]
4. **Solve OAVOE as a two-stage integer program with PuLP.** PuLP 3.3.2 ships the CBC solver (including Windows) and installs with pip; PuLP 4.x does not. Stage 1 maximizes weighted feature coverage; stage 2 minimizes cost while holding that coverage. \[RECOMMENDATION\]
5. **Model overlap through coverage variables.** A feature is worth its weight once, however many selected plans provide it. Redundant plans therefore add cost but no value, and the solver drops them on its own. \[PROPOSED\]
6. **Give the three identifiers separate jobs.** `user_id` is the account, `thread_id` is a chat conversation, and `run_id` (the workflow ID) is one optimization. The run ID doubles as LangGraph's checkpoint key. \[RECOMMENDATION\]
7. **Split memory by who writes it.** Anything the user edits in the UI (budget, subscriptions, required features) lives in relational tables. Anything the agent learns (rejected plans, stated priorities) lives in the LangGraph `SqliteStore`. Nothing is stored in both. \[RECOMMENDATION\]
8. **Replace `input()` approval with LangGraph `interrupt()`.** The run pauses with its state checkpointed, and the web UI resumes it with `Command(resume=...)`. \[RECOMMENDATION\]
9. **Store money as integer paise, never floats.** TA2 uses `float` throughout. \[RECOMMENDATION\]
10. **Run graphs in one in-process background worker and stream progress over SSE.** This needs no Redis, Celery or Docker, and a single worker matches what one local Ollama instance can serve. \[RECOMMENDATION\]

### Revision v2 (21 Nov 2026)

The team approved v1's architecture. v2 applies seven requested revisions, and two corrections found while verifying libraries.

| # | Revision | Where |
| --- | --- | --- |
| 1 | Name is **SubWise**; repository `github.com/saipatil2128/SubWise`; Python package stays `subwise` | Throughout, L |
| 2 | Provider-group constraint withdrawn. Replaced by declared **exclusion groups**, bundles as ordinary multi-entitlement plans, add-on prerequisites and eligibility gates | H.2, H.3, E.1 |
| 3 | Prices must be **bound** to provider, plan, billing cycle, currency and region within one page block | G.3 |
| 4 | Tavily is an optional extra; with no key or package the app runs on catalog + cache | G.4, O |
| 5 | Staged roadmap kept; only Phase 1 is built | M |
| 6 | Library versions and the LangGraph / Ollama APIs verified by installing them and running contract tests | P |
| 7 | Constraints kept: Windows, VS Code, local Ollama, Qwen 2.5 3B, free tools, no Docker | C, L, P |
| c1 | **Correction:** PuLP 4.x bundles no solver and changed its API. Pinned PuLP 3.3.2, which bundles CBC including Windows | Decision 4, C, P |
| c2 | **Correction:** Brave's search API now needs a credit card even for its free credit | G.4 |

## A. Product definition

SubWise is a web app for Indian consumers. It takes the subscriptions someone already pays for, their budget, how often they use each one and what they actually need. It then recommends the cheapest set of real plans that still covers those needs, and shows the source page and retrieval date for every price it used.

**The problem.** People drift into paying for overlapping services: three OTT apps that all stream movies, or a music app on top of a bundle that already includes music. They rarely re-check prices after a price rise. Comparison websites list plans one by one, but nobody evaluates the *whole portfolio* against what the person needs.

**Who it serves (MVP).** Individuals in India with 2–8 digital subscriptions, starting with two categories: **video OTT** and **music streaming**. \[RECOMMENDATION\] Cloud storage, productivity, gaming and learning are \[LATER\]. Each new category needs its own feature vocabulary and source adapters.

**What it is not.** It does not buy, cancel or change subscriptions. It does not know how much someone really watches unless they say so. It does not compare *catalogue content* (which films a service has); it compares coarse feature tags such as "live cricket", "ad-free" or "4K". A jury will ask about this, so the limitation should be stated up front.

**Why this is an agent and not a chatbot.** For each request the system decides what it needs to know, fetches it with tools, inspects whether the results are trustworthy enough, loops back for more research when they are not, and pauses for human approval before anything is saved. That is goal-directed, multi-step tool use with observation-driven branching, persistent memory and human-in-the-loop control. A chatbot only produces text.

**What makes it different from a comparison site.**

1. It optimizes a *combination* of plans under a budget, rather than ranking single plans.
2. Overlap is part of the maths, not just a label.
3. Every number carries a source URL, a retrieval time and a verification status.
4. It remembers what the user rejected and why.

## B. Audit of the existing repository

The existing code is a sound academic demo of *safety concepts*: input validation, a deterministic fallback, an approval gate and an audit log. Little of it carries over as working code, though. The biggest issues: the "Supervisor" is a fixed if/else chain rather than an LLM, the two memory modules disagree with each other, the thread ID is used as the user ID, and the tests exercise copies of functions instead of the real ones. Everything below is \[CONFIRMED\] from commit `731edeb`.

### B.1 What TA1 does

`ta1/subscription_optimizer.py` defines `calculate_annual_cost` and `compare_plans` as `@tool` functions and registers them with `create_agent()` on `ChatOllama(qwen2.5:3b, temperature=0)`. It then runs two prompts at import time: ₹899,999 vs ₹799,999, and the equal-cost case ₹500 vs ₹500. The equal-cost rule lives in two places: the tool itself returns "There is no difference between the plans.", and the system prompt repeats it.

- The root `subscription_optimizer.py` is described as the "original TA1 entry point (unchanged)", but it **differs** from the `ta1/` snapshot. It has no `@tool` decorators, and its equal-cost message is "No difference. Both plans cost the same." The CSV in `traces/` records that second string, which suggests the measurements came from the root file and not from the frozen snapshot.
- There is no input validation: a negative price returns a negative annual cost, and the CSV shows exactly that.

### B.2 What TA2 does

`ta2/main.py` asks for two prices, a priority and a "user/thread ID" on the command line, then calls `optimize_subscription()` in `ta2/agents/supervisor.py`. That builds a LangGraph `StateGraph` with five nodes:

| Node | What the code actually does | LLM? |
| --- | --- | --- |
| `supervisor` | A fixed if/else ladder: no cost analysis → Cost Analyst; no evaluation → Plan Evaluator; negotiation not done → Negotiator; otherwise Finalizer | No |
| `cost_analyst` | Calls a `create_agent` LLM agent twice, once per plan, to multiply by 12 | Yes, for arithmetic |
| `plan_evaluator` | Works out annual costs and the cheaper plan in Python, then asks the LLM to explain those facts | Yes, explanation only |
| `negotiator` | Recomputes annual costs and writes a consistency note; no actual negotiation | No |
| `finalizer` | Joins the three text blocks into one string | No |

Other parts of TA2:

- `safety.py` provides validated `@tool` versions of both calculations, `deterministic_recommendation()`, `safe_execute()`, an approval gate built on `input()`, a SQLite audit table `recommendation_decisions`, and per-thread JSONL traces.
- `rag_store.py` (Member 2) is a Chroma + `nomic-embed-text` RAG over a **fictional** 10-section catalogue (StreamNova, CloudVault, FitPulse). The LLM must answer only from retrieved chunks, otherwise it refuses. It is **not wired into the supervisor**.
- `ta2/memory/memory_manager.py` (Member 1) opens both `SqliteSaver` and `SqliteStore` correctly with context managers. It is **not wired into the supervisor either**.

### B.3 Findings that matter for the redesign

1. **Identity confusion is real.** `optimize_subscription` calls `get_preference(thread_id)`, so the conversation ID is passed where the user ID belongs. `main.py` even prompts for a "user/thread ID". It also only loads the saved preference when the priority equals the literal string `"Save money"`.
2. **There are two incompatible long-term memory modules.** `memory_store.py` uses namespace `("subscription_optimizer", user_id)` with key `preferences`, in a file located relative to the working directory. `memory/memory_manager.py` uses namespace `(user_id, "profile")` with key `subscription_preferences`, in a different file. **Nothing in the app ever calls a save function**, so long-term memory is read-only in practice.
3. **Short-term memory only stores the last run.** Every call passes a complete `initial_state` on the same `thread_id`, and the state has no reducers, so each run overwrites the previous one. `get_previous_comparison()` therefore returns only the last result. There is no conversation history to resume, because the state has no messages.
4. **The "review complete" branch can never run.** `MAX_HOPS = 3` equals the number of specialists. After the Negotiator (hop 3), the supervisor always takes the `MAX_HOPS` branch, so every successful run's trace says "MAX\_HOPS reached". This is visible in `AGENT_ARCHITECHTURE.md` step 8.
5. **The LLM does arithmetic.** The Cost Analyst sends "multiply by 12" to Qwen and stores its free text. Its local `calculate_annual_cost` also lacks the NaN/inf checks in `safety.py`. That makes three different implementations of the same calculation.
6. **Approval blocks on `input()`.** It runs *after* the graph, outside LangGraph, so it cannot work in a web app and cannot survive a restart.
7. **The tests do not test the real code.** `tests/main_safety.py` defines its own `extension_annual_cost` and `extension_compare_plans`, plus a local `decide()` and `safe_execute()`, and asserts against those. Nothing from `ta2/` is imported. The file name lacks the `test_` prefix, so a bare `pytest` run will not collect it. The README refers to `tests/test_member4_safety.py`, `ta1/SHA256SUMS.txt` and `reports/member4_report.*`, and none of these exist.
8. **A dependency is missing.** `requirements.txt` pins `langchain==1.4.6`, `langgraph==1.2.16`, `langchain-ollama` and `langchain-chroma`, but omits `langgraph-checkpoint-sqlite`, which provides both `SqliteSaver` and `SqliteStore`. It also omits `pytest`.
9. **Importing modules has side effects.** `supervisor.py` opens a SQLite connection when imported. `safety.py` creates `data/` and `traces/` when imported. `cost_analyst.py` and `plan_evaluator.py` create Ollama clients when imported.
10. **Money is stored as `float`.** Equality checks on floats (`a == b`) happen to work for whole-rupee inputs but are fragile once prices are derived, for example ₹1,499 per year divided by 12.

### B.4 Reuse classification

| Component | Verdict | What to carry over |
| --- | --- | --- |
| Equal-cost rule (TA1 `compare_plans`) | **Reuse after refactoring** | Keep the exact sentence "There is no difference between the plans." in `core/costing.py`, computed with `Decimal`/paise. Port TA1's two prompts as an LLM-integration test. Keep the `ta1/` file untouched in the old repo. |
| `safety.py` validators (finite, non-negative) | **Reuse after refactoring** | Becomes Pydantic field validators on `Money` and `PlanPrice` |
| `deterministic_recommendation()` | **Reuse after refactoring** | Generalized: when the LLM is down, the report is built from a template using optimizer output only |
| `safe_execute()` | **Reuse after refactoring** | Becomes the `@guarded_tool` wrapper (timeout, bounded retry, typed error, trace event) |
| Audit table `recommendation_decisions` | **Redesign** | Becomes `approval_decisions`, keyed by `run_id` and `user_id` and linked to a report version |
| `append_trace()` JSONL | **Redesign** | Becomes the `run_events` table: one source for both the live progress stream and the stored trace |
| `human_approval()` with `input()` | **Redesign** | LangGraph `interrupt()` + `Command(resume=…)` |
| Supervisor if/else routing + hop limit | **Redesign** | Keep the *idea* of a hop budget and a routing trace. Replace the routing with the graph in section D. |
| `cost_analyst.py` (LLM arithmetic) | **Discard** | Replaced by pure-Python costing |
| `plan_evaluator.py` ("facts in Python, LLM explains") | **Reuse after refactoring** | The pattern becomes the Explainer node; the two-plan code is discarded |
| `negotiator` node | **Discard** | Its cross-check becomes the deterministic `verify_report` step |
| `memory_store.py` | **Discard** | Superseded by Member 1's version |
| `memory/memory_manager.py` (`SqliteSaver` + `SqliteStore` context managers) | **Reuse after refactoring** | Becomes `memory/backends.py`, with namespace `("users", user_id, kind)` |
| `memory/test_memory.py` | **Reuse after refactoring** | Its two checks become pytest tests: preference survives a new process; workflow resumes |
| `rag_store.py` + fictional catalogue | **Reuse after refactoring — \[LATER\]** | Re-pointed at fetched *official* terms pages (refund and cancellation rules) with source URLs. The "answer only from chunks, otherwise refuse" contract is worth keeping. Not on the MVP critical path. |
| `subscription_catalogue.md` | **Discard** | Fictional; must never mix with real data |
| `demo_failure.py`, `traces/*.csv` | **Discard** | Historical evidence; stays in the old repo |
| Documentation: approval policy and "evidence limitation" wording | **Reuse as-is** | The README's honest-limitation tone should become a project rule |

Nothing is reused fully as-is apart from wording and concepts. That is expected: TA2 compares two numbers a user typed in, while SubWise works with researched plans, portfolios and a web front end.

## C. Final system architecture

SubWise is a single-machine, three-tier app: a React single-page app talks to one FastAPI process, and that process runs the LangGraph graph in a background worker. All maths and data handling live in a pure-Python core that the graph calls as tools. \[RECOMMENDATION\]

&#91;diagram (see the doc): SubWise components · 3 tiers, 9 parts\]

The graph orchestrates; the core computes; the LLM gateway is the only code that talks to Ollama. Read top to bottom, it shows how one optimization request travels.

| Layer | Technology | Responsibility | Status |
| --- | --- | --- | --- |
| Frontend | React 18 + Vite + TypeScript, Tailwind, Recharts, TanStack Query | Pages, forms, live run timeline (SSE), approval UI | \[PROPOSED\] — stack as you chose |
| API | FastAPI + Pydantic v2 | Typed request/response models, auth, error envelope | \[PROPOSED\] |
| Run worker | `concurrent.futures.ThreadPoolExecutor(max_workers=1)` + DB-backed event log | Runs and resumes graphs off the request thread; one at a time because one local Ollama is the bottleneck | \[RECOMMENDATION\] instead of Celery/Redis |
| Agent orchestration | LangGraph 1.x `StateGraph` + `SqliteSaver` + `SqliteStore` | Workflow, pause/resume, memory | \[PROPOSED\] |
| LLM | Ollama, `qwen2.5:3b` by default via the official ollama Python client (ADR-006), model name in config | Intent parsing, bounded decisions, explanations | \[RECOMMENDATION\]: keep the professor's model as default; let `qwen3:4b` be swapped in through config only if your evaluation set shows better JSON adherence |
| Search | `SearchProvider` interface; Tavily first, then a `NullSearchProvider` | Find candidate official URLs | \[RECOMMENDATION\] (see G) |
| Fetching | `httpx` (async, timeouts), BeautifulSoup + `lxml`; Playwright opt-in per source | Get page HTML/text | \[PROPOSED\] — `httpx` instead of `requests` for timeouts and async |
| Optimization | PuLP 3.3.2 + bundled CBC (4.x has no bundled solver) | Two-stage integer program | \[RECOMMENDATION\] |
| Persistence | SQLite via SQLAlchemy 2.0 + Alembic; WAL mode | Domain data and migrations | \[RECOMMENDATION\] |
| Testing | pytest, `respx` (HTTP mocking), Vitest + React Testing Library, Playwright for end-to-end | Test pyramid | \[PROPOSED\] |

**Why not a separate LLM agent per role?** A 3B model is unreliable at long multi-tool ReAct loops. Every extra LLM hop adds 5–30 s on a laptop CPU and another place to hallucinate. Your nine responsibilities in brief §6 map to **one LLM-backed supervisor node, one LLM-backed explainer node and seven deterministic modules**, which matches your own instinct in §6.

## D. Agent execution workflow

One optimization request is one LangGraph run. The supervisor role is split across two places: an LLM node that turns language into a typed plan, and a guarded decision node that chooses among *allowed* next actions. Neither can produce a number that reaches the user. \[RECOMMENDATION\]

&#91;diagram (see the doc): optimization run graph · 13 steps, 2 pauses, 3 bounded loops\]

Every loop has a counter in state: clarification ≤ 2, research rounds ≤ 2, revisions after rejection ≤ 2. The graph also has a hard `recursion_limit` of 40 as a backstop.

### D.1 Node contracts

| Node | Input (from state) | Output (to state) | Fallback if it fails |
| --- | --- | --- | --- |
| `load_context` | `user_id` | `profile`, `subscriptions[]`, `learned_prefs[]` (top 10 from the store) | Fail the run with `DB_UNAVAILABLE` |
| `parse_intent` | user message, profile | `RequestSpec` (Pydantic): categories, budget\_paise, must\_have\_features, nice\_to\_have with weights, keep\_providers, drop\_providers, billing\_preference, missing\_fields | Rule-based parser (keywords + regex for ₹ amounts) and any profile fields; failure is logged |
| `clarify` | `missing_fields` | `interrupt({"questions": [...]})` → merges answers into the spec | Run stays paused until the user answers or cancels |
| `plan_research` | spec, subscriptions, catalog registry | `ResearchPlan`: list of (provider, source adapter, reason) | None needed; pure function |
| `research` | plan | `PlanObservation[]` with evidence (URL, fetched\_at, snippet, status) | Per provider: cached catalog row, labelled `STALE` or `CACHED` |
| `validate` | observations | `ValidatedPlan[]` + a `DataQualityReport` (verified / partial / unverified / conflict / stale counts per required feature) | None needed; pure function |
| `decide` | quality report, round counter | `next_action` ∈ {`research_more`, `proceed`, `proceed_with_gaps`, `ask_user`} + a one-line rationale | Rule table: if verified coverage of every must-have feature exists → `proceed`; else if round < 2 → `research_more`; else `proceed_with_gaps` |
| `optimize` | validated plans, spec, usage | `OptimizationResult`: chosen set, alternatives, slack, infeasibility diagnosis | No fallback needed; failures raise `OPTIMIZER_ERROR` and the run ends |
| `explain` | `OptimizationResult`, evidence | report text in markdown + structured sections | Jinja2 template with the same sections |
| `check_numbers` | report text, result | pass/fail; every ₹ amount and plan name in the text must exist in `OptimizationResult` | On fail, replace with the template version and log `LLM_NUMBER_MISMATCH` |
| `approval` | report | `interrupt({"report_id": …})` → `approved` / `rejected` + reason | Stays paused until the user acts |
| `save_and_learn` | decision | `approval_decisions` row; on approval, writes chosen learned preferences to the store | Retried once, then `PERSISTENCE_ERROR` |

**Why the `decide` node still counts as an agent decision.** The LLM sees the data-quality report and *chooses* the next step, which shows the jury real autonomy. But it can only choose from actions the guard allows: `research_more` disappears after 2 rounds, and `proceed` is impossible while a must-have feature has zero verified coverage. If its JSON is invalid, the rule table decides. The trace records whether the LLM or the rule made each choice, which is honest and easy to demo.

### D.2 Worked example

The user (already set up with Netflix, Amazon Prime and Spotify, usage Daily / Weekly / Daily) types: *"My budget is ₹1,000 a month. I mainly watch movies and listen to music. Cut costs without losing what I use. Find better alternatives."*

1. **`POST /api/runs`** creates `run_id = r_7f…` under `thread_id = t_2a…` for `user_id = u_19…`. The worker starts the graph with LangGraph `thread_id = r_7f…`. The UI subscribes to `GET /api/runs/r_7f…/events`.
2. **load\_context** loads 3 subscriptions, budget ₹1,000 (profile) and one learned preference: "rejected JioHotstar Mobile on 2026-10-30: wants a TV screen".
3. **parse\_intent** → `RequestSpec{categories: [video, music], budget: 100000 paise, must_have: [movies, music_streaming], nice_to_have: {ad_free: 0.6, tv_screen: 0.8}, keep: [], missing: []}`. `tv_screen` comes from the learned preference, and the trace says so.
4. **plan\_research** → video: Netflix, Prime Video, JioHotstar, Sony LIV, ZEE5; music: Spotify, YouTube Music/Premium, JioSaavn, plus the Amazon Prime bundle (which includes Prime Music).
5. **research**, round 1: 9 providers. Netflix and Spotify pages refresh live (VERIFIED). JioHotstar's page needs JavaScript and Playwright is off, so the cached row is used (STALE, fetched 41 days ago). ZEE5 returns a timeout, so the cached row is used (CACHED).
6. **validate** → `movies` is covered by 3 verified plans and `music_streaming` by 2, so every must-have has verified coverage.
7. **decide** → LLM chooses `proceed_with_gaps` ("ZEE5 unverified, not needed for must-haves"). The guard accepts it.
8. **optimize**, stage 1: the best weighted coverage reachable within ₹1,000. Stage 2: the cheapest set achieving it. Result: keep Prime (bundle covers movies and music), drop the separate Spotify plan, keep Netflix at a lower tier, along with 2 alternative portfolios and the trade-offs of each. *(Plan names and prices here are illustrative only; real numbers come from the verified catalog.)*
9. **explain** writes the report. **check\_numbers** finds every ₹ figure in the result: pass.
10. **approval** pauses. The user rejects with the reason "I need Spotify playlists". The rejection is stored as learned preference `must_keep: Spotify`. The run goes back to `parse_intent` with that feedback (revision 1 of 2), and the new portfolio keeps Spotify.
11. The user approves. **save\_and\_learn** writes the decision, marks the report `approved`, and the run ends `completed`.

The UI timeline shows each of these as an event with its duration, so the jury watches the agent work in real time.

## E. Database architecture

All domain data lives in one SQLite file, `app.db`, behind SQLAlchemy 2.0 models and Alembic migrations. LangGraph keeps its own two files, which no app code queries directly. Every money column is an `INTEGER` in **paise**. Every timestamp is UTC ISO-8601. Every user-owned table carries `user_id` and is only ever queried through a repository that filters by it. \[RECOMMENDATION\]

### E.1 Entities

| Table | Key columns | Notes |
| --- | --- | --- |
| `users` | `id` (ULID), `email` UNIQUE, `password_hash` (argon2), `display_name`, `created_at` | Account identity = `user_id` |
| `user_profiles` | `user_id` PK/FK, `monthly_budget_paise`, `country` (default `IN`), `billing_preference` (`monthly`/`annual`/`any`), `ads_tolerance` (`ok`/`avoid`/`never`), `allow_unverified_prices` BOOL | Edited on the Profile page; the source of truth for hard constraints |
| `feature_definitions` | `code` PK (for example `movies`, `live_cricket`, `music_streaming`, `ad_free`, `uhd_4k`, `tv_screen`, `offline_download`), `category`, `label`, `description` | The fixed vocabulary that OAVOE optimizes over; seeded, versioned in code |
| `user_feature_requirements` | `user_id`, `feature_code`, `level` (`must`/`nice`/`none`), `weight` (0–1) | Feeds the optimizer's weights |
| `providers` | `id`, `name`, `category`, `official_domains` JSON, `country`, `adapter_key`, `robots_allowed` BOOL, `robots_checked_at` | `adapter_key` selects the extractor |
| `plans` | `id`, `provider_id`, `name`, `billing_cycle_months` (1/3/6/12), `is_bundle`, `active` BOOL | Catalog identity, independent of price |
| `plan_features` | `plan_id`, `feature_code`, `value` (`yes`/`no`/`unknown` + optional detail such as `screens=2`), `observation_id` | `unknown` is never treated as `yes` |
| `source_documents` | `id`, `url`, `domain`, `fetched_at`, `http_status`, `content_sha256`, `fetch_method` (`httpx`/`playwright`/`manual`), `text_excerpt_path` | One row per fetch; raw text stored on disk under `data/sources/{sha}.txt` |
| `price_observations` | `id`, `plan_id`, `source_document_id`, `price_paise`, `currency`, `billing_cycle_months`, `price_kind` (`standard`/`intro`/`renewal`), `intro_months`, `tax_included` (`yes`/`no`/`unknown`), `evidence_snippet`, `extracted_by` (`adapter`/`llm`/`manual`), `status` (`verified`/`partial`/`unverified`/`conflict`), `observed_at` | Append-only, so it **is** the price history |
| `plan_current_price` (view) | latest non-conflict observation per (plan, price\_kind) + `age_days` + derived `freshness` (`fresh`/`stale`/`expired`) | What the optimizer reads |
| `user_subscriptions` | `id`, `user_id`, `plan_id` NULL, `custom_name` NULL, `price_paise`, `billing_cycle_months`, `renewal_date`, `usage_frequency` (`daily`/`weekly`/`occasionally`/`never`/`unknown`), `is_mandatory` BOOL, `notes`, `active` | `plan_id` may be NULL for services outside the catalog: the user's own number is respected but not optimized |
| `conversations` | `id` = **thread\_id**, `user_id`, `title`, `created_at` | One chat thread on the AI Optimizer page |
| `messages` | `id`, `thread_id`, `role`, `content`, `run_id` NULL, `created_at` | Readable chat history; independent of checkpoints |
| `optimization_runs` | `id` = **run\_id** (workflow\_id), `user_id`, `thread_id`, `status` (`queued`/`running`/`waiting_clarification`/`waiting_approval`/`completed`/`failed`/`cancelled`), `request_spec` JSON, `revision` INT, `parent_run_id` NULL, `error_code`, `started_at`, `ended_at`, `llm_model` | One optimization; also LangGraph's checkpoint key |
| `run_events` | `id` autoinc, `run_id`, `seq`, `node`, `event_type` (`node_start`/`node_end`/`tool_call`/`tool_error`/`decision`/`fallback`/`interrupt`), `payload` JSON, `duration_ms`, `created_at` | Feeds SSE and the stored trace (replaces JSONL) |
| `reports` | `id`, `run_id`, `version` INT, `result` JSON (`OptimizationResult`), `markdown`, `generated_by` (`llm`/`template`), `current_monthly_paise`, `recommended_monthly_paise`, `created_at` | Immutable; a revision creates a new version |
| `report_evidence` | `report_id`, `price_observation_id` | Which exact observations backed the report |
| `approval_decisions` | `id`, `run_id`, `report_id`, `user_id`, `decision` (`approved`/`rejected`), `reason`, `decided_at` | Successor to TA2's `recommendation_decisions` |
| `price_alerts` \[LATER\] | `id`, `user_id`, `plan_id`, `old_paise`, `new_paise`, `detected_at`, `seen` | Output of future monitoring |

**v2 catalog tables (for H.2).** `service_lines` (`id`, `provider_id`, `name`, `category`); `plans` gains `service_line_id` and `exclusion_group` (NULL = the service line); `plan_entitlements` (`plan_id`, `service_line_id`, `tier`); `plan_prerequisites` (`plan_id`, `requires_any_of` JSON of plan or line IDs); `plan_eligibility` (`plan_id`, `condition`: student / new\_customer / telecom\_customer); `user_profiles.eligibility` JSON; `price_observations` gains `region` and `binding` JSON (`PriceBinding`, G.3).

### E.2 Relationships

- A user has one profile, many subscriptions, many feature requirements, many conversations and many runs.
- A conversation (`thread_id`) has many messages and many runs. A run has many events, one or more report versions and at most one decision per report version.
- A provider has many plans. A plan has many features and many price observations. Each observation points to exactly one source document.
- Reports reference observations through `report_evidence`, so a report keeps showing the price it used even after the catalog price changes.

### E.3 What lives outside app.db

| File | Owner | Contents | Key |
| --- | --- | --- | --- |
| `data/checkpoints.db` | LangGraph `SqliteSaver` | Serialized graph state per step, pending interrupts | `thread_id` config = **run\_id** |
| `data/memory.db` | LangGraph `SqliteStore` | Learned preferences as JSON items | namespace `("users", user_id, kind)` |
| `data/sources/*.txt` | Fetcher | Plain text of fetched pages, named by content hash | `content_sha256` |

**Rule:** no table copies checkpoint data. The run's *status* lives in `optimization_runs`; its *execution state* lives only in checkpoints. When they disagree after a crash, the startup sweep marks `running` runs with no live worker as `failed` with `WORKER_LOST`, and offers "Resume" if a checkpoint exists.

## F. Memory architecture

Short-term memory is the LangGraph checkpoint of **one run**. Long-term memory is the `SqliteStore` of **one user**. Neither duplicates the relational profile. Each identifier has exactly one job. \[RECOMMENDATION\]

### F.1 The three identifiers

| ID | Means | Created when | Used as | Never used as |
| --- | --- | --- | --- | --- |
| `user_id` | An account | Sign-up | Owner on every row; namespace of the long-term store | A LangGraph `thread_id` |
| `thread_id` | A chat conversation on the AI Optimizer page | User clicks "New conversation" | Groups `messages` and runs for display and follow-ups | A checkpoint key, a memory key |
| `run_id` (= workflow\_id) | One optimization execution, including its pauses and revisions | `POST /api/runs` | LangGraph `configurable.thread_id`; owner of events, reports, decisions | A user identity |

**Naming trap to document in code.** LangGraph calls its checkpoint key `thread_id`. In SubWise that value is always a `run_id`. Wrap it in one helper, `graph_config(run_id) -> {"configurable": {"thread_id": run_id, "user_id": user_id}}`, and forbid building that config anywhere else. This one helper prevents the TA2 bug from coming back.

**Why one checkpoint thread per run and not per conversation.** TA2 reused one checkpoint thread across runs, and each new run overwrote the last (finding B.3-3). With one thread per run, every run's state is isolated, can be resumed by its own ID, and can be replayed for the jury. Conversation continuity ("now also add cloud storage") is handled by `parse_intent` reading the thread's last 6 `messages` plus the previous run's `request_spec`, which is explicit, small and testable.

### F.2 Short-term memory (checkpoints)

- **What it holds:** the `RunState` TypedDict: spec, observations, quality report, optimizer result, report draft, counters, pending interrupt.
- **What it is for:** surviving the two human pauses (clarify, approval), surviving a backend restart, and showing intermediate results in the UI.
- **How resume works:** `POST /api/runs/{id}/approval` → the worker calls `graph.invoke(Command(resume={"decision": "approved"}), graph_config(run_id))`.
- **Caveat for implementers:** on resume, LangGraph re-runs the interrupted node from its start. Any side effect *before* `interrupt()` in that node (like writing an event row) must be idempotent, or must move into the previous node.
- **Retention:** checkpoints of runs finished more than 30 days ago can be pruned by a maintenance command; reports and events remain in `app.db`. \[LATER\]

### F.3 Long-term memory (store)

The test for where a fact lives: **if the user edits it in a form, it is relational; if the agent learned it from conversation or decisions, it goes in the store.**

| Kind (namespace `("users", user_id, kind)`) | Example value | Written by | Read by |
| --- | --- | --- | --- |
| `rejections` | `{plan_id, reason, run_id, at}` | `save_and_learn` after a rejection | `plan_research` (deprioritize), `explain` ("you rejected X because…") |
| `stated_priorities` | `{text: "don't care about 4K", feature: "uhd_4k", weight: 0, run_id}` | `save_and_learn` after **approval**, only for priorities the user confirmed in the report's "Remember these?" checklist | `parse_intent` |
| `provider_attitudes` | `{provider_id, stance: "avoid" or "keep", reason}` | Same as above | `plan_research`, optimizer constraints |

Rules:

- The agent **never writes** to the store without an approval action, which matches brief §9.8.
- The Profile page lists every store item with a delete button. `DELETE /api/me/memory/{namespace}/{key}` removes it.
- Budget, required features and subscriptions are **never** copied into the store. `load_context` reads them fresh from `app.db` on every run.
- Store items are injected into prompts as at most 10 short lines. The 3B model's context is small, and long memory makes it worse.

### F.4 Migration from TA2

| TA2 artifact | SubWise destination |
| --- | --- |
| `ta2_short_term_memory.sqlite` keyed by user-typed ID | `data/checkpoints.db` keyed by `run_id`; old data not migrated |
| `memory_store.py` namespace `("subscription_optimizer", uid)` | Dropped |
| `memory_manager.py` namespace `(uid, "profile")` with budget/billing JSON | Profile fields go to `user_profiles`; the namespace pattern becomes `("users", uid, kind)` |
| `data/safety_audit.sqlite3` | `approval_decisions` |

## G. Research architecture

Research runs on a **curated provider registry with per-provider adapters**, uses search only to discover *new* candidate URLs, and accepts no price unless its exact text appears in a page fetched from an official domain. Open-web "agent browses anything" research is the wrong design for a 3B model and a live jury demo. \[RECOMMENDATION\]

### G.1 Challenging the brief's research assumption

The brief wants the agent to discover providers and prices live. Three facts work against doing that naively:

1. **Pricing pages are hostile to scraping.** Big OTT sites render prices with JavaScript, vary by region (detected from IP), A/B-test layouts and often prohibit automated access in their terms. Your own rule "respect website terms" means some sources will simply be off-limits for automation.
2. **A 3B model extracting prices from raw HTML will invent numbers.** It needs either a deterministic extractor or a check that the number exists verbatim in the page.
3. **The demo must work offline-ish.** A conference-room Wi-Fi failure should degrade the demo, not kill it.

So the design has **three tiers**, and the UI always says which tier each number came from:

| Tier | How the data is obtained | Status it can reach | When used |
| --- | --- | --- | --- |
| 1. Adapter refresh | Provider-specific extractor (CSS selectors/regex) on the official pricing URL stored in `providers` | `verified` | Every run, for registry providers whose robots/terms allow it |
| 2. Cached catalog | Last good observation (originally collected by tier 1, or entered manually by the team from the official page, with URL and date) | Keeps its original status but gets `stale` after 30 days and `expired` after 90 | When tier 1 fails or is not allowed |
| 3. Discovery | Search API → candidate URLs → fetch → LLM-assisted extraction → evidence check | `partial` at best, or `unverified` | Only when the user names a provider not in the registry, or `decide` chooses `research_more` |

Manual seeding is **not cheating** if it is labelled. Each row records `fetch_method = manual`, the URL and the date it was copied. That is how real price-comparison sites bootstrap.

### G.2 Pipeline

1. **Plan** (`plan_research`): for each category in the spec, take registry providers in that category + providers of the user's current subscriptions + any named in the request.
2. **Policy check:** read the provider's `robots_allowed` (refreshed weekly with `urllib.robotparser`). If disallowed, skip straight to tier 2 and record `SOURCE_DISALLOWED`. Never solve CAPTCHAs, rotate user agents or use proxies.
3. **Fetch:** `httpx` with a 10 s connect / 20 s total timeout, one retry with backoff, an honest `User-Agent: SubWise/0.1 (academic project; contact: <team email>)`, at most 4 concurrent requests and 1 per domain. Playwright is used only if the provider row says `needs_js = true` and the feature flag is on.
4. **Store** the plain text (BeautifulSoup `get_text`, whitespace-collapsed) as a `source_documents` row + a file named by its SHA-256. If the hash equals the previous fetch, mark it "unchanged" and reuse the earlier observations, which is cheap and fast.
5. **Extract:** tier 1 adapters return `PlanObservation` objects. Tier 3 asks the LLM for a JSON array with Ollama's `format` set to the `PlanObservation` schema, given only text windows of about 400 characters around each ₹ match. That keeps the prompt small for a 3B model.
6. **Validate** (pure Python, section G.3).
7. **Persist** the observations. They are append-only, so this *is* the price history.

### G.3 Validation rules → status

A price counts only when it is **bound** to all five of provider, plan, billing cycle, currency and region, within one region of the page. Finding the number somewhere on an official page is not enough (v2). \[PROPOSED\]

**Binding rules.** Each extracted price carries a `PriceBinding` record, stored as JSON on `price_observations.binding`. Each dimension records *how* it was bound and the exact text that bound it.

| Dimension | Bound when | Not bound when (examples) |
| --- | --- | --- |
| **Provider** | The final URL after redirects is on a domain in that provider's `official_domains`, and the domain maps to exactly one provider | Redirect to a reseller, an aggregator or another provider's domain |
| **Plan** | The plan's name or a registered alias is in the **same block** as the price: the same DOM container for adapters; for tier-3, the same text window with **no other plan name** between them | Price sits in a comparison row nearer another plan's name; two plan names are equally near |
| **Billing cycle** | A cycle phrase (`/month`, `per month`, `monthly`, `3 months`, `/year`, `annually`) is in the same block and attached to this amount, and matches the plan's `billing_cycle_months` | No cycle phrase; the phrase belongs to a neighbouring amount; a yearly amount labelled as monthly |
| **Currency** | `₹`, `Rs` or `INR` immediately adjacent to the amount, and no other currency appears on the page | `$`, `USD` or several currencies on the page |
| **Region** | The adapter's declared India URL (for example a `/in/` path), **and** INR currency is bound; the fetch ran from India (`country = IN` in settings) | A `/us/` path, a region selector left unresolved, or a geo-redirect to another country |

Evidence text must also occur verbatim (after whitespace normalization) in the stored page text, and the ₹ amount inside it must parse to `price_paise`. One extra rule handles intro offers: a price whose block mentions "first N months", "introductory" or "then ₹X" becomes `price_kind = intro`, and a full verification also requires a bound renewal price.

**Other checks**

| Check | Rule | Failure effect |
| --- | --- | --- |
| Format | Currency INR; 0 < price ≤ ₹50,000; cycle ∈ {1, 3, 6, 12} months | Rejected, `INVALID_PRICE` |
| Plausibility | Within 0.33×–3× of that plan's previous verified price | `conflict` + both values shown |
| Cross-source conflict | Two observations for the same plan/kind within 7 days differ by more than ₹1 | Both marked `conflict`; optimizer uses neither unless the user picks one |
| Completeness | Feature tags present or explicitly `unknown`; `tax_included` known or `unknown` | Missing feature tags → `partial` |
| Freshness | Age ≤ 30 days `fresh`; 31–90 `stale`; > 90 `expired` | Expired is excluded from optimization by default |

**Resulting status**

- **verified**: all five dimensions bound + evidence text present + extracted by a provider adapter + format and plausibility pass + no conflict.
- **partial**: all five dimensions bound + evidence text present, but extracted by the LLM (tier 3) or with feature tags incomplete.
- **unverified**: any of the five dimensions unbound or ambiguous, or the evidence text is missing. These rows are kept for audit but **never** used by the optimizer unless the profile flag allows it, and then they are visibly labelled.

**Tests this adds (K.2):** price placed next to another plan's name → plan unbound; yearly price shown as monthly → cycle unbound; USD on page → currency unbound; `/us/` URL → region unbound; redirect to a reseller → provider unbound. Each must end `unverified`.

### G.4 Search provider

`SearchProvider.search(query, *, country, max_results) -> list[SearchHit]`, with implementations:

- `TavilySearchProvider`. Tavily's free plan gives [1,000 API credits per month with no credit card](https://docs.tavily.com/documentation/api-credits), and a basic search costs 1 credit. That is enough for development and demos if discovery stays a rare tier-3 path.
- `NullSearchProvider`: returns nothing; used in tests and when no key is configured. The app still works on tiers 1–2.
- Brave was the obvious alternative, but [on 12 February 2026 its 2,000-query free plan became a $5 monthly credit that requires a credit card](https://agentdeals.dev/vendor/brave-search-api). That conflicts with your no-mandatory-paid-services rule, so it should be optional only.

**Tavily is optional, not required (v2).** It is a pip extra (`pip install -e ".[search]"`) and is not in the default install. `get_search_provider(settings)` returns `NullSearchProvider` when `SUBWISE_TAVILY_API_KEY` is empty *or* the `tavily-python` package is not installed. Startup and `/health` never fail for lack of a key; health reports `search: "disabled"`. With search disabled, tier 3 discovery is off and every run uses tiers 1–2 (adapters + curated catalog + cached observations). The UI shows "Discovery off" instead of an error. An end-to-end test runs a full optimization with no key and no `tavily` package installed. No paid service is required at any point: Ollama, SQLite, PuLP/CBC and Playwright are all free and local.

Results are filtered to official domains when the provider is known. For unknown providers, a hit is a *candidate* only, and anything extracted from it stays `unverified` until a team member adds the provider to the registry.

### G.5 Initial catalog scope

**Video (India):** Netflix, Amazon Prime (as a bundle: Prime Video + Prime Music + delivery), JioHotstar, Sony LIV, ZEE5. **Music:** Spotify, YouTube Premium / YouTube Music, JioSaavn. Aim for 12–15 plans total.

This blueprint deliberately quotes **no prices**. They must be collected from the official pages at seed time, and that seeding task is module M4's first acceptance check. Telecom-bundled OTT (Jio/Airtel recharges) is often the real cheapest path in India; model it as `is_bundle` plans in a \[LATER\] phase.

## H. Portfolio optimization design (OAVOE)

OAVOE is a **lexicographic 0-1 integer program**. First it finds the best weighted feature coverage that fits the budget and hard constraints. Then it finds the cheapest portfolio that keeps that coverage. Then it lists the next-best distinct alternatives. Overlap is handled by counting each feature once. \[RECOMMENDATION\]

### H.1 Why not a single weighted score

A single objective such as "coverage − α·cost" forces you to pick α, an exchange rate between rupees and coverage points. Any value is arbitrary, and the jury will ask where it came from. Lexicographic optimization has no such constant: "never give up a feature you value to save money, unless you choose a savings mode" is a rule users understand. The trade-off moves into an explicit, user-visible **mode** (H.4).

Why ILP and not a greedy or brute-force search: greedy fails on bundles (one Prime plan beats two singles), and brute force over 2^n portfolios stops being practical past about 20 candidates. With 15–40 candidate plans, PuLP's CBC solver returns in milliseconds. Tests still compare it against brute force for small cases.

### H.2 Sets and data

- P = candidate plans (registry plans in the requested categories + plans of the user's current subscriptions), each with a usable price (status ∈ {verified, partial}, not expired, not in conflict).
- F = feature codes in the requested categories.
- a(p,f) ∈ {0,1}: 1 only if `plan_features.value = yes`. **Unknown counts as 0.** A bundle's row is the union of the features of every entitlement it includes.
- c(p) = monthly-equivalent price in paise = renewal/standard price ÷ billing\_cycle\_months, using integer arithmetic with the rounding remainder recorded.
- M ⊆ F = must-have features; w(f) ∈ (0,1\] = nice-to-have weights; B = monthly budget in paise.
- K = mandatory plans (subscriptions marked `is_mandatory`); X = excluded plans (dropped providers, hard rejections, failed eligibility).
- L\_cur = **service lines** the user currently subscribes to; u(s) = usage value of line s: daily 1.0, weekly 0.6, occasionally 0.2, never 0, unknown 0.5.

**Catalog vocabulary (v2).** A *provider* is a company (Amazon, Google). A *service line* is one product a person subscribes to (Netflix streaming, Prime membership, Prime Video standalone, Amazon Music Unlimited, YouTube Premium, Google One). A *plan* is one purchasable option of a line (a tier, a billing cycle, a family/student variant). An *entitlement* is a service line plus tier that a plan grants; a bundle grants several.

| Relationship | Declared in catalog as | Meaning in the optimizer | Example |
| --- | --- | --- | --- |
| **Mutually exclusive** | `exclusion_group` on plans; defaults to the plan's service line | At most one plan of the group per account: tiers, billing cycles and individual/family variants of one line | Netflix Mobile / Basic / Standard / Premium; Prime monthly vs Prime annual |
| **Bundle** | `plan_entitlements` with ≥ 2 rows | Ordinary plan whose feature row is the union of its entitlements. **Not exclusive** with standalone plans | Prime membership (Prime Video + Prime Music + delivery) |
| **Same provider, different line** | Different `service_line_id`, same `provider_id` | **No constraint.** A provider never forms an exclusion group by itself | Prime + Amazon Music Unlimited; YouTube Premium + Google One |
| **Add-on** | `plan_prerequisites` (requires any of a set of plans or lines) | Selectable only if a prerequisite is also selected | An ad-free upgrade that requires a base plan |
| **Eligibility-gated** | `plan_eligibility` (student, new customer, telecom customer) | Allowed only if the profile declares that eligibility; otherwise in X with the reason | Student plans; intro offers for new customers |
| **Duplicate entitlement** | Two plans grant the same line and tier | **Not forbidden.** The pair adds cost and zero coverage, so stage 2 never picks it; the report flags it if the user currently pays for both | Separate Prime Video plan while also holding Prime |

The v1 constraint "one plan per provider group" is withdrawn. It would have wrongly blocked valid combinations such as Prime + Amazon Music Unlimited.

### H.3 Model

Decision variables: x(p) ∈ {0,1} selects plan p; y(f) ∈ {0,1} means feature f is covered; k(s) ∈ {0,1} means current service line s is retained, by any selected plan that grants it, including a bundle.

```latex
\text{Stage 1:}\quad S^{*} = \max \sum_{f \in F \setminus M} w_f\, y_f \;+\; \lambda \sum_{s \in L_{cur}} u_s\, k_s
```

```latex
\text{s.t.}\quad y_f \le \sum_{p \in P} a_{pf}\, x_p \;\; \forall f, \qquad y_f = 1 \;\; \forall f \in M, \qquad \sum_{p} c_p\, x_p \le B
```

```latex
\sum_{p \in E} x_p \le 1 \;\; \forall E \in \mathcal{E}, \qquad x_a \le \sum_{q \in R(a)} x_q \;\; \forall a \in A, \qquad k_s \le \sum_{p \,:\, s \in \mathrm{ent}(p)} x_p
```

```latex
x_p = 1 \;\; \forall p \in K, \qquad x_p = 0 \;\; \forall p \in X
```

Here 𝓔 is the set of declared exclusion groups, A the add-on plans with prerequisite sets R(a), and ent(p) the service lines plan p grants.

```latex
\text{Stage 2:}\quad C^{*} = \min \sum_{p} c_p\, x_p \quad \text{s.t. stage-1 constraints and} \quad \text{score} \ge S^{*} - \delta
```

How to read it:

- **The overlap-awareness is the first constraint.** y(f) is capped at 1, so a second plan that also offers movies adds cost and zero score. The solver therefore drops redundant plans unless they bring a feature nothing else does. No separate "duplicate detector" is needed for the decision, though the report still lists overlaps for explanation (H.6).
- **Exclusion groups, not providers.** Only plans that one account cannot hold together (tiers, cycles, variants of one line) exclude each other. That stops answers such as Netflix Basic + Netflix Premium, while still allowing Prime + Amazon Music Unlimited.
- **Bundles need no special constraint.** Holding Prime and a separate Prime Video plan is never forbidden; it is just never optimal unless the separate plan adds a valued feature, such as a higher tier.
- **Add-ons and eligibility are hard constraints**, so the solver cannot recommend an upgrade without its base plan, or a student price to a non-student.
- **The usage term** (λ = 0.5, configurable) makes the model mildly prefer keeping service lines the user says they use daily, so it does not recommend churning a daily-use app for a tiny saving. Retention counts through bundles: keeping Prime Video via Prime counts as retained. Usage is **never** inferred, only reported.
- **Never-used subscriptions** (u = 0) get no retention credit, and the report flags them for review. The model itself does not force cancellation.

**Stage 3, alternatives.** Add a no-good cut (Σ over selected p of x(p) ≤ |selected| − 1) and re-solve stage 2 up to 2 more times, giving 3 portfolios ranked by (score, −cost).

### H.4 Modes (user-visible trade-off)

| Mode | δ in stage 2 | Behaviour |
| --- | --- | --- |
| Best coverage (default) | 0 | Keeps every nice-to-have reachable within budget |
| Balanced | 0.3 · S\* | Gives up a small share of nice-to-have value when that saves money |
| Max savings | S\* (coverage of nice-to-haves ignored) | Cheapest set that still meets every must-have and mandatory plan |

### H.5 Edge cases and feasibility

| Case | Detection | What the user sees |
| --- | --- | --- |
| **Equal cost** (the TA1 test, generalized) | Two portfolios with identical C and score | "There is no difference between the plans" in cost; the report shows features side by side; no fake savings |
| Recommendation = current portfolio | Chosen set equals current plans | "Your current subscriptions are already the best fit; savings ₹0" |
| No plan offers a must-have | Σ a(p,f) = 0 for some f ∈ M | Infeasible before solving: "No supported plan provides live cricket; remove it or add a provider" |
| Budget too low | Stage 1 infeasible | Solve min-cost-to-cover-musts without the budget: "Needs ₹X/month; your budget is ₹B; short by ₹(X−B)". Also solve the max number of musts coverable within B |
| Mandatory plans exceed budget | Σ c(K) > B | Same diagnosis, naming the mandatory plans |
| Conflicting or expired price on a needed plan | Excluded from P | Listed under "Not considered" with the reason; the user can approve a manual price |
| Promo prices | price\_kind = intro | Optimize on the renewal price; show "first-year cost" = intro × n + renewal × (12 − n) separately |
| Annual-only plan, monthly preference | billing\_preference = monthly | Plans with 12-month cycles are excluded; if annual is allowed, the report shows the upfront payment |
| Custom subscription outside the catalog | `plan_id` NULL | Its cost is a fixed constant (kept unless the user unticks it); its features are unknown, so it is never claimed to be replaced |

### H.6 Explainability outputs (deterministic, before any LLM)

The optimizer returns, as data: chosen plans; the feature matrix of chosen versus current plans; which chosen plan covers each feature (first provider by cost); **overlaps** (features covered by ≥ 2 chosen or current plans); **rejected candidates**, each with its binding reason (for example "adds ₹X for no new feature", "exceeds budget", "provider excluded", "price unverified"); current vs recommended monthly and annual cost; the alternatives; and the solver status and time. The LLM only verbalizes this structure, and `check_numbers` enforces that it does not alter it.

## I. Frontend and backend architecture

The frontend is a thin client over a versioned REST API (`/api/v1`). Every page reads through TanStack Query, and only the AI Optimizer page holds a live connection (Server-Sent Events). The backend splits HTTP routers, services (business rules) and repositories (SQL), so Antigravity can build and test each layer separately. \[RECOMMENDATION\]

### I.1 Pages

| Page | Route | Shows | Main calls |
| --- | --- | --- | --- |
| Sign in / up | `/login` | Email + password | `POST /auth/register`, `POST /auth/login` |
| Dashboard | `/` | Monthly and annual spend, active count, renewals in the next 30 days, latest report's potential savings (with its date), last 5 runs | `GET /dashboard` |
| My Subscriptions | `/subscriptions` | Table plus add/edit drawer: plan picker from catalog or custom name, price, cycle, renewal date, usage, mandatory toggle; "unused" badge for `never` | `GET/POST/PATCH/DELETE /subscriptions`, `GET /catalog/plans` |
| AI Optimizer | `/optimizer/:threadId?` | Chat box; live timeline of graph steps; sources panel (URL, fetched time, status badge); discovered-plans table; optimizer result with alternatives and mode switch; clarify form; Approve/Reject with reason; "Remember these?" checklist | `POST /threads`, `POST /runs`, `GET /runs/{id}/events` (SSE), `POST /runs/{id}/clarification`, `POST /runs/{id}/approval`, `POST /runs/{id}/cancel` |
| Price Intelligence | `/prices` | Per plan: current price, status, age, line chart of history (Recharts), changes since last check, "Refresh now" button | `GET /prices`, `GET /prices/{plan_id}/history`, `POST /prices/refresh` |
| Optimization History | `/history` | Runs with status, savings, decision; report viewer with evidence links | `GET /runs`, `GET /reports/{id}` |
| Profile & Preferences | `/profile` | Budget, billing, ads tolerance, feature must/nice/none with weight sliders, unverified-price toggle; learned memories list with delete | `GET/PUT /me/profile`, `GET/PUT /me/requirements`, `GET/DELETE /me/memory` |

UI rules: every price shows a status badge (Verified / Partial / Unverified / Stale / Conflict) and a tooltip with the source and age. A disabled "Approve" button explains why (for example "report still generating"). For demo resilience, an `Ollama: online / offline` indicator sits in the header and comes from `GET /health`.

### I.2 API contracts

All responses are JSON. Errors use one envelope (section J). IDs are ULIDs. Money is `{"paise": 49900, "display": "₹499.00"}`, formatted server-side so the client never does money arithmetic.

| Method & path | Request | Response | Notes |
| --- | --- | --- | --- |
| `POST /auth/register` | `{email, password, display_name}` | `201 {user}` + httpOnly cookie | Password ≥ 10 chars |
| `POST /auth/login` / `POST /auth/logout` | `{email, password}` | `200 {user}` + cookie | Rate-limited |
| `GET /me` | — | `{user, profile}` |  |
| `GET/POST /subscriptions`, `PATCH/DELETE /subscriptions/{id}` | `SubscriptionIn` | `SubscriptionOut` (+ `monthly_equivalent`) | Ownership enforced in repository |
| `GET /catalog/providers`, `GET /catalog/plans?category=` | — | Plans with current price + status | Read-only |
| `POST /threads` | `{title?}` | `{thread_id}` |  |
| `GET /threads/{id}/messages` | — | `Message[]` |  |
| `POST /runs` | `{thread_id, message, mode?: "best"\|"balanced"\|"savings"}` | `202 {run_id, status: "queued"}` | Returns at once; `409 RUN_IN_PROGRESS` if the user already has an active run |
| `GET /runs/{id}` | — | `{run, latest_report?, pending_interrupt?}` | Poll fallback if SSE fails |
| `GET /runs/{id}/events?after_seq=` | — | `text/event-stream` of `RunEvent` | Replays from `after_seq`, then streams; heartbeat every 15 s |
| `POST /runs/{id}/clarification` | `{answers: {field: value}}` | `202` | Only when `status = waiting_clarification` |
| `POST /runs/{id}/approval` | `{report_id, decision, reason?, remember?: [ids]}` | `202` | `409` if `report_id` is not the latest version |
| `POST /runs/{id}/cancel` | — | `202` |  |
| `GET /runs?status=&limit=&cursor=` | — | Paginated runs |  |
| `GET /reports/{id}` | — | `{report, result, evidence[]}` |  |
| `GET /prices`, `GET /prices/{plan_id}/history` | — | Observations |  |
| `POST /prices/refresh` | `{plan_ids?}` | `202 {job_id}` | Runs tier-1 refresh outside the agent |
| `GET /dashboard` | — | Aggregates | Computed in SQL/Python, never by the LLM |
| `GET/PUT /me/profile`, `GET/PUT /me/requirements` | Pydantic models | Same |  |
| `GET /me/memory`, `DELETE /me/memory/{kind}/{key}` | — | Store items |  |
| `GET /health` | — | `{db, ollama: {reachable, model_present}, search: {configured}}` | No auth |

### I.3 Backend services

| Module | Responsibility | Depends on |
| --- | --- | --- |
| `api/routers/*` | HTTP only: parse, authorize, call a service, map to a response | services |
| `services/subscriptions.py` | CRUD, monthly-equivalent maths via `core.costing` | repositories |
| `services/runs.py` | Create run, enqueue on worker, apply resume commands, cancel | worker, repositories |
| `services/reports.py`, `services/dashboard.py` | Read models | repositories |
| `worker/runner.py` | Single-thread executor; wraps `graph.invoke/stream`; writes `run_events`; updates run status | agent graph |
| `worker/events.py` | Async in-memory fan-out (one queue per subscriber) + DB replay for SSE | — |
| `agent/graph.py`, `agent/nodes/*`, `agent/state.py` | The section D graph | core, llm, memory |
| `core/*` | Pure functions: costing, validation, optimizer, report facts | nothing I/O |
| `research/*` | Search providers, fetcher, robots, adapters, extractor | httpx, bs4 |
| `llm/gateway.py` | One `call_structured(schema, prompt, timeout)` and one `call_text`; health check; never raises raw Ollama errors | ollama client only |

**Data flow for a run:** router → `RunService.create` (row `queued`) → worker thread `graph.stream(...)` → each node emits events → DB + fan-out → SSE to browser → interrupt reached → status `waiting_approval` → user POSTs a decision → `RunService.resume` → worker `graph.invoke(Command(resume=…))` → `completed`.

## J. Error handling and security

One typed exception hierarchy, one error envelope, one tool wrapper and one LLM gateway make every failure look the same to the UI and the logs. Every failure path ends in either a deterministic fallback or an honest "unavailable" message, never an invented value. \[RECOMMENDATION\]

### J.1 Mechanisms

- **Exception hierarchy** (`subwise/errors.py`): `SubWiseError(code, message, http_status, retryable, details)` → `ValidationFailed`, `NotFound`, `Forbidden`, `Conflict`, `ExternalServiceError` (→ `LLMUnavailable`, `LLMTimeout`, `LLMInvalidOutput`, `SearchUnavailable`, `FetchFailed`, `SourceDisallowed`), `DataQualityError`, `OptimizerInfeasible`, `PersistenceError`.
- **Error envelope** from one FastAPI exception handler: `{"error": {"code": "LLM_UNAVAILABLE", "message": "…", "retryable": true, "details": {}, "request_id": "…"}}`. Pydantic 422s are re-mapped into the same shape. Unknown exceptions become `INTERNAL_ERROR` without a stack trace in the response.
- **`@guarded_tool(timeout_s, retries, retry_on)`**, generalized from TA2's `safe_execute`: enforces a timeout, bounded retries with exponential backoff and jitter (no retry on 4xx), converts exceptions into typed errors, and emits `tool_call` / `tool_error` events with duration.
- **LLM gateway:** 60 s timeout per call (configurable, because a 3B model on CPU can be slow); one retry on invalid JSON with the validation error in the prompt; after that it raises `LLMInvalidOutput`, and the calling node uses its fallback. The model's presence is checked at startup with Ollama's `/api/tags`.
- **Loop bounds:** per-loop counters (D), `recursion_limit = 40`, and a run-level wall-clock budget of 10 minutes that ends the run as `failed: RUN_TIMEOUT` with its checkpoint kept.
- **Logging:** standard `logging` with a JSON formatter to `logs/app.log`, rotated. Every log line carries `request_id`, `user_id`, `run_id` and `node`. No prompts or page text are logged at INFO level.

### J.2 Failure matrix

| Failure | Detected by | Behaviour | User sees |
| --- | --- | --- | --- |
| Ollama not running / model missing | `/health`, gateway | Intent: rule parser. Decide: rule table. Explain: template. Run still completes. | Banner "AI explanations offline: using standard report"; trace shows `fallback` events |
| Model timeout | Gateway | Same as above for that node | Same |
| LLM returns invalid JSON | Pydantic | One repair retry, then fallback | Trace shows `LLM_INVALID_OUTPUT` |
| LLM text changes a number | `check_numbers` | Template replaces it | Report badge "generated from template" |
| Search API down / no key | Provider | Tier 3 skipped | "Discovery unavailable; using catalog" |
| Site timeout / 5xx / blocked / robots disallow | Fetcher | Tier 2 cached row with age | Status badge Stale/Cached + reason |
| Page layout changed | Adapter finds 0 prices or the evidence check fails | Mark adapter `broken` and use cache; alert in admin log | Same as above |
| Invalid / implausible price | Validator | Excluded or `conflict` | Listed under "Not considered" |
| No feasible portfolio | Optimizer | Diagnosis solve (H.5) | Shortfall explanation, no recommendation |
| DB locked/error | SQLAlchemy | Retry 3× on `database is locked` (WAL + `busy_timeout = 5000`); otherwise 503 | Error toast with retry |
| Backend restart mid-run | Startup sweep | Run marked `failed: WORKER_LOST`, resumable from checkpoint | "Resume" button |
| Unclear request | `parse_intent` missing fields | Clarify interrupt (max 2), then defaults from profile | Clarifying questions |

### J.3 Security and data protection

- **Auth:** argon2id password hashes (`pwdlib`), a short-lived JWT in an `HttpOnly`, `SameSite=Lax` cookie, and a CSRF token header on unsafe methods. `user_id` always comes from the token, **never from the request body or path**.
- **Authorization:** every repository method takes `user_id` and filters by it. A test suite tries to access another user's subscriptions, runs, reports and memory, and expects 404 for each.
- **Input validation:** Pydantic everywhere: prices 0–₹50,000, string lengths capped, the free-text request capped at 2,000 chars.
- **Prompt injection:** fetched page text is data. It is placed in delimited blocks, the extractor prompt has no tool access, and extracted output must still pass the evidence check, so injected instructions cannot create a price that is not on the page. The explainer receives only structured optimizer output, never raw page text.
- **Outbound fetching:** only `http(s)`, only to domains in the registry or search results; private IP ranges are blocked to prevent SSRF; response size is capped at 5 MB.
- **Secrets:** a `.env` holds `TAVILY_API_KEY` and `JWT_SECRET`; `.env.example` is committed and `.env` is ignored (TA2's `.gitignore` already does this, which is worth keeping).
- **Privacy:** all data stays on the laptop; nothing about a user is sent to the search API except the generic plan queries. The Profile page has "Export my data" (JSON) and "Delete my account" \[LATER for export\].
- **CORS:** only the Vite dev origin in development; in the demo build, FastAPI serves the built frontend from the same origin.

## K. Testing strategy

The deterministic core gets the heaviest testing because it carries every number. LLM nodes are tested through their fallbacks and through a small recorded evaluation set. The network is mocked everywhere except one opt-in live suite. Unlike TA2, every test imports the real module it tests. \[RECOMMENDATION\]

### K.1 Layers

| Layer | Tools | Scope | Runs |
| --- | --- | --- | --- |
| Unit | pytest, `hypothesis` | `core/*` (costing, validation, optimizer), adapters on saved HTML fixtures, Pydantic models | Every commit, < 30 s, no Ollama, no network |
| Integration | pytest, `respx`, temp SQLite, `FakeLLM` | Repositories, services, graph with fake LLM and fake search, interrupt/resume, SSE, auth isolation | Every commit, < 2 min |
| LLM evaluation | pytest marker `llm`, real Ollama | 30 recorded requests → expected `RequestSpec` fields; JSON-valid rate; `check_numbers` pass rate | Manually, before a demo or a model change |
| Live sources | marker `live` | Each registry adapter against its real URL; reports which are broken | Manually, weekly and before the demo |
| Frontend | Vitest + React Testing Library | Components, money formatting, status badges, forms | Every commit |
| End-to-end | Playwright test runner against the running app with FakeLLM + fixture sources | The 11-step demo journey (brief §13 Phase 3) | Before merge to `main` |

### K.2 Required cases (your list, mapped)

| # | Case | Test (level) | Pass condition |
| --- | --- | --- | --- |
| 1 | Different prices | `test_compare_different` (unit) | Correct cheaper plan and difference in paise; annual = 12× for monthly cycles |
| 2 | **Equal prices (TA1 original)** | `test_compare_equal_exact_sentence` (unit) + `test_optimizer_equal_cost_portfolios` (unit) + `test_ta1_equal_prompt` (llm) | Output contains "There is no difference between the plans."; no savings > 0 anywhere in the report |
| 3 | Cheaper plan lacks a must-have | `test_must_have_beats_price` (unit) | Cheaper plan not chosen; it appears in rejected candidates with reason `missing_must_have` |
| 4 | Overlapping features | `test_overlap_counted_once` (unit) | Of 3 plans all covering `movies`, only the ones adding a unique valued feature are kept |
| 5 | Budget too low | `test_infeasible_budget_diagnosis` (unit) | Status infeasible; shortfall = min-cost-for-musts − B, exactly |
| 6 | No suitable plan | `test_no_plan_has_feature` (unit) | Pre-solve error naming the feature |
| 7 | Scraping fails | `test_fetch_timeout_uses_cache` (integration, respx) | Observation status `stale`/`cached`; run completes; event `tool_error` recorded |
| 8 | Stale source | `test_freshness_thresholds` (unit) | 30/31/90/91-day boundaries give fresh/stale/stale/expired |
| 9 | Conflicting prices | `test_conflict_excluded` (unit) | Both observations `conflict`; plan absent from P |
| 10 | Promo vs renewal | `test_promo_uses_renewal` (unit) | Optimizer cost = renewal; first-year cost reported separately and correctly |
| 11 | Preference across sessions | `test_store_survives_new_process` (integration) | Write in one `SqliteStore` connection, read in a fresh process |
| 12 | Workflow resume | `test_resume_after_restart` (integration) | Run reaches approval, the graph object is discarded and recompiled from `checkpoints.db`, `Command(resume)` completes it |
| 13 | User rejects | `test_reject_records_and_revises` (integration) | `approval_decisions` row `rejected`; rejection in store; revision 2 excludes the plan |
| 14 | Tool failure | `test_llm_down_full_fallback` (integration) | With FakeLLM raising, the run completes with template report and rule decisions |
| 15 | End-to-end success | `e2e/optimizer.spec.ts` | Journey completes in UI; report visible in History |
| + | Optimizer correctness | `test_ilp_matches_bruteforce` (hypothesis, n ≤ 12 plans) | Same optimal cost and score as exhaustive search on 200 random instances |
| + | Identity separation | `test_graph_config_uses_run_id` + `test_cross_user_access_404` | No code path builds a config without `graph_config`; other users' data is unreachable |
| + | Hallucinated price blocked | `test_evidence_check_rejects_missing_snippet` | An LLM-extracted price absent from the page text cannot reach `verified`/`partial` |

### K.3 Test doubles

- `FakeLLM`: returns scripted JSON per prompt key and can be set to time out or return invalid JSON.
- `FakeSearchProvider`: returns fixture hits.
- **HTML fixtures:** saved copies of each official pricing page used in adapter tests, stored with their capture date. Never commit pages whose terms forbid redistribution; store only the extracted text excerpts in that case.
- `freezegun` for freshness tests.

## L. Repository structure (`SubWise`)

Use a monorepo with `backend/` (an installable Python package `subwise`) and `frontend/` (Vite). Commit runtime data folders empty with `.gitkeep`, and add an `AGENTS.md` that states the project rules for Antigravity. \[RECOMMENDATION\]

The tree below is what Phase 1 created (v2). Differences from v1 are recorded in ADR-009.

```text
SubWise/
├── README.md  AGENTS.md  .env.example  .gitignore  .gitattributes  .editorconfig
├── .github/workflows/ci.yml        # Windows + Ubuntu, Python 3.12/3.13, Node 22
├── .vscode/                        # settings, recommended extensions, launch configs
├── scripts/                        # setup.ps1, dev.ps1, test.ps1 (Windows)
├── docs/
│   ├── blueprint.md                # pointer to this document + summary
│   ├── roadmap.md                  # module status and acceptance
│   ├── verified-apis.md            # pinned versions + verified API usage
│   ├── decisions/                  # ADR-001 … ADR-009
│   ├── data-sources.md             # provider register (filled in M4)
│   └── ta2-migration.md
├── backend/
│   ├── pyproject.toml  README.md  alembic.ini  alembic/
│   ├── scripts/check_env.py
│   ├── src/subwise/
│   │   ├── main.py  config.py  errors.py  ids.py
│   │   ├── api/  error_handlers.py  deps.py  schemas/  routers/
│   │   ├── domain/                 # PURE: enums, catalog, evidence, request, optimization
│   │   ├── core/                   # PURE: money, costing, validation, features, optimizer/, report_facts
│   │   ├── research/  search/ (base, null, tavily)  fetch.py  adapters/  llm_extract.py  catalog_seed/
│   │   ├── llm/  gateway.py  fallbacks.py  prompts/
│   │   ├── memory/  backends.py  learned.py
│   │   ├── agent/  state.py  config.py  graph.py  nodes/ (12 nodes)
│   │   ├── worker/  runner.py  events.py  sweep.py
│   │   ├── services/  db/
│   └── tests/  unit/  integration/  llm_eval/  live/  fixtures/
├── frontend/
│   ├── package.json  package-lock.json  vite.config.ts  tsconfig*.json  index.html
│   ├── src/  main.tsx  router.tsx  App.tsx  api/ (client, types, schema.d.ts)  components/  pages/  hooks/
│   └── tests/
└── data/                           # runtime only; .gitkeep committed
```

**`AGENTS.md` must state:** never put arithmetic on money in prompts; never construct a LangGraph config outside `agent/config.py`; `core/` imports no I/O libraries; every new module ships with tests and an acceptance checklist; no claim of "done" without a passing test run pasted into the PR; money is paise integers; never commit `data/` or `.env`.

**Windows notes:** `python -m venv .venv` + `pip install -e backend[dev]`; Node 20 LTS; `ollama pull qwen2.5:3b`; optional `python -m playwright install chromium`. Use `pathlib` for every path; set `PYTHONUTF8=1` in `scripts/dev.ps1` (TA2's RAG script already had to call `stdout.reconfigure(encoding="utf-8")` to print ₹ on Windows).

## M. Development roadmap

Build the pure core (costing, validation, OAVOE) on a manually seeded catalog **before** web research. That way the differentiator works end to end even if scraping later proves fragile. This reorders your proposed sequence, which put discovery and scraping ahead of the optimizer. \[RECOMMENDATION\]

Each module is one Antigravity task: give it the module's section of this blueprint, `AGENTS.md`, and the acceptance list. A module is done only when its tests pass and the acceptance items are ticked in the PR description.

| # | Module | Depends on | Acceptance (all must hold) |
| --- | --- | --- | --- |
| M0 | Scaffold: repo layout (L), `pyproject`, Vite app, lint/format, pytest + Vitest wired, GitHub Actions running both, `check_env.py` | — | CI green on an empty test; `check_env.py` reports Python, Node, Ollama and the model on Windows |
| M1 | Config, error hierarchy + envelope, JSON logging, request IDs, `/health` | M0 | Unknown exception → envelope without trace; 422 → same envelope; `/health` reports Ollama down correctly |
| M2 | SQLAlchemy models, Alembic baseline, user-scoped repositories, WAL + busy timeout | M1 | `alembic upgrade head` on a blank DB; repository tests show cross-user reads return nothing |
| M3 | Auth, profile, requirements, subscriptions API | M2 | Register/login/logout; CRUD with monthly-equivalent; cross-user access returns 404 |
| M4 | Feature vocabulary + catalog seed YAML + `seed_catalog.py` | M2 | ≥ 12 plans in video and music, each with official URL, observed date, `fetch_method`; a second team member re-checked every price against the page |
| M5 | `core/money`, `costing` (equal-cost rule), `validation` (G.3) | M1 | Cases 1, 2, 8, 9, 10 pass; no float in money code (lint rule or test) |
| M6 | OAVOE: model, modes, diagnosis, alternatives, brute-force checker | M5 | Cases 3–6 + ILP-vs-brute-force property test pass; solve < 1 s for 40 plans |
| M7 | LLM gateway, prompts, rule parser, template report, `check_numbers` | M1 | With Ollama off, all fallbacks produce valid output; with Ollama on, ≥ 80% of the 30 eval requests parse into a valid `RequestSpec` |
| M8 | Research: fetcher, robots, SSRF guard, search providers, ≥ 4 adapters, tier-3 extractor + evidence check | M4, M5 | Case 7; evidence test; live suite reports each adapter's status; disallowed sources never fetched |
| M9 | Memory backends, `graph_config`, learned-preference read/write | M2 | Cases 11 and 12 (restart resume) pass; `graph_config` test passes |
| M10 | Agent graph: state, nodes, interrupts, loop counters, events | M6, M7, M8, M9 | Cases 13, 14 and the full graph test with fakes pass; trace shows LLM vs rule for each decision |
| M11 | Worker, runs API, SSE with replay, cancel, startup sweep | M3, M10 | Run survives page refresh (SSE replay); backend restart → `WORKER_LOST` + Resume works |
| M12 | Frontend shell, auth, Subscriptions, Profile | M3 | Vitest suite green; forms validate; money shown via `MoneyText` only |
| M13 | Frontend Optimizer, History, Prices, Dashboard | M11, M12 | Live timeline, sources panel with badges, approve/reject, report viewer with evidence links |
| M14 | End-to-end tests, LLM eval run, live-source check, demo script, docs | all | Section O criteria met |

**Parallel tracks for a 4-person team.** Track A: M2 → M3 → M12. Track B: M5 → M6. Track C: M7 → M9. Track D: M4 → M8. All four tracks merge at M10 → M11 → M13 → M14.

**Phase 1 (delivered with v2).** M0 is done: the scaffold, typed interfaces (domain models, `RunState`, `graph_config`, error classes and envelope, 31 API operations as 501 stubs), library contract tests, architecture-rule tests, CI and Windows scripts, `AGENTS.md` and nine ADRs. Error classes and the envelope moved from M1 into Phase 1, so **M1 now covers** JSON logging, request IDs and real `/health` probes. The per-module checklist lives in the repo at `docs/roadmap.md`. M2's acceptance now includes the v2 catalog tables (E.1), and M6's the exclusion-group cases (H.2).

## N. Risks and architectural challenges

The two risks most likely to sink the demo are fragile live price extraction and a slow or unreliable 3B model. The design above contains both by making them optional. The table also lists assumptions in the brief that are unrealistic as written.

| Risk / unrealistic assumption | Likelihood | Impact | Mitigation in this design |
| --- | --- | --- | --- |
| "The agent researches any provider live": OTT pricing pages are JS-rendered, geo-dependent and often forbid automated access | High | High | Registry + adapters + cached tier; discovery stays rare and `unverified`; demo shows tier labels openly |
| Prices depend on the requesting IP's country | Medium | High | Run fetches from India (your laptop); store `country` on observations; reject pages whose currency isn't INR |
| Adapters break when sites change layout | High over months | Medium | Evidence check catches silent breakage; weekly live suite; cache fallback |
| Qwen 2.5 3B misreads intent or emits bad JSON | Medium | Medium | Ollama `format` schema, one repair retry, rule fallback; eval set measures the rate before the demo |
| 3B model latency on a CPU-only laptop (seconds to tens of seconds per call) | High | Medium | Only 3–4 LLM calls per run; short prompts; SSE shows progress; template explanation if over the timeout |
| Feature tags too coarse ("movies" says nothing about which films) | Certain | Medium | State it as a limitation; let users mark a provider as "must keep" for catalogue-specific needs |
| Bundles and telecom offers (Jio/Airtel) dominate real-world value | High | Medium | `is_bundle` plans + provider groups now; telecom bundles \[LATER\] |
| Taxes (GST) inclusion unclear on some pages | Medium | Low | `tax_included = unknown` shown honestly; never add or subtract tax by assumption |
| SQLite write contention with worker + API | Low | Medium | WAL, busy timeout, single worker, short transactions |
| LangGraph interrupt re-executes node prefix on resume | Certain | Low | Keep interrupt nodes side-effect-free before `interrupt()` (F.2) |
| LangGraph/LangChain API churn (TA2 pinned 1.x versions) | Medium | Medium | Pin exact versions in `pyproject`; add `langgraph-checkpoint-sqlite`, which TA2 forgot |
| Search API free tiers change (Brave's now needs a credit card) | Medium | Low | Adapter interface + `NullSearchProvider`; app works without search |
| Scope creep: 6 pages + auth + agent + scraping + optimizer for a student team | High | High | Roadmap puts the differentiator first; "Price monitoring", "export", extra categories are \[LATER\] |
| Jury question: "Isn't this just a pipeline?" | Likely | Medium | Show the `decide` node choosing `research_more` on a degraded source, the clarify interrupt, memory changing a later run, and the trace marking LLM vs rule decisions |

## O. Final acceptance criteria

SubWise is "complete" for the jury when every box below is ticked on a clean Windows machine, by someone who did not write the code, following only the README.

**Setup and reliability**

- [ ] Fresh clone → running app in ≤ 15 minutes on Windows with the README alone (Python, Node, Ollama installed)
- [ ] `pytest` (unit + integration) and `vitest` pass with 0 failures; backend line coverage ≥ 85% on `core/` and ≥ 70% overall
- [ ] All 15 brief test cases + the 3 added cases (K.2) exist and pass
- [ ] With Ollama stopped, a full optimization still completes with fallback decisions and a template report, and the UI says so
- [ ] With the network unplugged, a full optimization completes on cached catalog data, every price labelled with its age
- [ ] Killing the backend while a run waits for approval, then restarting, lets the user resume and approve that run

**Correctness and honesty**

- [ ] Equal-cost scenario reports "There is no difference between the plans." and ₹0 savings
- [ ] ILP results match brute force on 200 random instances with ≤ 12 plans
- [ ] 0 prices in any report lack a source URL and timestamp; spot-check 10 at random against the source page
- [ ] 0 LLM-written reports with a number not present in the optimizer output (enforced by `check_numbers`, verified on the eval set)
- [ ] Catalog contains ≥ 12 real plans across 2 categories; ≥ 4 providers refresh live via adapters on demo day

**Product journey (demo)**

- [ ] The 11-step journey from brief §13 Phase 3 runs end to end in the browser in ≤ 3 minutes on the demo laptop
- [ ] A second run after a rejection visibly uses the stored rejection (trace shows the memory item)
- [ ] Two users cannot see each other's subscriptions, runs, reports or memories (automated test + manual check)

**Documentation**

- [ ] README: setup, run, demo script, known limitations
- [ ] `docs/data-sources.md` lists every provider with URL, terms/robots decision and last check date
- [ ] Architecture decision records for LLM scope, identifiers, ILP choice and the research tiers
- [ ] The original `SubscriptionCostOptimitzer` repository is unchanged (no commits after the fork date)

**Free-tier and offline guarantees (v2)**

- [ ] With no Tavily key and the `tavily-python` package not installed, the full demo journey completes on catalog + cached data, and `/health` shows `search: disabled`
- [ ] No step of setup or the demo needs a paid account, Docker or a credit card
- [ ] CI is green on `windows-latest` for Python 3.12 and 3.13 and Node 22

## P. Verified versions and API contracts

Every pin below was installed and exercised on 21 Nov 2026 by contract tests that live in the repo (`backend/tests/integration/test_library_contracts.py`). Users can re-run them on Windows, and CI runs them on `windows-latest`. The full backend dependency tree (90 packages) resolves to prebuilt Windows wheels for Python 3.12 and 3.13, so no compiler is needed.

| Area | Pinned | Verified behaviour |
| --- | --- | --- |
| Python | 3.12 recommended; 3.13 tested | Tests and `mypy --strict` pass on 3.12.13 and 3.13.18; install works with plain `pip` and with `uv` |
| LangGraph | `langgraph==1.2.24` + `langgraph-checkpoint-sqlite==3.1.3` | `interrupt(payload)` pauses; output has `__interrupt__`; `get_state(cfg).next == ("approval",)`; `invoke(Command(resume=v), cfg)` resumes **in a fresh process** over the same SQLite file; the interrupted node re-runs from its first line on resume |
| Long-term store | `SqliteStore` from the same package | `setup()`, `put/get/search/delete` with namespace `("users", user_id, kind)`; data persists across processes and is isolated per user |
| LLM client | `ollama==0.6.3` (official client, ADR-006) | `Client(host, timeout=…)` passes the timeout to httpx (default is **none**); `chat(format=<JSON schema dict>, options={"temperature": 0})`; server down raises `ConnectionError`. Needs Ollama server ≥ 0.5. Qwen 2.5 3B output quality is measured in M7 (`pytest -m llm`) |
| Optimizer | `pulp==3.3.2` | Bundled CBC (`PULP_CBC_CMD`) solves binary programs on Windows/Linux/macOS. 4.x would need `pulp[cbc]` and its new API (ADR-005) |
| API | `fastapi==0.165.0`, `pydantic==2.14.4`, `sqlalchemy==2.1.9`, `alembic==1.20.1` | 31 operations in OpenAPI; envelope on 404/422/500/501; `alembic upgrade head` works on SQLite. In this FastAPI version, `app.routes` holds lazy router objects, so tests enumerate `app.openapi()` |
| Search | `tavily-python==0.8.5` as optional extra | Absent by default; `NullSearchProvider` selected |
| Frontend | React 19.3, react-router 8.5, TanStack Query 5.108, Vite 8.3, Tailwind 4.3, Vitest 5.1, **TypeScript 5.9.3** | Type-check, 16 tests and production build pass. TypeScript 7 rejected because `openapi-typescript` requires TS 5 (ADR-008) |

Full details and code snippets are in the repo at `docs/verified-apis.md`.

## Sources

- [Sarthak0521/SubscriptionCostOptimitzer](https://github.com/Sarthak0521/SubscriptionCostOptimitzer): audited at commit `731edeb` (cloned and read in full)
- [Tavily API credits documentation](https://docs.tavily.com/documentation/api-credits): free plan, 1,000 credits/month, no card (from Tavily's documentation as indexed by search, November 2026)
- [Brave Search API pricing tracker (AgentDeals)](https://agentdeals.dev/vendor/brave-search-api): 2,000-query plan converted to a $5 monthly credit on 12 Feb 2026; card required

LangGraph `interrupt()`/`Command(resume)` behaviour and Ollama's JSON-schema `format` parameter are described from the libraries' documented APIs. Confirm both against the versions you pin in M0.
