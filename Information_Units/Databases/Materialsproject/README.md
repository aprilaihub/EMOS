# Materials Project Database

Provides access to the Materials Project database, one of the largest repositories of computed materials data using the OPTIMADE API.

## Overview

The Materials Project (MP) contains 3+ million computed crystal structures and their properties calculated using high-throughput DFT. This database is particularly valuable for thermodynamic stability analysis and materials discovery.

### Key Features
- **Size**: 3+ million structures
- **Primary Functional**: r2SCAN (queryable)
- **Alternative Functionals**: GGA, GGA+U, GGA+U+r2SCAN (available in responses but not queryable)
- **Focus**: Thermodynamic stability, formation energies, convex hull analysis
- **Access**: OPTIMADE v1.0 compatible API
- **Endpoint**: `https://api.materialsproject.org/optimade/v1/`

## Key Methods

### `info()`
Returns description and capabilities of Materials Project database.

```python
db = database_factory["materialsproject"]("materialsproject")
print(db.info())
# Output: Materials Project: Computed materials database with thermodynamic properties (3+ million structures, r2SCAN functional)
```

### `retrieve(params)`
Retrieves materials matching specified criteria.

**Parameters**:
- `query` (str): Material formula or element (required, e.g., 'Fe', 'Al2O3')
- `limit` (int): Maximum number of results (default: 10)
- Additional keys: Standard property names for filtering

**Returns**: List of CIF file paths for matching structures

## Supported Properties

### Common OPTIMADE Properties

**Identifiers & Metadata**:
- `id`: Unique structure ID
- `type`: Entry type (always "structures")
- `last_modified`: ISO 8601 timestamp

**Composition**:
- `chemical_formula_descriptive`: Human-readable formula
- `elements`: List of chemical element symbols
- `nelements`: Number of unique elements - supports range filtering

**Structural**:
- `nperiodic_dimensions`: Number of periodic dimensions - supports range filtering

### Materials Project-Specific Properties (r2SCAN)

Only the r2SCAN functional properties are queryable via the MP OPTIMADE API. GGA+U and GGA+U+r2SCAN variants exist in the data but cannot be used in filter queries due to URL encoding limitations with the `+` symbol.

**r2SCAN Functional (Queryable ✓)**:
- `energy_above_hull_r2scan`: Distance from convex hull (eV/atom) - **supports range filtering**
  - Example: `[0.0, 0.05]` for near-hull stable structures
- `formation_energy_r2scan`: Formation energy per atom (eV/atom) - **supports range filtering**
  - Example: `[-2.0, -0.5]` for thermodynamically stable structures
- `chemical_system`: Chemical system identifier (string, e.g., "Fe", "Fe-O", "Al-Si-O")
  - Example: `"Fe-O"` to query specific binary systems

## Usage Examples

### Basic Query
```python
from Information_Units.Databases.DatabaseFactory import database_factory

db = database_factory["materialsproject"]("materialsproject")

# Simple element query
results = db.retrieve({
    'query': 'Fe',
    'limit': 5
})

print(f"Retrieved {len(results)} structures")
for cif_path in results:
    print(f"  - {cif_path}")
```

### Thermodynamic Stability (r2SCAN)
```python
# Find energetically stable iron compounds (near convex hull)
results = db.retrieve({
    'query': 'Fe',
    'limit': 10,
    'energy_above_hull_r2scan': [0.0, 0.05]  # eV/atom above hull
})
```

### Formation Energy Filtering
```python
# Find thermodynamically favorable structures
results = db.retrieve({
    'query': 'Al2O3',
    'limit': 5,
    'formation_energy_r2scan': [-2.0, -0.5]  # eV/atom formation energy
})
```

### Combined Structural & Energy Filters
```python
# Find specific chemical systems with energy constraints
results = db.retrieve({
    'query': 'Fe',
    'limit': 3,
    'nelements': [1, 3],  # 1-3 unique elements
    'energy_above_hull_r2scan': [0.0, 0.05],  # Stability constraint
    'nperiodic_dimensions': 3  # 3D periodic structures
})
```

### Composition-Based Discovery
```python
# Find oxides in a specific chemical system
results = db.retrieve({
    'query': 'Al-Si-O',
    'limit': 20
})
```

## Known Limitations

### GGA+U Functional Properties (NOT Queryable)

The following properties exist in MP API responses but **cannot be used in query filters**:
- `energy_above_hull_gga_u`: Energy above hull with GGA+U
- `formation_energy_gga_u`: Formation energy with GGA+U
- `energy_above_hull_gga_u_r2scan`: Energy above hull with GGA+U+r2SCAN
- `formation_energy_gga_u_r2scan`: Formation energy with GGA+U+r2SCAN

**Reason**: The `+` symbol in functional names causes URL encoding/parsing failures in the MP OPTIMADE API.

**Workaround**: Use r2SCAN properties for filtering, then post-process results if GGA+U values are needed.

## Related Documentation

- [Materials Project Official Site](https://www.materialsproject.org/)
- [Materials Project OPTIMADE API](https://api.materialsproject.org/optimade/v1/)
- [OPTIMADE Specification](https://www.optimade.org/)
- [Implementation Plan](./IMPLEMENTATION_PLAN.md)
