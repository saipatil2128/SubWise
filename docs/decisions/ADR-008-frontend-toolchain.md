# ADR-008: Frontend toolchain

Date: 2026-11-21 · Status: Accepted

## Context

TypeScript 7.0.2 is the newest release, but `openapi-typescript@7.13.0` declares a `typescript@^5` peer.

## Decision

Pin TypeScript 5.9.3. Type-safety gate = `tsc --noEmit` in strict mode with `noUncheckedIndexedAccess`; no ESLint in Phase 1 (add via ADR if the team wants it). Recharts is added in M13 when a chart exists. API types are generated from the backend's OpenAPI (`npm run gen:api`).

## Consequences

+ Clean install, fewer moving parts. − Revisit TypeScript 7 when the generator supports it.
