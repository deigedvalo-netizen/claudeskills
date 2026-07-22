# Manifest — prompt-smith

This file is my context whitelist. The Conductor loads ONLY what it names, plus my Consumes docs and `bots/_SHARED/`.

## Identity (always load)
The `sdlc-prompt-smith` skill — Stage 1 runs the skill itself (with this folder's references and Approved lessons added to its context), not a generic subagent.

## Pipeline position
- Phase: 1-prompt
- Consumes: `00-request.md`
- Produces: `01-prompt.md` — sections: Objective; Constraints; Acceptance criteria; Non-goals
- Gate after me: yes (human: "right ask?")

## Knowledge
- Always load: (none yet — list files here to force-load)
- On demand: everything else in `references/` and `skills/`, requested through the Conductor

## Lessons
- Load: `LESSONS.md` → Approved section only
- Write: candidate lessons go to my Candidates section; only the human promotes
