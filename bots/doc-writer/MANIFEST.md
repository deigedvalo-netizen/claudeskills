# Manifest — doc-writer

This file is my context whitelist. The Conductor loads ONLY what it names, plus my Consumes docs and `bots/_SHARED/`.

## Identity (always load)
`prompts/documentation/doc-writer.md` (a local `PROMPT.md` here overrides it if present)

## Pipeline position
- Phase: docs pass after 6-test (green), before 7-release
- Consumes: `05-impl.md`, `06-test.md`
- Produces: docs in the target repo (`docs/**`, README updates) + a one-line note of what changed
- Gate after me: no

## Knowledge
- Always load: (none yet — docs voice/style guides belong here)
- On demand: everything else in `references/` and `skills/`, requested through the Conductor

## Lessons
- Load: `LESSONS.md` → Approved section only
- Write: candidate lessons go to my Candidates section; only the human promotes
