# Router — Maintenance findings → next request

Maintenance never dead-ends. Each finding in `08-maint.md` becomes a new request with a fresh `req_id`. Apply these rules in order:

| If the finding is… | Route to | Why |
|---|---|---|
| A defect **with a reproduction** and a clear expected-vs-actual | **Stage 2 Planning** | The ask is already precise; skip prompt generation. |
| A defect **without** a reliable repro | **Stage 1 Prompt Smith** | Needs sharpening into a precise, testable ask first. |
| A new feature or enhancement | **Stage 1 Prompt Smith** | Ambiguous scope; generate the working prompt first. |
| A pure ops/infra tweak (no code behavior change) | **Stage 2 Planning** | Scope is known; plan and go. |

## Minting the request

1. Allocate the next `REQ-<year>-<nnn>`.
2. Copy `requests/_TEMPLATE/` to `requests/REQ-<id>/`.
3. Write the finding into `00-request.md` (`Source: maintenance-finding <id>`).
4. Add a row to `STATE.md` with `current_phase` = the routed entry phase.

A finding routed to Planning still writes `00-request.md` for provenance, but `01-prompt.md` is left empty/`n/a` — Planning consumes `00-request.md` directly in that case.
