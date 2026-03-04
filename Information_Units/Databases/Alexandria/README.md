# Alexandria Database (PBEsol)

Provides access to the Alexandria database, a collection of DFT-calculated crystal structures and properties using the PBEsol functional.

## Overview

The Alexandria database contains 415K structures calculated with DFT using the PBEsol functional. This functional is optimized for band gap predictions in semiconductors and is ideal for EMOS electronics applications.

### Key Features
- **Size**: 415,000 structures
- **Primary Functional**: PBEsol (band gap optimized)
- **Secondary Functional**: SCAN (alternative calculations)
- **Focus**: Electronic properties, formation energies, thermodynamic stability
- **Access**: OPTIMADE v1.1.0 compatible API

## Key Methods

### `info()`
Returns description and capabilities of Alexandria database.

```python
db = database_factory["alexandria"]("alexandria")
print(db.info())
# Output: Alexandria (PBEsol): DFT-calculated materials database (415K structures, optimized for band gap accuracy)
```

### `retrieve(params)`
Retrieves materials matching specified criteria.

**Parameters**:
- `query` (str): Material formula or element (required, e.g., 'Fe', 'Al2O3')
- `limit` (int): Maximum number of results (default: 10)
- Additional keys: Standard property names for filtering

**Returns**: List of CIF file paths for matching structures

## Supported Properties

### PBEsol Properties (Default Functional)

**Electronic Properties**:
- `band_gap`: Electronic band gap (eV) - supports range filtering
- `band_gap_direct`: Direct band gap (eV) - supports range filtering
- `dos_ef`: Density of states at Fermi level (states/eV/cell) - supports range filtering
- `magnetization`: Total magnetization (μB/unit_cell) - supports range filtering
- `charges`: Atomic charges - supports range filtering
- `magnetic_moments`: Local magnetic moments (μB) - supports range filtering

**Energetic Properties**:
- `energy`: Total energy (eV) - supports range filtering
- `energy_corrected`: Total energy with pymatgen corrections (eV) - supports range filtering
- `formation_energy_per_atom`: Formation energy (eV/atom) - supports range filtering
- `hull_distance`: Distance from convex hull (eV/atom) - supports range filtering
- `phase_separation_energy`: Phase separation energy (eV/atom) - supports range filtering
- `decomposition`: Most likely decomposition channel (string)

**Structural Properties**:
- `space_group`: Space group number - supports range filtering
- `forces`: Forces on atoms (eV/Angstrom) - supports range filtering
- `stress_tensor`: Stress components (kbar) - supports range filtering

**Metadata**:
- `xc_functional`: Exchange-correlation functional used (string)

### SCAN Variant Properties

All electronic and energetic properties also available with SCAN functional:
- `band_gap_scan`, `band_gap_direct_scan`, `formation_energy_per_atom_scan`, `hull_distance_scan`, `magnetization_scan`, `energy_scan`, `energy_corrected_scan`, `phase_separation_energy_scan`, `decomposition_scan`, `dos_ef_scan`, `charges_scan`, `forces_scan`, `stress_tensor_scan`, `magnetic_moments_scan`

## Usage Examples

### Basic Query
```python
from Information_Units.Databases.DatabaseFactory import database_factory

db = database_factory["alexandria"]("alexandria")

# Simple query
results = db.retrieve({
    'query': 'Fe',
    'limit': 5
})

print(f"Retrieved {len(results)} structures")
for cif_path in results:
    print(f"  - {cif_path}")
```

### Band Gap Filtering (Electronics)
```python
# Find semiconductors with specific band gap range
results = db.retrieve({
    'query': 'Al2O3',
    'limit': 10,
    'band_gap': [2.0, 5.0]  # eV range for visible-light semiconductors
})
```

### Thermodynamic Stability Analysis
```python
# Find thermodynamically stable structures
results = db.retrieve({
    'query': 'Fe2O3',
    'limit': 20,
    'formation_energy_per_atom': [-2.0, -1.0],  # eV/atom
    'hull_distance': [0.0, 0.05]  # Nearly on convex hull (stable)
})
```

### Multi-Property Filtering
```python
# Complex query combining multiple filters
results = db.retrieve({
    'query': 'GaAs',
    'limit': 15,
    'band_gap': [1.0, 2.0],
    'formation_energy_per_atom': [-0.5, 0.0],
    'space_group': [1, 230]
})
```

### PBEsol vs SCAN Comparison
```python
# Get structures calculated with both functionals for comparison
results = db.retrieve({
    'query': 'Si',
    'limit': 5,
    'band_gap': [1.0, 2.0],  # PBEsol band gap range
    'band_gap_scan': [1.5, 3.0]  # SCAN band gap range (typically larger)
})
```

### Magnetic Materials
```python
# Find magnetic structures
results = db.retrieve({
    'query': 'Fe',
    'limit': 10,
    'magnetization': [0.5, 10.0]  # μB/unit_cell - magnetic threshold
})
```

## Output Format

All `retrieve()` calls return a list of file paths (strings) pointing to CIF files:

```python
results = db.retrieve({'query': 'Fe', 'limit': 2})
# Returns: ['/tmp/alexandria_xyz/Fe_0.cif', '/tmp/alexandria_xyz/Fe_1.cif', ...]
```

Each CIF file contains:
- Crystal structure (lattice, atomic positions)
- Chemical composition
- Space group information (from Alexandria metadata)
- Formula units

**Note**: DFT properties (band gaps, energies, etc.) are available in the API but not embedded in CIF files. For property values, query the Alexandria API directly via `AlexandriaAPIHelper`.

## API Details

### Base URL
- PBEsol: `https://alexandria.icams.rub.de/pbesol/v1/`

### OPTIMADE Standard
- API Version: v1.1.0
- Page Limit: 100 (Alexandria max: 500)
- Response Fields: Dynamically determined from `/info/structures` endpoint

### Rate Limiting
- 1 second delay between paginated requests (built-in)
- No explicit rate limit published; respects HTTP 429 responses

## Integration with Features

Example of using Alexandria in a Feature:

```python
from Information_Units.Databases.DatabaseFactory import database_factory

class ElectronicsExplorer:
    def __init__(self, logger=None):
        self.logger = logger
        self.db = database_factory["alexandria"]("alexandria", logger=logger)
    
    def find_semiconductors(self, composition, band_gap_range):
        """Find semiconductors with specified band gap."""
        return self.db.retrieve({
            'query': composition,
            'limit': 20,
            'band_gap': band_gap_range
        })
```

## Limitations and Considerations

1. **Band Gap Accuracy**: PBEsol typically underestimates band gaps by ~20-30% compared to experiments
2. **Missing Properties**: Some structures may not have all properties calculated
3. **Coverage**: PBEsol calculations may miss some exotic phases
4. **Property Availability**: More properties available for simpler compositions

## Related Documentation

- [BaseDatabase.py](../BaseDatabase.py) - Base interface documentation
- [AlexandriaAPIHelper.py](./AlexandriaAPIHelper.py) - Low-level API client
- [AlexandriaDatabase.py](./AlexandriaDatabase.py) - Database implementation

