# Implementation Plan — Wallcovering Takeoff App

**Working title:** WC Takeoff
**Purpose:** A small, single-purpose **desktop application** that reads an interior-design drawing set (PNG images of construction sheets) and produces a wallcovering material takeoff for the tagged finishes **WC-1, WC-2, WC-3**.
**Target stack:** Python + a PNG-reading step (manual / OCR / vision — see §4) + a local desktop UI. No server, no website.
**Scope of this document:** A plan for the app that does the takeoff. It does **not** contain application code, and it does **not** perform the takeoff itself.

A hard line runs through everything below:

> **Compute** only WC quantities (net area → rolls / linear yards, with roll width, pattern repeat, and waste).
> **Set read** everything else — pull it verbatim from the schedule. Never derive, infer, or "improve" a set-read value.

---

## 1. Assumptions & Open Questions

These are flagged, not resolved. The app should not silently design around any of them; each maps to either a configurable input, a surfaced review step, or an explicit question to the estimator.

### 1.1 Open questions (need an answer before or during build)

**Q1 — Drawing scale source.** How does the app know real-world dimensions?
Options: (a) the estimator types dimensions in from dimension strings printed on the sheet; (b) the app OCR-reads printed dimension strings ("12'-0\"") off the plan/elevation; (c) the app measures pixels and applies a scale (e.g. 1/4"=1'-0") plus the sheet's DPI. Pixel-scaling from a PNG is the least reliable (PNGs carry no reliable scale metadata, sheets get cropped/rescaled on export). **Recommendation to confirm:** treat printed dimension text as the source of truth; use pixel measurement only as a cross-check or last resort, never as the primary number.

**Q2 — Where do wall lengths come from — plan or elevations?** Wall *widths* can be read from the finish plan (room dimensions / wall runs); wall *heights* come from the ceiling-height plan. Elevations may restate both. Which sheet wins when they disagree? **Recommendation to confirm:** plan for widths, ceiling-height plan for heights, elevations as the tie-breaker and for partial-height conditions (wainscot, back-wall-only).

**Q3 — How is "ALL WALLS U.N.O." resolved?** A note like `ALL WALLS: WC-1, TP-1, WB-1` plus per-wall exceptions ("Unless Noted Otherwise"). Does the app apply the blanket finish to the full room perimeter and then subtract walls that carry an explicit override tag? What if only one wall is tagged (back-wall accent) with no "all walls" note? **Recommendation to confirm:** model each room as a set of walls; a room-level note sets a default for all four walls, a wall-level tag overrides that default for that wall only. Any room where the override logic is ambiguous is sent to review, not guessed.

**Q4 — Opening deductions.** Do we deduct doors, windows, storefront, casework backs from wall area? Estimating practice varies: many wallcovering takeoffs do **not** deduct small openings (you hang full drops and cut around them), while large openings (storefront, full-height glazing) are deducted. **Recommendation to confirm:** make deductions a policy toggle with a size threshold (default: deduct openings ≥ a set sf, e.g. 20 sf; ignore below). Whatever the default, the app must show what it deducted.

**Q5 — Waste %.** Default 10–15%. Is this a single global default, or per-WC (a large repeat needs more)? Is the pattern-repeat loss counted *inside* the waste % or *separately*? **Recommendation to confirm (and this is important):** pattern-repeat loss is computed explicitly by the strip method (§2) and is **separate** from the waste %. The waste % covers cutting, trimming, defects, and attic stock — not repeat matching. Double-counting repeat loss inside waste inflates the order.

**Q6 — Unit of sale per WC.** Commercial goods are often sold by the **linear yard** off a 54" bolt; residential goods by the **roll** / double-roll. The schedule's "coverage/unit" field tells us which. Does every WC in this set use the same unit, or mixed? **Recommendation to confirm:** read the unit from each WC's schedule row independently; never assume all three WCs sell the same way.

**Q7 — Match type / pattern repeat.** Repeat can be **straight match**, **half-drop match**, or **random/free match (no repeat)**. Half-drop changes the drop math. Does the schedule state match type, or only the repeat dimension? **Recommendation to confirm:** if match type is not on the schedule, surface it for the estimator rather than assuming straight match.

