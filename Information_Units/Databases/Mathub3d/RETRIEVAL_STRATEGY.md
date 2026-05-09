# MatHub-3d Retrieval Strategy

## Context

Unlike COD, Materials Project, and Alexandria — which use the OPTIMADE API to query a remote server
and return full crystal structures (with atomic positions) as CIF files — **MatHub-3d is a local,
file-based dataset**. The data is loaded from `MatHub-3d.json` inside the shipped zip archive.

> **Note**: The zip also contains `MatHub-3d.pkl` and `electric_data.xlsx`, but these are derived
> subsets created later. The JSON file is the **original and authoritative data source** from the
> MatHub-3d website, containing all 74,177 entries and 54 fields.

### Critical Limitation: No Atomic Positions

The MatHub-3d dataset does **not** contain atomic site positions (fractional or Cartesian coordinates).
It provides lattice parameters, spacegroup, formula, and elements — but **not** enough information to
directly generate a CIF file. This means:

- **CIF files cannot be fully constructed from this dataset alone.**
- The dataset can be used to **identify and filter candidate materials**, after which full structures
  must be retrieved from a secondary source (e.g., ICSD via the `folder`/`name` field, or by
  cross-referencing with COD/Materials Project).

---

## Data Source: MatHub-3d.json

Single file, 74,177 entries, 54 fields. Loaded once into memory on first `retrieve()` call.

### Available Properties

The "Standard Name" column refers to the universal property key in
`Information_Units/property_mappings/common_properties.json` — the central corpus that maps
standardised names. Source-specific field names for mathub3d are defined in
`Information_Units/property_mappings/sources/databases/mathub3d.json`.

| Category | JSON Field | Standard Name (common_properties.json) | Completeness |
|----------|-----------|----------------------------------------|-------------|
| **Identity** | `formula` | `query` | 100% |
| **Identity** | `elements` | (element filter) | 100% |
| **Identity** | `nelements` | `nelements` | 100% |
| **Identity** | `name` / `folder` | (ICSD cross-ref) | 100% |
| **Lattice (initial)** | `before_a/b/c` | `lattice_a/b/c` (initial) | 100% |
| **Lattice (initial)** | `before_alpha/beta/gamma` | `lattice_alpha/beta/gamma` (initial) | 100% |
| **Lattice (relaxed)** | `after_a/b/c` | `lattice_a/b/c` (relaxed) | ~40% |
| **Lattice (relaxed)** | `after_alpha/beta/gamma` | `lattice_alpha/beta/gamma` (relaxed) | ~40% |
| **Structure** | `spacegroup` | `spacegroup` | 100% |
| **Structure** | `spacegroup_type` | `spacegroup_type` | 100% |
| **Structure** | `natoms` | `natoms` | ~40% |
| **Structure** | `volume` | `volume` | ~40% |
| **Structure** | `density` | `density` | ~40% |
| **Structure** | `mass` | `mass` | ~40% |
| **Energetics** | `energy` | `energy` | ~40% |
| **Energetics** | `energy_per_atom` | `energy_per_atom` | ~40% |
| **Electronic** | `gap` | `gap` | ~40% |
| **Electronic** | `vbm` | `vbm` | ~8.5% |
| **Electronic** | `cbm` | `cbm` | ~8.5% |
| **Electronic** | `efermi` | `efermi` | ~40% |
| **Magnetic** | `is_magnetic` | `is_magnetic` | ~40% |
| **Magnetic** | `total_magnetic_moment` | `total_magnetic_moment` | ~40% |
| **Mechanical** | `bulk_modulus` | `bulk_modulus` | ~22% |
| **Transport** | `dp_n` | `deformation_potential_n` | ~14% |
| **Transport** | `dp_p` | `deformation_potential_p` | ~14% |
| **Transport** | `trans` | (transport flag) | ~5% |

### Property Completeness Notes

Not all 74,177 entries have full DFT results. The coverage breakdown:

- **100%** (74,177): Identity fields, initial lattice, spacegroup, formula, elements
- **~40%** (~30K): Relaxed lattice, energy, gap, efermi, magnetic properties, density, volume
- **~22%** (~16K): Bulk modulus
- **~14%** (~10K): Deformation potentials (`dp_n`, `dp_p`)
- **~8.5%** (~6K): Band edge details (`vbm`, `cbm`)

