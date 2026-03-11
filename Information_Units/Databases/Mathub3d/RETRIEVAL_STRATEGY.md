# MatHub-3d Retrieval Strategy

## Context

Unlike COD, Materials Project, and Alexandria — which use the OPTIMADE API to query a remote server
and return full crystal structures (with atomic positions) as CIF files — **MatHub-3d is a local,
file-based dataset**. The data must be loaded from the shipped files (`MatHub-3d.json`,
`MatHub-3d.pkl`, `electric_data.xlsx`) inside the zip archive.

### Critical Limitation: No Atomic Positions

The MatHub-3d dataset does **not** contain atomic site positions (fractional or Cartesian coordinates).
It provides lattice parameters, spacegroup, formula, and elements — but **not** enough information to
directly generate a CIF file. This means:

- **CIF files cannot be fully constructed from this dataset alone.**
- The dataset can be used to **identify and filter candidate materials**, after which full structures
  must be retrieved from a secondary source (e.g., ICSD via the `folder`/`name` field, or by
  cross-referencing with COD/Materials Project).

---

## Dataset Selection Strategy

The `retrieve` method should select the appropriate dataset file based on what properties the user
is filtering on.

### Decision Tree

```
User provides filter properties
        │
        ├── Contains thermoelectric-specific properties?
        │   (Seebeck, power_factor, thermal_conductivity_electronic, pf_ke_ratio)
        │   │
        │   └── YES → Load electric_data.xlsx (elecinfo sheet)
        │             10,195 entries, 20 columns
        │             Unique properties: Seebeck_n/p, PF_n/p, Ke_n/p, PF/Ke
        │
        ├── Contains electrical transport properties only?
        │   (carrier_concentration, conductivity, mobility)
        │   BUT NOT Seebeck/PF/Ke
        │   │
        │   └── YES → Load MatHub-3d.pkl (via joblib)
        │             7,150 entries, 11 columns
        │             Fastest to load (839 KB), has mobility data
        │
        └── Contains only basic structural/electronic/energetic properties?
            (formula, elements, spacegroup, gap, energy, density, volume,
             bulk_modulus, magnetic properties, lattice parameters)
            │
            └── YES → Load MatHub-3d.json
                      74,177 entries, 54 fields
                      Most complete dataset, broadest coverage
```

### Property-to-File Mapping

| Standard Property | JSON | PKL | XLSX | Recommended Source |
|---|:---:|:---:|:---:|---|
| `query` (formula/elements) | ✓ | ✓ | ✓ | JSON (largest pool) |
| `spacegroup` | ✓ | ✓ | — | JSON |
| `nelements` | ✓ | — | — | JSON |
| `gap` (band gap) | ✓ | ✓ | — | JSON |
| `energy_per_atom` | ✓ | ✓ | — | JSON |
| `density` | ✓ | — | — | JSON |
| `volume` | ✓ | — | — | JSON |
| `bulk_modulus` | ✓ | — | ✓ (as BM) | JSON (22% coverage) |
| `is_magnetic` | ✓ | — | — | JSON |
| `total_magnetic_moment` | ✓ | — | — | JSON |
| `vbm` / `cbm` | ✓ | — | — | JSON |
| `efermi` | ✓ | — | — | JSON |
| `lattice_a/b/c` | ✓ | — | — | JSON |
| `carrier_concentration_n` | ✓* | ✓ | ✓ | PKL (cleanest) |
| `carrier_concentration_p` | ✓* | ✓ | ✓ | PKL (cleanest) |
| `conductivity_n` | ✓* | ✓ | ✓ | PKL (cleanest) |
| `conductivity_p` | ✓* | ✓ | ✓ | PKL (cleanest) |
| `mobility_n` | — | ✓ | — | PKL (exclusive) |
| `mobility_p` | — | ✓ | — | PKL (exclusive) |
| `deformation_potential_n` | ✓* | — | ✓ | XLSX |
| `deformation_potential_p` | ✓* | — | ✓ | XLSX |
| `seebeck_n` | — | — | ✓ | XLSX (exclusive) |
| `seebeck_p` | — | — | ✓ | XLSX (exclusive) |
| `power_factor_n` | — | — | ✓ | XLSX (exclusive) |
| `power_factor_p` | — | — | ✓ | XLSX (exclusive) |
| `thermal_conductivity_electronic_n` | — | — | ✓ | XLSX (exclusive) |
| `thermal_conductivity_electronic_p` | — | — | ✓ | XLSX (exclusive) |
| `pf_ke_ratio_n` | — | — | ✓ | XLSX (exclusive) |
| `pf_ke_ratio_p` | — | — | ✓ | XLSX (exclusive) |

