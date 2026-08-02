# Pipeline Index

Machine-maintained index of SDLC pipeline artifacts. One row per feature per stage.
Written by pipeline bots - do not edit by hand.

## Architecture stage

| feature_id | status | spec | ADRs | chosen option | requirements source | updated |
|---|---|---|---|---|---|---|
| wallcovering-takeoff | COMPLETE | [architecture_spec.json](architecture/wallcovering-takeoff/architecture_spec.json) | [ADR-001...ADR-012](architecture/wallcovering-takeoff/adr/) | OPT-1 - single-process layered desktop monolith with a pure math core | `requirements/wallcovering-takeoff/plan.md` (see note) | 2026-08-02 |

### Accepted ADRs - wallcovering-takeoff

| ADR | Title | Status |
|---|---|---|
| ADR-001 | Single-process layered desktop monolith with a pure core | ACCEPTED |
| ADR-002 | Set-read and compute are separate modules with a one-way dependency | ACCEPTED |
| ADR-003 | Deterministic exact arithmetic via Decimal in a pure math core | ACCEPTED |
| ADR-004 | All reading enters through a pluggable ExtractionPort; manual entry is the v1 adapter | ACCEPTED |
| ADR-005 | Flag rather than guess, with blocking flags gating computation | ACCEPTED |
| ADR-006 | Waste is applied exactly once, structurally separate from repeat loss | ACCEPTED |
| ADR-007 | Per-WC unit fidelity with no cross-unit conversion path | ACCEPTED |
| ADR-008 | Rooms model an explicit wall set; wall-level tags override room-level defaults | ACCEPTED |
| ADR-009 | Wall identity is (room_id, wall_id) and drives cross-sheet de-duplication | ACCEPTED |
| ADR-010 | Takeoff policy is explicit configuration captured as a snapshot per result | ACCEPTED |
| ADR-011 | Machine-read values are provisional until confirmed, enforced by a finalisation gate | ACCEPTED |
| ADR-012 | Every computed number is registered in a trace ledger | ACCEPTED |

> **Note on the requirements source for `wallcovering-takeoff`.** The contracted upstream input
> `requirements/wallcovering-takeoff/handoff.json` does not exist. On explicit orchestrator instruction the
> architecture stage consumed `requirements/wallcovering-takeoff/plan.md` instead. That document is markdown rather
> than a schema-valid `requirements_artifact`, but it carries stable requirement ids (FR-1...FR-8, NFR-1...NFR-4) with
> Given/When/Then acceptance criteria, so traceability is preserved. Its open questions Q1-Q7 were adopted as
> explicit assumptions ARCH-A2...ARCH-A8 using the planner's own stated recommendations. The planner stage should
> backfill a conforming `handoff.json` so downstream stages validate at the boundary.
