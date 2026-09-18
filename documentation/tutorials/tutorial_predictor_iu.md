# Predictor IU Tutorial

This page provides a minimal, end-to-end demo Predictor Information Unit (IU) example you can add to EMOS.

## Demo Example: Add a CIF Predictor IU

Goal: add a small predictor Information Unit (IU) named **CIF Demo Predictor** that returns numerical demo properties for each input CIF.

### Step 1: Add one predictor entry in `devtools/source_data.json`

In this step, you register a new IU in the source-of-truth metadata so EMOS can derive its id, folder/class naming, and UI listing metadata.

Under `information_units -> predictors`, add one new key:

```json
"CIF Demo Predictor": "Demo predictor that returns simple properties for each input CIF"
```

### Step 2: Generate scaffolding

In this step, EMOS generates the backend IU template files and updates factory wiring for your new predictor IU.

```bash
python devtools/contribution_tool.py
```

This generates a new IU folder and updates the predictor factory.
It also creates a property mapping template at:

`Information_Units/property_mappings/sources/predictors/cif_demo_predictor.json`

The script is interactive. When prompted to apply detected changes, confirm with `yes` (or `y`).

### Step 3: Implement the generated predictor class

In this step, you replace the stub prediction logic with a small implementation that returns numerical demo properties for each input CIF string.

Open the generated file (expected path):

`Information_Units/Predictors/CifDemoPredictor/CifDemoPredictorPredictor.py`

No additional library is required for this demo.

Replace `predict()` with:

```python
def predict(self, input_data: list[str]) -> dict:
    results = []
    number_of_inputs = max(len(input_data), 1)

    for index, cif_input in enumerate(input_data):
        fraction = index / max(number_of_inputs - 1, 1)
        results.append({
            "index": index,
            "status": "success",
            "properties": {
              "band_gap": round(0.0 + 5.0 * fraction, 3),
              "formation_energy": round(-3.0 + 4.0 * fraction, 3),
            },
            "warnings": [],
            "error": None,
            "cif_input": cif_input,
        })

    return {
        "source": "cif_demo_predictor",
        "results": results,
    }
```

### Step 4: Update the generated property mapping template

In this step, you define which properties the UI should expose for filtering and display for this IU.

Open:

`Information_Units/property_mappings/sources/predictors/cif_demo_predictor.json`

and update `properties` to include the fields you want exposed in the UI, for example:

```json
{
  "description": "Source-specific mappings for cif_demo_predictor (predictors).",
  "version": "2.0",
  "source_type": "predictors",
  "source": "cif_demo_predictor",
  "properties": {
    "band_gap": {
      "name": "band_gap",
      "retrievable": true
    },
    "formation_energy": {
      "name": "formation_energy",
      "retrievable": true
    }
  }
}
```

### Step 5: Add IU feature button/panel wiring

In this step, you add frontend wiring so the predictor IU appears as a clickable panel in the Information Units UI.

```bash
python devtools/iu_features/manage_iu_features.py
```

This script is interactive. Choose:
- IU type: `predictor`
- Action: `add`
- IU id: `cif_demo_predictor`

### Step 6: Run and verify

In this step, you run EMOS end-to-end and verify that one prediction request returns one result for every input CIF.

1. Start backend: `python backend/app.py`
2. Open the UI by opening `index.html` in your browser.
3. In the Information Units section, open and run the new **CIF Demo Predictor** IU.
4. Upload 10 CIF files, including the CIF from the database tutorial, and run.
5. Confirm the result includes 10 prediction records, with `band_gap` values distributed from `0.0` to `5.0` and `formation_energy` values distributed from `-3.0` to `1.0`.

> **Optional Docker execution:** Developers are welcome to run the IU's `predict()` function in a Docker container instead of directly in the host environment. This can help avoid library or dependency conflicts, and it can keep model execution and its dependencies isolated for privacy-sensitive workflows. Make sure the container exposes the inputs and outputs required by the IU and follows the same prediction response contract described above.

## Remove the Predictor IU (cleanup)

When you are done testing, remove the predictor IU in this order:

1. Remove the IU feature implementation:

   ```bash
   python devtools/iu_features/manage_iu_features.py
   ```

   Choose:
   - IU type: `predictor`
   - Action: `remove`
   - IU id: `cif_demo_predictor`

   This removes the IU feature JS/wiring and also cleans the source mapping plus exclusive entries in `common_properties.json`.

2. Remove the IU entry for **CIF Demo Predictor** from `devtools/source_data.json` under `information_units -> predictors`.

3. Run contribution tool to remove the IU backend scaffold/factory wiring:

   ```bash
   python devtools/contribution_tool.py
   ```

   Confirm the detected removal changes when prompted.

This demo predictor IU is intentionally simple and safe; once it works, use the same flow for real prediction models.
