# What came from TA1/TA2 (`Sarthak0521/SubscriptionCostOptimitzer` @ `731edeb`)

The old repository is the academic record and is **not modified**. Nothing was copied wholesale.
Concepts were re-implemented under the blueprint's rules (blueprint section B.4).

| Old component | Verdict | Where it lives in SubWise |
| --- | --- | --- |
| TA1 `compare_plans` equal-cost sentence | Reused (concept + exact text) | `core/costing.EQUAL_COST_MESSAGE`, test `test_ta1_equal_cost_sentence_preserved_verbatim`; full behaviour in M5 |
| `safety.py` finite/non-negative checks | Refactored | `core/money.Paise` (non-negative, capped) + Pydantic validators |
| `deterministic_recommendation()` | Refactored | `llm/fallbacks.render_template_report` (M7) |
| `safe_execute()` | Refactored | `@guarded_tool` wrapper (M8/M10) |
| `recommendation_decisions` audit table | Redesigned | `approval_decisions` (M2), keyed by run_id + user_id + report version |
| JSONL traces | Redesigned | `run_events` table + SSE (M11) |
| `human_approval()` with `input()` | Redesigned | LangGraph `interrupt()` + `Command(resume=…)`, verified in contract tests |
| Rule-based supervisor + `MAX_HOPS` | Redesigned | Graph with per-loop counters (`RunState`) + `recursion_limit` |
| `cost_analyst.py` (LLM multiplies by 12) | Discarded | — |
| `plan_evaluator.py` pattern (facts in Python, LLM explains) | Kept as a pattern | `explain` node + `check_numbers` |
| Negotiator node | Discarded | Its cross-check becomes `check_numbers` |
| `memory_store.py` | Discarded | — |
| `memory/memory_manager.py` | Refactored | `memory/backends.py` (M9), namespace `("users", user_id, kind)` |
| `rag_store.py` + fictional catalogue | Later | May be re-pointed at official terms pages after M14 (refund and cancellation rules) |
| `tests/main_safety.py` | Not reused | It tested copies of functions; SubWise tests import real modules |

Bugs fixed by design: thread ID used as user ID; each run overwrote the last in one checkpoint
thread; long-term memory never written; `langgraph-checkpoint-sqlite` missing from requirements;
side effects at import time; float money; README drift.
