# MatterGen: Base Model

**Type:** Generator  
**ID:** `mattergen_base_model`  
**Implementation:** `Information_Units/Generators/MattergenBaseModel/MattergenBaseModelGenerator.py`

Generates general inorganic crystal structures with the MatterGen base model.

## Inputs

- `batch_size: int` (default: `64`)
- `num_batches: int` (default: `1`)
- Optional `model_path`, `properties_to_condition_on`, and `target_compositions`
- Optional `record_trajectories: bool` and `diffusion_guidance_factor: float | None`

## Outputs

- `status: str`
- `source: str`
- `queries: dict`
- `cif_strings: list[str]`
- Optional `message`, `num_structures`, `structures`, `debug_logs`, and `job_id`
