---
req_id: REQ-2026-002
phase: 3-analysis
status: complete
produced_by: analyst
produced_at: 2026-07-22T12:05:00-05:00
consumes: [02-plan.md]
---

## Impacted modules

The frontend is a single-page app served statically from `public/`. All five refresh milestones land in three files: `public/index.html` (markup/structure), `public/styles.css` (visual system), `public/app.js` (view rendering + theme). The backend under `src/` is touched only as a read-only boundary to be preserved (Milestone 6).

| Milestone | Path → why it's touched |
|---|---|
| 1 — Shared visual system | `public/styles.css` (token layer `:root` + `[data-theme="light"]`; component rules); `public/index.html` (class vocabulary); `public/app.js` theme apply/init/toggle + `#themeToggle`. **Greenfield** for the artifacts the milestone names separately: no standalone token file, no written UI-element catalog, no accessibility/responsive checklist exists — the "system" lives only inline in `styles.css` (header comment calls it "visual system v2"). A visual baseline exists via `shots/*.png` + `shots.mjs`. |
| 2 — Landing / login | `public/index.html` `#view-auth` (`.landing`, `.hero`, `.auth-card` tabs, `.hiw` strip); `public/styles.css` `.landing`/`.hero-*`/`.auth-*`/`.hiw*`; `public/app.js` auth mode/submit/logout + `showAuth`/`showAppChrome`. |
| 3 — Projects list | `public/index.html` `#view-projects` (`.card-grid`, `#projectEmpty`); `public/styles.css` `.card-grid`/`.project-card`/`.empty`; `public/app.js` `loadProjects`. |
| 4 — Project detail | `public/index.html` `#view-project` (`#moneyBanner`, `#requestList`, `#deliverableList`, `#changeOrderList`); `public/styles.css` money tiles + `.request`/`.badge`/`.confbar`/`.deliverables`/`.co-item`; `public/app.js` `renderProject`/`renderDeliverables`/`renderRequests`/`renderChangeOrders`/`updateSelection` + modals. |
| 5 — Pricing estimator | `public/index.html` `#view-pricing` (inputs `#pxHours`/`#pxRate`/`#pxMaterials`/`#pxMargin`/`#pxComplexity`/`#pxCurrency`, `#pxResult`); `public/styles.css` `.result-card`/`.px-big`/`.rangebar`/`.range-labels`/`.px-reasons`; `public/app.js` `calcPricing`/`showPricing` + margin readout. |
| 6 — Cross-cutting verification | `public/styles.css` single `@media (max-width: 900px)` block governs responsive; theme correctness spans `app.js` theme fns + `styles.css` token layer; focus governed by `styles.css` `input:focus`/`textarea:focus`/`select:focus`. "Backend/data-model/API routes unchanged" pins `src/server.js` route table + `src/router.js`/`handlers.js`/`db.js`/`engine.js`/`pricing.js`/`export.js`/`auth.js`/`supabase.js` as read-only. |

## Current-state findings

- **Serving / architecture.** `src/server.js` is a zero-dependency `node:http` server. Any non-`/api/` path is served from `public/` by `serveStatic`, with SPA fallback to `index.html`. No bundler/build step; browsers load `public/app.js` directly as `type="module"`.
- **A visual system already exists and is theme-aware.** `styles.css` defines CSS custom properties for color, surfaces, text, accents, status colors, radii, shadows, gradients under `:root` (`color-scheme: dark`) and overrides a subset under `[data-theme="light"]` (`color-scheme: light`). Components consume these variables, so both themes render from one rule set. Header states status colors follow "the validated data-viz palette (warning/good), always paired with icon + label."
- **Theming mechanism.** `app.js` `applyTheme` toggles `data-theme="light"` on `<html>` and swaps the toggle glyph; `initTheme` reads `localStorage['sl-theme']` (default `dark`); `toggleTheme` flips and persists. Toggle is `#themeToggle` in the topbar.
- **View routing.** `VIEWS = ['auth','projects','project','pricing']`; `show()` toggles `.hidden`. Navigation is hash-based (`#/p/:id`, `#/pricing`) resolved in `boot()`. No router library, no framework — DOM built via the `el()` helper.
- **Landing / login (M2).** One `#view-auth` section holds both the marketing landing (`.hero`, `.why`, `.hiw` three-step strip) and the auth card with Log in / Sign up tabs. Auth state drives topbar chrome via `showAuth`/`showAppChrome`. Login vs signup is a client toggle hitting `/api/auth/login` or `/api/auth/signup`.
- **Projects list (M3).** `loadProjects` fetches `/api/projects` and renders `.project-card` tiles into `.card-grid` (auto-fill `minmax(270px,1fr)`); `#projectEmpty` shown when empty.
- **Project detail (M4).** `renderProject` builds four stat tiles into `#moneyBanner` — "At risk" (`.risk`), "On change orders" (`.neutral`), "Quoted" (`.neutral`), "Recovered" (`.recovered`) — each with an emoji icon and an animated money value (`animateMoney`, which respects `prefers-reduced-motion`). The request feed (`renderRequests`) renders `.request` cards with a classification `.badge`, a `.confbar` confidence meter or "manual override" note, an inline classification `<select>`, an editable hours `<input>`, and an out-of-scope checkbox. Agreed scope and change orders render into the side column.
- **Pricing estimator (M5).** Inputs: number fields, a `range` slider (margin, live `#pxMarginVal` readout), a complexity `<select>`, a currency text field. `calcPricing` POSTs to `/api/pricing/estimate` and renders a `.px-big` recommended price, a `.rangebar` marker between low/high, an effective-rate line, and a `.px-reasons` list.
- **Accessibility surface today.** Grep of `public/` for `aria-*`/`role=`/`alt=`/`tabindex`/`:focus-visible` returns only `aria-hidden="true"` on the brand SVG and `aria-label="Toggle theme"` on `#themeToggle`. Controls are native elements so are keyboard-focusable by default. Focus styling is defined only via `:focus` (not `:focus-visible`) on form fields (border + 3px ring); no explicit focus style for `.btn`, `.nav-btn`, `.auth-tab`, `.project-card`, `.icon-btn`, `.link-back`. Status is conveyed by color + icon/label + text, not color alone. Icons throughout are emoji text nodes.
- **Responsive state today.** A single breakpoint at `max-width: 900px` collapses `.columns`/`.landing-top`/`.hiw-flow` to one column, drops `.money-banner` to 2 columns, unsticks sticky cards, wraps the topbar, shrinks the hero title. No breakpoint below 900px; the plan's lower bound is ~360px.
- **Existing visual baseline.** `shots/` contains `01-landing-dark.png`, `02-landing-light.png`, `03-projects-empty.png`, `04-project-detail.png`, `05-pricing.png`. `shots.mjs` boots the server on an ephemeral port + throwaway SQLite DB, drives Chromium (Playwright) at 1280×900 @2x, seeds a demo project via the API, and captures those five full-page screenshots.
- **Tests.** `test/` holds `engine.test.js`, `api.test.js`, `export.test.js`, `auth.test.js`, `pricing.test.js` — all backend (`node:test`). No frontend/DOM test, no visual-regression assertion, no accessibility/contrast test.

