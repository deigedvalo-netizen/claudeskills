---
req_id: REQ-2026-002
phase: 5-impl
status: complete
produced_by: implementer
produced_at: 2026-07-22T12:30:00-05:00
consumes: [04-design.md]
---

## Branch

n/a. The ScopeLine working tree at `/root/scopeline` is **not a git repository** and has no remote (`git status` → "fatal: not a git repository"), so no feature branch could be opened. All work was done in place in the working tree. See *Deviations from design* for the standing environment note. "Self-run before opening" was satisfied by running `npm test` locally and confirming it stays green (49/49).

## PR link

n/a. With no git repo and no remote/forge, a pull request cannot be created. The equivalent reviewer hand-off is this doc plus the edited files under `public/` and `shots.mjs`, and the `shots/` render sweep (24 images) for visual review. The reviewer bot gates next.

## File map

- **public/styles.css** — Full rewrite into a single, ordered stylesheet: `TOKEN LAYER → BASE → LAYOUT PRIMITIVES → COMPONENT CATALOG → VIEW OVERRIDES → MEDIA → MOTION GATE → KEYFRAMES`. Adds the commented `/* === TOKEN LAYER === */` region declaring the **full `--sl-*` token set in BOTH `:root` (dark default) and `[data-theme="light"]`** (color-role, status base+`-fg`, spacing 1–6, radius/elevation, type scale, motion, gradients, `color-scheme`). Every prior component rule was re-expressed against the `sl-*` catalog and made to reference tokens only — all superseded legacy rules (`.btn`, `.badge`, `.stat`, `.request`, `.confbar`, `.rangebar`, `.px-*`, `.landing/.hero/.hiw`, `.topbar`, `.nav-btn`, `.auth-*`, `.columns/.col`, etc.) were removed, not left alongside.
- **public/index.html** — Class strings swapped to the `sl-*` catalog and wrapper structure updated. **All node ids, event-target elements, view markup, `data-view` attributes, the theme toggle, and the script include are unchanged.** No ids added/removed.
- **public/app.js** — `el()` builder untouched. Class strings emitted by render functions swapped to the `sl-*` catalog; the two `document.querySelectorAll('.nav-btn')` selectors retargeted to `.sl-nav__btn` (same nodes, same bindings); added a `STATUS_MOD` map so classification → status-token modifier; money-tile calls now pass `risk/order/quoted/recovered` modifiers; project cards gained `tabindex="0"`, `role="button"`, `aria-label` and an Enter/Space `keydown` (keyboard-reachability per the focus decision) while keeping the existing `onclick`. **No API path, HTTP method, request payload, hash route (`#/p/:id`, `#/pricing`), `VIEWS` list, `.hidden` toggling, or theme contract changed.**
- **shots.mjs** (approved harness) — Extended from 5 fixed shots to a sweep of the **four areas (landing/auth, projects, project detail, pricing) × 3 widths (360 / 768 / 1280) × 2 themes (dark, light) = 24 image-only screenshots**. Uses the same global Playwright import path; adds a `setup()` helper that sets viewport, seeds `localStorage['sl-theme']`, and forces a full document reload so hash-routing + theme re-apply per shot; retargeted the `.nav-btn[...]` selector to `.sl-nav__btn`. No new dependency.
- **test result:** `npm test` → **49 tests, 49 pass, 0 fail** (unchanged from baseline). The extended `shots.mjs` also runs clean and writes 24 PNGs to `shots/`.

## Changelog

