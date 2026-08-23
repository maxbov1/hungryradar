# Agent Instructions

## Repository Overview

HungryRadar is a restaurant availability concierge. Google Places owns canonical place metadata. Reservation sources own reservation and waitlist facts. Google visit data is a secondary wait-risk signal when no reservation is available.

## High-Risk Areas

Provider boundaries, wait-time interpretation, and lifecycle graph gates can create misleading recommendations if they silently invent data or skip required evidence.

## Required constraints

- Keep vendor SDKs inside adapters.
- Keep product rules deterministic and testable without network access.
- Do not treat missing visit data as a short wait.
- Do not present historical wait estimates as live guarantees.
- Keep source links and checked timestamps with external facts.
- Treat the graph as the agent investigation lifecycle, with explicit gates and backtracking targets.
- Do not let Strands skip lifecycle gates or turn missing evidence into a positive fact.
- Do not add a graph database dependency until a real persistence or visualization need requires it.

## Preferred workflow

Run `PYTHONPATH=src python -m unittest discover -s tests` before handing off changes. Keep new modules small and update `ARCHITECTURE.md` when adding a provider, orchestration layer, or persistence boundary.
