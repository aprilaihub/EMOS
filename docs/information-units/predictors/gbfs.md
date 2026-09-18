# GBFS

**Type:** Predictor  
**ID:** `gbfs`  
**Implementation:** `Information_Units/Predictors/Gbfs/GbfsPredictor.py`

Provides pretrained GBFS workflow predictions for material properties.

## Inputs

- `inputs: list[str]` containing CIF strings

## Outputs

- Per-structure results include `index`, `cif_input`, `status`, `warnings`, and `error`
- Properties include `bandgap`, `dielectric`, `e_form`, `is_metal`, `mob_n`, and `mob_p`
