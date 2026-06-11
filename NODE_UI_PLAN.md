# Node UI — Implementation Plan

## Overview

A Blender-style node editor page for EMOS where users drag Information Units (databases, generators, predictors) onto a canvas, wire them together into a processing pipeline, and execute it. Each node shows its own log/progress during execution.

---

## 1. New Files

| File | Purpose |
|------|---------|
| `node-editor.html` | Page shell: nav menu, canvas, sidebar, Process button |
| `node-editor.css` | All styles for the node editor (grid, nodes, wires, sidebar, etc.) |
| `node-editor.js` | All logic: drag-and-drop, node creation, wiring, pan/zoom, execution |

No backend changes. The node UI reuses the existing backend endpoints:
- `POST /api/process/toggle_IU` — activate an IU before running
- `POST /api/process/<feature_id>/stream` — SSE streaming (if we route through features)
- Or direct calls to IU `.process()` via a new lightweight endpoint

> **Decision point**: The current backend processes *Features* (which internally orchestrate IUs). The node editor bypasses features and orchestrates IUs directly from the frontend. We will need **one new backend endpoint** that accepts a single IU invocation (type + key + inputs) and streams results back via SSE. This avoids coupling the node UI to the Feature layer.
> **ANSWER**: Ok, create a new backend endpoint that does not interfere with the Feature layer as is. 
---

## 2. Navigation Integration

Add `"Node UI"` link to the `<ul class="nav-links">` in **every** page's nav menu (`index.html`, `about.html`, `team.html`, `documentation.html`, `node-editor.html`).

```html
<li><a href="node-editor.html">Node UI</a></li>
```

---

## 3. Page Layout (`node-editor.html`)

```
┌─────────────────────────────────────────────────────┬──────────────┐
│                                                     │  SIDEBAR     │
│                                                     │              │
│              CANVAS (SVG wires + HTML nodes)         │ ▸ Databases  │
│              infinite pan & zoom                    │   COD        │
│              dot-grid background                    │   MatProj    │
│                                                     │   ...        │
│                                                     │              │
│                                                     │ ▸ Generators │
│                                                     │   MatterGen  │
│                                                     │   ...        │
│                                                     │              │
│                                                     │ ▸ Predictors │
│                                                     │   MatterSim  │
│                                                     │   ...        │
│                                                     │              │
│                                                     │ ▸ Utility    │
│                                                     │   CIF Viewer │
│                                                     │   Text View  │
│                                                     │              │
├─────────────────────────────────────────────────────┴──────────────┤
│  [ ▶ Process ]   [ 🗑 Clear ]                    zoom: 100%        │
└────────────────────────────────────────────────────────────────────┘
```

**Key elements:**
- **Canvas container** — `div.node-canvas` with CSS `overflow: hidden`. Inside:
  - `div.canvas-transform` — the pannable/zoomable layer (CSS `transform`)
  - `svg.wires-layer` — SVG overlay for Bézier connection wires
  - Individual `div.node` elements positioned absolutely
- **Sidebar** — `div.node-sidebar` on the right, fixed width (~260 px), collapsible sections
- **Bottom toolbar** — Process button (bottom-left), Clear button, zoom indicator

---

## 4. Node Types & Data Model

### 4.1 Internal State

```js
// Global state
const nodeState = {
    nodes: {},          // id → { type, key, x, y, inputs: {}, outputs: {} }
    connections: [],    // [{ fromNodeId, fromPort, toNodeId, toPort }]
    nextId: 1,
};
```

### 4.2 Node Categories

| Category | Type key | Inputs (ports) | Input fields | Outputs (ports) |
|----------|----------|----------------|--------------|-----------------|
| Database | `database` | — (none) | Material formula, property filters, min/max ranges | `cif` (CIF string) |
| Generator | `generator` | — (none) | Model-specific params (from property_mappings) | `cif` (CIF string) |
| Predictor | `predictor` | `cif` (CIF string) | Property selection, parameters | `result` (dict/string) |
| CIF Viewer | `cif_viewer` | `cif` (CIF string) | — | — |
| Text Viewer | `text_viewer` | `any` (string/dict) | — | — |

