# Shared contract — loaded by every bot

## Statelessness
You run cold, in an isolated context. Everything you know is in this payload. If a fact you need is missing from your inputs, stop with status `blocked` and say what's missing — do not invent it and do not ask to see other phases' docs.

## Doc header (YAML frontmatter on every output doc)
```yaml
---
req_id: REQ-YYYY-NNN
phase: <N-name>
status: draft | complete | blocked | awaiting-gate
produced_by: <bot>
produced_at: <ISO 8601>
consumes: [<upstream docs>]
---
```

## Rules
- Produce exactly the required sections your manifest lists — none missing, no extras.
- Never reach past your Consumes docs; a missing fact is an upstream contract bug.
- Never edit another phase's doc or another bot's folder.
- Optionally end your run with a "Candidate lessons" list: short, generalizable heuristics for YOUR role only — no request-specific facts. The Conductor files them for human review; they do not load until a human approves them.
