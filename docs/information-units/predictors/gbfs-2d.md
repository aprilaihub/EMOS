# GBFS-2D

**Type:** Predictor  
**ID:** `gbfs_2d`  
**Implementation:** `Information_Units/Predictors/Gbfs2d/Gbfs2dPredictor.py`

Provides GBFS workflow predictions for two-dimensional layered materials.

## Inputs

- `input_data: list[str]` containing CIF strings

## Outputs

- Per-structure results include `index`, `cif_input`, `status`, `warnings`, and `error`
- Properties include `bandgap_2d`, `is_metal_2d`, `is_stable_2d`, and `is_vdw_layered`