When filtering on a property with partial coverage, entries where that property is `null` / missing
are excluded from results (they simply don't match).

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
    # Transport filters
    'deformation_potential_n': [-10, -1],  # range (eV)
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

### Step 1: Load JSON on First Call (Lazy Loading)

```python
import json
import zipfile
from pathlib import Path

class Mathub3dDatabase(BaseDatabase):
    def __init__(self, ...):
        ...
        self._data = None  # Loaded on demand
        self._zip_path = Path(__file__).parent / 'MatHub-3d.zip'

    def _load_data(self):
        """Lazy-load MatHub-3d.json from the zip archive."""
        if self._data is None:
            with zipfile.ZipFile(self._zip_path, 'r') as zf:
                with zf.open('MatHub-3d.json') as f:
                    self._data = json.load(f)
        return self._data
```

### Step 2: Property Name Mapping via Modular Property Mapping Files

Instead of a hardcoded local dict, the mapping from standard property names to MatHub-3d JSON
field names is read from **`Information_Units/property_mappings/sources/databases/mathub3d.json`**.

Property metadata is defined in `common_properties.json`, and source-specific config is defined in
the mathub3d source file:

```json
"nelements": {
    "name": "nelements",
    "retrievable": true,
    "range_support": true
}
```

At runtime, the database class loads the mapping once and builds a lookup:

```python
def _load_property_map(self):
    """Build {standard_name: json_field_name} from modular mappings."""
    source_path = Path(__file__).parent.parent / 'property_mappings' / 'sources' / 'databases' / 'mathub3d.json'
    with open(source_path) as f:
        mappings = json.load(f)
    return {
        prop_name: prop_info['name']
        for prop_name, prop_info in mappings['properties'].items()
        if prop_info.get('retrievable')
    }
```

This keeps the mapping centralised — any new property added to the modular mapping files is
automatically available, with no code changes in the database class.

The full list of `mathub3d` entries to add to the modular mapping files:

| Standard Name | mathub3d `name` | `range_support` | Notes |
|---|---|---|---|
| `elements` | `elements` | false | Already exists, add mathub3d key |
| `nelements` | `nelements` | true | Already exists, add mathub3d key |
| `energy` | `energy` | true | Already exists (alexandria), add mathub3d key |
| `band_gap` | `gap` | true | Already exists (alexandria), add mathub3d key |
| `space_group` | `spacegroup` | true | Already exists (alexandria), add mathub3d key |
| `magnetization` | `total_magnetic_moment` | true | Already exists (alexandria), reuse for mathub3d |
| `energy_per_atom` | `energy_per_atom` | true | **New property** (total DFT energy/atom, distinct from `formation_energy_per_atom`) |
| `density` | `density` | true | **New property** |
| `volume` | `volume` | true | **New property** |
| `mass` | `mass` | true | **New property** |
| `natoms` | `natoms` | true | **New property** |
| `bulk_modulus` | `bulk_modulus` | true | **New property** |
| `is_magnetic` | `is_magnetic` | false | **New property** (boolean) |
| `vbm` | `vbm` | true | **New property** |
| `cbm` | `cbm` | true | **New property** |
| `efermi` | `efermi` | true | **New property** |
| `deformation_potential_n` | `dp_n` | true | **New property** |
| `deformation_potential_p` | `dp_p` | true | **New property** |

### Step 3: Filter and Return

```python
def retrieve(self, inputs: dict) -> list:
    query = inputs.get('query', '')
    limit = inputs.get('limit', 10)
    filters = {k: v for k, v in inputs.items() if k not in ['query', 'limit']}

    prop_map = self._load_property_map()  # from modular property mappings
    data = self._load_data()
    results = self._apply_formula_filter(data, query)
    results = self._apply_property_filters(results, filters, prop_map)
    results = results[:limit]

    return self._format_results(results)
```

No file-selection logic needed — every query hits the same JSON dataset.
Property name translation is driven entirely by modular property mappings.

---

## CIF Generation: Cross-Reference via COD + Materials Project

### Why Not a Direct ICSD Lookup?

MatHub-3d entries reference ICSD structures (e.g., `icsd-100001-Cu6K2S4`), where `100001` is an
ICSD collection code. However, **COD and ICSD are separate databases** with independent ID systems:

- COD uses its own numeric IDs (e.g., `1005027`), not ICSD codes.
- COD's OPTIMADE API exposes no `_cod_icsd_code` or similar cross-reference field.
- The `spacegroup_number` field in COD's OPTIMADE endpoint is not reliably populated (returns `null`
  in practice), limiting even indirect filtering.