### 4.3 Node HTML Structure

Each node is a `div.node` with:
```
┌──────────────── Node Title ─────────────────┐
│  ● input-port       [type: Database]        │
│                                             │
│  ┌─ Input Fields ─────────────────────────┐ │
│  │ Formula: [________]                    │ │
│  │ Property: [dropdown▾]                  │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  ┌─ Log / Output ─────────────────────────┐ │
│  │ (scrollable log area, hidden until run)│ │
│  └────────────────────────────────────────┘ │
│                                             │
│                         output-port ●       │
└─────────────────────────────────────────────┘
```

- Input ports: left edge, small coloured circles
- Output ports: right edge, small coloured circles
- Title bar: draggable handle, colour-coded by category
- Body: collapsible input fields + log area

---

## 5. Drag & Drop from Sidebar

1. Sidebar items have `draggable="true"` and carry `data-type` (database|generator|predictor|cif_viewer|text_viewer) and `data-key` (e.g. `"cod"`, `"mattersim"`).
2. `dragstart` sets the data on `dataTransfer`.
3. Canvas listens for `dragover` (prevent default) and `drop`.
4. On `drop`, create a new node at the drop position (adjusted for pan/zoom transform).

---

## 6. Wiring (Connections)

- Click-and-drag from an **output port** circle to an **input port** circle.
- While dragging, render a temporary Bézier curve following the mouse.
- On release over a valid input port, create a connection.
- Connections rendered as SVG `<path>` cubic Bézier curves in `svg.wires-layer`.
- Colour-coded by data type (e.g. CIF = blue, result = green).
- Click a wire to select it; press Delete to remove.
- **Validation**: only allow compatible port types (e.g. `cif` output → `cif` input).

---

## 7. Pan & Zoom

- **Pan**: middle-mouse-drag or hold Space + left-drag on canvas background.
- **Zoom**: mouse wheel → scale `canvas-transform` with `transform: scale(z) translate(x, y)`.
- Clamp zoom between 0.25× and 2×.
- Dot-grid background scales with zoom for visual feedback.

---

## 8. Pipeline Execution ("Process" Button)

### 8.1 Topological Sort
When user clicks **Process**:
1. Build a DAG from `nodeState.connections`.
2. Topological-sort the nodes.
3. Detect cycles → show error if found.

### 8.2 Execution Loop
For each node in topological order:
1. Gather input data from connected upstream node outputs.
2. Merge with the node's own input field values.
3. Call the backend endpoint for this IU type.
4. Stream SSE events into the node's log area (progress, logs).
5. Store the node's output AS STRING, NOT AS FILE (CIF string, prediction result, etc.).
6. Pass output to downstream connected nodes.

### 8.3 New Backend Endpoint

```python
@app.route('/api/node/run', methods=['POST'])
def run_node():
    """
    Execute a single Information Unit.
    Body: { "type": "database"|"generator"|"predictor",
            "key": "cod"|"mattersim"|...,
            "inputs": { ... } }
    Returns: SSE stream with log, progress, result, done events.
    """
```

This endpoint:
- Instantiates the IU from the appropriate factory
- Calls its `.process()` or `.predict()` method
- Streams logs and results back via SSE

### 8.4 Node Visual Feedback During Execution
- **Waiting**: grey border, dimmed
- **Running**: pulsing blue border, spinning indicator in title bar, log area visible and streaming
- **Done**: green border flash, output ports filled with data
- **Error**: red border flash, error shown in log area

---

## 9. CIF Viewer Node

- Uses `$3Dmol.js` (already loaded in index.html — will also load in node-editor.html).
- When a CIF string arrives at the input port, render it in a `div` inside the node body.
- Node body has a fixed-size 3D viewport (~300×250 px).
- Viewer supports rotate/zoom within the node.

---

## 10. Text Viewer Node

- Displays any string or JSON dict in a scrollable `<pre>` block inside the node body.
- If input is a dict/object, pretty-print it with `JSON.stringify(data, null, 2)`.
- Auto-updates when upstream node produces output.

---

## 11. Styling Approach

