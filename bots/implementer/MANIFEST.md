# Manifest — implementer

This file is my context whitelist. The Conductor loads ONLY what it names, plus my Consumes docs and `bots/_SHARED/`.

## Identity (always load)
`prompts/implementation/feature-implementer.md` (a local `PROMPT.md` here overrides it if present)

## Pipeline position
- Phase: 5-impl
- Consumes: `04-design.md` (plus, on a loop-back, the review findings or red `06-test.md` the Conductor names)
- Produces: `05-impl.md` + code on a branch + PR — sections: Branch; PR link; File map; Changelog; Deviations from design
- Gate after me: no (the reviewer bot gates the PR)

## Knowledge
- Always load: (none yet — house style guides belong here)
- On demand: everything else in `references/` and `skills/`, requested through the Conductor

## Lessons
- Load: `LESSONS.md` → Approved section only
- Write: candidate lessons go to my Candidates section; only the human promotes
