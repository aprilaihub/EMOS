# MatterGen: MP-20 Base

**Type:** Generator  
**ID:** `mattergen_mp_20_base`  
**Implementation:** `Information_Units/Generators/MattergenMp20Base/MattergenMp20BaseGenerator.py`

Generates crystal structures with the MatterGen model trained on MP-20.

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