*\* JSON has `dp_n`/`dp_p` fields but only for ~14% of entries; XLSX has broader coverage.*

---

## Proposed `retrieve` Input/Output Format

### Input Format (consistent with other databases)

```python
db.retrieve({
    'query': 'Fe',              # formula or element filter (string)
    'limit': 10,                # max results (int)
    # Structural filters
    'spacegroup': 225,          # exact match (int) or [min, max]
    'nelements': [2, 3],        # range
    'density': [5.0, 10.0],     # range (g/cm³)
    'volume': [50, 200],        # range (ų)
    # Electronic filters
    'gap': [0.5, 2.0],          # band gap range (eV)
    'is_magnetic': True,        # exact match
    # Energetic filters
    'energy_per_atom': [-7.0, -4.0],  # range (eV)
    'bulk_modulus': [50, 200],  # range (GPa)
    # Transport filters (triggers PKL)
    'mobility_n': [10, 500],    # range (cm²/Vs)
    'conductivity_n': [1000, None],  # min only
    # Thermoelectric filters (triggers XLSX)
    'seebeck_n': [None, -200],  # max only (µV/K)
    'power_factor_n': [10, None],  # min only
})
```

### Output Format

Since MatHub-3d has **no atomic positions**, the output differs from OPTIMADE-based databases:

```python
# Other databases return:
list[str]  # Paths to CIF files

# MatHub-3d should return:
list[dict]  # List of matching material records with metadata
```

Each returned dict should contain:
```python
{
    'source_id': 'icsd-100001-Cu6K2S4',       # ICSD reference for cross-lookup
    'mathub_id': 'MatHub3d-39787-Cu6K2S4',     # MatHub-3d internal ID
    'formula': 'Cu6K2S4',
    'spacegroup': 12,
    'lattice': {                                # Relaxed if available, else initial
        'a': 7.64, 'b': 7.64, 'c': 8.29,
        'alpha': 113, 'beta': 113, 'gamma': 30
    },
    'properties': {                             # All available properties for this entry
        'gap': 0.729571,
        'energy_per_atom': -3.27,
        'bulk_modulus': 62.37,
        'density': 2.66,
        ...
    },
    'cif_path': None,                           # No CIF (no atomic positions)
    'cross_reference': 'icsd-100001'            # Parseable ICSD ID for external lookup
}
```

---

## Implementation Approach

### Step 1: Load Data on First Call (Lazy Loading)

```python
class Mathub3dDatabase(BaseDatabase):
    def __init__(self, ...):
        ...
        self._json_data = None    # Loaded on demand
        self._pkl_data = None     # Loaded on demand
        self._xlsx_data = None    # Loaded on demand
        self._zip_path = Path(__file__).parent / 'MatHub-3d.zip'
```

### Step 2: Determine Which File to Load

```python
XLSX_ONLY_PROPERTIES = {
    'seebeck_n', 'seebeck_p',
    'power_factor_n', 'power_factor_p',
    'thermal_conductivity_electronic_n', 'thermal_conductivity_electronic_p',
    'pf_ke_ratio_n', 'pf_ke_ratio_p',
    'deformation_potential_n', 'deformation_potential_p',
}

PKL_ONLY_PROPERTIES = {
    'mobility_n', 'mobility_p',
}

PKL_SHARED_PROPERTIES = {
    'carrier_concentration_n', 'carrier_concentration_p',
    'conductivity_n', 'conductivity_p',
}

def _select_source(self, filter_keys: set) -> str:
    """Determine which data file to query based on requested properties."""
    if filter_keys & XLSX_ONLY_PROPERTIES:
        return 'xlsx'
    if filter_keys & (PKL_ONLY_PROPERTIES | PKL_SHARED_PROPERTIES):
        return 'pkl'
    return 'json'
```

### Step 3: Property Name Mapping

Map standard input names to file-specific column/field names:

