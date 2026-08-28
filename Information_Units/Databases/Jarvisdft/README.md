# JARVIS-DFT Database

Provides access to the JARVIS-DFT database from NIST, a collection of DFT-calculated crystal structures and properties using the OptB88vdW functional.

## Overview

The JARVIS-DFT database contains structures calculated with DFT using the OptB88vdW functional. It covers electronic, optical, thermoelectric, elastic, and solar cell properties and is accessed via the OPTIMADE API.

### Key Features
- **Size**: ~80,000 structures (3D and 2D materials)
- **Primary Functional**: OptB88vdW
- **Focus**: Electronic, optical, thermoelectric, elastic, and solar cell properties
- **Access**: OPTIMADE API
- **Provider Property Prefix**: `_jarvis_*`

## Key Methods

### `info()`
Returns description and capabilities of JARVIS-DFT database.

```python
db = database_factory["jarvisdft"]("jarvisdft")
print(db.info())
# Output: JARVIS-DFT: NIST computational materials database with electronic, optical, thermoelectric, and solar cell properties
```

### `retrieve(params)`
Retrieves materials matching specified criteria.

**Parameters**:
- `query` (str): Material formula or element (required, e.g., 'Si', 'Fe2O3')
- `limit` (int): Maximum number of results (default: 10)
- Additional keys: Standard property names for filtering

**Returns**: List of CIF file paths for matching structures

## Supported Properties

### Electronic Properties
- `band_gap`: Electronic band gap, OptB88vdW (eV) - supports range filtering
- `mbj_bandgap`: MBJ band gap (eV) - supports range filtering
- `hse_gap`: HSE06 band gap (eV) - supports range filtering
- `spillage`: Spin-orbit spillage - supports range filtering

### Energetic Properties
- `energy`: Total energy (eV) - supports range filtering
- `formation_energy_per_atom`: Formation energy (eV/atom) - supports range filtering
- `hull_distance`: Distance from convex hull (eV/atom) - supports range filtering

### Elastic Properties
- `bulk_modulus`: Bulk modulus, Kv (GPa) - supports range filtering
- `shear_modulus`: Shear modulus, Gv (GPa) - supports range filtering
- `poisson_ratio`: Poisson's ratio - supports range filtering

### Thermoelectric Properties
- `n_seebeck`: n-type Seebeck coefficient (μV/K) - supports range filtering
- `p_seebeck`: p-type Seebeck coefficient (μV/K) - supports range filtering
- `n_powerfact`: n-type power factor (μW/(cm·K²)) - supports range filtering
- `p_powerfact`: p-type power factor (μW/(cm·K²)) - supports range filtering

### Optical / Dielectric Properties
- `epsx`: Static dielectric constant (x) - supports range filtering
- `mepsx`: Electronic dielectric constant (x) - supports range filtering

### Solar Cell Properties
- `slme`: Spectroscopic limited maximum efficiency (%) - supports range filtering

### Other Properties
- `magnetization`: Total magnetization (μB) - supports range filtering
- `density`: Density (g/cm³) - supports range filtering
- `space_group`: Space group number - supports range filtering
- `exfoliation_energy`: Exfoliation energy (meV/atom) - supports range filtering
- `Tc_supercon`: Superconducting critical temperature (K) - supports range filtering
- `dfpt_piezo_max_dij`: Max piezoelectric strain coefficient (C/N) - supports range filtering
- `avg_elec_mass`: Average electron effective mass (mₑ) - supports range filtering
- `avg_hole_mass`: Average hole effective mass (mₑ) - supports range filtering

### Structural Properties (OPTIMADE standard)
- `nelements`: Number of unique chemical elements - supports range filtering
- `nperiodic_dimensions`: Number of periodic dimensions - supports range filtering

## Usage Examples

### Basic Query
```python
from Information_Units.Databases.DatabaseFactory import database_factory

db = database_factory["jarvisdft"]("jarvisdft")

# Simple query
results = db.retrieve({
    'query': 'Si',
    'limit': 5
})

print(f"Retrieved {len(results)} structures")
for cif_path in results:
    print(f"  - {cif_path}")
```

### Band Gap Filtering
```python
# Find structures with specific band gap range
results = db.retrieve({
    'query': 'Si',
    'limit': 10,
    'band_gap': [0.5, 2.0]  # eV range (OptB88vdW)
})
```

### Thermodynamic Stability Analysis
```python
# Find thermodynamically stable structures
results = db.retrieve({
    'query': 'Fe',
    'limit': 20,
    'formation_energy_per_atom': [-2.0, -0.5],  # eV/atom
    'hull_distance': [0.0, 0.1]  # Near convex hull (stable)
})
```

### Multi-Property Filtering
```python
# Complex query combining multiple filters
results = db.retrieve({
    'query': 'Fe',
    'limit': 10,
    'band_gap': [0.0, 2.0],
    'formation_energy_per_atom': [-2.0, 0.0],
    'hull_distance': [0.0, 0.1]
})
```

### Elastic Property Query
```python
# Find structures with high bulk modulus
results = db.retrieve({
    'query': 'Fe',
    'limit': 10,
    'bulk_modulus': [100.0, 300.0]  # GPa
})
```

## Output Format

All `retrieve()` calls return a list of file paths (strings) pointing to CIF files:

```python
results = db.retrieve({'query': 'Si', 'limit': 2})
# Returns: ['/tmp/jarvisdft_xyz/Si_0.cif', '/tmp/jarvisdft_xyz/Si_1.cif', ...]
```

Each CIF file contains:
- Crystal structure (lattice, atomic positions)
- Chemical composition
- Space group information
- Formula units

**Note**: DFT properties (band gaps, energies, etc.) are available in the API but not embedded in CIF files. For property values, query the JARVIS-DFT API directly via `JarvisdftAPIHelper`.

## API Details

### Base URL
- `https://jarvis.nist.gov/optimade/jarvisdft/v1/`

### OPTIMADE Standard
- Pagination: Page-number based (`page=1`, `page=2`, ...)
- Page Size: Server-enforced hard cap of 20 entries per page
- Response Fields: Dynamically determined from `/info/structures` endpoint
- Composition Filter Syntax: `elements HAS ALL "Fe","O"` (comma-separated list required)

### Rate Limiting
- 1 second delay between paginated requests (built-in)

### Known Server Quirks
- `elements HAS "X"` returns 0 results; must use `elements HAS ALL "X"`
- Multi-element queries require comma-separated list syntax: `elements HAS ALL "Fe","O"`
- Range filters on provider-specific properties (`_jarvis_*`) are not enforced server-side
- The sentinel value `-99999` is used for properties that have not been computed

## Limitations and Considerations

1. **Server-Side Filtering**: JARVIS does not enforce range filters on `_jarvis_*` properties server-side; results may include values outside the requested range
2. **Sentinel Values**: Properties not computed for a given structure are returned as `-99999`
3. **Pagination Cap**: The server always returns a maximum of 20 entries per page regardless of the `page_limit` parameter
4. **Band Gap Accuracy**: OptB88vdW band gaps may differ from experimental values; MBJ and HSE06 band gaps are also available for comparison

## Related Documentation

- [BaseDatabase.py](../BaseDatabase.py) - Base interface documentation
- [JarvisdftAPIHelper.py](./JarvisdftAPIHelper.py) - Low-level API client
- [JarvisdftDatabase.py](./JarvisdftDatabase.py) - Database implementation
