# ADR-005: Optimizer library and constraint model

Date: 2026-11-21 · Status: Accepted

## Context

The blueprint assumed PuLP bundles CBC. Verification showed PuLP 4.x bundles **no** solver and changed its modelling API (`LpVariable(..., cat=...)` is gone in favour of `prob.add_variable`). Blueprint v1's "one plan per provider group" constraint would also block valid combinations such as Prime + Amazon Music Unlimited.

## Decision

Pin `pulp==3.3.2`, which bundles CBC for Windows, Linux and macOS and keeps the widely documented API. Constraints use declared **exclusion groups** (tiers, cycles and variants of one service line), add-on prerequisites and eligibility gates. A provider never forms an exclusion group. Bundles are ordinary plans whose features are the union of their entitlements. Upgrade path: PuLP 4 + `pulp[cbc]` (cbcbox has Windows wheels), via a new ADR.

## Consequences

+ Works offline on Windows with pip alone. − PuLP 3.3 emits deprecation notices (filtered in tests); a future migration is needed.
