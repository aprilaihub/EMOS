# Minimal Strategy: `manage_predictor_iu_features.py`

## Goal

Build one general script that can create and remove Predictor IU Features, the same way we already do for databases and generators.

Assumptions for this strategy:

- each predictor is correctly implemented
- each predictor `predict()` works
- **predictor mapping files have been corrected to use "predictable" spelling (fixed before manager script is created)**
- each predictor has property mappings in `Information_Units/property_mappings/sources/predictors/*.json`
- predictor input is CIF string(s)
- predictor output is predicted properties from the mapping
- if output includes CIF text, show it in the same CIF viewer style used in IU features

---

## General UI For Any Predictor

Use one shared UI template for all predictors.

### Inputs

- Primary input: multi-file CIF upload (`.cif`, multiple files)
- drag-and-drop on the same upload box
- Small preview that shows cif visualization for the uploaded cif files. cif viewer will be same as that in outputs of generator/databse IU feature. 

Why this is the default:

- most intuitive for users working with crystal structures
- directly maps to `predict(list_of_cif_strings)`
- reliable for single and batch workflows

Internal conversion rule:

- each uploaded `.cif` file is read as text and appended to the `list[str]` payload in UI order
- zip files containing multiple `.cif` files are extracted and each CIF appended in order
- structure indices in inputs and outputs always correspond (structure N in dropdown = input N)

### Process
- same UI as generators (streaming endpoint): process and cancel button with live processing log
- uses `/api/process/iu/predictor/<predictor_id>/stream` for real-time updates

### Outputs

- at the top a dropdown indexed by input order (1..N CIF files uploaded) to select which structure's results to view
- selected structure index always matches input file index for traceability
- based on selection, show predicted properties and status from that result entry
- properties are created using property mappings of the specific predictor (marked as predictable)
- downloadable JSON result of full prediction output

CIF viewer section should only appear when predictor output contains CIF text fields.

---

## How To Keep It Generic

Do not hardcode predictor-specific fields.

Drive the UI from:

- predictor id from `PredictorFactory.py`
- display name/description from `devtools/ui_data.json`
- predicted property names from `Information_Units/property_mappings/sources/predictors/<predictor>.json`

For each predictor:

1. read its mapping file
2. collect properties marked as predictable
3. render those properties in the output view
4. if output contains CIF-like content, enable CIF viewer

---

## What `manage_predictor_iu_features.py` Should Do

Same workflow as the other manager scripts.

### `--list`

Show for each predictor:

- mapping exists or not
- button row exists in `index.html`
- module entry exists in `script.js`
- JS IU feature file exists
- fully implemented or not

### `--add <PREDICTOR_ID>`

- add/upgrade predictor row in `index.html` with IU feature button
- add/upgrade predictor module entry in `script.js`
- create `Features/IU_Features/Predictors/<ClassName>.js` from one general template

### `--remove <PREDICTOR_ID>`

- remove predictor IU button row (keep plain checkbox label)
- remove module entry from `script.js`
- remove predictor IU feature JS file

---

## Predictor IU Feature JS (Single General Template)

Create one reusable JS class template that works for every predictor.

Template behavior:

1. collect CIF input(s)
2. call predictor IU endpoint
3. receive result JSON
4. render only mapped properties for that predictor
5. show download link for full JSON
6. if CIF output exists, show CIF viewer panel

This keeps the script future-proof: new predictors work without writing a new custom UI file, as long as they follow the expected contract and mapping registration.

---

## Pre-Implementation Step (✅ COMPLETE)

**Fix mapping file spellings:**
- ✅ Fixed all misspellings: `predicatble` → `predictable` across:
  - `Information_Units/property_mappings/sources/predictors/synthnn.json` (2 fixes)
  - `Information_Units/property_mappings/sources/predictors/mattersim.json` (9 fixes)
  - `Information_Units/Predictors/Synthnn/SynthnnPredictor.py` (1 fix)
- Manager script will assume only `predictable` flag exists

## Minimal Implementation Plan

1. ✅ fix predictor mapping spelling (pre-step complete)
2. ✅ create `devtools/iu_features/manage_predictor_iu_features.py` with full CLI support
   - `--list`: Shows all predictors and their implementation status
   - `--add PRED_ID`: Adds Complete IU feature (button, module, JS file)
   - `--remove PRED_ID`: Removes all wiring completely
   - Interactive mode: Prompts user to select action
   - Tested: Add/remove flow works end-to-end
3. ✅ Adapted all discovery logic to predictor paths
   - Factory: `Information_Units/Predictors/PredictorFactory.py`
   - Mappings: `Information_Units/property_mappings/sources/predictors/`
   - Output: `Features/IU_Features/Predictors/`
4. ✅ Added predictor module block support in script.js
   - Created `/predictor: { ... }` block with proper indexing (starting at ID 2001)
   - Handles case when block doesn't exist yet (creates it on first predictor add)
5. ✅ Generic predictor IU feature template created
   - Multi-file .cif upload + drag-drop UI
   - CIF file validation and 3D viewer display
   - Input-indexed output structure (dropdown by input index)
   - Dynamic property rendering from mapping JSON
   - Streaming endpoint support (`/api/process/iu/predictor/<id>/stream`)
   - N/A display for missing property values
   - JSON download of predictions
6. ✅ End-to-end testing completed:
   - `--list`: Shows 4 predictors (mattersim, synthnn, gbfs, gbfs_2d)
   - `--add mattersim`: Creates JS, adds button row, wires module entry
   - `--remove mattersim`: Cleans up all artifacts
   - Verified file deletion and index.html/script.js modifications

---

## Bottom Line

Keep predictors simple and general:

- one common input model: CIF string(s)
- one common output model: mapped predicted properties
- one optional extension: CIF viewer when CIF output is present

With this approach, `manage_predictor_iu_features.py` can support any properly implemented predictor automatically.

---

## Implementation Status: ✅ COMPLETE

### Deliverables

| Component | File | Status |
|-----------|------|--------|
| Manager Script | `devtools/iu_features/manage_predictor_iu_features.py` | ✅ Created & Tested |
| Predictor Block | `script.js` | ✅ Ready for insertion |
| UI Template | Generic template in manager | ✅ Dynamically generated |
| Mapping Fixes | Properties files | ✅ Fixed (`predictable` standardized) |

### Ready for Next Steps

The manager script is production-ready and tested. To activate a predictor IU feature:

```bash
cd /home/soe/EMOS
python devtools/iu_features/manage_predictor_iu_features.py --add <predictor_id> --yes
```

Example:
```bash
python devtools/iu_features/manage_predictor_iu_features.py --add synthnn --yes
python devtools/iu_features/manage_predictor_iu_features.py --add gbfs --yes
python devtools/iu_features/manage_predictor_iu_features.py --add mattersim --yes
```

To see current status:
```bash
python devtools/iu_features/manage_predictor_iu_features.py --list
```

To remove a predictor IU feature:
```bash
python devtools/iu_features/manage_predictor_iu_features.py --remove <predictor_id> --yes
```

### Notes

- Predictor module IDs start at **2001** (distinct from generators which use 1000s range)
- Script handles missing predictor block gracefully (creates it on first predictor add)
- Each predictor gets individualized display name and description from `ui_data.json`
- Generator IU features are separate and unaffected by predictor changes
- All property mappings must declare `"predictable": true` for properties to render in UI
