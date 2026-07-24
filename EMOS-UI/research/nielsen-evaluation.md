# EMOS UI — Nielsen Heuristic Re-Evaluation

**Method:** Heuristic evaluation against Nielsen & Molich's 10 usability heuristics.
**Scope:** The EMOS web interface (form workspace, node editor, and the About / Team / Documentation pages).
**Purpose:** Compare the redesigned interface against the first evaluation to demonstrate measurable UX improvement.
Severity scale: 0 = not a problem, 1 = cosmetic, 2 = minor, 3 = major, 4 = usability catastrophe.

---

## 1. First evaluation (baseline)

| # | Finding | Severity | Heuristics |
|---|---------|----------|------------|
| B1 | No pipeline connection — opening a new tool destroyed the previous one; users could not chain or return | 4 | H3 User control, H6 Recognition, H7 Flexibility |
| B2 | Checkbox vs play button — identical visual weight, completely different meaning | 4 | H4 Consistency |
| B3 | Empty runs reported success ("0 records / completed successfully") | 4 | H5 Error prevention, H3 User control, H9 Help with errors |
| B4 | Predicted values shown with no uncertainty | 3 | H1 Visibility, H2 Match with real world |
| B5 | 9 generators, no guidance on which to use | 3 | H6 Recognition, H8 Minimalism, H10 Documentation |
| B6 | Raw code labels shown to the user (e.g. `Chemical_composition`) | 2 | H2 Match with real world, H8 Minimalism |

Baseline profile: **three severity-4 issues, two severity-3, one severity-2.**

---

## 2. What changed in the redesign

| Baseline issue | Change made | New severity |
|----------------|-------------|-------------|
| B1 — tool destroys previous / no way back | IUs and features open in the main panel with a **Back** control and a clickable **EMOS** breadcrumb; clicking an active feature again deselects it; selections persist across views. The **node editor** now lives on the same page via an in-page view switch. | **0** |
| B2 — checkbox vs play button | Selection is now **whole-row click** (a selection list, not a settings panel); running is a separate, clearly labelled **Open** / **Run** action. No ambiguous twin controls. | **0** |
| B3 — empty runs report success | The run button is **disabled until at least one compatible unit is selected**, and an explicit message blocks empty runs. | **0** |
| B4 — no uncertainty | Predicted values now show **± uncertainty** with a visual range bar, and stability as solid Stable / Marginal / Unstable pills. | **1** |
| B5 — generators unguided | Every IU and feature has an always-visible **clickable help popover** with a plain-English description, backed by a full **Documentation** page. | **1** |
| B6 — raw code labels / raw JSON | Units show human-readable names; the Outputs section shows a **structured summary + results table**, with raw JSON moved to a **Download JSON** action. | **1** |

---

## 3. Re-evaluation (post-redesign)

New heuristic wins introduced by the redesign, beyond fixing the baseline issues:

- **H1 Visibility of system status** — a live SOURCE → GENERATE → SCREEN → EVALUATE pipeline strip, named run stages (Initialise → Fetch → Compute → Score → Rank), progress bar and streaming log.
- **H2 Match with the real world** — outputs framed as records extracted / databases queried / retrieval mode, and real 3D crystal structures rendered from CIF rather than a synthetic animation.
- **H4 Consistency & standards** — one design system (single red accent, SF type, consistent radii), one navigation bar across every screen, one search.
- **H7 Flexibility** — the same units and features are usable both in the guided form and as a drag-and-drop node pipeline.
- **H8 Minimalism** — removed the dead second search bar, the long red AI rail, the star/twinkle decoration, and prototype/version clutter.
- **H10 Help & documentation** — dedicated Documentation page with a node-editor how-to, plus clickable help on every control.

Residual minor items (severity 1) are honest-labelling refinements rather than usability blockers, and depend partly on live backend data.

---

## 4. Before / after summary

| Metric | Baseline | Redesign |
|--------|----------|----------|
| Severity-4 (catastrophic) issues | 3 | **0** |
| Severity-3 (major) issues | 2 | **0** |
| Severity-2 (minor) issues | 1 | **0** |
| Residual severity-1 (cosmetic) | 0 | 3 |
| Heuristics with a positive signal | 4 of 10 | **10 of 10** |

**Result:** every catastrophic and major usability issue from the first evaluation has been resolved, with the remaining items reduced to cosmetic severity. The interface now gives positive support across all ten heuristics.

> Note: this is an expert (heuristic) evaluation. It predicts usability problems but is not a substitute for testing with real users — see `user-testing-plan.md`.
