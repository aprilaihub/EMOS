# EMOS-UI

Redesigned front end for **EMOS — the Electronic Materials Operating System**, a unified platform for
electronic-materials discovery from the APRIL AI Hub (University of Edinburgh & University of Cambridge).

Plain HTML / CSS / JavaScript, no build step. Open `index.html` or serve the folder statically.

## Run locally

```bash
python3 -m http.server 8000
# then open http://localhost:8000/
```

## Pages

| File | Purpose |
|------|---------|
| `index.html` | Landing / entry point |
| `form.html` | Guided workspace: select Information Units, open Features, run and explore results. The **node editor** opens in-page from the nav bar (no separate page). |
| `node-editor.html` | Drag-and-drop pipeline editor (embedded into the form via the nav) |
| `about.html` | What EMOS is, the pipeline and architecture |
| `team.html` | Research and advisory team |
| `documentation.html` | Getting started, Information Units, Features, node-editor how-to, FAQ |

## Structure

- `tokens.css`, `fonts.css` — design system (SF Pro Display / SF Mono, single red accent)
- `site.css` — shared styling for the About / Team / Documentation pages
- `form-app.js`, `form-data.js` — form workspace logic and data
- `node-app.js`, `node-data.js` — node editor logic and data
- `cif-samples.js` — real CIF structures for the 3D crystal viewer (rendered with vendored `assets/3Dmol-min.js`)
- `assets/` — fonts, the original EMOS logo, team photos, 3Dmol
- `research/` — Nielsen heuristic re-evaluation and the usability testing plan

## Backend

The UI runs against representative sample data in this build. It is structured so the fetch and
assistant layers can be pointed at the live EMOS backend (Render) and LLM endpoint without reworking
the interface.
