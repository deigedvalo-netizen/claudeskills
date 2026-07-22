# Manifest — tester

This file is my context whitelist. The Conductor loads ONLY what it names, plus my Consumes docs and `bots/_SHARED/`.

## Identity (always load)
`prompts/testing/test-verifier.md` (a local `PROMPT.md` here overrides it if present)

## Pipeline position
- Phase: 6-test
- Consumes: `05-impl.md`, `04-design.md` (acceptance criteria + test strategy)
- Produces: `06-test.md` — sections: Tests added; Run results; Coverage; Open defects
- Gate after me: only if red (a red report routes back to Planning)

## Knowledge
- Always load: (none yet — test conventions and coverage policy belong here)
- On demand: everything else in `references/` and `skills/`, requested through the Conductor

## Lessons
- Load: `LESSONS.md` → Approved section only
- Write: candidate lessons go to my Candidates section; only the human promotes

## Isolation note
I must NEVER see the implementer's reasoning — only the shipped code, the design, and `05-impl.md`. I test what was specified, not what was intended.
