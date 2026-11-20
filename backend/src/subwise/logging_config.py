"""Structured JSON logging with request IDs (blueprint J.1). Configured in the app lifespan,
never at import time."""

from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
from datetime import UTC, datetime
from pathlib import Path

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def configure_logging(logs_dir: Path, level: str = "INFO") -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("subwise")
    if any(getattr(h, "_subwise", False) for h in root.handlers):
        return
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(JsonFormatter())
    file_handler._subwise = True  # type: ignore[attr-defined]
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    console._subwise = True  # type: ignore[attr-defined]
    root.addHandler(file_handler)
    root.addHandler(console)
    root.setLevel(level)
