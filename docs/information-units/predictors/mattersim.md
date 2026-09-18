# MatterSim

**Type:** Predictor  
**ID:** `mattersim`  
**Implementation:** `Information_Units/Predictors/Mattersim/MattersimPredictor.py`

Predicts material properties from crystal structures and can perform structure relaxation.

## Inputs

- `input_data: list[str]` containing CIF strings
- Optional flags: `compute_energy`, `compute_forces`, `compute_stress`, `relax`, `relax_atoms`, and `relax_cell`
- Optional `output_dir: str`

## Outputs

- `source: "mattersim"`
- `results: list[dict]`
- Each result includes `index`, `cif_input`, `status`, `properties`, `warnings`, and `error`
- Properties may include `energy`, `forces`, `stress`, and relaxed structure data
