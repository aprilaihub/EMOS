# MatHub-3d Database

Provides access to the MatHub-3d database, a first-principles materials repository of 74K+ 3D crystal structures with computed thermoelectric and transport properties.

## Overview

MatHub-3d contains 74,177 structures calculated with DFT, focusing on materials for electronics and thermoelectric applications. Unlike other databases in EMOS, MatHub-3d is a local dataset (loaded from a bundled JSON archive). Since the dataset does not include atomic positions, CIF files are obtained by cross-referencing matching structures in COD and Materials Project via formula and lattice parameter comparison.

### Key Features
- **Size**: 74,177 structures
- **Focus**: Thermoelectric transport, electronic band structure, mechanical properties
- **Data Source**: Local JSON archive (`MatHub-3d.zip`)
- **CIF Retrieval**: Cross-references COD and Materials Project by formula + lattice matching (5% tolerance)
- **Reference**: [Li et al., *Mater. Genome Eng. Adv.*, 2023](https://onlinelibrary.wiley.com/doi/10.1002/mgea.21)
- **Website**: [https://www.mathub3d.net/](https://www.mathub3d.net/) (accessed 07/04/2025)

## Key Methods

### `info()`
Returns description and capabilities of MatHub-3d database.

```python
db = database_factory["mathub3d"]("mathub3d")
print(db.info())
# Output: MatHub-3d: first-principles materials repository (74K structures, thermoelectric transport properties). CIF files retrieved via COD/Materials Project cross-referencing.
```

### `retrieve(params)`
Retrieves materials matching specified criteria.

**Parameters**:
- `query` (str): Material formula or element (required, e.g., 'Fe', 'Al2O3')
- `limit` (int): Maximum number of results (default: 10)
- Additional keys: Standard property names for filtering

**Returns**: List of CIF file paths for matching structures

## Supported Properties

### Shared with Other Databases

**Structural**:
- `elements`: List of chemical element symbols
- `nelements`: Number of unique elements — supports range filtering

**Electronic**:
- `band_gap`: Electronic band gap (eV) — maps to `gap` — supports range filtering
- `magnetization`: Total magnetic moment (μB) — maps to `total_magnetic_moment` — supports range filtering

**Energetic**:
- `energy`: Total DFT energy (eV) — supports range filtering

**Structural/Symmetry**:
- `space_group`: Space group number — maps to `spacegroup` — supports range filtering

### Unique to MatHub-3d

**Electronic**:
- `vbm`: Valence band maximum (eV) — supports range filtering
- `cbm`: Conduction band minimum (eV) — supports range filtering
- `efermi`: Fermi energy (eV) — supports range filtering

**Energetic**:
- `energy_per_atom`: Total DFT energy per atom (eV/atom) — supports range filtering

**Structural**:
- `density`: Mass density (g/cm³) — supports range filtering
- `volume`: Unit cell volume (Å³) — supports range filtering
- `mass`: Unit cell mass (amu) — supports range filtering
- `natoms`: Number of atoms in unit cell — supports range filtering

**Mechanical**:
- `bulk_modulus`: Bulk modulus (GPa) — supports range filtering

**Magnetic**:
- `is_magnetic`: Whether the material is magnetic (boolean)

**Transport**:
- `deformation_potential_n`: n-type deformation potential (eV) — supports range filtering
- `deformation_potential_p`: p-type deformation potential (eV) — supports range filtering

## Usage Examples

### Basic Query
```python
from Information_Units.Databases.DatabaseFactory import database_factory

db = database_factory["mathub3d"]("mathub3d")

results = db.retrieve({
    'query': 'Fe',
    'limit': 5
})

print(f"Retrieved {len(results)} structures")
for cif_path in results:
    print(f"  - {cif_path}")
```

### Band Gap Filtering
```python
# Find semiconductors with specific band gap range
results = db.retrieve({
    'query': 'Si',
    'limit': 10,
    'band_gap': [0.5, 2.0]
})
```

### Combined Filters
```python
# Find magnetic Fe compounds with specific band gap
results = db.retrieve({
    'query': 'Fe',
    'limit': 10,
    'band_gap': [1.0, 3.0],
    'nelements': [2, 4]
})
```

### Density Filtering
```python
# Find lightweight structures
results = db.retrieve({
    'query': 'Al2O3',
    'limit': 5,
    'density': [1.0, 5.0]
})
```

## Limitations and Considerations

1. **No Atomic Positions**: MatHub-3d entries lack atomic coordinates. CIF files are sourced from COD/Materials Project via cross-referencing, so entries with no lattice match in either database are silently skipped.
2. **Cross-Reference Latency**: Each entry may trigger API calls to COD and MP, making retrieval slower than direct-API databases.
3. **Lattice Matching Tolerance**: A 5% fractional tolerance is used for lattice parameter comparison. Materials Project is preferred as a fallback when no exact match is found.
4. **Property Coverage**: Not all entries have values for all properties (e.g., some transport properties may be `None`).

## Related Documentation

- [MatHub-3d Website](https://www.mathub3d.net/)
- [Li et al., *Mater. Genome Eng. Adv.*, 2023](https://onlinelibrary.wiley.com/doi/10.1002/mgea.21)
- [BaseDatabase API](../BaseDatabase.py)
