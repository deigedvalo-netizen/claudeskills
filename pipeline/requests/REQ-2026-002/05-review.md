---
req_id: REQ-2026-002
phase: 5-review (PR gate, between 5-impl and 6-test)
status: changes-requested
produced_by: reviewer
produced_at: 2026-07-22T13:05:00-05:00
consumes: [05-impl.md, 04-design.md, code]
---

**Verification performed (independent):** `npm test` → 49/49 pass, 0 fail; `src/` untouched (only `public/*` + `shots.mjs` edited) — no backend/API/data drift. Token sets under `:root` and `[data-theme="light"]` are byte-for-byte identical and every `var(--sl-*)` resolves in both themes. All HTML/JS classes are `sl-*` or sanctioned utilities; no legacy classes remain. All ids, hash routes (`#/pricing`, `#/p/:id`), `VIEWS`, `el()`, and event bindings intact. Single `@media (max-width:900px)` mode-switch; motion gated by `prefers-reduced-motion` (CSS + `matchMedia`). `shots.mjs` = 4 areas × 3 widths × 2 themes = 24 image-only shots. No dependency added.

## 1. Correctness & design-conformance
- **MAJOR — styles.css `.sl-btn--success`.** The "Create change order" button uses hardcoded `color:#ffffff` on a `#12a06a→#12907f` green gradient; white-on-green measures **3.35–3.95:1**, below AA 4.5:1 for normal-weight control text — a design must-prevent case, on an interactive element. Fix: dark ink on the green (mirror `--sl-color-accent-ink` on primary) or darken the gradient so the label clears 4.5:1; drive from tokens.
- **MINOR — app.js / styles.css `.sl-value`.** `.sl-value` is hardwired to `--sl-status-risk-fg` (amber) and reused for change-order totals (`sl-co__total sl-value`), so recovered/quoted totals render in the risk color — semantic mismatch (no contrast problem). Fix: neutral or `-recovered-fg` treatment for totals.

## 2. Security
No findings. DOM built via `el()`/`textContent`; the two `innerHTML` sinks carry only static/empty strings. No authz or network-contract change. No new/unsafe deps.

## 3. Performance
No findings. Intrinsic reflow primitives; transform/opacity animations; the count-up rAF loop self-terminates and honors reduced-motion.

## 4. Readability & house style
- **MINOR — `--sl-color-text-muted` on non-base surfaces.** Muted text drops below AA on raised/sunken fills: `.sl-badge--muted` "on order" (`#6b7280` on sunken `#e9edf6`) = **4.12:1**; `.muted` on light raised `#f2f4f9` = **4.39:1**; dark `#7f8693` on raised `#1c1f28` = **4.49:1**. Fix: darken (light) / lighten (dark) the muted token a step, or use `--sl-color-text-2` on raised/sunken fills.
- **NIT — raw literals outside the token layer** (token-contract A): `.sl-btn--success` gradient + `#ffffff`, `rgba(...)` hover shadows on primary/success, `.sl-px-big` `#34d0b4`, `.sl-rangebar__marker` `#fff`. Fix: promote to `--sl-*` tokens.
- **NIT — dead vocabulary:** `--sl-space-6`, `.sl-stack`, `.sl-badge--quoted` defined but never emitted (`STATUS_MOD` yields only risk/recovered/order). Fix: drop or wire up.
- **NIT — shots.mjs:3** hardcodes an absolute global-Playwright path; non-portable (acceptable as out-of-tree dev tool; add a comment/resolvable import).

## Verdict
**REQUEST CHANGES** — token layer, theme parity, feature/route preservation, focus, and reduced-motion are correctly implemented and tests pass, but `.sl-btn--success` control text fails WCAG AA (3.35:1), violating an explicit acceptance criterion; several muted-text pairs also sit below 4.5:1. Fix contrast (and ideally the raw-literal leak at the same locus), then clean approve.
