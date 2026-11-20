# ADR-009: Phase 1 structural deviations from blueprint section L

Date: 2026-11-21 · Status: Accepted

## Context

Building the scaffold surfaced small layout improvements.

## Decision

(1) `errors.py` holds pure exception classes; HTTP rendering moved to `api/error_handlers.py` so `core/` can raise errors without importing FastAPI. (2) New `domain/` package for shared Pydantic models and enums (catalog, evidence, request, optimisation), pure like `core/`. (3) New `ids.py` for prefixed IDs. (4) `logging.py` will be named `logging_config.py` (M1) to avoid confusion with the stdlib module. (5) `backend/README.md` exists because current setuptools refuses a readme outside the package directory. (6) Windows helpers live in `scripts/*.ps1` at the repo root; Python helpers in `backend/scripts/`.

## Consequences

+ Layer rules are testable (`tests/unit/test_architecture.py`). − Section L of the blueprint is updated to match.
