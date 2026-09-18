# MatterGen: Chemical System + Stability

**Type:** Generator  
**ID:** `mattergen_chemical_system_stability`  
**Implementation:** `Information_Units/Generators/MattergenChemicalSystemStability/MattergenChemicalSystemStabilityGenerator.py`

Generates structures within a chemical system with a stability target.

## Inputs

- `batch_size: int` (default: `64`)
- `num_batches: int` (default: `1`)
- `target_compositions: list[dict[str, int]]` (optional)
- Optional `properties_to_condition_on`, `model_path`, `record_trajectories`, and `diffusion_guidance_factor`

## Outputs

- `status: str`
- `source: str`
- `queries: dict`
- `cif_strings: list[str]`
- Optional `message`, `num_structures`, `structures`, `debug_logs`, and `job_id`
