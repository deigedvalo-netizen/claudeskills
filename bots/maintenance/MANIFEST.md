# Manifest — maintenance

This file is my context whitelist. The Conductor loads ONLY what it names, plus my Consumes docs and `bots/_SHARED/`.

## Identity (always load)
`prompts/maintenance/maintenance-triager.md` (a local `PROMPT.md` here overrides it if present)

## Pipeline position
- Phase: 8-maint
- Consumes: `07-release.md` + live signals (GitHub Issues, CI status, user reports)
- Produces: `08-maint.md` — append-only Findings table (id, severity, repro, proposed request, route)
- Gate after me: triage — the Conductor mints new requests from my routes per `ROUTER.md`

## Knowledge
- Always load: (none yet — severity rubric belongs here)
- On demand: everything else in `references/` and `skills/`, requested through the Conductor

## Lessons
- Load: `LESSONS.md` → Approved section only
- Write: candidate lessons go to my Candidates section; only the human promotes
