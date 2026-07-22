# Manifest — release

This file is my context whitelist. The Conductor loads ONLY what it names, plus my Consumes docs and `bots/_SHARED/`.

## Identity (always load)
`prompts/release/release-manager.md` (a local `PROMPT.md` here overrides it if present)

## Pipeline position
- Phase: 7-release
- Consumes: `06-test.md` (must be green), `05-impl.md`
- Produces: `07-release.md` — sections: Version; Deploy steps; Rollback; Env / targets
- Gate after me: BEFORE me — I only run after the human ship gate; I never publish or tag without the row marked `approved`

## Knowledge
- Always load: (none yet — semver/changelog policy belongs here)
- On demand: everything else in `references/` and `skills/`, requested through the Conductor

## Lessons
- Load: `LESSONS.md` → Approved section only
- Write: candidate lessons go to my Candidates section; only the human promotes
