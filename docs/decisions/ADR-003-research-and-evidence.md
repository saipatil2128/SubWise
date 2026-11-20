# ADR-003: Research tiers and evidence binding

Date: 2026-11-21 · Status: Accepted

## Context

Pricing pages are JS-heavy, region-dependent and sometimes off-limits to automation. Finding a number somewhere on an official page does not prove it is the right plan's monthly INR price for India.

## Decision

Tier 1: provider adapters on official India pricing URLs. Tier 2: cached/curated observations, with age labels. Tier 3: optional search-based discovery, `partial` at best. Every price carries a `PriceBinding` over five dimensions: provider (final URL's domain maps to exactly one provider), plan (name/alias in the same DOM block or text window, no other plan name in between), billing cycle (phrase attached to this amount, matching the plan), currency (₹/Rs/INR adjacent, no other currency on the page), and region (India URL + INR + fetch from India). Any unbound dimension → `unverified`, which the optimizer excludes by default.

## Consequences

+ Wrong-plan, wrong-cycle and wrong-region prices are caught. − Adapters need maintenance; some providers stay cache-only.