### 1.2 Working assumptions (stated so they can be rejected)

- **A1.** Input is a set of readable PNGs (finish/millwork schedule, finish plan, ceiling-height plan, room elevations), e.g. sheets ID-1.x / ID-2.x / ID-3.x of the "Domain Spring Cypress" set. Only these three tags — WC-1, WC-2, WC-3 — are in scope; TP-, WB-, PT-, etc. are ignored.
- **A2.** The finish schedule is the authoritative definition of each WC (manufacturer, pattern, roll width, pattern repeat, coverage/unit, match type). These are **set reads**.
- **A3.** One takeoff run = one drawing set for one project. No cross-project memory required in v1.
- **A4.** The estimator reviews and can correct every auto-read value before quantities are finalized. The app assists; it does not autonomously submit an order.
- **A5.** Dimensions on the sheets are in feet-and-inches (imperial). Metric is out of scope for v1 unless stated.
- **A6.** A single wall is planar and rectangular for area purposes (height × width). Sloped ceilings, curved walls, and soffits are edge cases (§6), not the base case.

---

## 2. Functional Requirements (with Given/When/Then acceptance criteria)

Requirement IDs are stable. Every requirement has ≥1 testable acceptance criterion. The takeoff math is expressed as concrete, checkable cases.

### FR-1 — Ingest a drawing set
The app accepts one or more PNG files and lets the estimator label each sheet's role (schedule / finish plan / ceiling-height plan / elevation) or infers the role from the sheet number/title.

- **AC-1.1** — *Given* four PNGs are dropped in, *when* ingest completes, *then* each file appears in the set with an assigned role and a thumbnail, and any unlabeled sheet is flagged for the estimator to label.
- **AC-1.2** — *Given* a non-PNG or unreadable file, *when* it is dropped in, *then* the app rejects it with a clear message and does not add it to the set.

### FR-2 — Read WC definitions from the schedule (SET READ)
For each of WC-1, WC-2, WC-3 the app captures, verbatim: manufacturer, pattern/product name, roll (bolt) width, pattern repeat (and match type if present), and coverage/unit (unit of sale + yield).

- **AC-2.1** — *Given* the schedule defines WC-1 as `Roll width 54", Repeat 18" straight, 30 LY/bolt`, *when* the schedule is read, *then* those exact values are stored against WC-1 and shown for confirmation — none of them recomputed.
- **AC-2.2** — *Given* a WC row is missing a field the takeoff needs (e.g. no roll width), *when* the schedule is read, *then* that field is marked UNKNOWN and blocks quantity computation for that WC until the estimator supplies it (see FR-8).

### FR-3 — Locate WC applications (tag → walls/rooms)
The app finds every place WC-1/2/3 is applied and to which walls of which rooms, from finish-plan notes and elevation tags, including blanket notes ("ALL WALLS: WC-1 …") and single-wall tags (back-wall accent).

- **AC-3.1** — *Given* Room 101 carries `ALL WALLS: WC-1`, *when* applications are resolved, *then* all four walls of Room 101 are associated with WC-1.
- **AC-3.2** — *Given* Room 102 carries `ALL WALLS: WC-1` **and** its north wall is separately tagged `WC-2`, *when* applications are resolved, *then* the north wall maps to WC-2 and the remaining walls map to WC-1 (wall-level override beats room-level default).
- **AC-3.3** — *Given* a WC tag whose target wall/room cannot be determined unambiguously, *when* applications are resolved, *then* that application is placed in a review queue and is **not** guessed.

### FR-4 — Derive wall area per application
For each application, compute wall area from wall width (plan/elevation) × wall height (ceiling-height plan), with optional opening deductions per policy (Q4).

- **AC-4.1** — *Given* a back wall of 12'-0" width and a ceiling height of 9'-0", *when* area is derived, *then* gross wall area = 108 sf.
- **AC-4.2** — *Given* opening-deduction policy is ON with a 20 sf threshold and the wall has a 3'-0"×7'-0" door (21 sf), *when* area is derived, *then* the door is deducted and net area = 108 − 21 = 87 sf, and the deduction is itemized.
- **AC-4.3** — *Given* the ceiling height for a room is missing, *when* area is derived, *then* the app blocks that room's area (no default height assumed) and flags it (FR-8).

