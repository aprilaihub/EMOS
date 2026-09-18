# COD

**Type:** Database  
**ID:** `cod`  
**Implementation:** `Information_Units/Databases/Cod/CodDatabase.py`

COD provides access to the open Crystallography Open Database.

## Inputs

- `target_compositions: str`
- `batch_size: int` (default: `10`)
- Optional property filters such as `natoms`, `volume`, and `spacegroup_number`

## Outputs

- `source: "cod"`
- `queries: dict`
- `cif_strings: list[str]`
