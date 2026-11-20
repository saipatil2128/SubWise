"""Opt-in: needs a running Ollama with the configured model.  Run:  pytest -m llm -rA

Evaluates Qwen 2.5 3B through SubWise's own gateway and intent schema on a small set of requests
with known answers. The LLM is only trusted for intent parsing, guarded decisions and wording; the
graph accepts an LLM budget only when the user typed one (``amount_stated``), which is checked here
too. The threshold is deliberately modest: a 3B model is not perfect, and every LLM call has a
deterministic fallback.
"""

from __future__ import annotations

import pytest

from subwise.agent.graph import IntentLLM
from subwise.config import Settings
from subwise.errors import SubWiseError
from subwise.llm.fallbacks import amount_stated
from subwise.llm.gateway import ChatMessage, OllamaGateway
from subwise.llm.prompts import PARSE_INTENT_SYSTEM

pytestmark = pytest.mark.llm

# (request, expected categories subset, expected monthly budget in rupees or None)
CASES: list[tuple[str, set[str], int | None]] = [
    ("I watch movies and listen to music. Budget ₹1000 a month.", {"video", "music"}, 1000),
    ("Keep cricket, I don't care about music. Spend under 500 rupees monthly.", {"video"}, 500),
    ("I only use Spotify. Can I pay less?", {"music"}, None),
    ("Cut my OTT bill, I mostly watch web series.", {"video"}, None),
    ("I want ad-free music and 4K movies for at most ₹800.", {"video", "music"}, 800),
    ("Which of my subscriptions overlap?", set(), None),
]


@pytest.fixture(scope="module")
def gateway() -> OllamaGateway:
    gw = OllamaGateway(Settings())
    health = gw.health()
    if not (health.reachable and health.model_present):
        pytest.skip(f"Ollama not ready: {health.model_dump()}")
    return gw


def test_intent_parsing_quality(gateway: OllamaGateway) -> None:
    valid = correct = 0
    report = []
    for text, cats, budget in CASES:
        try:
            out = gateway.call_structured(
                IntentLLM,
                [
                    ChatMessage(role="system", content=PARSE_INTENT_SYSTEM),
                    ChatMessage(role="user", content=text),
                ],
            )
        except SubWiseError as exc:
            report.append(f"INVALID  {text!r}: {exc.code.value}")
            continue
        valid += 1
        got_budget = (
            out.budget_rupees
            if out.budget_rupees and amount_stated(text, out.budget_rupees)
            else None
        )
        ok = cats.issubset(set(out.categories)) and got_budget == budget
        correct += ok
        report.append(
            f"{'OK ' if ok else 'BAD'}      {text!r}: categories={out.categories} budget={got_budget}"
        )
    print("\n" + "\n".join(report))
    print(f"schema-valid {valid}/{len(CASES)}, correct {correct}/{len(CASES)}")
    assert valid >= len(CASES) - 1  # structured output works
    assert correct >= len(CASES) * 2 // 3  # usable quality; failures fall back safely


def test_hallucinated_budget_is_rejected_by_guard() -> None:
    # The guard used by parse_intent: an amount the user never typed is not accepted.
    assert not amount_stated("Cut my OTT bill", 500)
    assert amount_stated("stay under ₹500", 500)