Therefore, **direct ICSD identifier lookup through COD is not possible**.

### Adopted Strategy: Multi-Database Formula + Lattice Parameter Matching

To maximize coverage, we query **both COD and Materials Project** via their OPTIMADE APIs. This
combines:

- **COD** (~500K structures): Experimental crystal structures from published literature.
- **Materials Project** (~154K structures): Computed (DFT) crystal structures, many originally
  sourced from ICSD — giving the highest overlap with MatHub-3d's ICSD-derived entries.

The approach:

1. **Filter** materials locally using MatHub-3d's property data (thermoelectric, electronic, etc.).
2. **Query both COD and Materials Project** by chemical formula via OPTIMADE.
3. **Post-filter by lattice parameter similarity** to identify the best structural match across
   both databases.
4. **Prefer the best lattice match** regardless of source. If both databases have a match, the
   one with the smallest lattice deviation wins.

This is still an approximate matching strategy, but using two databases significantly increases the
chance of finding a match.

### Why Both Databases?

| Database | Strengths | Limitations |
|---|---|---|
| **COD** | Largest open-access collection (~500K); experimental structures | No ICSD cross-ref; spacegroup filter unreliable |
| **Materials Project** | Many structures from ICSD; computed (relaxed) lattice params closer to MatHub-3d's DFT values | Smaller total count (~154K); requires functional matching considerations |

MatHub-3d's lattice parameters are DFT-relaxed, so **Materials Project's computed lattice parameters
are likely a closer match** than COD's experimental values. However, COD's larger catalog ensures
broader formula coverage. Using both gives the best of both worlds.

### Implementation

```python
from Information_Units.Databases.Cod.CodDatabase import CodDatabase
from Information_Units.Databases.Materialsproject.MaterialsprojectDatabase import MaterialsprojectDatabase


def retrieve_cif_for_mathub_results(mathub_results, lattice_tolerance=0.05):
    """
    Attempt to retrieve CIF files from COD and Materials Project for MatHub-3d
    filtered results. Queries both databases and selects the best lattice match.
    
    Args:
        mathub_results: list[dict] from Mathub3dDatabase.retrieve()
        lattice_tolerance: fractional tolerance for lattice parameter matching
                           (0.05 = 5% deviation allowed)
    
    Returns:
        list[dict]: mathub_results enriched with 'cif_path' where a match was found
    """
    cod_db = CodDatabase()
    mp_db = MaterialsprojectDatabase()
    
    for result in mathub_results:
        formula = result['formula']
        mathub_lattice = result.get('lattice', {})
        
        # Query both databases by formula
        cod_cif_paths = cod_db.retrieve({
            'query': formula,
            'limit': 10
        })
        mp_cif_paths = mp_db.retrieve({
            'query': formula,
            'limit': 10
        })
        
        # Tag each path with its source for reporting
        all_candidates = []
        for p in (cod_cif_paths or []):
            all_candidates.append(('cod', p))
        for p in (mp_cif_paths or []):
            all_candidates.append(('materialsproject', p))
        
        if not all_candidates:
            result['cif_path'] = None
            result['cif_source'] = None
            result['cif_match_status'] = 'no_match'
            continue
        
        # Find best lattice match across both databases
        best_match = _find_best_lattice_match(
            all_candidates, mathub_lattice, lattice_tolerance
        )
        
        if best_match:
            result['cif_path'] = best_match[1]
            result['cif_source'] = best_match[0]
            result['cif_match_status'] = 'matched'
        else:
            # Fallback: use first available result (prefer MP over COD since
            # MatHub-3d entries are ICSD-derived and MP has high ICSD overlap)
            mp_first = next((c for c in all_candidates if c[0] == 'materialsproject'), None)
            fallback = mp_first or all_candidates[0]
            result['cif_path'] = fallback[1]
            result['cif_source'] = fallback[0]
            result['cif_match_status'] = 'approximate'
    
    return mathub_results


def _find_best_lattice_match(candidates, target_lattice, tolerance):
    """
    Compare CIF file lattice parameters against MatHub-3d target values.
    Selects the best match across all candidate CIF files from any source.
    
    Args:
        candidates: list of (source_name, cif_path) tuples
        target_lattice: dict with keys 'a', 'b', 'c', 'alpha', 'beta', 'gamma'
        tolerance: fractional tolerance (e.g., 0.05 for 5%)
    
    Returns:
        tuple: (source_name, cif_path) of best match, or None if no match within tolerance
    """
    from pymatgen.core import Structure
    
    target_a = target_lattice.get('a')
    target_b = target_lattice.get('b')
    target_c = target_lattice.get('c')
    
    if not all([target_a, target_b, target_c]):
        return None
    
    best_candidate = None
    best_deviation = float('inf')
    
    for source, cif_path in candidates:
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
                best_candidate = (source, cif_path)
        except Exception:
            continue
    
    return best_candidate
```

