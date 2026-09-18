# MatHub-3d

**Type:** Database  
**ID:** `mathub3d`  
**Implementation:** `Information_Units/Databases/Mathub3d/Mathub3dDatabase.py`

MatHub-3d provides first-principles materials data and 3D structures.

## Inputs

- `target_compositions: str`
- `batch_size: int` (default: `10`)
- Optional filters such as `band_gap`, `energy_per_atom`, `bulk_modulus`, `density`, `volume`, `space_group`, and `is_magnetic`

## Outputs

- `source: "mathub3d"`
- `queries: dict`
- `cif_strings: list[str]`
