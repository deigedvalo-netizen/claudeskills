# Lessons — architect

## Approved (loaded every run)
_(none yet)_

## Candidates (bot-proposed; a human moves lines up to Approved)
- When a "no-build / served-verbatim" constraint governs, prefer *logical* separation (commented regions, naming conventions) over *physical* file splits — the constraint is usually protecting runtime characteristics that extra files quietly break.
- Make cross-cutting acceptance criteria mechanically checkable by turning them into a contract: "every token defined in both themes" and "every interactive element uses the focus token" are auditable in a way that "looks consistent" is not.
- Prefer intrinsic/fluid layout primitives over stacking discrete breakpoints when the goal is "holds from small to large" — one mechanism with fewer places to forget beats N per-view media queries.
- When the only verification harness lacks assertions, decide explicitly whether to extend it (and flag any scope creep at the gate) versus fall back to a written manual checklist — don't silently assume tooling you're forbidden to add.
