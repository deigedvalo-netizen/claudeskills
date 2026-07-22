# Bot Roster — the pipeline's downstream agents

This is the readable plan for the agents that run **after** Stage 1 Prompt Smith. It reconciles the "design the remaining bots" work to this repo's existing 8-phase model in `ARCHITECTURE.md` / `SCHEMAS.md` — the canonical flow stays 8 phases; nothing here forks it. Each phase worker is one general subagent driven by a phase-specific system prompt stored under `prompts/<stage>/`. Full design rationale (guardrails, acceptance criteria, orphan check) lives in the Project doc `sdlc-bot-pipeline.md`.

## The rule every bot obeys

Read your upstream doc(s) named in the `Consumes` cell + `STATE.md` → do your job → write your output doc with the `SCHEMAS.md` header + sections → update your row in `STATE.md` → commit both. Nothing rides in session memory (see `README.md`).

## Roster

| Phase | Bot (prompt) | Consumes | Produces | Human gate |
|---|---|---|---|---|
| 2 Planning | `planning/project-planner` | `01-prompt.md` | `02-plan.md` | optional |
| 3 Analysis | (analysis instruction) + GitHub | `02-plan.md` + repo | `03-analysis.md` | no |
| 4 Design | `architecture/system-architect` | `02-plan.md` + `03-analysis.md` | `04-design.md` | **Yes** |
| 5 Implementation | `implementation/feature-implementer` | `04-design.md` | `05-impl.md` + code | no |
| — Review (per-PR) | `code-review/generic-pr-review` | PR diff + `05-impl.md` + `04-design.md` | review verdict | no (bot gate) |
| 6 Testing | `testing/test-verifier` | `05-impl.md` + `04-design.md` | `06-test.md` | if red |
| — Docs (as-built) | `documentation/doc-writer` | `05-impl.md` + `06-test.md` | docs | no |
| 7 Deployment | `release/release-manager` | `06-test.md` (green) + `05-impl.md` | `07-release.md` | **Yes** |
| 8 Maintenance | (maintenance instruction) + Issues | `07-release.md` + signals | `08-maint.md` | triage |

## Reconciliation notes (earlier roster → this repo)

- **Orchestrator = the Conductor** already in `CONDUCTOR.md`; not a new bot. It owns `STATE.md`, the three gates, and loop-backs.
- **Reviewer and Doc-writer** are not separate phases in the 8-phase table — they are reusable **library prompts** (like the existing `ts-pr-review`) invoked within/alongside Implementation and Testing. This keeps the canonical flow unchanged while filling the review/docs gap.
- **Analysis (3)** and **Maintenance (8)** keep their existing phase instructions; no new prompt added here.
- **Loop-backs** follow this repo, not the earlier draft: a **red test report routes to Stage 2 Planning** and Maintenance findings route via `ROUTER.md`. Circuit-breaker: escalate to a human rather than loop forever.

## Build order (why)

1. **Design (system-architect)** — Planning already exists and feeds it; unblocks a real handoff first.
2. **Implementation (feature-implementer)** — first executable artifact; needs the design.
3. **Review (generic-pr-review)** — needs a real PR; activates the first quality gate.
4. **Testing (test-verifier)** — activates the red→Planning loop-back.
5. **Docs (doc-writer)** — linear, low-risk; after the loops are proven.
6. **Deployment (release-manager)** — last; the only irreversible action, behind the ship gate.