- **Dark theme** canvas (matches Blender aesthetic): `#1e1e1e` background with subtle dot grid.
- **Node colours** by category:
  - Database: blue header (`#4a9eff`)
  - Generator: purple header (`#9b59b6`)
  - Predictor: green header (`#2ecc71`)
  - CIF Viewer: teal header (`#1abc9c`)
  - Text Viewer: orange header (`#e67e22`)
- **Wire colours**: follow output port type colour.
- **Font**: same Montserrat as the rest of the app.
- Sidebar: slightly lighter dark (`#2a2a2a`), with collapsible sections.

---

## 12. Implementation Order

### Phase 1 — Static Shell
1. Create `node-editor.html` with nav, canvas container, sidebar (populated from `ui_data.json` categories), and bottom toolbar.
2. Create `node-editor.css` with layout, dark theme, grid background.
3. Add "Node UI" link to all nav menus.

### Phase 2 — Node Creation & Dragging
4. Implement drag-from-sidebar → create node on canvas.
5. Node rendering: title bar, input fields (based on type/key), input/output ports.
6. Node dragging within canvas (reposition).

### Phase 3 — Wiring
7. Port click-drag → temporary wire → snap to target port.
8. SVG Bézier wire rendering & updating on node move.
9. Wire deletion (click + Delete).
10. Port compatibility validation.

### Phase 4 — Pan & Zoom
11. Canvas panning (middle mouse / Space+drag).
12. Mouse wheel zoom with transform.
13. Grid background scaling.

### Phase 5 — Pipeline Execution
14. Add new backend endpoint `POST /api/node/run`.
15. Topological sort of the node graph.
16. Sequential execution with SSE streaming per node.
17. Data passing between connected nodes.
18. Node visual state feedback (waiting/running/done/error).

### Phase 6 — Utility Nodes
19. CIF Viewer node (3Dmol.js rendering).
20. Text Viewer node (pretty-print).

### Phase 7 — Polish
21. Wire colour coding by data type.
22. Node collapse/expand toggle.
23. Minimap (optional, low priority).
24. Save/load pipeline to JSON (optional, low priority).

---

## 13. What We Do NOT Change

- `backend/app.py` existing endpoints — untouched (we add one new endpoint).
- `index.html`, `script.js`, `styles.css` — only change is adding the nav link.
- Feature architecture (`BaseFeature.py/js`, Feature subclasses) — untouched.
- `property_mappings.json`, `ui_data.json` — read-only (sidebar populated from `ui_data.json`).
- Docker/deployment files — untouched.

---

## 14. Open Questions for Review

1. **Input fields per node**: Should we auto-generate input fields from `property_mappings.json` (like the current feature UI does), or keep them simpler for the node editor (e.g. just a CIF text area for databases, a formula field for generators)?
    ***ANSWER***: yes, auto-generate input fields from property_mappings.json, as I have done for MatterGen, but same concept for all information units.
2. **Multiple outputs**: Should a database node produce multiple CIF strings (one per result), or a single combined output? If multiple, we need array port support.
    ***ANSWER***: databases and generators can produce multiple CIF strings. Make sure arrays are supported, and the cif viewer has a dropdown to select which structure to show.
3. **Save/Load**: Should we support saving pipeline layouts to JSON for later reload? (Can defer to Phase 7.)
    ***ANSWER***: not yet, but keep in mind it might be needed in the future.
4. **Parallel execution**: Should independent branches of the DAG execute in parallel, or strictly sequential for simplicity?
    ***ANSWER***: for now keep it fully sequential

---

## 15. Implementation Ambiguities (to resolve before coding)

### A. Database return format mismatch
Databases currently return **file paths** (`list[str]` of CIF file paths on the server), not CIF strings. The plan says "outputs are strings, not files." The new `/api/node/run` endpoint will need to **read the CIF files into strings** before returning them to the frontend. This means the backend endpoint must:
1. Call `database.retrieve(inputs)` → get file paths
2. Read each file into a CIF string
3. Return the array of CIF strings in the SSE `result` event

**Is this acceptable, or should we also preserve the file paths for download?**
***ANSWER***: yes, this is acceptable, and delete the generated files once read.

