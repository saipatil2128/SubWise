# Verified dependency versions and API contracts

Verified on 2026-11-21 by installing the exact pins and running
`backend/tests/integration/test_library_contracts.py` on Python 3.12.13 and 3.13.18 (Linux),
with plain `pip` and with `uv`. The full dependency tree (90 packages, including the `dev` and
`search` extras) was resolved with **Windows-only binary wheels** for Python 3.12 and 3.13, so no C
compiler is needed on Windows. CI repeats the tests on `windows-latest`.

Re-run after any pin change: `cd backend; pytest tests/integration -q`.

## Backend pins (`backend/pyproject.toml`)

| Package | Pin | Why this version / notes |
| --- | --- | --- |
| fastapi | 0.165.0 | Latest at verification. Note: `app.routes` now holds lazy `_IncludedRouter` objects; enumerate endpoints via `app.openapi()["paths"]` |
| uvicorn | 0.54.0 | Plain install (no `[standard]`, avoids uvloop which has no Windows build) |
| pydantic / pydantic-settings | 2.14.4 / 2.16.3 | v2 API; PEP 695 generics (`class Page[T](BaseModel)`) work |
| email-validator | 2.4.0 | Needed by `EmailStr` |
| sqlalchemy / alembic | 2.1.9 / 1.20.1 | `alembic upgrade head` verified against an empty SQLite DB; `render_as_batch=True` for SQLite |
| langgraph | 1.2.24 | Pulls langgraph-checkpoint 4.3.2, langchain-core 1.8.4 |
| langgraph-checkpoint-sqlite | 3.1.3 | Provides **both** `SqliteSaver` and `SqliteStore` (TA2 forgot this package) |
| ollama | 0.6.3 | Official client; used directly instead of `langchain-ollama` (ADR-006) |
| pulp | **3.3.2** | Bundles CBC incl. `win/i64/cbc.exe`. **PuLP 4.x bundles no solver and changed the modelling API** (ADR-005) |
| httpx | 0.28.1 | Fetching and Ollama transport |
| beautifulsoup4 / lxml | 4.15.0 / 6.1.3 | lxml has Windows wheels |
| pwdlib[argon2] / pyjwt | 0.4.2 / 2.15.1 | Auth (M3) |
| python-ulid | 4.2.0 | Prefixed IDs (`run_…`, `usr_…`) |
| sse-starlette | 3.7.0 | SSE (M11) |
| tavily-python *(extra `search`)* | 0.8.5 | Optional |
| playwright *(extra `browser`)* | 1.65.2 | Optional; then `python -m playwright install chromium` |
| pytest, pytest-cov, respx, hypothesis, freezegun, ruff, mypy *(extra `dev`)* | 9.2.0, 7.1.0, 0.23.1, 6.170.17, 1.5.5, 0.17.6, 2.4.1 | |

Python: **3.12 recommended** (`requires-python = ">=3.12,<3.14"`).

## Frontend pins (`frontend/package.json`)

React 19.3.1 · react-router 8.5.2 · @tanstack/react-query 5.108.2 · Vite 8.3.8 ·
@vitejs/plugin-react 6.3.0 · Tailwind CSS 4.3.5 (`@tailwindcss/vite`) · Vitest 5.1.1 · jsdom 31.0.1 ·
@testing-library/react 16.3.3 · openapi-typescript 7.13.0 · **TypeScript 5.9.3**.
TypeScript 7.0.2 is newer but conflicts with openapi-typescript's `typescript@^5` peer (ADR-008).
Recharts is deferred until M13 needs it.

## LangGraph: checkpoint, interrupt, resume (langgraph 1.2.24 + checkpoint-sqlite 3.1.3)

```python
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command

conn = sqlite3.connect(path, check_same_thread=False)    # long-lived worker thread
graph = builder.compile(checkpointer=SqliteSaver(conn))
# or, short-lived:  with SqliteSaver.from_conn_string(path) as saver: ...

out = graph.invoke(initial_state, config)       # config = graph_config(run_id=..., user_id=...)
"__interrupt__" in out                           # True when paused; list[Interrupt(value=..., id=...)]
graph.get_state(config).next                     # ("approval",) while paused, () when finished
graph.get_state(config).interrupts               # (Interrupt(value=payload, ...),)
graph.invoke(Command(resume={"decision": "approved"}), config)   # value is returned by interrupt()
```

Verified behaviours (each has a test):

- A run paused at `interrupt()` can be resumed **from a new process** that recompiles the graph over
  the same SQLite file (backend restart, blueprint K.2 case 12).
- On resume the interrupted node **runs again from its first line**. Code before `interrupt()`
  executes twice, so it must be side-effect-free (AGENTS.md rule 7).
- `Annotated[list[...], operator.add]` reducers accumulate across nodes.
- `Interrupt` objects in 1.2.x also carry `id` and `response_schema` fields.

## LangGraph store (long-term memory)

```python
from langgraph.store.sqlite import SqliteStore
with SqliteStore.from_conn_string(path) as store:
    store.setup()                                         # idempotent
    store.put(("users", user_id, "rejections"), key, {"reason": "..."})
    store.get(ns, key)            # -> Item | None  (item.value is the dict)
    store.search(("users", user_id))                      # prefix search across kinds
    store.delete(ns, key)
```

Verified: data written in one process is read in another; the namespace prefix isolates users.

## Ollama structured output (ollama 0.6.3)

```python
import ollama
client = ollama.Client(host="http://localhost:11434", timeout=60)   # default timeout is None!
resp = client.chat(
    model="qwen2.5:3b",
    messages=[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
    format=RequestSpec.model_json_schema(),   # format: '' | 'json' | dict (JSON schema)
    options={"temperature": 0},
)
spec = RequestSpec.model_validate_json(resp.message.content)
```

Verified: `format` accepts a JSON-schema dict; the `timeout` kwarg reaches the underlying
`httpx.Client`; an unreachable server raises the built-in `ConnectionError` (the gateway must map it
to `LLMUnavailable`); `ollama.ResponseError` / `ollama.RequestError` exist for server and request
errors. Schema-constrained output needs an Ollama **server ≥ 0.5**; `check_env.py` prints the
server version. Still to measure with a real server (M7, `pytest -m llm`): how often Qwen 2.5 3B
returns schema-valid, semantically correct output.

## PuLP / CBC

```python
import pulp
solver = pulp.PULP_CBC_CMD(msg=False)            # bundled CBC; available() is True on Windows/Linux/macOS
prob = pulp.LpProblem("oavoe", pulp.LpMaximize)
x = pulp.LpVariable("x_netflix_basic", cat="Binary")
```

PuLP 3.3.2 prints deprecation notices pointing to its 4.0 API; they are filtered in pytest config.
Upgrade path (needs a new ADR): `pulp[cbc]` 4.x with `cbcbox` (Windows wheel exists) and
`prob.add_variable(...)`.
