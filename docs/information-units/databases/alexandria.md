# Alexandria

**Type:** Database  
**ID:** `alexandria`  
**Implementation:** `Information_Units/Databases/Alexandria/AlexandriaDatabase.py`

Alexandria provides DFT materials data and crystal structures.

## Inputs

- `target_compositions: str`
- `batch_size: int` (default: `10`)
- Optional filters such as `band_gap`, `formation_energy_per_atom`, `hull_distance`, `space_group`, and `magnetization`

## Outputs

- `source: "alexandria"`
- `queries: dict`
- `cif_strings: list[str]`
- `entries: list[dict]` with material IDs, formulas, hull distance, and formation energy
