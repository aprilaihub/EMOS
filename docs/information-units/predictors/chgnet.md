# CHGNet

**Type:** Predictor  
**ID:** `chgnet`  
**Implementation:** `Information_Units/Predictors/Chgnet/ChgnetPredictor.py`

Predicts energy, force, stress, and relaxation results for crystal structures.

## Inputs

- `input_data: list[str]` containing CIF strings
- Optional energy, force, stress, and relaxation flags
- `fmax: float` (default: `0.1`)
- `max_steps: int` (default: `500`)

## Outputs

- `source: "chgnet"`
- `results: list[dict]`
- Each result includes `index`, `cif_input`, `status`, `properties`, `warnings`, and `error`
- Properties may include energy, forces, stress, and relaxed structure data