```python
PROPERTY_MAP = {
    # Standard name → {source: column_name}
    'query':                          {'json': 'formula',  'pkl': 'formula',  'xlsx': None},
    'spacegroup':                     {'json': 'spacegroup', 'pkl': 'spacegroup', 'xlsx': None},
    'gap':                            {'json': 'gap', 'pkl': 'gap', 'xlsx': None},
    'energy_per_atom':                {'json': 'energy_per_atom', 'pkl': 'energy_per_atom', 'xlsx': None},
    'carrier_concentration_n':        {'json': 'dp_n', 'pkl': 'carr_n(10^20/cm3)', 'xlsx': 'carr_n(10^20/cm3)'},
    'carrier_concentration_p':        {'json': 'dp_p', 'pkl': 'carr_p(10^20/cm3)', 'xlsx': 'carr_p(10^20/cm3)'},
    'conductivity_n':                 {'json': None, 'pkl': 'sigma_n(S/m)', 'xlsx': 'sigma_n(S/m)'},
    'conductivity_p':                 {'json': None, 'pkl': 'sigma_p(S/m)', 'xlsx': 'sigma_p(S/m)'},
    'mobility_n':                     {'json': None, 'pkl': 'mob_n(cm2/Vs)', 'xlsx': None},
    'mobility_p':                     {'json': None, 'pkl': 'mob_p(cm2/Vs)', 'xlsx': None},
    'seebeck_n':                      {'json': None, 'pkl': None, 'xlsx': 'Seebeck_n(uV/K)'},
    'seebeck_p':                      {'json': None, 'pkl': None, 'xlsx': 'Seebeck_p(uV/K)'},
    'power_factor_n':                 {'json': None, 'pkl': None, 'xlsx': 'PF_n(1E-4Wm-1K-2)'},
    'power_factor_p':                 {'json': None, 'pkl': None, 'xlsx': 'PF_p(1E-4Wm-1K-2)'},
    'thermal_conductivity_electronic_n': {'json': None, 'pkl': None, 'xlsx': 'Ke_n(Wm-1K-1)'},
    'thermal_conductivity_electronic_p': {'json': None, 'pkl': None, 'xlsx': 'Ke_p(Wm-1K-1)'},
    'deformation_potential_n':        {'json': 'dp_n', 'pkl': None, 'xlsx': 'DP_n(eV)'},
    'deformation_potential_p':        {'json': 'dp_p', 'pkl': None, 'xlsx': 'DP_p(eV)'},
    'pf_ke_ratio_n':                  {'json': None, 'pkl': None, 'xlsx': 'PF/Ke_N'},
    'pf_ke_ratio_p':                  {'json': None, 'pkl': None, 'xlsx': 'PF/Ke_P'},
    'bulk_modulus':                    {'json': 'bulk_modulus', 'pkl': None, 'xlsx': 'BM(GPa)'},
    # Structural (JSON only)
    'nelements':                      {'json': 'nelements', 'pkl': None, 'xlsx': None},
    'density':                        {'json': 'density', 'pkl': None, 'xlsx': None},
    'volume':                         {'json': 'volume', 'pkl': None, 'xlsx': None},
    'is_magnetic':                    {'json': 'is_magnetic', 'pkl': None, 'xlsx': None},
    'total_magnetic_moment':          {'json': 'total_magnetic_moment', 'pkl': None, 'xlsx': None},
}
```

### Step 4: Filter and Return

```python
def retrieve(self, inputs: dict) -> list:
    query = inputs.get('query', '')
    limit = inputs.get('limit', 10)
    filters = {k: v for k, v in inputs.items() if k not in ['query', 'limit']}

    source = self._select_source(set(filters.keys()))
    data = self._load_source(source)               # lazy load from zip
    results = self._apply_formula_filter(data, query, source)
    results = self._apply_property_filters(results, filters, source)
    results = results[:limit]

    return self._format_results(results, source)    # → list[dict]
```

---

## CIF Generation: Cross-Reference via COD Formula + Lattice Matching

### Why Not a Direct ICSD Lookup?

MatHub-3d entries reference ICSD structures (e.g., `icsd-100001-Cu6K2S4`), where `100001` is an
ICSD collection code. However, **COD and ICSD are separate databases** with independent ID systems:

- COD uses its own numeric IDs (e.g., `1005027`), not ICSD codes.
- COD's OPTIMADE API exposes no `_cod_icsd_code` or similar cross-reference field.
- The `spacegroup_number` field in COD's OPTIMADE endpoint is not reliably populated (returns `null`
  in practice), limiting even indirect filtering.

Therefore, **direct ICSD identifier lookup through COD is not possible**.

### Adopted Strategy: Formula + Lattice Parameter Matching (Approximate)

A two-step approach is used to obtain CIF files for MatHub-3d materials:

1. **Filter** materials locally using MatHub-3d's property data (thermoelectric, electronic, etc.).
2. **Retrieve CIF candidates** from COD by querying the chemical formula and then **post-filtering
   by lattice parameter similarity** to identify the best structural match.

This is an approximate matching strategy — not every MatHub-3d entry will have a COD match, and
some formulas may return multiple candidates.

### Implementation