### FR-5 — Compute material quantity per WC (THE COMPUTE)
Convert net area into ordered quantity using the WC's roll width, pattern repeat/match, unit of sale, yield, and the waste %. Two methods; the app selects by whether a vertical repeat exists.

**Method A — Strip / drop method (use when pattern repeat > 0).** Accounts for repeat loss explicitly.
```
drops        = ceil(wall_width / roll_width)                  # full-width strips needed
cut_length   = ceil((wall_height + trim_allow) / repeat) * repeat   # per-drop, straight match
total_length = drops * cut_length
raw_LY       = total_length / 36                              # if sold by linear yard
order_qty    = raw_LY * (1 + waste_pct)                       # waste is SEPARATE from repeat loss
bolts        = ceil( (raw_LY * (1 + waste_pct)) / bolt_yield )
```

- **AC-5.1 (worked, straight-match, linear yard)** — *Given* WC-1 (roll width 54", repeat 18" straight, bolt yield 30 LY), a back wall 12'-0" wide × 9'-0" high, trim allowance 4", waste 10%, *when* quantity is computed, *then*:
  - drops = ceil(144" / 54") = **3**
  - cut_length = ceil((108"+4") / 18") × 18" = ceil(6.22)×18 = 7×18 = **126"**
  - total_length = 3 × 126" = **378"** = **10.5 LY** raw
  - with 10% waste = 11.55 LY → **order 12 LY / 1 bolt** (ceil(11.55/30)=1)
  - and the result shows the 10.5 raw vs 11.55 with-waste figures distinctly.

**Method B — Area method (use when repeat = 0 / random match, or as a cross-check).**
```
net_sy    = net_area_sf / 9
order_sy  = net_sy * (1 + waste_pct)
rolls     = ceil(order_sy / coverage_per_roll_sy)
```

- **AC-5.2 (worked, no repeat, rolls)** — *Given* WC-2 (roll width 54", repeat 0, coverage 13.5 sy/roll), a room whose net wall area after deductions is 320 sf, waste 15%, *when* quantity is computed, *then*:
  - net_sy = 320 / 9 = **35.56 sy**
  - with 15% waste = 40.89 sy
  - rolls = ceil(40.89 / 13.5) = ceil(3.03) = **4 rolls**.

- **AC-5.3 (unit fidelity)** — *Given* two WCs where one sells by linear yard and one by roll, *when* quantities are computed, *then* each is expressed in **its own** schedule unit; the app never converts one WC's order into another WC's unit.
- **AC-5.4 (waste isolation)** — *Given* a WC with a pattern repeat, *when* quantity is computed, *then* the repeat loss appears in the drop math and the waste % is applied once, on top — verifiable by toggling waste to 0% and seeing the repeat-driven quantity remain.

### FR-6 — Aggregate per WC across the whole set
Sum every application of a WC (across rooms/walls/sheets) into one order line per WC, rounded up to the sale unit.

- **AC-6.1** — *Given* WC-1 is applied in three rooms yielding raw 10.5 + 6.0 + 4.5 LY, *when* aggregated with 10% waste, *then* total = 21.0 LY raw → 23.1 LY with waste → order line shows both, and bolts = ceil(23.1/30) = **1 bolt**.
- **AC-6.2** — *Given* the same room appears on two sheets (plan + elevation) for the same wall, *when* aggregated, *then* that wall is counted **once** (no double count — see §6).

### FR-7 — Present the takeoff to the estimator
Produce a reviewable, per-WC output (§5) with drill-down to the rooms/walls and dimensions behind each number, plus every set-read value shown alongside.

- **AC-7.1** — *Given* a completed run, *when* the estimator opens WC-1's line, *then* they see the contributing rooms, each wall's width/height/net area, the drops/cut math, waste applied, and final order qty.
- **AC-7.2** — *Given* any value that was auto-read (dimension or schedule field), *when* the estimator views it, *then* its source (which sheet, read how) is shown and it is editable, with the quantity recomputing on edit.

### FR-8 — Flag rather than guess
Any missing, contradictory, or ambiguous input (unknown WC definition field, missing ceiling height, unresolved "U.N.O.", tag with no schedule definition, tag applied to no locatable wall) is surfaced as a blocking review item. The app computes no quantity that depends on a flagged value.

- **AC-8.1** — *Given* a wall tagged `WC-3` but WC-3 is absent from the schedule, *when* the run executes, *then* WC-3 is reported as "defined-but-missing" and no WC-3 quantity is fabricated.
- **AC-8.2** — *Given* the finish plan says `ALL WALLS: WC-1` and an elevation of the same room shows `WC-2` on every wall, *when* applications resolve, *then* the conflict is flagged for the estimator, not auto-resolved.

### Non-functional (kept minimal, single-user desktop)
- **NFR-1 (transparency)** — Every computed number is traceable to its inputs (formula + source dimensions) on screen. No black-box totals.
- **NFR-2 (determinism)** — The same input set + same settings yields identical numbers on every run.
- **NFR-3 (offline)** — Core takeoff runs locally without network; only the optional vision/OCR step (§4) may call out, and that must be a clearly-labeled choice.
- **NFR-4 (correctable)** — No auto-read value is final until the estimator confirms it.

---

## 3. Input → Processing → Output Data Flow

```
INPUT                     PROCESSING                                  OUTPUT
─────                     ──────────                                  ──────
PNG sheets                (1) Ingest & role-tag each sheet            Per-WC order lines:
  • schedule        ──►                                        ──►      • rooms/walls covered
  • finish plan           (2) SET READ: WC definitions from             • net area (sf / sy)
  • ceiling-ht plan            schedule (verbatim, no compute)          • waste % applied
  • elevations            (3) READ: WC tags + application               • rolls / linear yards
                               (tag → room → walls)                       to order (bolts/rolls)
                          (4) READ: dimensions                        Set-read reference block:
                               widths (plan/elev), heights (ceiling)    • mfr, pattern, roll width,
                          ──────────────── review gate ──────────────    repeat, unit  (verbatim)
                          (5) COMPUTE: area per application            Review queue:
                               = width × height − openings(policy)       • flags / conflicts /
                          (6) COMPUTE: quantity per application            unknowns (FR-8)
                               strip method or area method            Exportable takeoff
                          (7) COMPUTE: aggregate per WC + waste           (screen + file)
```

Key control points: the **review gate** between reading and computing (steps 4→5) is where flagged items (FR-8) stop the flow for that item; and the **set-read boundary** (step 2) whose outputs feed the compute as fixed constants but are never themselves computed.

---

## 4. Architecture Options for the PNG-Reading Step

The rest of the app (data model, math, UI, export) is the same regardless. The real design choice is **how tags and dimensions get out of the PNGs**. Three options, worst-to-best on automation but that is not the only axis.

### Option 1 — Manual dimension entry (assisted)
The app displays each sheet; the estimator clicks a room/wall and types the width, height, tag, and reads schedule fields into a form. The app does the math and bookkeeping only.

- **Pros:** Simplest to build; no OCR/vision dependency; numbers are exactly what a trained estimator sees; effectively no misread risk; fully offline; deterministic. Fastest path to a trustworthy v1.
- **Cons:** Most manual effort per set; value is "calculator + organizer," not "reader"; scales poorly to large sets.

### Option 2 — OCR-assisted extraction
Run OCR (e.g. a Tesseract-class engine or a cloud OCR) over the sheets to auto-pull dimension strings ("12'-0\""), WC tags, and schedule cells; the estimator confirms/corrects.

- **Pros:** Automates the tedious reading of printed text; schedule tables and dimension strings are printed text, which OCR handles reasonably; keeps a human confirm step; can run offline with a local engine.
- **Cons:** Construction sheets are dense — leader lines, hatching, rotated text, tight tables — so OCR accuracy is uneven and needs heavy post-parsing (feet-inch parsing, associating a tag with the right wall). Association ("which room does this WC belong to") is *layout* understanding OCR alone does not give. Higher build/tuning cost; error modes are silent unless every value is reviewed.

### Option 3 — Vision-model extraction
Use a multimodal vision model to read each sheet and return structured data (tags, their rooms/walls, dimensions, schedule rows), which the estimator confirms.

- **Pros:** Best at the hard part — *associating* a tag with a room/wall and reading a schedule table into structured fields, including messy layouts; can return "unsure" so ambiguities land in the review queue (FR-8) naturally; least manual effort when it works.
- **Cons:** Non-deterministic and can hallucinate a plausible-but-wrong dimension — unacceptable for numbers unless every value is human-confirmed; typically needs a network/API call (cost + offline story); needs guardrails so it never *computes* the takeoff (it reads; the app's math engine computes).

### Recommendation
**Build the app around Option 1 as the foundation, and add Option 3 (vision) as an assist layer that pre-fills the same forms — not as an autonomous path.** Concretely:

- The data model, math engine, review UI, and export are built once and are input-source-agnostic.
- v1 ships with **manual entry** (Option 1): trustworthy, offline, deterministic, and it forces the review UI to exist.
- v1.1 adds a **vision pre-fill** (Option 3): the model proposes tags/dimensions/schedule fields into the *same* editable forms, with source + confidence shown, and low-confidence items auto-route to the review queue. The estimator confirms every number before it's final (A4, NFR-4).
- **OCR (Option 2)** is a middle path worth considering specifically for the **schedule table** (printed, tabular, high-value) even if vision handles the plans/elevations. It is not recommended as the primary reader for the plans because tag-to-wall association is a layout problem it handles poorly.

This ordering means the app is useful and correct on day one, and automation is layered on without ever letting an unconfirmed machine-read number reach an order.

---

## 5. Output the Estimator Sees

A per-WC takeoff, screen-first with export. One card/line per WC, drill-down underneath, set-read reference alongside, flags surfaced up top.

**Per-WC order line (the headline):**

| WC | Product (set read) | Rooms | Net area | Waste | Order qty |
|----|--------------------|-------|----------|-------|-----------|
| WC-1 | Mfr / Pattern, 54" bolt, 18" straight | 101, 103, 105 | 210 sf / 23.3 sy | 10% | **12 LY (1 bolt)** |
| WC-2 | Mfr / Pattern, 54", no repeat | Lobby | 320 sf / 35.6 sy | 15% | **4 rolls** |
| WC-3 | *defined-but-missing — flagged* | 210 | — | — | **⚠ review** |

**Drill-down under each WC (per contributing room/wall):**
room → wall → width × height → openings deducted → net area → drops & cut length (if strip method) → subtotal. So WC-1 / Room 101 / back wall shows: `12'-0" × 9'-0", door −21 sf, net 87 sf, 3 drops × 126", 10.5 LY raw`.

**Set-read reference block (verbatim, clearly non-computed):** manufacturer, pattern name, roll/bolt width, pattern repeat + match type, coverage/unit — shown exactly as the schedule states them, labeled "from schedule."

**Waste & policy summary:** waste % used, opening-deduction policy + threshold, trim allowance — so the reader knows the settings behind the numbers.

**Review queue:** every FR-8 flag (missing height, undefined WC, unresolved U.N.O., conflict) listed with the sheet it came from and what it blocks.

**Export:** a takeoff file the estimator can hand off (e.g. a spreadsheet for the order + a PDF/printable summary). Raw vs with-waste figures both shown; nothing rounded away silently.

---

## 6. Edge Cases

- **Missing tags / undefined WC.** A wall tagged WC-3 but WC-3 absent from the schedule → "defined-but-missing," flagged, no quantity fabricated (AC-8.1). Conversely a WC defined in the schedule but applied nowhere → "defined, unused," reported so the estimator can confirm it's intentional.
- **No pattern repeat.** Repeat = 0 / random match → use area method (Method B), skip drop rounding; make sure repeat loss isn't added anyway (AC-5.4).
- **Half-drop match.** Repeat present but half-drop → cut length rounding differs from straight match and drop-to-drop offset changes yield; if match type is unknown, flag it (Q7) rather than assume straight.
- **Partial-height walls.** Wainscot, back-wall accent to a datum, wallcovering above/below a chair rail → height is not the full ceiling height; take the applied height from the elevation, not the ceiling-height plan. If only a plan tag exists with no height qualifier, flag.
- **Openings.** Doors/windows/storefront/casework: deduction is policy-driven with a threshold (Q4); always itemize what was and wasn't deducted; never let a large glazed opening silently inflate the order.
- **Multi-sheet rooms / double counting.** The same wall shown on both the finish plan and an elevation must be counted once (AC-6.2). De-dupe by (room, wall) identity, preferring the elevation for applied height and the plan for width; if the two disagree on width, flag the conflict.
- **Blanket note vs. override conflict.** Plan says "ALL WALLS WC-1," elevation shows WC-2 on every wall → conflict, flagged, not auto-resolved (AC-8.2).
- **Non-rectangular / sloped / curved walls.** Sloped ceiling (area = average height × width, or trapezoid), curved wall (developed length), soffit returns → out of the base rectangular model; v1 flags for manual area entry rather than guessing geometry.
- **Unreadable dimension.** Dimension text illegible in the PNG and no fallback → do not pixel-guess silently; require manual entry (ties to Q1).
- **Mixed units of sale across WCs.** One WC by LY, another by roll → keep each in its own unit (AC-5.3); the aggregate view must not blend them.
- **Rounding direction.** Always round the *final order* up to the sale unit; never round intermediate areas down in a way that loses material. Show raw and rounded.

---

## 7. Task Breakdown for the Implementer

Ordered so a working, trustworthy manual-entry app exists before any automation is added. No task below asks anyone to write app code as part of *this* plan — this is the build list for whoever implements it.

**Phase 0 — Foundations**
1. Define the data model: `DrawingSet`, `Sheet(role)`, `WCDefinition` (set-read fields), `Room`, `Wall(width, height, openings)`, `Application(wc, room, wall, applied_height)`, `TakeoffLine`. Make it input-source-agnostic.
2. Implement the **math engine** as a pure, independently-testable module: area (with opening policy), strip method (Method A), area method (Method B), aggregation + waste, unit handling. No UI, no I/O.
3. Write unit tests for the math engine straight from §2 — including AC-5.1 (12 LY / 1 bolt) and AC-5.2 (4 rolls) as fixtures, plus waste-isolation (AC-5.4) and mixed-unit (AC-5.3).

**Phase 1 — Manual-entry desktop app (Option 1, the trustworthy v1)**
4. Build the desktop UI shell: import PNGs, assign sheet roles (FR-1), display sheets with zoom.
5. Build the set-read entry form for WC definitions (FR-2), labeled non-computed.
6. Build the application + dimension entry: pick a room/wall, enter width/height/tag/openings (FR-3, FR-4).
7. Wire entry → math engine → per-WC output view with drill-down (FR-5, FR-6, FR-7).
8. Implement the review queue and flagging (FR-8) and the policy/settings panel (waste %, opening threshold, trim allowance).
9. Implement export (spreadsheet + printable summary), raw vs with-waste shown (§5).
10. Validate end-to-end on the "Domain Spring Cypress" set (or a representative set) with an estimator; confirm numbers against a hand takeoff.

**Phase 2 — Assisted reading (Option 3 vision pre-fill, optional Option 2 OCR for schedule)**
11. Add an extraction adapter interface (input: sheet image; output: proposed tags/dimensions/schedule rows + source + confidence) so readers are pluggable.
12. Implement the vision pre-fill adapter; route low-confidence/ambiguous outputs to the review queue; every value lands in an editable, confirmable field — never final unmodified.
13. (Optional) Add an OCR adapter targeted at the schedule table.
14. Add a "confirm all read values" gate before any quantity is treated as final (enforces A4 / NFR-4).
15. Re-validate against the same set: confirm pre-fill speeds entry without changing confirmed numbers.

**Cross-cutting**
16. Traceability: every displayed number links to its formula + source (NFR-1).
17. Determinism check: same inputs + settings → identical output (NFR-2).
18. Guardrail test: confirm the vision/OCR layer can only *populate reads* and can never invoke or alter the compute path (the set-read vs compute boundary holds).

---

### Verification note
The two worked cases were arithmetic-checked: AC-5.1 → 3 drops × 126" = 378" = 10.5 LY, ×1.10 = 11.55 → 1 bolt / order 12 LY; AC-5.2 → 320/9 = 35.56 sy, ×1.15 = 40.89, ÷13.5 = 3.03 → 4 rolls. No takeoff was performed on any real set here and no application code was written — this document plans the app that does both.