### B. Generator return format inconsistency
- MatterGen generators return a dict `{"structures": [...], "num_structures": N, ...}` where each structure entry contains CIF data as a string field.
- Stub generators (`GnomeGenerator`, `ImatgenGenerator`, etc.) return a bare `str` from `generate()`.
- MatterGen also has `generate_stream()` which yields SSE event dicts.

**For the `/api/node/run` endpoint:** should we always prefer `generate_stream()` when available (for real-time log streaming into the node), and fall back to `generate()` wrapped in SSE for stubs?
***ANSWER***: for real time log streaming always go for generate_stream(). Add it to the base class of each UI, if you have to, so that each subclass UI can define what it streams.


### C. Predictor input: CIF string vs file path
GBFS_PredPredictor's `predict()` accepts a CIF **file path** (or a dict with `cif_path`), not a raw CIF string. But in the node editor, the upstream data flowing through wires is CIF **strings** (from databases/generators). The backend endpoint will need to:
1. Receive the CIF string from the frontend
2. Write it to a temporary file (or modify the predictor to accept a CIF string directly)
3. Pass the temp file path to `predict()`

**Option A:** Write to a temp file in the endpoint. Simple, no predictor changes.
**Option B:** Extend `predict()` to accept `{'cif_string': '...'}` and parse it with `pymatgen.core.Structure.from_str()`. Cleaner long-term.
Which approach?
***ANSWER***: Go with option B, extend it to accept cif string.

### D. Predictor property selection
GBFS_PredPredictor requires a `property_name` at construction time (e.g. `"bandgap"`, `"e_form"`). A single GBFS node can only predict one property. In the node editor:
- **Option A:** Each GBFS node has a dropdown to select the property. The backend instantiates `GBFS_PredPredictor(predictor_name="gbfs", property_name=selected)` per run.
- **Option B:** A single GBFS node predicts all 6 properties at once (like `/batch-predict` in the Docker API).

Which behaviour? (Other predictors like MatterSim are single-call-for-everything.)
***ANSWER***: Go with option B, predict everything with a single call

### E. Multiple CIF outputs → predictor fan-in
A database or generator node may output an **array** of CIF strings. When wired to a predictor node:
- **Option A:** The predictor runs once per CIF in the array (automatic batch loop), and its output becomes an array of results.
- **Option B:** The predictor receives only the first CIF (user must select via a CIF Viewer or selector node).
- **Option C:** The predictor receives the full array and the backend handles batching internally.

Which fan-in strategy?
***ANSWER***: Go with option A, predictor runs for all CIFs in array, returns array of results

### F. Node deletion
Can users delete individual nodes from the canvas? If yes:
- Should deleting a node also delete all connected wires? ***ANSWER***: Yes
- Keyboard shortcut (Delete/Backspace) or right-click context menu, or both? ***ANSWER***: both

### G. Sidebar population: hardcoded vs dynamic
The sidebar lists databases, generators, and predictors. Should it:
- **Option A:** Be hardcoded in `node-editor.html` (like `index.html` does today with checkbox lists)?
- **Option B:** Fetch `ui_data.json` at page load and dynamically build the sidebar?

Option B is more maintainable but adds an async fetch on page load.
***ANSWER***: go with option B, fetch it from ui_data

### H. Port type `any` on Text Viewer
The text viewer accepts `any` input. Should it also accept CIF strings (showing raw CIF text), or should the type system distinguish between `cif`, `result`, and a generic `any` that matches everything?

***ANSWER***: Allow it to show raw CIF string, don't differentiate. The text viewer should basically show any possible output as text.

### I. Wire re-connection
If a user drags a new wire to an input port that already has a connection, should the old connection be replaced, or should the drop be rejected?

***ANSWER***: Replace connection

### J. Node resizing / scrolling
Some nodes (CIF Viewer, Text Viewer) have content that may be large. Should nodes:
- Have a fixed size with internal scrolling?
- Be resizable by dragging a corner?
- Auto-expand to fit content?

***ANSWER***: Allow resizable nodes by dragging corner, plus internal strolling at current size.