```python
from Information_Units.Databases.Cod.CodDatabase import CodDatabase

def retrieve_cif_for_mathub_results(mathub_results, lattice_tolerance=0.05):
    """
    Attempt to retrieve CIF files from COD for MatHub-3d filtered results.
    
    Args:
        mathub_results: list[dict] from Mathub3dDatabase.retrieve()
        lattice_tolerance: fractional tolerance for lattice parameter matching
                           (0.05 = 5% deviation allowed)
    
    Returns:
        list[dict]: mathub_results enriched with 'cif_path' where a match was found
    """
    cod_db = CodDatabase()
    
    for result in mathub_results:
        formula = result['formula']
        
        # Step 1: Query COD by formula (elements)
        cod_cif_paths = cod_db.retrieve({
            'query': formula,
            'limit': 10  # Fetch several candidates for lattice comparison
        })
        
        if not cod_cif_paths:
            result['cif_path'] = None
            result['cif_match_status'] = 'no_cod_match'
            continue
        
        # Step 2: Post-filter by lattice parameter similarity
        # Compare COD structures against MatHub-3d relaxed lattice params
        mathub_lattice = result.get('lattice', {})
        best_match = _find_best_lattice_match(
            cod_cif_paths, mathub_lattice, lattice_tolerance
        )
        
        if best_match:
            result['cif_path'] = best_match
            result['cif_match_status'] = 'matched'
        else:
            # Fallback: use first COD result (same composition, different polymorph possible)
            result['cif_path'] = cod_cif_paths[0]
            result['cif_match_status'] = 'approximate'
    
    return mathub_results


def _find_best_lattice_match(cif_paths, target_lattice, tolerance):
    """
    Compare CIF file lattice parameters against MatHub-3d target values.
    
    Args:
        cif_paths: list of CIF file paths from COD
        target_lattice: dict with keys 'a', 'b', 'c', 'alpha', 'beta', 'gamma'
        tolerance: fractional tolerance (e.g., 0.05 for 5%)
    
    Returns:
        str: path to best matching CIF, or None if no match within tolerance
    """
    from pymatgen.core import Structure
    
    target_a = target_lattice.get('a')
    target_b = target_lattice.get('b')
    target_c = target_lattice.get('c')
    
    if not all([target_a, target_b, target_c]):
        return None
    
    best_path = None
    best_deviation = float('inf')
    
    for cif_path in cif_paths:
        try:
            structure = Structure.from_file(cif_path)
            lat = structure.lattice
            
            # Calculate fractional deviation for a, b, c
            dev_a = abs(lat.a - target_a) / target_a
            dev_b = abs(lat.b - target_b) / target_b
            dev_c = abs(lat.c - target_c) / target_c
            max_dev = max(dev_a, dev_b, dev_c)
            
            if max_dev < tolerance and max_dev < best_deviation:
                best_deviation = max_dev
                best_path = cif_path
        except Exception:
            continue
    
    return best_path
```

### Usage Example

```python
# Step 1: Filter MatHub-3d for thermoelectric candidates
mathub_db = Mathub3dDatabase('mathub3d')
candidates = mathub_db.retrieve({
    'query': 'Ni',
    'gap': [0.1, 1.0],
    'seebeck_n': [None, -150],
    'limit': 5
})

# Step 2: Retrieve CIF files from COD via formula + lattice matching
enriched = retrieve_cif_for_mathub_results(candidates, lattice_tolerance=0.05)

for entry in enriched:
    print(f"{entry['formula']}: CIF={entry['cif_path']} ({entry['cif_match_status']})")
```

### Expected Outcomes

| Scenario | `cif_match_status` | Meaning |
|---|---|---|
| COD has same structure | `matched` | Lattice params match within tolerance — high confidence |
| COD has same formula, different polymorph | `approximate` | Same composition found but lattice differs — use with caution |
| Formula not in COD | `no_cod_match` | No COD entry for this composition — CIF unavailable |

### Limitations

- **Not all MatHub-3d entries will have COD matches.** COD contains ~500K structures from published
  literature; MatHub-3d's 74K entries originate from ICSD, and the overlap is partial.
- **Polymorphism:** A formula like `SiO2` has dozens of polymorphs in COD. Lattice parameter
  matching helps select the right one, but is not infallible.
- **COD API rate limits:** COD's OPTIMADE API returns max 10 results per page. For large-scale
  cross-referencing, batch processing with delays is recommended.
- **Approximate, not exact:** This is a best-effort approach. For guaranteed structural accuracy,
  direct ICSD access (institutional license required) is the definitive source.

---

## Summary

| Aspect | COD / MP / Alexandria | MatHub-3d |
|--------|----------------------|-----------|
| **Data Source** | Remote OPTIMADE API | Local files (zip) |
| **Has Atomic Positions** | Yes | No |
| **Returns CIF** | Yes (directly) | Via COD cross-reference (approximate) |
| **CIF Match Method** | N/A (native) | Formula + lattice parameter matching |
| **Unique Value** | Full crystal structures | Thermoelectric transport properties |
| **Query Method** | HTTP API calls | In-memory DataFrame filtering |
| **Best For** | Structure retrieval | Property-based material screening |
