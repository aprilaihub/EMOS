# AFLOW Database (AFLUX)

Provides access to the AFLOW database through the AFLUX API, with EMOS-standard filtering and CIF outputs.

## Overview

AFLOW (Automatic FLOW) is a high-throughput computational materials database with electronic, structural, and mechanical properties for a large number of materials.

This EMOS integration uses **AFLUX** (not OPTIMADE) for retrieval, then downloads AFLOW-linked CIF files and writes normalized CIFs to a temporary output folder.

### Key Features
- **Backend API**: AFLUX (`https://aflow.org/API/aflux/`)
- **Data scope**: Electronic, structural, thermodynamic, and mechanical metadata
- **Output**: Local CIF files (same EMOS behavior as other database units)
- **Filtering**: Uses EMOS standard property names mapped via modular files in `property_mappings/`

## Key Methods

### `info()`
Returns description and capabilities of AFLOW integration.

```python
db = database_factory["aflow"]("aflow")
print(db.info())
# Output: AFLOW: Automatic-FLOW computational materials database with electronic, mechanical, and thermal properties
```

### `retrieve(params)`
Retrieves materials matching query/filter criteria.

**Parameters**:
- `query` (str): Element or formula query (e.g., `'Fe'`, `'Al2O3'`)
- `limit` (int): Maximum number of results (default: `10`)
- Additional keys: EMOS standard property names for filtering

**Returns**: List of CIF file paths.

## Supported Properties (EMOS -> AFLOW)

The current AFLOW integration maps these standard EMOS properties:

- `chemical_formula_descriptive` -> `compound`
- `elements` -> `species`
- `id` -> `auid`
- `last_modified` -> `aflowlib_date`
- `nelements` -> `nspecies`
- `band_gap` -> `Egap`
- `space_group` -> `spacegroup_relax`
- `energy_per_atom` -> `energy_atom`
- `density` -> `density`
- `volume` -> `volume_cell`
- `natoms` -> `natoms`
- `magnetization` -> `spin_cell`
- `bulk_modulus` -> `ael_bulk_modulus_vrh`
- `shear_modulus` -> `ael_shear_modulus_vrh`
- `poisson_ratio` -> `ael_poisson_ratio`
- `forces` -> `forces`
- `stress_tensor` -> `stress_tensor`

Range filters are supported for numeric properties (e.g., `[min, max]`).

## Usage Examples

### Basic Query
```python
from Information_Units.Databases.DatabaseFactory import database_factory

db = database_factory["aflow"]("aflow")

results = db.retrieve({
    'query': 'Fe',
    'limit': 5
})

print(f"Retrieved {len(results)} structures")
```

### Formula Query
```python
results = db.retrieve({
    'query': 'Al2O3',
    'limit': 5
})
```

### Band Gap Filtering
```python
results = db.retrieve({
    'query': 'Si',
    'limit': 10,
    'band_gap': [0.0, 2.0]
})
```

### Structural + Mechanical Filtering
```python
results = db.retrieve({
    'query': 'Fe',
    'limit': 10,
    'nelements': [1, 3],
    'bulk_modulus': [50.0, 400.0],
    'poisson_ratio': [0.1, 0.45]
})
```

## Output Format

All `retrieve()` calls return paths to CIF files in a temporary AFLOW output folder:

```python
results = db.retrieve({'query': 'Fe', 'limit': 2})
# Example:
# ['/tmp/aflow_xxxxx/Fe_0.cif', '/tmp/aflow_xxxxx/Fe_1.cif']
```

Notes:
- AFLOW entries are retrieved from AFLUX metadata first.
- CIF text is downloaded from AFLOW file URLs (`aurl + files`).
- EMOS then writes standardized CIFs to local temp paths and returns those paths.

## API Details

### Base URL
- AFLUX: `https://aflow.org/API/aflux/`

### Pagination
- Uses AFLUX directive `paging(J,K)`
- EMOS implementation uses page-based retrieval until `limit` is reached

### Request behavior
- Default response fields include `auid`, `aurl`, `files`, `compound`, `species`, and common filter fields.
- 1-second delay is applied between AFLUX pages to avoid overloading endpoints.

## Integration with Features

```python
from Information_Units.Databases.DatabaseFactory import database_factory

class MetalsExplorer:
    def __init__(self, logger=None):
        self.db = database_factory["aflow"]("aflow", logger=logger)

    def find_candidates(self):
        return self.db.retrieve({
            'query': 'Fe',
            'limit': 20,
            'band_gap': [0.0, 1.0],
            'density': [5.0, 12.0]
        })
```

## Limitations and Considerations

1. AFLUX query latency can dominate runtime compared with CIF download time.
2. Some entries may not expose a preferred CIF variant; fallback selection is used.
3. Filter behavior depends on AFLOW property availability for the matched entries.
4. DFT/mechanical properties are filterable via API metadata; returned CIFs contain structural data.

## Related Documentation

- [AflowDatabase.py](./AflowDatabase.py) - Database implementation
- [AflowAPIHelper.py](./AflowAPIHelper.py) - AFLUX client and conversion logic
- [AFLOW_IMPLEMENTATION_PLAN.md](./AFLOW_IMPLEMENTATION_PLAN.md) - Implementation plan and mapping design
- [BaseDatabase.py](../BaseDatabase.py) - Base database interface
