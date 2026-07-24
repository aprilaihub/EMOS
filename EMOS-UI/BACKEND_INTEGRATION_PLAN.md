# EMOS-UI → Live Backend Integration Plan

> Prepared for the connect-the-backend session. **Nothing in here has been executed yet.**
> The prototype still runs fully on simulated data. This document is the safe, step-by-step
> map for wiring it to the real EMOS backend and the LLM assistant.

---

## 1. Where things stand today

**Front end (`EMOS-UI`, this repo):** 100% self-contained and simulated.
- All units/features/candidates come from `form-data.js`; crystals from `cif-samples.js`.
- There is **no `fetch()` layer at all yet** — the only mention of the backend is a comment
  in `cif-samples.js`.
- The AI assistant is a canned `setTimeout` responder in `form-app.js` (`sendAI`, ~line 1193)
  plus `nodeAIHandle` in `node-app.js`. No network calls.

**Back end (`aprilaihub/EMOS`, read-only reference):** Flask API, deployed on Render.
- `backend/app.py` (~980 lines), `CORS(app, resources={r"/api/*": {"origins": "*"}})`.
- Deploy: `render.yaml` → `emos-backend` (Flask, port 5001), `emos-mattergen` (Docker),
  `emos-gbfs-pred` (FastAPI). Backend base URL is the Render service (confirm exact host).

### Real API surface (from `backend/app.py`)
| Method & route | Purpose | UI action it backs |
|---|---|---|
| `GET /api/health` | liveness | connection check on app load |
| `GET /api/features/info` | list features + their metadata | build the Features list / IU strips |
| `POST /api/process/toggle_IU` | activate/deactivate an IU (`class_name`, `active`) | the "databases used by this feature" toggles |
| `POST /api/process/<feature_id>` | run a whole feature | the **Run** button on a Feature |
| `POST /api/process/iu/<iu_type>/<iu_id>` | run a single IU (db / generator / predictor) | node-editor node execution + IU "Open" run |
| `GET /api/debug/mattergen` | generator connectivity probe | optional status indicator |

---

## ✅ STATUS: the seam is now BUILT (this session)

`data-layer.js` exists and the UI runs through it. **Default is sim, so the showcase build
is unchanged and verified byte-identical (10-row run, plot, crystal, pins, node run, tour —
all pass with 0 errors).** To exercise the live path, no code edit needed:

```
form.html?live=1                          # live mode
form.html?live=1&api=https://<backend>    # + point at the backend
```

Proven safety property: **with `?live=1` and the backend unreachable, the app falls back to
the sample data (10 rows), shows a "Backend unavailable" toast, and a top-right connection
badge reads "backend offline (using samples)" — it never blanks the screen.**

What's wired: the feature **Run** (`completeRun` → `EmosAPI.runFeature`) and node **Run**
(`finishRun` → `maybeFetchNodeResults`) both fetch through the seam; every results read goes
through `resultRows()` / `findCand()` (form) and `liveRows()` / `nfind()` (node), which return
live rows when present and the bundled `CANDIDATES` otherwise.

What's left for the morning (all marked `// CONFIRM` / `// TODO(morning)` in code):
1. Real backend base URL + confirm it's awake.
2. Backend numeric feature ids ↔ UI ids (`FEATURE_IDS` in data-layer.js).
3. IU class names (`CLASS_NAMES` in data-layer.js).
4. Real result JSON field names (`normalizeCandidate` adapter).
5. Fill in `maybeFetchNodeResults` (node graph → backend call).
6. LLM route + key handling (see §4).

---

## 2. The seam (reference): a swappable data layer

Add a **single module** the whole UI talks to, so switching sim → live is a config flag, not a rewrite.

Create `EMOS-UI/data-layer.js` exposing one object, e.g. `EmosAPI`, with methods that mirror
the current in-memory reads:

```js
window.EmosAPI = {
  mode: "sim",                       // "sim" | "live"  (flip via ?live=1 or a localStorage flag)
  base: "",                          // Render backend URL when live
  async health() {...},
  async featuresInfo() {...},        // GET /api/features/info
  async toggleIU(className, active) {...},
  async runFeature(featureId, params) {...},        // POST /api/process/<id>
  async runIU(type, id, inputs) {...},              // POST /api/process/iu/<type>/<id>
};
```

- In **sim mode**, each method returns the existing canned data from `form-data.js`
  (wrapped in `Promise.resolve`) so behaviour is identical to today.
- In **live mode**, each method does the matching `fetch`.
- Then replace the direct data reads in `form-app.js` / `node-app.js`
  (feature render, Run handler, IU open/run) with `await EmosAPI.…`. The render code stays;
  only the data source changes.

