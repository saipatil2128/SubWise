"""Contract tests for the exact library behaviour SubWise relies on (blueprint revision 6).

If a dependency upgrade breaks one of these, the blueprint/ADR must be revisited before the pin
changes. They run offline: no Ollama server, no network.
"""

from __future__ import annotations

import inspect
import operator
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Annotated, TypedDict

import httpx
import ollama
import pulp
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.sqlite import SqliteStore
from langgraph.types import Command, interrupt
from pydantic import BaseModel

from subwise.agent.config import as_runnable_config, graph_config

RUN_ID, USER_ID = "run_contract", "usr_contract"


# ------------------------------------------------------------------ LangGraph checkpoints
class _S(TypedDict):
    log: Annotated[list[str], operator.add]
    decision: str


def _before(state: _S) -> dict[str, object]:
    return {"log": ["before"]}


def _approval(state: _S) -> dict[str, object]:
    value = interrupt({"report_id": "rep_1"})
    return {"log": ["resumed"], "decision": value["decision"]}


def _build(checkpointer: object) -> object:
    g = StateGraph(_S)
    g.add_node("before", _before)
    g.add_node("approval", _approval)
    g.add_edge(START, "before")
    g.add_edge("before", "approval")
    g.add_edge("approval", END)
    return g.compile(checkpointer=checkpointer)  # type: ignore[arg-type]


def test_interrupt_pauses_and_checkpoint_exposes_pending_node(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "cp.db", check_same_thread=False)
    graph = _build(SqliteSaver(conn))
    cfg = as_runnable_config(graph_config(run_id=RUN_ID, user_id=USER_ID))
    out = graph.invoke({"log": [], "decision": ""}, cfg)  # type: ignore[attr-defined]
    assert "__interrupt__" in out
    state = graph.get_state(cfg)  # type: ignore[attr-defined]
    assert state.next == ("approval",)
    assert [i.value for i in state.interrupts] == [{"report_id": "rep_1"}]
    conn.close()


RESUME_SCRIPT = textwrap.dedent(
    """
    import sys
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.types import Command
    sys.path.insert(0, sys.argv[2])
    from test_library_contracts import _build, RUN_ID, USER_ID
    from subwise.agent.config import as_runnable_config, graph_config
    cfg = as_runnable_config(graph_config(run_id=RUN_ID, user_id=USER_ID))
    with SqliteSaver.from_conn_string(sys.argv[1]) as cp:
        g = _build(cp)
        assert g.get_state(cfg).next == ("approval",), "pending interrupt lost across restart"
        out = g.invoke(Command(resume={"decision": "approved"}), cfg)
        assert out["log"] == ["before", "resumed"], out
        assert out["decision"] == "approved"
        assert g.get_state(cfg).next == ()
    print("RESUMED_OK")
    """
)


def test_resume_in_a_fresh_process_after_restart(tmp_path: Path) -> None:
    """Blueprint K.2 case 12: a paused run survives a backend restart."""
    db = tmp_path / "cp.db"
    conn = sqlite3.connect(db, check_same_thread=False)
    graph = _build(SqliteSaver(conn))
    cfg = as_runnable_config(graph_config(run_id=RUN_ID, user_id=USER_ID))
    graph.invoke({"log": [], "decision": ""}, cfg)  # type: ignore[attr-defined]
    conn.close()

    script = tmp_path / "resume.py"
    script.write_text(RESUME_SCRIPT, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script), str(db), str(Path(__file__).parent)],
        capture_output=True, text=True, timeout=120, check=False,
    )  # fmt: skip
    assert result.returncode == 0, result.stderr
    assert "RESUMED_OK" in result.stdout


def test_node_body_reexecutes_from_start_on_resume() -> None:
    """Why AGENTS.md forbids side effects before interrupt() in a node."""
    calls = {"n": 0}

    class S(TypedDict):
        x: int

    def node(state: S) -> dict[str, int]:
        calls["n"] += 1
        interrupt("ok?")
        return {"x": 1}

    g = StateGraph(S)
    g.add_node("n", node)
    g.add_edge(START, "n")
    g.add_edge("n", END)
    graph = g.compile(checkpointer=InMemorySaver())
    cfg = as_runnable_config(graph_config(run_id=RUN_ID, user_id=USER_ID))
    graph.invoke({"x": 0}, cfg)  # type: ignore[arg-type]
    graph.invoke(Command(resume=True), cfg)  # type: ignore[arg-type]
    assert calls["n"] == 2


# ------------------------------------------------------------------ LangGraph store
STORE_READ_SCRIPT = textwrap.dedent(
    """
    import sys
    from langgraph.store.sqlite import SqliteStore
    with SqliteStore.from_conn_string(sys.argv[1]) as store:
        item = store.get(("users", "usr_1", "rejections"), "plan_9")
        assert item is not None and item.value == {"reason": "needs TV"}, item
        assert [i.key for i in store.search(("users", "usr_1"))] == ["plan_9"]
        assert store.search(("users", "usr_2")) == []
        store.delete(("users", "usr_1", "rejections"), "plan_9")
        assert store.get(("users", "usr_1", "rejections"), "plan_9") is None
    print("STORE_OK")
    """
)


def test_store_survives_new_process_and_is_isolated_per_user(tmp_path: Path) -> None:
    """Blueprint K.2 case 11."""
    db = tmp_path / "memory.db"
    with SqliteStore.from_conn_string(str(db)) as store:
        store.setup()
        store.put(("users", "usr_1", "rejections"), "plan_9", {"reason": "needs TV"})
    script = tmp_path / "read.py"
    script.write_text(STORE_READ_SCRIPT, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script), str(db)], capture_output=True, text=True, timeout=60,
        check=False,
    )  # fmt: skip
    assert result.returncode == 0, result.stderr
    assert "STORE_OK" in result.stdout


# ------------------------------------------------------------------ Ollama client
class _Spec(BaseModel):
    categories: list[str]


def test_ollama_chat_accepts_json_schema_in_format() -> None:
    annotation = str(inspect.signature(ollama.Client.chat).parameters["format"].annotation)
    assert "dict" in annotation and "json" in annotation
    assert _Spec.model_json_schema()["type"] == "object"


def test_ollama_client_timeout_reaches_httpx() -> None:
    client = ollama.Client(host="http://127.0.0.1:9", timeout=7.5)
    inner = client._client
    assert isinstance(inner, httpx.Client)
    assert inner.timeout.read == 7.5


def test_ollama_unreachable_server_raises_connection_error() -> None:
    client = ollama.Client(host="http://127.0.0.1:9", timeout=2)
    try:
        client.list()
    except ConnectionError:
        pass  # what the gateway must translate into LLMUnavailable
    else:  # pragma: no cover
        raise AssertionError("expected ConnectionError when Ollama is not running")


def test_ollama_error_types_exist() -> None:
    assert issubclass(ollama.ResponseError, Exception)
    assert issubclass(ollama.RequestError, Exception)


# ------------------------------------------------------------------ PuLP / CBC
def test_pulp_bundled_cbc_solves_binary_program() -> None:
    assert pulp.__version__.startswith("3."), "PuLP 4.x has no bundled solver (ADR-005)"
    solver = pulp.PULP_CBC_CMD(msg=False)
    assert solver.available()
    prob = pulp.LpProblem("contract", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x{i}", cat="Binary") for i in range(3)]
    prob += pulp.lpSum(x)
    prob += 2 * x[0] + 3 * x[1] + 4 * x[2] <= 5
    assert pulp.LpStatus[prob.solve(solver)] == "Optimal"
    assert [v.value() for v in x] == [1.0, 1.0, 0.0]
