# Manifest — reviewer

This file is my context whitelist. The Conductor loads ONLY what it names, plus my Consumes docs and `bots/_SHARED/`.

## Identity (always load)
`prompts/code-review/generic-pr-review.md` (a local `PROMPT.md` here overrides it if present; swap in a stack-specific reviewer like `prompts/code-review/ts-pr-review.md` per project)

## Pipeline position
- Phase: PR gate between 5-impl and 6-test (not a numbered doc)
- Consumes: the PR diff, `05-impl.md`, `04-design.md`
- Produces: PR review — findings with severity + file:line, and a verdict (APPROVE | APPROVE WITH NITS | REQUEST CHANGES | ESCALATE-DESIGN). The Conductor records the verdict in `STATE.md`.
- Gate after me: I am the bot gate; REQUEST CHANGES loops to the implementer, ESCALATE-DESIGN routes to the architect

## Knowledge
- Always load: (none yet — security checklists belong here)
- On demand: everything else in `references/` and `skills/`, requested through the Conductor

## Lessons
- Load: `LESSONS.md` → Approved section only
- Write: candidate lessons go to my Candidates section; only the human promotes

## Isolation note
I must NEVER share context with the implementer's run. I judge the diff against the design cold.
