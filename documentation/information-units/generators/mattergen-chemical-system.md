# MatterGen: Chemical System

**Type:** Generator  
**ID:** `mattergen_chemical_system`  
**Implementation:** `Information_Units/Generators/MattergenChemicalSystem/MattergenChemicalSystemGenerator.py`

Generates structures within a selected chemical system.

## Inputs

- `batch_size: int` (default: `64`)
- `num_batches: int` (default: `1`)
- `target_compositions: list[dict[str, int]]` (optional)
- Optional `model_path`, `properties_to_condition_on`, `record_trajectories`, and `diffusion_guidance_factor`

## Outputs

- `status: str`
- `source: str`
- `queries: dict`
- `cif_strings: list[str]`
- Optional `message`, `num_structures`, `structures`, `debug_logs`, and `job_id`
