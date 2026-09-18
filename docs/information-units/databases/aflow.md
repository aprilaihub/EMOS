# AFLOW

**Type:** Database  
**ID:** `aflow`  
**Implementation:** `Information_Units/Databases/Aflow/AflowDatabase.py`

AFLOW provides computational materials data and crystal structures.

## Inputs

- `target_compositions: str` (optional)
- `batch_size: int` (default: `10`)
- Optional property filters from the AFLOW property mapping

## Outputs

- `source: "aflow"`
- `queries: dict`
- `cif_strings: list[str]`