### Usage Example

```python
# Step 1: Filter MatHub-3d for candidate materials
mathub_db = Mathub3dDatabase('mathub3d')
candidates = mathub_db.retrieve({
    'query': 'Ni',
    'gap': [0.1, 1.0],
    'bulk_modulus': [50, 200],
    'limit': 5
})

# Step 2: Retrieve CIF files from COD + Materials Project via formula + lattice matching
enriched = retrieve_cif_for_mathub_results(candidates, lattice_tolerance=0.05)

for entry in enriched:
    print(f"{entry['formula']}: CIF={entry['cif_path']} "
          f"(source={entry['cif_source']}, status={entry['cif_match_status']})")
```

### Expected Outcomes

| Scenario | `cif_match_status` | `cif_source` | Meaning |
|---|---|---|---|
| Lattice match found | `matched` | `cod` or `materialsproject` | Lattice params match within tolerance — high confidence |
| Formula found, lattice differs | `approximate` | `materialsproject` (preferred) or `cod` | Same composition, different polymorph possible — use with caution |
| Formula not in either database | `no_match` | `None` | No entry for this composition — CIF unavailable |

### Lookup Priority

When no exact lattice match is found, the fallback preference is:

1. **Materials Project first** — because MatHub-3d entries originate from ICSD, and MP has
   significant ICSD overlap. MP's DFT-relaxed lattice parameters are also methodologically
   closer to MatHub-3d's computed values.
2. **COD second** — broader coverage but experimental lattice parameters may differ more from
   MatHub-3d's DFT values.

When an exact lattice match *is* found, the best match wins regardless of source.

### Limitations

- **Not all MatHub-3d entries will have matches.** Combined, COD (~500K) and MP (~154K) cover a
  large portion of known materials, but gaps remain for novel or rare compositions.
- **Polymorphism:** A formula like `SiO2` has dozens of polymorphs across both databases. Lattice
  parameter matching helps select the right one, but is not infallible.
- **API rate limits:** Both COD and MP OPTIMADE APIs have per-page limits (COD: 10, MP: varies).
  For large-scale cross-referencing, batch processing with delays is recommended.
- **DFT vs experimental lattice:** MP values (DFT-relaxed) will generally be closer to MatHub-3d's
  values than COD's experimental values. This is accounted for by the tolerance-based matching.
- **Approximate, not exact:** This is a best-effort approach. For guaranteed structural accuracy,
  direct ICSD access (institutional license required) is the definitive source.

---

## Summary

| Aspect | COD / MP / Alexandria | MatHub-3d |
|--------|----------------------|-----------|
| **Data Source** | Remote OPTIMADE API | Local JSON (from zip) |
| **Has Atomic Positions** | Yes | No |
| **Returns CIF** | Yes (directly) | Via COD + MP cross-reference (approximate) |
| **CIF Match Method** | N/A (native) | Formula + lattice matching across COD & MP |
| **Unique Value** | Full crystal structures | Thermoelectric transport properties |
| **Query Method** | HTTP API calls | In-memory JSON filtering |
| **Best For** | Structure retrieval | Property-based material screening |
