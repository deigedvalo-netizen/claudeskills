# Handoff Contracts

Every artifact doc carries the same header, so a downstream phase reads only the immediately upstream doc + `STATE.md` — never the full history.

## Header (YAML frontmatter on every doc)

```yaml
---
req_id: REQ-2026-014          # stable across all 8 phases of one request
phase: 4-design               # who produced this doc
status: complete              # draft | complete | blocked | awaiting-gate
produced_by: design-subagent
produced_at: 2026-07-22T14:02-05:00
consumes: [02-plan.md, 03-analysis.md]   # explicit provenance
---
```

## Phase table

| Phase | Runs as | Consumes | Produces | Gate? |
|---|---|---|---|---|
| 1 Prompt Smith | `sdlc-prompt-smith` skill | `00-request.md` | `01-prompt.md` | **Yes** |
| 2 Planning | planner subagent | `01-prompt.md` | `02-plan.md` | optional |
| 3 Analysis | analysis subagent + GitHub | `02-plan.md` + repo | `03-analysis.md` | no |
| 4 Design | design subagent | `02-plan.md` + `03-analysis.md` | `04-design.md` | **Yes** |
| 5 Implementation | impl subagent + GitHub branch/PR | `04-design.md` | `05-impl.md` + code | no |
| 6 Testing | testing subagent + CI | `05-impl.md` + `04-design.md` | `06-test.md` | if red |
| 7 Deployment | deploy subagent + CI/CD | `06-test.md` (green) + `05-impl.md` | `07-release.md` | **Yes** |
| 8 Maintenance | maintenance subagent + Issues | `07-release.md` + signals | `08-maint.md` | triage |

Runner note: phases 2–8 are one general subagent driven by a phase-specific instruction, not eight installed skills. Only Stage 1 is a distinct skill.

## Required sections per doc (the contract — a phase may only read the sections it consumes)

- **00-request.md** → `Raw ask` · `Source` (human | maintenance-finding id)
- **01-prompt.md** → `Objective` · `Constraints` · `Acceptance criteria` · `Non-goals`
- **02-plan.md** → `Milestones` · `Acceptance criteria` (carried) · `Out of scope` · `Risks/unknowns`
- **03-analysis.md** → `Impacted modules` · `Current-state findings` · `Dependencies (present/missing)` · `Constraints`
- **04-design.md** → `Interfaces/API contract` · `Data/schema changes` · `Component diagram` · `Error cases` · `Test strategy`
- **05-impl.md** → `Branch` · `PR link` · `File map` · `Changelog` · `Deviations from design`
- **06-test.md** → `Tests added` · `Run results` · `Coverage` · `Open defects`
- **07-release.md** → `Version` · `Deploy steps` · `Rollback` · `Env/targets`
- **08-maint.md** → append-only list of `Finding{id, severity, repro, proposed request, route}`

Contract rule: if a needed fact isn't in the upstream doc, that's a contract bug — fix the upstream doc's sections, don't reach back two phases.
