# SynthNN

**Type:** Predictor  
**ID:** `synthnn`  
**Implementation:** `Information_Units/Predictors/Synthnn/SynthnnPredictor.py`

Predicts material synthesizability from crystal structure inputs.

## Inputs

- `input_data: list[str]` containing CIF strings

## Outputs

- `source: "synthnn"`
- `results: list[dict]`
- Each result includes `index`, `cif_input`, `status`, `warnings`, `error`, `synthesizable`, and `synthesizability_score`
