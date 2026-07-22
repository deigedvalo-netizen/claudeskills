# SDLC Pipeline Runtime

This folder turns the Prompt Smith (Stage 1) into the front door of a full 8-stage SDLC pipeline that runs inside a Claude Project. It is the **writable state layer** the design calls for: Claude reads and writes here through a GitHub connector — the only place it can persist across sessions (Project Knowledge is human-curated and read-only to the agent).

## The one rule

Claude Projects has **no server and no shared memory between sessions**. So every phase is a stateless worker:

> read your input doc + `STATE.md` → do your job → write your output doc → update your row in `STATE.md`.

Nothing rides in session memory. Any phase can run cold tomorrow and pick up exactly where the docs left off.

## What's here

| File | Role |
|---|---|
| `CONDUCTOR.md` | Paste into your Claude Project's custom instructions. It's the orchestration logic — on every session it reads `STATE.md` and runs whatever phase is next. |
| `SCHEMAS.md` | The handoff contract: the fixed header every doc carries + the required sections per phase. |
| `ROUTER.md` | How a Maintenance finding becomes the next request (routes to Planning or back to Stage 1). |
| `STATE.md` | The single source of truth: one row per active request, naming the current phase and next action. |
| `ARCHITECTURE.md` | The full design reference (phase table, flow diagram, risks, worked trace). |
| `requests/_TEMPLATE/` | The 8 handoff docs as empty stubs. Copy this folder to `requests/REQ-<id>/` to start a request. |

## Running one request

1. Drop the raw ask into `requests/REQ-<id>/00-request.md` (or let Maintenance/Router create it).
2. Add a row to `STATE.md`.
3. In your Claude Project session, say **"advance the pipeline"**. The conductor reads `STATE.md`, runs the current phase, writes that phase's doc, and moves the row forward.
4. Repeat until Deployment. Three checkpoints pause for you: after Prompt Smith, after Design, before Deploy.

## What needs external tools (flagged)

- **Testing / Deployment** need real execution → wire **GitHub Actions**; the agent orchestrates and reads CI status, it doesn't run the suite itself.
- **Automatic advancement** isn't a web-Projects primitive → on desktop you can add a scheduled task to poll `STATE.md`; on web you type "advance".
