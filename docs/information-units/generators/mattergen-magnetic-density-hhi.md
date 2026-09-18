# MatterGen: Magnetic Density + HHI

**Type:** Generator  
**ID:** `mattergen_magnetic_density_hhi`  
**Implementation:** `Information_Units/Generators/MattergenMagneticDensityHhi/MattergenMagneticDensityHhiGenerator.py`

Generates structures targeting magnetic density and elemental scarcity.

## Inputs

- `batch_size: int` (default: `64`)
- `num_batches: int` (default: `1`)
- `properties_to_condition_on: dict[str, Any]` (optional)
- Optional `model_path`, `target_compositions`, `record_trajectories`, and `diffusion_guidance_factor`

## Outputs

- `status: str`
- `source: str`
- `queries: dict`
- `cif_strings: list[str]`
- Optional `message`, `num_structures`, `structures`, `debug_logs`, and `job_id`
