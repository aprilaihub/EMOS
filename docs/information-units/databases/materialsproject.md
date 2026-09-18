# Materials Project

**Type:** Database  
**ID:** `materialsproject`  
**Implementation:** `Information_Units/Databases/Materialsproject/MaterialsprojectDatabase.py`

Materials Project provides computational materials data and crystal structures.

## Inputs

- `target_compositions: str`
- `batch_size: int` (default: `10`)
- Optional filters such as `id`, `elements`, `chemical_system`, `energy_above_hull_r2scan`, and `formation_energy_r2scan`

## Outputs

- `source: "materialsproject"`
- `queries: dict`
- `cif_strings: list[str]`
- `entries: list[dict]` with material IDs, formulas, space groups, and stability properties
