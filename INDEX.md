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

## Implementation stage

| feature_id | status | modules | PRs | spec commit consumed | tests / CI | updated |
|---|---|---|---|---|---|---|
| wallcovering-takeoff | COMPLETE | 13 of 13 | [#1...#13](https://github.com/deigedvalo-netizen/claudeskills/pulls) (open, unmerged) | `0f420dd` | not authored (owned by test-bot / CI stage) | 2026-08-03 |

### Module branches - wallcovering-takeoff

| module_id | PR | branch | head commit | files | frozen signatures implemented |
|---|---|---|---|---|---|
| wctakeoff.resolve | [#1](https://github.com/deigedvalo-netizen/claudeskills/pull/1) | `impl/wallcovering-takeoff/wctakeoff.resolve` | `ba4cc19` | 3 | ResolveApplications |
| wctakeoff.geometry | [#2](https://github.com/deigedvalo-netizen/claudeskills/pull/2) | `impl/wallcovering-takeoff/wctakeoff.geometry` | `befd4b5` | 3 | ComputeWallArea |
| wctakeoff.math | [#3](https://github.com/deigedvalo-netizen/claudeskills/pull/3) | `impl/wallcovering-takeoff/wctakeoff.math` | `8cfc303` | 4 | SelectTakeoffMethod, ComputeQuantityStrip, ComputeQuantityArea |
| wctakeoff.domain | [#4](https://github.com/deigedvalo-netizen/claudeskills/pull/4) | `impl/wallcovering-takeoff/wctakeoff.domain` | `1f4bc60` | 7 | UpsertWCDefinition, GetWCDefinition |
| wctakeoff.aggregate | [#5](https://github.com/deigedvalo-netizen/claudeskills/pull/5) | `impl/wallcovering-takeoff/wctakeoff.aggregate` | `6a1f1b1` | 3 | AggregateByWC |
| wctakeoff.extraction | [#6](https://github.com/deigedvalo-netizen/claudeskills/pull/6) | `impl/wallcovering-takeoff/wctakeoff.extraction` | `2fb70bb` | 4 | ExtractionAdapter |
| wctakeoff.review | [#7](https://github.com/deigedvalo-netizen/claudeskills/pull/7) | `impl/wallcovering-takeoff/wctakeoff.review` | `56cd6be` | 3 | RaiseFlag, BlockingFlagsFor, ConfirmValue, IsTakeoffFinalisable |
| wctakeoff.ingest | [#8](https://github.com/deigedvalo-netizen/claudeskills/pull/8) | `impl/wallcovering-takeoff/wctakeoff.ingest` | `088f3c5` | 3 | IngestSheets, AssignSheetRole |
| wctakeoff.presentation | [#9](https://github.com/deigedvalo-netizen/claudeskills/pull/9) | `impl/wallcovering-takeoff/wctakeoff.presentation` | `aa554d5` | 4 | BuildTakeoffView, ExportTakeoff |
| wctakeoff.persistence | [#10](https://github.com/deigedvalo-netizen/claudeskills/pull/10) | `impl/wallcovering-takeoff/wctakeoff.persistence` | `3e2a8f1` | 3 | SaveProject, LoadProject |
| wctakeoff.policy | [#11](https://github.com/deigedvalo-netizen/claudeskills/pull/11) | `impl/wallcovering-takeoff/wctakeoff.policy` | `f95ce0b` | 2 | GetPolicySnapshot |
| wctakeoff.trace | [#12](https://github.com/deigedvalo-netizen/claudeskills/pull/12) | `impl/wallcovering-takeoff/wctakeoff.trace` | `0ac84f6` | 2 | RecordTrace, ExplainValue |
| wctakeoff.ui | [#13](https://github.com/deigedvalo-netizen/claudeskills/pull/13) | `impl/wallcovering-takeoff/wctakeoff.ui` | `e508bbe` | 8 | (none - empty public_interfaces) |

All 22 frozen `interface_signatures` implemented exactly once across 49 files. Zero unsatisfiable requirements,
so no `clarification_request` was raised. Build, typecheck and lint pass on every branch. All 13
`implementation_manifest` documents validate against `pipeline/handoff.schema.json`.

> **Merge order matters before the test stage.** Every `impl/` branch was cut from `main`, which carries no `src/`
> tree, so each branch contains only its own module and is not importable in isolation (for example
> `impl/wallcovering-takeoff/wctakeoff.math` has no `wctakeoff/domain/` package). The 13 branches touch 49 distinct
> paths with zero overlap, so they merge cleanly in any order - but test-bot must run against merged code, not
> against a single module branch.

> **Two files have no module owner.** `pyproject.toml` and `src/wctakeoff/__main__.py` appear in
> `downstream_contract.in_scope` but in no `module_boundaries[*].in_scope` list; the 13 `__init__.py` package markers
> are likewise covered only by the `src/wctakeoff/**` glob. On orchestrator instruction the implementation stage
> assigned `pyproject.toml` to `wctakeoff.domain` and `src/wctakeoff/__main__.py` to `wctakeoff.ui`. The architect
> stage should enumerate these explicitly if a different owner is intended.

> **Pinned wheels were not installable in the implementation sandbox.** Egress to pypi.org is denied there
> (HTTP 403 `host_not_allowed`), so PySide6 6.7.2, pydantic 2.8.2, Pillow 10.4.0 and reportlab 4.2.2 were not
> installed. Every version in `pyproject.toml` matches `technology_choices` exactly and the non-Qt tree was fully
> typechecked and smoke-tested, but the Qt widgets are syntax- and lint-verified only, not import-verified. The
> test stage must run in an environment that can install the pinned versions.