## Dependencies (present / missing)

Present:
- **Node.js ≥ 22.5.0** runtime (`package.json` `engines`); uses built-in `node:sqlite`, `node:test`, `node:crypto`, `node:http`.
- **Zero runtime dependencies** — `package.json` `dependencies: {}`; no `node_modules` for the app.
- **Vanilla frontend stack** — HTML + CSS custom properties + ES modules; no framework or CSS library imported anywhere in `public/`.
- **Playwright** available globally, referenced only by `shots.mjs` for screenshots — not a runtime app dependency.
- **`.env.example`** present for optional Supabase config (off by default).

Missing (not present in the tree):
- No build tooling, bundler, transpiler, or `build` script (scripts are only `start`/`dev`/`test`).
- No CSS preprocessor, PostCSS, or design-token pipeline; no standalone token/theme file separate from `styles.css`.
- No linter, formatter, or style config (no ESLint/Prettier/Stylelint).
- No frontend test runner, DOM testing library, or visual-regression tooling (Playwright present but only wired to screenshots, no assertions).
- No accessibility/contrast tooling in the repo.
- No written UI-element catalog and no accessibility/responsive checklist artifact (Milestone 1 names these — greenfield).

## Constraints

- **Not a version-controlled checkout.** `git rev-parse --is-inside-work-tree` reports "not a git repository" at `/root/scopeline`. No `.git`, so no branches, branch protections, or history.
- **No CI.** No `.github/` or workflows; no required checks.
- **Frontend is three files, no build.** All UI work goes through `public/index.html`, `public/styles.css`, `public/app.js`, served verbatim by `src/server.js`. No compilation — CSS/JS must run natively in the browser.
- **Theming contract in place.** Light mode is driven solely by `data-theme="light"` on `<html>`; persistence key `localStorage['sl-theme']`; default dark. New styling must resolve under both `:root` and `[data-theme="light"]`.
- **Status-color convention.** `styles.css` header documents status colors from a "validated data-viz palette," "always paired with icon + label" — visible in badges and tiles.
- **Single responsive breakpoint today.** Only `@media (max-width: 900px)`. No rules target the ~360px lower bound the plan requires.
- **Focus styling is `:focus`-only and partial.** Visible focus for form inputs only; not for buttons, nav/auth tabs, cards, icon button, back link; `:focus-visible` unused.
- **`node:sqlite` is experimental.** Backend relies on Node's experimental `node:sqlite`; requires Node ≥ 22.5. Out of scope to change; frames the "backend unchanged" boundary.
- **Backend API surface to preserve.** Routes fixed in `src/server.js`: `/api/auth/{signup,login,logout,me}`, `/api/pricing/estimate`, `/api/projects`, `/api/projects/:id`, `/api/projects/:id/{deliverables,requests,change-orders}`, `/api/deliverables/:id`, `/api/requests/:id`, `/api/change-orders/:id`, `/api/change-orders/:id/export`. Response shapes (e.g. `project.stats.{at_risk,on_orders,quoted,recovered,currency}`, request fields `classification`/`confidence`/`est_hours`/`overridden`/`reasons`) are the data model the UI reads and must stay unchanged.
- **Icons are emoji.** Tiles, how-it-works strip, and control glyphs use emoji text nodes; the only inline SVG is the brand mark.
- **Screenshot harness is the only visual verification path.** `shots.mjs` depends on a globally-installed Playwright at a hard-coded path and captures five fixed full-page shots at 1280×900; no assertions.
