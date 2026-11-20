"""Blueprint F.1: run_id is the ONLY LangGraph checkpoint key; user and thread IDs never are."""

from __future__ import annotations

import pytest

from subwise.agent.config import graph_config
from subwise.agent.graph import INTERRUPT_NODES, LLM_NODES, NODE_NAMES
from subwise.agent.state import initial_state
from subwise.ids import new_id
from subwise.memory.backends import store_namespace


def test_graph_config_uses_run_id_as_checkpoint_key() -> None:
    run_id, user_id = new_id("run"), new_id("usr")
    cfg = graph_config(run_id=run_id, user_id=user_id)
    assert cfg["configurable"]["thread_id"] == run_id
    assert cfg["configurable"]["user_id"] == user_id
    assert cfg["recursion_limit"] == 40


@pytest.mark.parametrize("wrong", ["thr_01ABC", "usr_01ABC", "demo", ""])
def test_graph_config_rejects_non_run_ids(wrong: str) -> None:
    with pytest.raises(ValueError):
        graph_config(run_id=wrong, user_id="usr_1")


def test_graph_config_rejects_non_user_ids() -> None:
    with pytest.raises(ValueError):
        graph_config(run_id="run_1", user_id="thr_1")


def test_ids_are_prefixed_and_unique() -> None:
    ids = {new_id("run") for _ in range(100)}
    assert len(ids) == 100 and all(i.startswith("run_") for i in ids)


def test_store_namespace_is_per_user() -> None:
    assert store_namespace("usr_1", "rejections") == ("users", "usr_1", "rejections")
    with pytest.raises(ValueError):
        store_namespace("", "rejections")


def test_initial_state_has_zeroed_loop_counters() -> None:
    s = initial_state(run_id="run_1", user_id="usr_1", thread_id="thr_1", user_message="hi")
    assert (s["clarification_count"], s["research_round"], s["revision_count"]) == (0, 0, 0)
    assert s["trace"] == [] and s["mode"] == "balanced"


def test_graph_node_inventory_matches_blueprint() -> None:
    assert len(NODE_NAMES) == 12
    assert {"parse_intent", "decide", "explain"} == LLM_NODES
    assert set(NODE_NAMES) >= INTERRUPT_NODES
