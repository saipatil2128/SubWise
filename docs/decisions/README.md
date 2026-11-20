# Architecture decision records

| ADR | Decision | Status |
| --- | --- | --- |
| [001](ADR-001-llm-scope.md) | The LLM parses intent, picks guarded actions and explains; it never produces numbers | Accepted |
| [002](ADR-002-identifiers.md) | `user_id` / `thread_id` / `run_id`; run_id is LangGraph's checkpoint key | Accepted |
| [003](ADR-003-research-and-evidence.md) | Three research tiers; prices bound on five dimensions | Accepted (v2) |
| [004](ADR-004-memory-split.md) | Form data in app.db, agent-learned data in the LangGraph store | Accepted |
| [005](ADR-005-optimizer.md) | OAVOE as a lexicographic ILP on PuLP 3.3.2 + CBC; exclusion groups, not providers | Accepted (v2) |
| [006](ADR-006-ollama-client.md) | Official `ollama` client instead of `langchain-ollama` | Accepted (new in Phase 1) |
| [007](ADR-007-optional-search.md) | Search is optional; NullSearchProvider by default | Accepted (v2) |
| [008](ADR-008-frontend-toolchain.md) | TypeScript 5.9, no ESLint yet, Recharts deferred | Accepted (new in Phase 1) |
| [009](ADR-009-phase1-structure.md) | Small structural deviations from blueprint section L | Accepted (new in Phase 1) |
| [010](ADR-010-full-build.md) | Full build: no seeded prices, price labels, factory mode, SSE, worker, E2E | Accepted |

New decisions: copy the format, number sequentially, and add the ADR **before** the code.