---

## 16. Final Implementation Ambiguities

### K. Generator CIF extraction: which key holds the CIF strings?
MatterGen's result dict contains **both** `structures` (pymatgen JSON objects) and `cif_strings` (plain CIF text). Stub generators (GNoME, iMatGen, etc.) return a bare `str` from `generate()` — currently just placeholder text, not a real CIF. For the node output:
- I will normalise in the backend endpoint: if the result has `cif_strings`, use that array. If the result is a plain `str`, wrap it as `[str]`. If it has `structures` but no `cif_strings`, convert via pymatgen.
- **Is this acceptable?**
***ANSWER***: Yes

### L. Database input fields: what fields should a database node expose?
Looking at `CodDatabase.retrieve()`, it accepts `{query, limit, ...property_filters}`. The property filters come from property_mappings.json keys specific to that database. For the node UI, should each database node show:
- **Minimal**: just `query` (text) + `limit` (number)?
- **Full**: `query` + `limit` + auto-generated filter fields from property_mappings (same pattern as generators)?

This matters because auto-generating database filters from property_mappings involves scanning all properties for entries matching that database key (e.g. `"cod"`) and building min/max range inputs. This is significant work — but you said to auto-generate from property_mappings.
***ANSWER***: Go with the full option with auto-generated filter fields from property_mappings

### M. Predictor batch-all: GBFS has 6 properties — what about other predictors?
Answer to D says "predict everything with a single call." GBFS has 6 sub-properties that each need a separate `GBFS_PredPredictor` instance. Other predictors (MatterSim, M3GNet, etc.) are stubs that return `None`. For the endpoint:
- For `gbfs`: instantiate all 6 property predictors, run each, and aggregate results into one dict `{bandgap: ..., e_form: ..., ...}`.
- For all other predictors: call their single `predict()` method and return whatever it returns.
- **Correct?**
***ANSWER***: Correct. Make sure gbfs calls the predict_batch, which essentially does this, i.e. predicts all properties. DOUBLE CHECK IF THIS IS INDEED THE CASE, and tell me if not.


### N. Backend endpoint location
The new `/api/node/run` endpoint goes into the existing `backend/app.py` file (alongside the existing endpoints), not a separate file. **Correct?**
***ANSWER***: Yes, correct

### O. property_mappings.json loading on the node page
The node editor page needs to load `property_mappings.json` to auto-generate input fields. The current `BaseFeature.js` loads it via a `<script>` tag or fetch. For the node editor:
- I'll fetch it from `Information_Units/property_mappings.json` (relative URL) at page load, same as the existing app does.
- The sidebar will be built from `devtools/ui_data.json`.
- Both are fetched client-side. **Correct?**
***ANSWER***: Sounds correct, but do whatever is most efficient for running the app

### P. Wiring from output port to input port — direction only, or bidirectional drag?
Currently the plan says drag from output → input. Should users also be able to drag from an **input port backward** to an output port to create the same connection? (Blender supports both directions.)
- I'll implement **output → input only** for simplicity unless you say otherwise.
***ANSWER***: do output to input only

### Q. Multiple instances of the same IU
Can a user drag two COD database nodes or two GBFS predictor nodes onto the canvas (same type, same key, different inputs/parameters)?
- I'll assume **yes** — each drag creates a new independent node instance.
***ANSWER***: Yes

### R. Cancel support during node execution
The existing app has cancel support per feature. Should the node editor support cancelling a running pipeline mid-execution?
- If yes: a "Cancel" button appears next to "Process" while running, and the currently-executing node's backend call is aborted (and downstream nodes are skipped).
- If no: once Process is clicked, it runs to completion or error.
***ANSWER***: Yes, include cancel button and functionality

### S. Error handling mid-pipeline
If node 3 of 5 in the pipeline fails:
- **Option A:** Stop the entire pipeline, mark the failed node red, leave downstream nodes grey.
- **Option B:** Skip the failed node, continue with downstream nodes that don't depend on it.
- I'll go with **Option A** (stop on first error) unless you say otherwise.
***ANSWER***: Yes, go with option A.