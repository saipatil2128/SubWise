# SubWise

SubWise finds the cheapest combination of **real** video and music subscription plans in India that
still covers what you actually use. It reads each provider's official pricing page when you ask,
ties every price to its plan with evidence from the page, optimizes your portfolio with an integer
program (OAVOE), and explains the result in plain English. You approve or reject every
recommendation; rejections teach it your priorities.

Everything runs on your own Windows PC: FastAPI + SQLite backend, React frontend, and a local
language model (Qwen 2.5 3B through Ollama). No Docker, no WSL, no paid APIs.

Providers: Netflix, Amazon Prime Video, JioHotstar, Sony LIV, ZEE5, Spotify, YouTube Premium,
Apple Music.

> **No prices are shipped with the app.** All plan prices come from live retrieval of the
> providers' official pages on your machine. If a page can't be reached or parsed, SubWise says so
> and uses nothing for that provider (or, if you allow it, a price it verified earlier, clearly
> labelled as cached). See [Data honesty](#data-honesty).

---

## 1. Prerequisites (Windows 10/11)

Open **PowerShell** (or the VS Code terminal, which uses PowerShell by default) and install what is
missing. `winget` is built into Windows 10 (1809+) and 11.

| Tool | Install command | Check |
| --- | --- | --- |
| Python 3.12 | `winget install -e --id Python.Python.3.12` | `py -3.12 --version` |
| Node.js 22 LTS | `winget install -e --id OpenJS.NodeJS.LTS` | `node --version` (≥ 22) |
| Git | `winget install -e --id Git.Git` | `git --version` |
| Ollama | `winget install -e --id Ollama.Ollama` | `ollama --version` (server ≥ 0.5) |
| VS Code | `winget install -e --id Microsoft.VisualStudioCode` | — |

Close and reopen the terminal after installing so the new commands are on `PATH`.
Python 3.13 also works; 3.12 is recommended.

If PowerShell refuses to run scripts, allow local scripts for your user once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Ollama and the model

The Ollama installer starts the Ollama server in the background (tray icon) on
`http://localhost:11434`. Download the model once (about 1.9 GB):

```powershell
ollama pull qwen2.5:3b
ollama list                      # qwen2.5:3b should be listed
```

If the server isn't running, start the **Ollama** app from the Start menu, or run `ollama serve` in
a separate terminal. SubWise still works without Ollama: it then uses its rule-based request parser
and a template report, and the UI shows "LLM offline (fallbacks)".

## 2. Get the code and open it in VS Code

Unzip the project (or `git clone https://github.com/saipatil2128/SubWise.git`), then:

```powershell
cd SubWise
code .
```

Accept the **recommended extensions** prompt (Python, debugpy, Ruff, Mypy, PowerShell, Tailwind,
Vitest).

## 3. Install (one command)

In the VS Code terminal (**Terminal → New Terminal**), from the repository root:

```powershell
.\scripts\setup.ps1
```

This creates `backend\.venv` (Python 3.12), installs the backend with its dev tools, creates `.env`
from `.env.example` with a random `SUBWISE_JWT_SECRET`, initialises the database, installs the
frontend packages, pulls `qwen2.5:3b` if Ollama is installed, and runs an environment check.
Add `-Browser` to also install Playwright + Chromium (needed for the browser E2E test and for
pricing pages that only render with JavaScript):

```powershell
.\scripts\setup.ps1 -Browser
```

Then select the interpreter in VS Code: **Ctrl+Shift+P → Python: Select Interpreter →
`backend\.venv\Scripts\python.exe`** (it is preselected by `.vscode/settings.json`).

<details>
<summary>Manual install, step by step</summary>

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e "backend[dev]"                 # add ,browser for Playwright: "backend[dev,browser]"
python -m playwright install chromium         # only if you installed the browser extra
Copy-Item .env.example .env                   # then set SUBWISE_JWT_SECRET to a long random string
cd backend; python -m subwise.cli init-db; cd ..
cd frontend; npm ci; cd ..
python backend\scripts\check_env.py
```
</details>

## 4. Configure (`.env`)

`.env` lives in the repository root and is never committed. All settings have defaults:

| Variable | Default | Meaning |
| --- | --- | --- |
| `SUBWISE_JWT_SECRET` | — | Signs login sessions. `setup.ps1` generates one. |
| `SUBWISE_DATA_DIR` | `<repo>\data` | Databases, fetched pages, logs |
| `SUBWISE_OLLAMA_HOST` | `http://localhost:11434` | Ollama server |
| `SUBWISE_OLLAMA_MODEL` | `qwen2.5:3b` | Model name |
| `SUBWISE_LLM_TIMEOUT_S` | `60` | Per-call timeout; slower PCs may need more |
| `SUBWISE_TAVILY_API_KEY` | empty | Optional: lets SubWise find a provider's moved pricing page (`pip install -e "backend[search]"`) |
| `SUBWISE_PLAYWRIGHT_ENABLED` | `false` | Render JavaScript-only pricing pages with Chromium (needs the browser extra) |

## 5. Initialise the database

`setup.ps1` already did this, and the backend also applies migrations on start. To do it by hand:

```powershell
cd backend
.\.venv\Scripts\python.exe -m subwise.cli init-db
```

Databases are created in `data\`: `app.db` (accounts, subscriptions, prices, runs, reports),
`checkpoints.db` (LangGraph run checkpoints) and `memory.db` (what SubWise learned from your
decisions). Delete the `data` folder to start from scratch.

## 6. Run

**From VS Code:** Run and Debug (**Ctrl+Shift+D**) → **SubWise: backend + frontend** → ▶. The browser
opens http://localhost:5173. (Or **Terminal → Run Task → SubWise: start both** for auto-reload.)

**From PowerShell:**

```powershell
.\scripts\dev.ps1          # opens two windows: API on :8000 and UI on :5173
```

Or in two terminals:

```powershell
# terminal 1 - backend
cd backend
.\.venv\Scripts\python.exe -m uvicorn subwise.main:create_app --factory --reload --host 127.0.0.1 --port 8000

# terminal 2 - frontend
cd frontend
npm run dev
```

Open **http://localhost:5173**. API docs: http://127.0.0.1:8000/docs · health:
http://127.0.0.1:8000/api/v1/health.

**Single-server mode:** `cd frontend; npm run build`, then start only the backend and open
http://127.0.0.1:8000 — the backend serves the built UI.

### First use

1. **Create an account.**
2. **Plans & prices → Refresh all prices.** SubWise fetches all eight official pages (takes up to a
   minute). Each provider shows whether it succeeded; failures show the reason.
3. **Subscriptions → Add subscription** for each service you pay for, with the price **you** pay,
   how often you use it, and its renewal date.
4. **Preferences:** set a budget, ads tolerance, eligibility (student etc.), which price labels the
   optimizer may use, and must-have / nice-to-have features.
5. **Optimizer:** describe what you want ("keep cricket, cut my bill, under ₹500"), pick a mode and
   start. Watch the agent's steps live; answer a question if it asks one; review the report with its
   evidence; approve, or reject with a reason to get a revised recommendation.
6. **Dashboard / History / Compare plans** show spend, past runs, and side-by-side plans.

Prices can also be fetched from the command line:

```powershell
cd backend
.\.venv\Scripts\python.exe -m subwise.cli refresh            # all providers
.\.venv\Scripts\python.exe -m subwise.cli refresh netflix spotify
.\.venv\Scripts\python.exe -m subwise.cli prices             # stored prices with labels
```

## 7. Tests

```powershell
.\scripts\test.ps1          # ruff, mypy, pytest, TypeScript, Vitest, production build
.\scripts\test.ps1 -E2E     # + the real-browser end-to-end test (needs setup.ps1 -Browser and a build)
```

VS Code: **Terminal → Run Task → SubWise: run all tests**, or the Testing panel (pytest and Vitest).

| Suite | Command (in `backend` unless noted) | Needs |
| --- | --- | --- |
| Backend unit + integration + workflow + auth/isolation | `pytest` | nothing |
| Frontend unit/component/page | `npm test` (in `frontend`) | nothing |
| Browser E2E (built UI + real server + Chromium) | `pytest -m e2e` | `npm run build`, browser extra |
| Live provider retrieval | `pytest -m live -rA` | internet |
| Local LLM quality | `pytest -m llm -rA` | Ollama + `qwen2.5:3b` |

The default `pytest` run uses synthetic HTML fixtures from `backend/tests/fixtures` served through a
mock transport into a temporary folder. Fixtures never touch `data\` and are never shown as real
prices. The latest test report is [`docs/test-report.md`](docs/test-report.md).

## Data honesty

Every price carries a label:

| Label | Meaning |
| --- | --- |
| **Live · verified** | From the latest successful fetch of the official page (under 24 h old), bound to provider, plan, billing cycle, currency and region by text on the page |
| **Cached · verified** | Verified on an earlier fetch; the latest fetch did not re-confirm it. Used by the optimizer only if ≤ 30 days old and you allow cached prices |
| **Partial** | On the official page but not every dimension could be bound. Used only if you allow it |
| **Unverified** / **Conflict** | Not usable unless you explicitly allow unverified prices |
| **You entered** | Your own subscription's price, as you typed it |

SubWise respects `robots.txt`, uses an honest User-Agent, never bypasses logins or CAPTCHAs, and
fetches only the providers' official domains. Provider websites change; when a page layout changes,
that provider shows *no prices* until the extractor is updated — it is never filled in. Always
confirm the price on the provider's site before subscribing.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `py` not found | Reinstall Python with the launcher, or use the full path to `python.exe` |
| "running scripts is disabled" | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| UI says "Cannot reach the SubWise backend" | Start the backend (step 6) and reload |
| "LLM offline (fallbacks)" | Start Ollama; `ollama pull qwen2.5:3b`; check `SUBWISE_OLLAMA_HOST` |
| A provider shows `needs_js` | `.\scripts\setup.ps1 -Browser`, set `SUBWISE_PLAYWRIGHT_ENABLED=true` in `.env`, restart |
| A provider shows `disallowed` | Its robots.txt disallows the page; SubWise will not fetch it |
| Port 8000 or 5173 busy | Stop the other process, or change the port in the command and in `frontend\vite.config.ts` |
| `₹` prints as `?` | Set `$env:PYTHONUTF8 = "1"` (the scripts do this) |

## Repository layout

```text
backend/    FastAPI app (package `subwise`), Alembic migrations, tests, scripts
  src/subwise/core/       money, costing, validation, OAVOE optimizer, report facts (pure)
  src/subwise/research/   provider registry, robots-aware fetcher, extractor, optional search
  src/subwise/agent/      LangGraph workflow (clarify, research, validate, decide, optimize, explain, approval)
  src/subwise/worker/     background run worker and run events
  src/subwise/api/        REST + Server-Sent Events
frontend/   React 19 + Vite + TypeScript + Tailwind + Recharts
docs/       blueprint, ADRs, roadmap, verified APIs, data sources, test report
data/       runtime data (SQLite, fetched pages, logs) - never committed
scripts/    Windows PowerShell helpers (setup, dev, test)
.vscode/    launch configurations, tasks, settings, extension recommendations
```

Architecture: [`docs/blueprint.md`](docs/blueprint.md) · Decisions: [`docs/decisions/`](docs/decisions/) ·
Contributor and AI-tool rules: [`AGENTS.md`](AGENTS.md).

## Origin

SubWise grows out of the TA1/TA2 "Subscription Cost Optimizer" assignment
(`Sarthak0521/SubscriptionCostOptimitzer`), which stays untouched as the academic record. What was
reused, redesigned or dropped is in [`docs/ta2-migration.md`](docs/ta2-migration.md).
