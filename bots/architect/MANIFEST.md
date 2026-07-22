# Manifest — architect

This file is my context whitelist. The Conductor loads ONLY what it names, plus my Consumes docs and `bots/_SHARED/`.

## Identity (always load)
`prompts/architecture/system-architect.md` (a local `PROMPT.md` here overrides it if present)

## Pipeline position
- Phase: 4-design
- Consumes: `02-plan.md`, `03-analysis.md`
- Produces: `04-design.md` — sections: Interfaces / API contract; Data / schema changes; Component diagram; Error cases; Test strategy
- Gate after me: yes (human: "right approach?")

## Knowledge
- Always load: (none yet — ADR standards and design principles belong here)
- On demand: everything else in `references/` and `skills/`, requested through the Conductor

## Lessons
- Load: `LESSONS.md` → Approved section only
- Write: candidate lessons go to my Candidates section; only the human promotes
