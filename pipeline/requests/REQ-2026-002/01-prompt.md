---
req_id: REQ-2026-002
phase: 1-prompt
status: awaiting-gate
produced_by: sdlc-prompt-smith
produced_at: 2026-07-22T11:52:00-05:00
consumes: [00-request.md]
---

## Objective

Refresh ScopeLine's visual design and UX across all existing pages — landing/login, projects list, project detail (money-at-risk tiles, request feed, agreed-scope panel, change orders), and pricing estimator — delivering a more polished, modern, cohesive look without changing what the app does.

## Constraints

- Keep the stack: Node.js zero-dependency backend, vanilla HTML/CSS/JS single-page frontend. No new runtime dependencies, build steps, or frameworks.
- No functional or behavioral regressions: every existing flow, route, form, and data interaction works exactly as before.
- Accessibility: semantic HTML, keyboard-navigable, visible focus states, WCAG AA color contrast, labeled controls.
- Responsive: usable and correctly laid out from mobile (~360px) through desktop.
- Support both light and dark themes.

## Acceptance criteria

- All four page areas render with the refreshed design and share one consistent visual system (color, type, spacing, components).
- No existing feature, route, or interaction is broken or removed; all forms and actions behave as before.
- Layout holds without overflow or overlap at 360px, tablet, and desktop widths.
- Light and dark themes both render correctly with no unstyled or low-contrast elements.
- Interactive elements are keyboard-reachable with visible focus; text/background contrast meets WCAG AA.
- Backend responses, data model, and API routes are unchanged.
- No third-party libraries or frameworks are added; frontend remains vanilla HTML/CSS/JS.

## Non-goals

- No new business features or changes to app functionality.
- No backend, API, or data-model changes.
- No framework migration or new dependencies/build tooling.