- Built the `/* === TOKEN LAYER === */` region: one namespaced `--sl-*` vocabulary, declared in full under **both** `:root` and `[data-theme="light"]` (no theme-missing token). Tokens are the only place raw color/space/type values live; components reference tokens (or `color-mix()` of a token), never literals.
- Refactored every component to the BEM-ish `sl-*` catalog: `sl-btn` (`--primary/--ghost/--danger/--icon`, plus `--success/--sm/--full`), `sl-back-link`, `sl-card`, `sl-panel`, `sl-tile` (`__top/__ico/__label/__value`, status `--risk/--order/--quoted/--recovered`), `sl-badge` (`__dot` icon-node + label-node, status modifiers, `--muted`), `sl-field__label`, `sl-select`/`select`, `sl-check`, `sl-confbar` (`__track/__fill/__pct/__ovr`), `sl-rangebar` (`__marker/__labels`), `sl-px-big`, `sl-feed__item` (`__text/__reasons/__foot`), `sl-nav` (`__btn`), `sl-tabs` (`__tab`), and layout primitives `sl-stack/sl-cluster/sl-grid`.
- Kept `el()` and all node identities/ids/event bindings; only class names and wrapper structure changed.
- Standardized focus on `:focus-visible` + a `--sl-color-focus-ring` token across all interactive elements (buttons, nav, tabs, back-link, icon button `#themeToggle`, cards-as-links, form controls), with a `:focus:not(:focus-visible)` reset so no legacy ring doubles up.
- Status colors are always paired with an icon node + text label (tiles keep `__ico` + label; badges keep `__dot` + label), and each status token carries an AA-contrast `-fg` companion used for the label/value.
- Converted layouts to fluid/intrinsic primitives: `sl-grid`/`sl-tiles` use `repeat(auto-fit, minmax(min(100%, <token>), 1fr))`, `sl-cluster` uses `flex-wrap`, the topbar wraps, `clamp()` drives the hero title — so layout reflows continuously 360→desktop with no horizontal overflow at 360px. The single explicit `@media (max-width: 900px)` remains as the one mode-switch.
- Gated motion: durations come from `--sl-motion-*` tokens and a `@media (prefers-reduced-motion: reduce)` block neutralizes transitions/animations; the JS count-up already respects reduced-motion.
- Single ordered stylesheet with all superseded legacy rules removed (no cascade fights).
- Extended `shots.mjs` to cover the four areas at 360/768/1280 in both themes (24 image-only captures).
- **No new dependencies** (package.json `dependencies` stays `{}`). **No `src/` changes** — only `public/index.html`, `public/styles.css`, `public/app.js`, and the approved `shots.mjs` were edited. `npm test` → **49/49 pass**.

## Deviations from design

- **Branch / PR (environment).** Design/manifest assume a branch + PR; the working tree is not a git repo and has no remote, so both are `n/a`. Implemented in place; self-run = `npm test` green. (Environment fact, not a design change.)
- **Interface contract (B) — `sl-btn` modifier set.** The catalog enumerates `--primary/--ghost/--danger/--icon`. I additionally kept `sl-btn--success` (for the green "Create change order" CTA) and `sl-btn--sm` (for the pre-existing small buttons). These are additive modifiers within the same `sl-btn` component; no enumerated modifier was dropped.
- **Focus decision (cards-as-links) vs. the "only class names/wrapper/styles change" rule for app.js.** The design's focus decision requires cards-as-links to be keyboard-reachable with a visible `:focus-visible` ring. The projects list card is a click-`div`, so I added `tabindex="0"`, `role="button"`, `aria-label`, and an Enter/Space `keydown` calling the same `openProject`. Additive accessibility preserving the existing `onclick`, ids, and payloads; slightly exceeds "only class names change" but is required by the focus/a11y decision. No behavior regression.
- **Catalog scope — view-scaffolding + utility classes.** View-specific presentational classes (`sl-landing`, `sl-hero*`, `sl-hiw*`, `sl-auth*`, `sl-result`, `sl-empty*`, `sl-tiles`, `sl-deliv*`, `sl-co*`, `sl-cols/sl-col`) and small utilities (`muted`, `small`, `mt`, `hidden`, `active`) are not individually enumerated in catalog (B). They are token-based and `sl-`-namespaced (utilities kept by their original names to avoid churning bindings that toggle `active`/`hidden`). Treated as in-spirit extensions of the catalog, not literals.
- Nothing from the design was left unimplemented across M1–M6; the only omissions from a strict literal reading of the catalog are the additive modifiers/classes noted above.
