---
req_id: REQ-2026-002
phase: 2-plan
status: complete
produced_by: planner
produced_at: 2026-07-22T11:58:00-05:00
consumes: [01-prompt.md]
---

## Milestones

> Assumption (default): the existing app is functionally complete and this effort is purely a visual/UX refresh; no page is added or removed. Assumption (default): a single shared visual system is defined once and applied uniformly, rather than each page being styled independently.

| # | Goal | Contains | Depends on | Size |
|---|------|----------|------------|------|
| 1 | Establish shared visual system | Baseline audit of current pages and flows; catalog of reusable UI elements (color, type, spacing, components, states); light/dark theming approach; accessibility and responsive targets captured as a checklist | — | M |
| 2 | Refresh landing / login | Apply the shared system to landing and login/auth surfaces | 1 | S |
| 3 | Refresh projects list | Apply the shared system to the projects list view | 1 | S |
| 4 | Refresh project detail | Apply the shared system to money-at-risk tiles, request feed, agreed-scope panel, and change orders | 1 | L |
| 5 | Refresh pricing estimator | Apply the shared system to the estimator page and its inputs/outputs | 1 | M |
| 6 | Cross-cutting verification | Verify no functional/behavioral regressions across all flows; confirm responsive layout (~360px → desktop), light/dark rendering, keyboard reachability, visible focus, and WCAG AA contrast; confirm backend, data model, and API routes unchanged | 2, 3, 4, 5 | M |

## Acceptance criteria (carried)

- **Given** any of the four page areas (landing/login, projects list, project detail, pricing estimator), **when** it is rendered, **then** it shows the refreshed design and shares one consistent visual system (color, type, spacing, components) with the others.
- **Given** every existing feature, route, form, and interaction, **when** exercised after the refresh, **then** it behaves exactly as before with nothing broken or removed.
- **Given** any refreshed page, **when** viewed at 360px, tablet, and desktop widths, **then** the layout holds with no overflow or overlap.
- **Given** light theme and dark theme, **when** any page is rendered in each, **then** it renders correctly with no unstyled or low-contrast elements.
- **Given** any interactive element, **when** navigated by keyboard, **then** it is reachable and shows a visible focus state, and its text/background contrast meets WCAG AA.
- **Given** the backend, data model, and API routes, **when** the refresh is complete, **then** they are unchanged.
- **Given** the delivered frontend, **when** its dependencies are inspected, **then** no third-party libraries or frameworks have been added and it remains vanilla HTML/CSS/JS.

## Out of scope

- New business features or any change to what the app does (deferred: none planned).
- Backend, API, or data-model changes.
- Framework migration or new runtime dependencies, build steps, or tooling.
- New pages or removal of existing pages beyond the four named areas.

## Risks / unknowns

- **Silent behavioral regression during restyle.** A visual change inadvertently alters a form, route, or data interaction. *Mitigation:* treat Milestone 6 regression verification as a gating step, exercising every existing flow before sign-off.
- **Inconsistent application of the shared system.** Pages styled in parallel drift apart. *Mitigation:* lock the shared visual system in Milestone 1 before any page is refreshed, and apply it as the single source for Milestones 2–5.
- **Accessibility targets missed under refresh.** New styling breaks contrast, focus visibility, or keyboard reach. *Mitigation:* carry the WCAG AA / keyboard / focus checklist from Milestone 1 through each page and confirm it in Milestone 6.
- **Theming or responsive gaps.** Elements unstyled in dark theme or broken at narrow widths. *Mitigation:* verify both themes and the 360px→desktop range on every page during Milestone 6.
- **Unknown: true breadth of existing flows and states.** The full inventory of interactions per page is not enumerated in the inputs. *Mitigation:* the Milestone 1 baseline audit establishes the complete flow/state catalog before refresh work begins.
