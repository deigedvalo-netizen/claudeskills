# Lessons — implementer

## Approved (loaded every run)
_(none yet)_

## Candidates (bot-proposed; a human moves lines up to Approved)
- When a hard "don't change bindings" constraint collides with an explicit a11y decision (e.g. a click-`div` that must be keyboard-reachable), prefer the *additive* accessibility fix (tabindex/role/keydown alongside the existing handler) and record it as a scoped deviation, rather than silently dropping the a11y requirement or rewriting the binding.
- In a zero-build, token-only refactor, derive tinted surfaces with `color-mix(in srgb, <token> …%, transparent)` so status soft-backgrounds stay single-sourced from the status token instead of introducing per-theme `-soft` literals.
- For SPA screenshot harnesses that route on `location.hash`, a hash-only `page.goto` is a same-document navigation and won't re-run boot; force a `reload()` so routing + persisted theme re-apply deterministically per shot.
