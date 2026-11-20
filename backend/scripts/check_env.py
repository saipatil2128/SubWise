"""Check that this machine can run SubWise. Works on Windows, macOS and Linux.

    python backend/scripts/check_env.py            # from the repo root, venv activated
    python backend/scripts/check_env.py --strict   # also fail if Ollama/the model is missing

Exit code 0 = required checks passed. Ollama, Node and Tavily are reported but optional
unless --strict (the app falls back to rule-based parsing and template reports without Ollama).
"""

from __future__ import annotations

import argparse
import importlib
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

OK, WARN, FAIL = "OK", "WARN", "FAIL"


@dataclass
class Check:
    name: str
    status: str
    detail: str


def _cmd_version(cmd: str) -> str | None:
    exe = shutil.which(cmd)
    if exe is None:
        return None
    try:
        out = subprocess.run(
            [exe, "--version"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else ""


def run_checks(strict: bool) -> list[Check]:
    checks: list[Check] = []
    v = sys.version_info
    py_ok = (3, 12) <= (v.major, v.minor) < (3, 14)
    checks.append(
        Check(
            "Python 3.12-3.13",
            OK if py_ok else FAIL,
            f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        )
    )

    for module in ("subwise", "fastapi", "langgraph", "langgraph.checkpoint.sqlite", "pulp"):
        try:
            importlib.import_module(module)
            checks.append(Check(f"import {module}", OK, "installed"))
        except ImportError as exc:
            checks.append(Check(f"import {module}", FAIL, f"{exc} (pip install -e backend[dev])"))

    try:
        import pulp

        cbc = pulp.PULP_CBC_CMD(msg=False).available()
        checks.append(Check("PuLP bundled CBC solver", OK if cbc else FAIL, pulp.__version__))
    except Exception as exc:  # report, never crash the checker
        checks.append(Check("PuLP bundled CBC solver", FAIL, str(exc)))

    try:
        from subwise.config import get_settings

        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=settings.data_dir):
            pass
        checks.append(Check("data dir writable", OK, str(settings.data_dir)))
    except Exception as exc:
        checks.append(Check("data dir writable", FAIL, str(exc)))
        return checks

    soft = FAIL if strict else WARN
    try:
        import httpx

        base = settings.ollama_host.rstrip("/")
        version = httpx.get(f"{base}/api/version", timeout=3).json().get("version", "?")
        tags = httpx.get(f"{base}/api/tags", timeout=5).json().get("models", [])
        names = {m.get("name", "") for m in tags} | {m.get("model", "") for m in tags}
        checks.append(Check("Ollama server", OK, f"{base} version {version} (needs >= 0.5)"))
        present = settings.ollama_model in names
        checks.append(
            Check(
                f"model {settings.ollama_model}",
                OK if present else soft,
                "pulled" if present else f"run: ollama pull {settings.ollama_model}",
            )
        )
    except Exception as exc:
        checks.append(
            Check("Ollama server", soft, f"not reachable at {settings.ollama_host} ({exc})")
        )

    for tool in ("node", "npm"):
        version = _cmd_version(tool)
        checks.append(
            Check(tool, OK if version else WARN, version or "not found (needed for the frontend)")
        )

    checks.append(
        Check(
            "Tavily search (optional)",
            OK,
            "enabled" if settings.search_enabled else "disabled (official URLs only)",
        )
    )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true", help="require Ollama and the model")
    args = parser.parse_args()
    checks = run_checks(args.strict)
    width = max(len(c.name) for c in checks)
    for c in checks:
        print(f"[{c.status:4}] {c.name.ljust(width)}  {c.detail}")
    failed = [c for c in checks if c.status == FAIL]
    print("\nResult:", "FAILED" if failed else "ready")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
