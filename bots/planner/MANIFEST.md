# Manifest — planner

This file is my context whitelist. The Conductor loads ONLY what it names, plus my Consumes docs and `bots/_SHARED/`.

## Identity (always load)
`prompts/planning/project-planner.md` (a local `PROMPT.md` here overrides it if present)

## Pipeline position
- Phase: 2-plan
- Consumes: `01-prompt.md` (or `00-request.md` directly when routed from Maintenance per ROUTER.md)
- Produces: `02-plan.md` — sections: Milestones; Acceptance criteria (carried); Out of scope; Risks / unknowns
- Gate after me: optional

## Knowledge
- Always load: (none yet)
- On demand: everything else in `references/` and `skills/`, requested through the Conductor

## Lessons
- Load: `LESSONS.md` → Approved section only
- Write: candidate lessons go to my Candidates section; only the human promotes
