"""Architecture rules from AGENTS.md, enforced by reading source files (no imports needed)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[2] / "src" / "subwise"

PURE_DIRS = ("core", "domain")
FORBIDDEN_IN_PURE = {
    "fastapi", "starlette", "httpx", "requests", "sqlalchemy", "ollama", "langgraph",
    "langchain", "langchain_core", "bs4", "playwright", "tavily", "sse_starlette",
}  # fmt: skip


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


PURE_FILES = sorted(p for d in PURE_DIRS for p in (PKG / d).rglob("*.py"))


@pytest.mark.parametrize("path", PURE_FILES, ids=lambda p: str(p.relative_to(PKG)))
def test_pure_layers_import_no_io_libraries(path: Path) -> None:
    bad = _imports(path) & FORBIDDEN_IN_PURE
    assert not bad, f"{path.name} imports I/O libraries {bad}; core/ and domain/ must stay pure"


def test_only_llm_gateway_imports_ollama() -> None:
    offenders = [
        p.relative_to(PKG)
        for p in PKG.rglob("*.py")
        if "ollama" in _imports(p) and p != PKG / "llm" / "gateway.py"
    ]
    assert not offenders


def test_only_agent_config_builds_configurable_dicts() -> None:
    offenders = [
        p.relative_to(PKG)
        for p in PKG.rglob("*.py")
        if '"configurable"' in p.read_text(encoding="utf-8") and p.name != "config.py"
    ]
    assert not offenders, "Build LangGraph configs only with subwise.agent.config.graph_config"


def test_no_float_money_fields() -> None:
    for p in PKG.rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                if "paise" in name and "float" in ast.unparse(node.annotation):
                    pytest.fail(f"{p.name}: money field {name} annotated as float")
