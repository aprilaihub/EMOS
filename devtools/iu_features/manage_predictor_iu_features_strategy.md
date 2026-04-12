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

## Pre-Implementation Step

**Fix mapping file spellings:**
- standardize all `predicatble` → `predictable` in `Information_Units/property_mappings/sources/predictors/*.json`
- manager script will assume only `predictable` flag exists

## Minimal Implementation Plan

1. fix predictor mapping spelling (see pre-step above)
2. create `devtools/iu_features/manage_predictor_iu_features.py`
3. copy structure from existing generator manager script
4. switch all discovery logic to predictor paths
5. add predictor block support in `script.js` (`iuFeatureModules.predictor`)
6. add a single generic predictor IU feature template under `Features/IU_Features/Predictors/`
7. verify with one predictor, then run `--list` and test all predictors

---

## Bottom Line

Keep predictors simple and general:

- one common input model: CIF string(s)
- one common output model: mapped predicted properties
- one optional extension: CIF viewer when CIF output is present

With this approach, `manage_predictor_iu_features.py` can support any properly implemented predictor automatically.
