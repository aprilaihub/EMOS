# PDD

**Type:** Predictor  
**ID:** `pdd`  
**Implementation:** `Information_Units/Predictors/Pdd/PddPredictor.py`

Computes pointwise distance distribution descriptors for crystal structures.

## Inputs

- `input_data: list[str]` containing CIF strings
- `k: int` (default: `100`)

## Outputs

- `source: "pdd"`
- `results: list[dict]`
- Each result includes `index`, `cif_input`, `status`, `warnings`, `error`, `pdd_vector`, and `pdd_matrix`
