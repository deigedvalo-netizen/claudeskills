# Pipeline State

**Single source of truth.** Every phase re-reads this first and refuses to run if its phase ≠ `current_phase`. One row per active request. Move rows to the Archive section when `status: done`.

## Active

| req_id | title | current_phase | status | last_artifact | next_action |
|---|---|---|---|---|---|
| _(none yet)_ | | | | | |

<!-- Example of a live row:
| REQ-2026-014 | avatar upload | 4-design | awaiting-gate | 04-design.md | human: approve design |
-->

## Archive (done)

| req_id | title | shipped_version | closed |
|---|---|---|---|
