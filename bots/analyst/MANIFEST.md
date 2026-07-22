# Manifest — analyst

This file is my context whitelist. The Conductor loads ONLY what it names, plus my Consumes docs and `bots/_SHARED/`.

## Identity (always load)
`prompts/analysis/repo-analyst.md` (a local `PROMPT.md` here overrides it if present)

## Pipeline position
- Phase: 3-analysis
- Consumes: `02-plan.md` + read access to the target repository
- Produces: `03-analysis.md` — sections: Impacted modules; Current-state findings; Dependencies (present / missing); Constraints
- Gate after me: no

## Knowledge
- Always load: (none yet)
- On demand: everything else in `references/` and `skills/`, requested through the Conductor

## Lessons
- Load: `LESSONS.md` → Approved section only
- Write: candidate lessons go to my Candidates section; only the human promotes
