"""Opt-in: needs a running Ollama with the configured model.  Run:  pytest -m llm

Verifies the structured-output path the gateway will use (blueprint revision 6). The full
30-request evaluation set arrives with M7.
"""

from __future__ import annotations

import ollama
import pytest
from pydantic import BaseModel

from subwise.config import Settings

pytestmark = pytest.mark.llm


class Intent(BaseModel):
    categories: list[str]
    budget_rupees: int | None


def test_qwen_returns_schema_valid_json() -> None:
    s = Settings()
    client = ollama.Client(host=s.ollama_host, timeout=s.llm_timeout_s)
    resp = client.chat(
        model=s.ollama_model,
        messages=[
            {"role": "system", "content": "Extract the request as JSON. Use only given facts."},
            {"role": "user", "content": "I watch movies and listen to music. Budget ₹1000."},
        ],
        format=Intent.model_json_schema(),
        options={"temperature": 0},
    )
    intent = Intent.model_validate_json(resp.message.content or "")
    assert intent.categories
