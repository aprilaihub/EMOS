# JARVIS-DFT

**Type:** Database  
**ID:** `jarvisdft`  
**Implementation:** `Information_Units/Databases/Jarvisdft/JarvisdftDatabase.py`

JARVIS-DFT provides computational materials data, including electronic and optical properties.

## Inputs

- `target_compositions: str`
- `batch_size: int` (default: `10`)
- Optional filters such as `band_gap`, `hse_gap`, `formation_energy_per_atom`, `hull_distance`, `density`, `bulk_modulus`, and `poisson_ratio`

## Outputs

- `source: "jarvisdft"`
- `queries: dict`
- `cif_strings: list[str]`
