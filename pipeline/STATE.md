# Pipeline State

**Single source of truth.** Every phase re-reads this first and refuses to run if its phase ≠ `current_phase`. One row per active request. Move rows to the Archive section when `status: done`.

## Active

| req_id | title | current_phase | status | last_artifact | next_action |
|---|---|---|---|---|---|
| REQ-2026-001 | INDEX/prompts sync check | 1-prompt | ready | 00-request.md | run Stage 1 Prompt Smith → 01-prompt.md |
| REQ-2026-002 | site visual redesign | 5-impl | complete | 05-impl.md | run Review (reviewer bot) on impl → then Stage 6 Testing → 06-test.md |

<!-- Example of a live row:
| REQ-2026-014 | avatar upload | 4-design | awaiting-gate | 04-design.md | human: approve design |
-->

## Archive (done)

| req_id | title | shipped_version | closed |
|---|---|---|---|
