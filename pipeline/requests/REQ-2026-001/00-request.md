---
req_id: REQ-2026-001
phase: 0-request
status: complete
produced_by: human
produced_at: 2026-07-21T23:17-05:00
consumes: []
---

## Raw ask

Add a small script that keeps `INDEX.md` in sync with the prompt library. It should verify that every prompt file under `prompts/` (excluding any folder README) has a matching row in `INDEX.md`, and that every row in `INDEX.md` points to a file that actually exists. On any mismatch, print the offending paths and exit non-zero, so it can run as a CI check.

## Source

human
