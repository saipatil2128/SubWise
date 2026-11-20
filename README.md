# SubWise

SubWise recommends the cheapest combination of real subscription plans (video and music, India)
that still covers what a person actually needs. Every price it uses comes with a source page and
a retrieval date. A local LLM (Qwen 2.5 3B via Ollama) reads the request and explains the result.
All prices, maths and optimization are deterministic Python.

> **Status: Phase 1 scaffold.** The project structure, typed interfaces, error handling, test
> setup and CI are in place. Business features are stubs that answer `501 NOT_IMPLEMENTED` and name
> the roadmap module that will build them. See [`docs/roadmap.md`](docs/roadmap.md).

- Architecture: [`docs/blueprint.md`](docs/blueprint.md) · Decisions: [`docs/decisions/`](docs/decisions/)
- Rules for contributors and AI coding tools: [`AGENTS.md`](AGENTS.md)
- Verified library APIs and versions: [`docs/verified-apis.md`](docs/verified-apis.md)

## Requirements (Windows 10/11)

| Tool | Version | Notes |
| --- | --- | --- |
| Python | 3.12.x (3.13 also tested) | python.org installer, tick "Add python.exe to PATH" |
| Node.js | 22 LTS or newer | nodejs.org installer |
| Git | any recent | git-scm.com |
| Ollama | server ≥ 0.5 | ollama.com; needed for AI features, **not** for the scaffold tests |
| VS Code | recent | open the repo folder and accept the recommended extensions |

No Docker and no paid services are needed. A Tavily API key is optional.

## Setup on Windows (PowerShell)

```powershell
git clone https://github.com/saipatil2128/SubWise.git
cd SubWise
.\scripts\setup.ps1
```

`setup.ps1` creates `backend\.venv`, installs the backend with dev tools, installs frontend packages,
copies `.env.example` to `.env` if missing, and runs the environment check. The equivalent manual
steps are:

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e "backend[dev]"
Copy-Item .env.example .env        # then edit SUBWISE_JWT_SECRET
cd frontend; npm ci; cd ..
python backend\scripts\check_env.py
```

If PowerShell refuses to run scripts, allow them for your user once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### Local LLM (optional for Phase 1)

```powershell
ollama pull qwen2.5:3b
ollama --version                    # structured outputs need server 0.5 or newer
python backend\scripts\check_env.py --strict
cd backend; pytest -m llm           # one live structured-output test against your Ollama
```

### Optional extras

```powershell
pip install -e "backend[search]"    # Tavily discovery; also set SUBWISE_TAVILY_API_KEY in .env
pip install -e "backend[browser]"; python -m playwright install chromium   # JS-rendered pages
```

## Run

```powershell
.\scripts\dev.ps1          # starts the API (http://127.0.0.1:8000) and the UI (http://localhost:5173)
```

Or in two terminals:

```powershell
# terminal 1
backend\.venv\Scripts\Activate.ps1; cd backend; uvicorn subwise.main:app --reload --host 127.0.0.1 --port 8000
# terminal 2
cd frontend; npm run dev
```

API docs: http://127.0.0.1:8000/docs · Health: http://127.0.0.1:8000/api/v1/health

## Verify the scaffold

```powershell
cd backend
ruff check .; ruff format --check .; mypy; pytest          # 88 tests
cd ..\frontend
npm run typecheck; npm test; npm run build                 # 16 tests
```

Expected in Phase 1: `GET /api/v1/health` returns `"status": "ok"` and `"search": "disabled"`.
Every other endpoint returns `501` with `{"error": {"code": "NOT_IMPLEMENTED", ...}}`. The UI shows
the navigation, a green "API 0.1.0" indicator, and a placeholder on each page naming its module.

After the backend runs, `npm run gen:api` (in `frontend`) regenerates `src/api/schema.d.ts` from
the live OpenAPI schema.

## Repository layout

```text
backend/   FastAPI app (package `subwise`), tests, Alembic, scripts
frontend/  React + Vite + TypeScript + Tailwind UI
docs/      blueprint, ADRs, roadmap, verified APIs, data sources, TA2 migration notes
data/      runtime files (SQLite DBs, fetched pages, logs) - never committed
scripts/   Windows PowerShell helpers
```

## Origin

SubWise grows out of the TA1/TA2 "Subscription Cost Optimizer" assignment
(`Sarthak0521/SubscriptionCostOptimitzer`), which stays untouched as the academic record. What was
reused, redesigned or dropped is in [`docs/ta2-migration.md`](docs/ta2-migration.md).