**Why this shape:** the UI keeps working with zero backend (demo-safe for Friday), and the live
switch is one flag. No component needs to know whether data is real or simulated.

---

## 3. Field mapping to nail down before wiring

The UI's `form-data.js` shapes must be reconciled with the real API responses:
- **Feature IDs:** the UI uses string ids (`db_extract`, …); `/api/process/<feature_id>` takes an
  **int**. Map UI feature → backend numeric id (from `GET /api/features/info`).
- **IU class names:** `toggle_IU` wants the backend **`class_name`** (e.g. `MaterialsProject`,
  `CHGNet`). Add a `className` field to each unit in `form-data.js`.
- **Results schema:** confirm the real `POST /api/process/*` response fields (band gap, formation
  energy, stability, CIF string) and adapt `renderTable` / `renderPlot` / `renderCrystal` to them.
  Keep a tiny adapter function so the render code is untouched.
- **CIF:** live features return real CIF strings → feed straight into the existing 3Dmol
  `renderCIF` path (already wired), replacing the `cif-samples.js` lookup.

---

## 4. LLM assistant

There is **no LLM key or endpoint in the backend today** — this is a separate service (Aisha's
endpoint, per the original plan). Two clean options:

1. **Preferred / safest:** add a thin backend proxy route (e.g. `POST /api/assistant`) that holds
   the API key server-side and forwards to the LLM. The UI never sees the key. This is a backend
   change → do it on the backend branch, not here.
2. **UI-only interim:** point `sendAI` / `nodeAIHandle` at the LLM endpoint directly via
   `EmosAPI.assistant(prompt, context)`. Only acceptable if the key can be public/scoped;
   otherwise use option 1.

Swap point in the UI is small and already isolated: `sendAI` (form-app.js) and
`nodeAIHandle` (node-app.js). Pass the current feature + selected units as context.

---

## 5. Branch & safety strategy (recommended)

- **Front end (this repo):** do the data-layer work on a **new branch off the current one**,
  e.g. `backend-wiring`, so the demo-ready simulated build on the current UI branch
  stays untouched and presentable for the showcase.
- **Back end (`aprilaihub/EMOS`):** **do not push anything without Blessing's explicit go-ahead.**
  Atish mentioned wanting a separate branch — confirm the exact name with him. Any assistant-proxy
  route lands there, on that branch, via a PR they review.
- **Guard rails:** keep `mode:"sim"` the default; live mode behind `?live=1` so a bad backend can
  never break the presentation build. Add a visible "connecting… / offline" status from
  `/api/health` so failures are legible, not silent.
- **CORS** is already open for `/api/*`, so a browser can call the Render backend directly in dev.

---

## 6. New backend work by Atish / Alexandros to fold in

Recent live commits (`aprilaihub/EMOS`) that the UI should catch up to:
- **CHGNet** predictor added (`d2bd021`, `#32`) → add a CHGNet unit to the predictor list.
- **MOSFET evaluator**: real 2D Poisson + drift-diffusion solver and channel-material selection
  (`b9ba748`, `db818fe`, `f2ac1b0`) → the MOSFET feature's real output schema (device metrics,
  Id–Vd curve) should replace the simulated one.
- **Database Extractor**: input labels / batch-size prompt refined (`016b3eb`, `8d74dae`).
- **Node editor**: dynamic module parsing (`61d9dff`) — worth a side-by-side review of the live
  `node-editor.js` (66 KB) before assuming our inlined node editor matches its latest node types.

**These need a proper diff review against the live files, not a guess** — flagged here so the
morning session starts from the real current state, not stale assumptions.

---

## 7. Suggested order of operations (morning)

1. Confirm the live backend URL + that `/api/health` responds.
2. Build `data-layer.js` in **sim mode** and route the UI through it (no behaviour change → safe commit).
3. Flip one read (Features list) to live behind `?live=1`; reconcile the schema; verify.
4. Wire Run (feature + IU), then results schema + CIF.
5. Decide LLM option (proxy vs direct); wire the assistant.
6. Fold in CHGNet / MOSFET / node-editor updates after diffing the live files.
7. Keep sim as the default until every live path is verified.

## 8. Open items to confirm with the team
- Exact Render backend base URL, and whether it's currently up.
- Backend numeric feature ids ↔ UI feature ids.
- Real result JSON schema for each feature.
- LLM endpoint + how the key is handled (proxy strongly preferred).
- The backend branch name Atish wants the assistant proxy on.
