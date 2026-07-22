# Bot Roster — the pipeline's agents

**The folder is the bot.** Each agent lives under `bots/<name>/`: its `MANIFEST.md` (context whitelist), `references/` (knowledge you drop in), `skills/` (optional procedures), and `LESSONS.md` (learned heuristics — Approved loads, Candidates await human promotion). The Conductor (`CONDUCTOR.md`) spawns each phase as a fresh, isolated subagent loaded with exactly what the manifest names + the upstream doc(s) it consumes + `bots/_SHARED/`. Nothing else. Handoff contract: `SCHEMAS.md`.

## The rule every bot obeys

Get your whitelisted payload + Consumes doc(s) → do your job → return your output doc (header + required sections) + optional candidate lessons → the Conductor commits and advances `STATE.md`. Nothing rides in session memory.

## Roster

| Phase | Folder | Identity prompt | Consumes | Produces | Gate |
|---|---|---|---|---|---|
| 1 Prompt Smith | `bots/prompt-smith/` | `sdlc-prompt-smith` skill | `00-request.md` | `01-prompt.md` | **Yes** |
| 2 Planning | `bots/planner/` | `prompts/planning/project-planner.md` | `01-prompt.md` | `02-plan.md` | optional |
| 3 Analysis | `bots/analyst/` | `prompts/analysis/repo-analyst.md` | `02-plan.md` + repo | `03-analysis.md` | no |
| 4 Design | `bots/architect/` | `prompts/architecture/system-architect.md` | `02-plan.md` + `03-analysis.md` | `04-design.md` | **Yes** |
| 5 Implementation | `bots/implementer/` | `prompts/implementation/feature-implementer.md` | `04-design.md` | `05-impl.md` + code/PR | no |
| — Review (PR gate) | `bots/reviewer/` | `prompts/code-review/generic-pr-review.md` | PR diff + `05-impl.md` + `04-design.md` | review verdict | bot gate |
| 6 Testing | `bots/tester/` | `prompts/testing/test-verifier.md` | `05-impl.md` + `04-design.md` | `06-test.md` | if red |
| — Docs (as-built) | `bots/doc-writer/` | `prompts/documentation/doc-writer.md` | `05-impl.md` + `06-test.md` | `docs/**` | no |
| 7 Deployment | `bots/release/` | `prompts/release/release-manager.md` | `06-test.md` + `05-impl.md` | `07-release.md` | **Yes** |
| 8 Maintenance | `bots/maintenance/` | `prompts/maintenance/maintenance-triager.md` | `07-release.md` + signals | `08-maint.md` | triage |

## Why folders

- **Unbiased:** the manifest is a hard whitelist — a cross-stage leak now requires a visible manifest edit in a git diff.
- **Effective:** enrich any bot by dropping files into its `references/` or `skills/` — no prompt surgery, no Conductor edits.
- **Learning:** each bot may propose lessons to its own Candidates; only the human promotes to Approved, and only Approved loads.
- **Efficient:** manifests mark always-load vs on-demand so context stays lean; the shared contract lives once in `bots/_SHARED/`; identity prompts stay single-source in `prompts/` (local `PROMPT.md` overrides per pipeline if ever needed).

## Build-out order (why)

Design → Implementation → Review → Testing → Docs → Release: follow the runtime data flow so every bot is smoke-tested against real upstream artifacts, front-loading the two loop-backs (review→impl, red-test→planning) because they are the riskiest control paths, deferring the linear and irreversible stages to last. Analysis and Maintenance folders start thin and grow as their references fill in.
