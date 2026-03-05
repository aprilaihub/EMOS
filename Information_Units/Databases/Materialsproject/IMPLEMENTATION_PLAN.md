# Materials Project (MP) Dataset Implementation Plan for EMOS

**Date:** March 5, 2026  
**Status:** Reference Guide for Implementation  
**Scope:** Adding Materials Project OPTIMADE database support to EMOS

---

## Overview

Implement Materials Project (MP) database support following the same code structure and patterns as Alexandria and COD databases. MP uses the public OPTIMADE API endpoint at `https://api.materialsproject.org/optimade/v1/`.

**Key Principle:** Maintain consistency with existing database implementations (Alexandria, COD). MP is treated as a standard OPTIMADE provider with its own set of queryable thermodynamic properties.

---

## 1. Property Mappings (`property_mappings.json`)

### 1.1 Common Queryable Properties

Add `"materialsproject"` block to the following existing properties:

#### Identifiers & Metadata
- `id`: Material identifier (e.g., "mp-149")
- `type`: Entry type (always "structures")
- `last_modified`: ISO 8601 timestamp

#### Composition
- `nelements`: Count of unique chemical elements
- `elements`: List of chemical element symbols
- `chemical_formula_descriptive`: Human-readable formula

**Format in JSON:**
```json
{
  "id": {
    "type": "string",
    "description": "Unique structure ID",
    "category": "identifier",
    "cod": { "name": "id", "retrievable": true },
    "alexandria": { "name": "id", "retrievable": true },
    "materialsproject": { "name": "id", "retrievable": true }
  },
  "nelements": {
    "type": "integer",
    "description": "Number of unique chemical elements",
    "category": "structural",
    "cod": { "name": "nelements", "retrievable": true },
    "alexandria": { "name": "nelements", "retrievable": true },
    "materialsproject": { "name": "nelements", "retrievable": true }
  }
  // ... similar for other common properties
}
```

### 1.2 MP-Specific Thermodynamic Properties (NEW ENTRIES)

Create 3 new property entries for MP-specific thermodynamic calculations.

**Note:** Only r2SCAN functional properties are queryable via MP OPTIMADE API. GGA+U and GGA+U+r2SCAN variants exist in the data but **cannot be queried** due to URL encoding issues with the `+` symbol in filter strings (verified March 5, 2026).

#### r2SCAN Functional (2 properties) ✅ QUERYABLE
- **`mp_energy_above_hull_r2scan`**
  - Type: `float`
  - Description: Distance from convex hull using r2SCAN functional
  - Unit: `eV/atom`
  - Category: `thermodynamic`
  - Queryable: **Yes**, range support
  - API field: `_mp_stability.r2scan.energy_above_hull`
  - Verified: ✅ Works in actual API queries

- **`mp_formation_energy_r2scan`**
  - Type: `float`
  - Description: Formation energy per atom using r2SCAN functional
  - Unit: `eV/atom`
  - Category: `thermodynamic`
  - Queryable: **Yes**, range support
  - API field: `_mp_stability.r2scan.formation_energy_per_atom`
  - Verified: ✅ Works in actual API queries

#### Chemical System (1 property) ✅ QUERYABLE
- **`mp_chemical_system`**
  - Type: `string`
  - Description: Chemical system identifier (e.g., "Si", "Fe-O", "Al-Si-O")
  - Category: `mp_specific`
  - Queryable: **Yes**, string filter
  - API field: `_mp_chemical_system`
  - Verified: ✅ Works in actual API queries

#### GGA+U and GGA+U+r2SCAN Functionals ❌ NOT QUERYABLE

**These properties exist in API responses but CANNOT be used in query filters:**

- `mp_energy_above_hull_gga_u` (`_mp_stability.gga_gga+u.energy_above_hull`) - ❌ API parsing error
- `mp_formation_energy_gga_u` (`_mp_stability.gga_gga+u.formation_energy_per_atom`) - ❌ API parsing error
- `mp_energy_above_hull_gga_u_r2scan` (`_mp_stability.gga_gga+u_r2scan.energy_above_hull`) - ❌ API parsing error
- `mp_formation_energy_gga_u_r2scan` (`_mp_stability.gga_gga+u_r2scan.formation_energy_per_atom`) - ❌ API parsing error

**Reason:** The `+` symbol in functional names causes URL encoding/parsing failures in the MP OPTIMADE API filter implementation. Even with proper URL encoding (`%2B`), queries return HTTP 400 "Unable to parse filter" errors.

**Do NOT include these in `property_mappings.json`** as they cannot be used for retrieval queries.

**Format in JSON:**
```json
{
  "mp_energy_above_hull_r2scan": {
    "type": "float",
    "description": "Distance from convex hull using r2SCAN functional",
    "category": "thermodynamic",
    "unit": "eV/atom",
    "materialsproject": {
      "name": "_mp_stability.r2scan.energy_above_hull",
      "retrievable": true,
      "range_support": true
    }
  },
  "mp_formation_energy_r2scan": {
    "type": "float",
    "description": "Formation energy per atom using r2SCAN functional",
    "category": "thermodynamic",
    "unit": "eV/atom",
    "materialsproject": {
      "name": "_mp_stability.r2scan.formation_energy_per_atom",
      "retrievable": true,
      "range_support": true
    }
  }
  // ... similar for other MP-specific properties
}
```

### 1.3 Properties NOT Included in Mapping

**Excluded:** Non-queryable structural properties that are only for display/retrieval:
- `lattice_vectors`
- `cartesian_site_positions`
- `species_concentrations`
- `species_masses`
- `assemblies_*` (all assembly-related properties)

These properties are available in the API response but cannot be used as filters in queries, so they don't belong in `property_mappings.json`.

---

## 2. Code Structure and Files

### 2.1 Directory Structure
```
Information_Units/Databases/Materialsproject/
├── MaterialsprojectDatabase.py        # Main database class
├── MaterialsprojectAPIHelper.py       # API interaction helper
├── __init__.py                        # Package initialization
├── README.md                          # Database documentation
└── IMPLEMENTATION_PLAN.md            # This file
```

### 2.2 File Descriptions

#### `MaterialsprojectDatabase.py`
**Location:** `Information_Units/Databases/Materialsproject/MaterialsprojectDatabase.py`

**Purpose:** Main database class that extends `BaseDatabase` and implements MP-specific retrieval logic.

**Key Components:**
- **Constructor (`__init__`)**
  - Initialize with MP's OPTIMADE API base URL: `https://api.materialsproject.org/optimade/v1/`
  - Create temporary output directory for saving CIF files
  - Initialize `MaterialsprojectAPIHelper` instance
  - Set logger if provided

- **`info()` method**
  - Brief description of MP database
  - Example: `"Materials Project: Computed materials database with thermodynamic properties (3+ million structures)"`

- **`retrieve(inputs: dict) -> list` method**
  - **Input parameters:**
    - `query` (str): Material query (e.g., 'Fe', 'Al2O3', 'Fe2O3')
    - `limit` (int): Max results to return (default: 10)
    - Additional keys: Property filters (e.g., `{'nelements': [1, 3], 'mp_energy_above_hull_r2scan': [0.0, 0.05]}`)
  
  - **Implementation steps:**
    1. Extract `query` and `limit` from inputs
    2. Extract property filters (all other keys)
    3. Use `MaterialsprojectAPIHelper.map_properties()` to convert standard property names to MP API field names
    4. Build OPTIMADE filter string using mapped properties
    5. Call MP OPTIMADE API with query + filters
    6. Parse response and validate results
    7. Convert each structure to CIF format using pymatgen
    8. Save CIF files to temporary directory
    9. Return list of file paths
  
  - **Error handling:**
    - API connection errors
    - Invalid queries
    - Response parsing errors
    - Log all errors via logger if provided

  - **Example usage:**
    ```python
    db = MaterialsprojectDatabase()
    files = db.retrieve({
        'query': 'Fe',
        'limit': 5,
        'nelements': [1, 3],
        'mp_energy_above_hull_r2scan': [0.0, 0.05]
    })
    # Returns: ['/tmp/mp_*.cif', '/tmp/mp_*.cif', ...]
    ```

#### `MaterialsprojectAPIHelper.py`
**Location:** `Information_Units/Databases/Materialsproject/MaterialsprojectAPIHelper.py`

**Purpose:** Helper class for MP API interaction, property mapping, and data conversion.

**Key Components:**
- **Constructor (`__init__`)**
  - Store base URL: `https://api.materialsproject.org/optimade/v1/`
  - Load property mapping from `property_mappings.json`
  - Store logger if provided

- **`_load_property_mapping()` -> dict**
  - Read `property_mappings.json` from `Information_Units/` directory
  - Extract only MP-retrievable properties (where `materialsproject.retrievable = true`)
  - Build mapping: standard name → MP API field name
  - Return mapping dict
  - Example:
    ```python
    {
      'nelements': {'name': 'nelements', 'retrievable': True, 'range_support': False},
      'mp_energy_above_hull_r2scan': {'name': '_mp_stability.r2scan.energy_above_hull', 'retrievable': True, 'range_support': True},
      ...
    }
    ```

- **`map_properties(standard_properties: dict) -> dict`**
  - Convert user-provided standard property names to MP API field names
  - Use internal property mapping
  - Skip non-retrievable properties with warning
  - Return mapped dict ready for OPTIMADE filter construction
  - Example:
    ```python
    input: {'nelements': [1, 3], 'mp_energy_above_hull_r2scan': [0.0, 0.05]}
    output: {'nelements': [1, 3], '_mp_stability.r2scan.energy_above_hull': [0.0, 0.05]}
    ```

- **`build_optimade_filter(mapped_properties: dict, query: str) -> str`**
  - Construct OPTIMADE query filter string from mapped properties
  - Handle range filters (e.g., `[min, max]` → `property >= min AND property <= max`)
  - Handle string filters (e.g., exact match)
  - Combine with chemical formula query
  - Example:
    ```
    Input: query='Fe', filters={'nelements': [1, 3]}
    Output: "chemical_formula_hill CONTAINS 'Fe' AND nelements >= 1 AND nelements <= 3"
    ```

- **`query_api(filter_string: str, limit: int) -> dict`**
  - Make HTTP GET request to MP OPTIMADE `/structures` endpoint
  - Pass filter as `filter` parameter
  - Pass limit as `page_limit` parameter
  - Return JSON response
  - Log API calls for debugging

- **`parse_response(response: dict) -> list`**
  - Extract list of structure objects from OPTIMADE response
  - Validate each structure has required fields (`id`, `type`)
  - Return list of parsed structures

- **`structure_to_cif(structure_dict: dict, output_path: str) -> str`**
  - Convert MP structure JSON to pymatgen Structure object
  - Save as CIF file at `output_path`
  - Return file path on success
  - Raise exception with helpful error message on failure

#### `__init__.py`
**Location:** `Information_Units/Databases/Materialsproject/__init__.py`

**Purpose:** Package initialization.

**Content:**
```python
from .MaterialsprojectDatabase import MaterialsprojectDatabase
from .MaterialsprojectAPIHelper import MaterialsprojectAPIHelper

__all__ = ['MaterialsprojectDatabase', 'MaterialsprojectAPIHelper']
```

#### `README.md`
**Location:** `Information_Units/Databases/Materialsproject/README.md`

**Contents:**
- Brief description of Materials Project database
- Link to MP OPTIMADE API documentation
- List of available queryable properties by category
- Example usage
- Notes on functional variants (r2SCAN, GGA+U, combined)

---

## 3. Testing

### 3.1 Unit Tests

**File:** `tests/unit/test_materialsproject_api_behaviour.py`

**Pattern:** Same structure as Alexandria and COD unit tests

**Test Cases:**

#### Filter Building Tests
```python
@pytest.mark.unit
@pytest.mark.parametrize("elements,properties,expected", [
    ("Fe", {}, 'elements HAS "Fe"'),
    ("Al2O3", {}, '(elements HAS "Al" AND elements HAS "O")'),
    ("Fe", {"nelements": 2}, 'elements HAS "Fe" AND nelements = 2'),
    ("Fe", {"nelements": [1, 3]}, 'elements HAS "Fe" AND nelements >= 1 AND nelements <= 3'),
    ("Fe", {"mp_energy_above_hull_r2scan": [0.0, 0.05]}, 'elements HAS "Fe" AND _mp_stability.r2scan.energy_above_hull >= 0.0 AND _mp_stability.r2scan.energy_above_hull <= 0.05'),
    ("Al", {"mp_formation_energy_r2scan": [-2.0, -0.5]}, 'elements HAS "Al" AND _mp_stability.r2scan.formation_energy_per_atom >= -2.0 AND _mp_stability.r2scan.formation_energy_per_atom <= -0.5'),
    ("Fe", {"mp_energy_above_hull_r2scan": [0.0, 0.05], "nelements": [1, 3]}, 'elements HAS "Fe" AND _mp_stability.r2scan.energy_above_hull >= 0.0 AND _mp_stability.r2scan.energy_above_hull <= 0.05 AND nelements >= 1 AND nelements <= 3'),
])
def test_build_filter_variations(elements, properties, expected):
    """Verify filter building with various element and property inputs."""
```

#### API Fetching Tests
```python
@pytest.mark.unit
def test_fetch_api_host_down(monkeypatch):
    """Verify no API calls when host is unreachable."""

@pytest.mark.unit
def test_fetch_api_with_pagination_and_limit(monkeypatch):
    """Verify API handles pagination, respects limit, and processes empty results."""
    # Test 1: Pagination - Multiple API calls for results > page_limit
    # Test 2: Respects Limit - Stop fetching once limit reached  
    # Test 3: Empty Results - Return empty list gracefully
```

### 3.2 Integration Tests

**File:** `tests/integration/test_materialsproject_api_sanity.py`

**Pattern:** Same structure as Alexandria and COD integration tests (with MP-specific parameters)

**Setup:**
```python
@pytest.fixture(autouse=True)
def rate_limit_delay():
    """Add delay between tests to avoid MP API rate limiting."""
    time.sleep(4.0)  # 4 second delay
    yield
```

**Test Cases:**

#### Main Parametrized Test
```python
@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
@pytest.mark.parametrize("query,expected_elements,filters,expected_nperiodic_dimensions,expected_nelements_range,expected_props", [
    # Basic queries without property filters
    ("Fe", ["Fe"], {}, None, None, None),
    ("Al2O3", ["Al", "O"], {}, None, None, None),
    ("Fe2O3", ["Fe", "O"], {}, None, None, None),
    # Structural property filters
    ("Fe", ["Fe"], {"nelements": [1, 3]}, None, (1, 3), None),
    ("Al2O3", ["Al", "O"], {"nelements": [2, 5]}, None, (2, 5), None),
    ("Fe", ["Fe"], {"nperiodic_dimensions": 3}, 3, None, None),
    # r2SCAN thermodynamic property filters
    ("Fe", ["Fe"], {"mp_energy_above_hull_r2scan": [0.0, 0.05]}, None, None, {"_mp_stability.r2scan.energy_above_hull": (0.0, 0.05)}),
    ("Al", ["Al"], {"mp_formation_energy_r2scan": [-2.0, -0.5]}, None, None, {"_mp_stability.r2scan.formation_energy_per_atom": (-2.0, -0.5)}),
    # Combined filters
    ("Fe", ["Fe"], {"mp_energy_above_hull_r2scan": [0.0, 0.05], "nelements": [1, 3]}, None, (1, 3), {"_mp_stability.r2scan.energy_above_hull": (0.0, 0.05)}),
])
def test_materialsproject_retrieve_structures(
    query,
    expected_elements,
    filters,
    expected_nperiodic_dimensions,
    expected_nelements_range,
    expected_props,
):
    """Verify MP returns valid CIF files with various queries and property filters.
    
    Tests both structural properties (encoded in CIF) and DFT properties (from API).
    """
```

**Test Implementation:**
1. If `expected_props` is provided, validate properties at API level before CIF retrieval
2. Retrieve CIF files through database
3. Verify CIF files exist and are valid
4. Verify expected elements present in CIF content
5. If `expected_nelements_range` or `expected_nperiodic_dimensions`, validate from CIF

#### Performance Benchmark Test
```python
@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
@pytest.mark.parametrize("limit", [1, 10, 15])
def test_materialsproject_retrieve_performance(benchmark, limit):
    """Benchmark retrieval performance for different result limits."""
```

**Utilities:**
- Reuse CIF parsing utilities from `tests/integration/conftest.py`:
  - `validate_cif_file(filepath)` → bool
  - `extract_formula_from_cif(filepath)` → str
  - `extract_nelements_from_cif(filepath)` → int
  - `extract_nperiodic_dimensions_from_cif(filepath)` → int

---

## 4. Implementation Notes

### 4.1 No MP-Specific Handling Required

Materials Project is treated as a standard OPTIMADE database provider. **No special handling needed.**

- No API key authentication (public OPTIMADE endpoint)
- No functional filter validation (users can query any combination of functional variants)
- No custom rate limiting logic (follow standard practice: add delay in integration tests)

### 4.2 API Endpoint Details

**Base URL:** `https://optimade.materialsproject.org/v1/` (verified March 5, 2026)

**Structures Endpoint:** `/v1/structures`

**Query Parameters:**
- `filter`: OPTIMADE filter string
- `page_limit`: Max results per request (default: 10)
- `response_fields`: Comma-separated field names to include in response

**Response Format:** Standard OPTIMADE v1.0 JSON structure

### 4.3 Code Reuse from Alexandria/COD

Follow these patterns from existing implementations:

**From `AlexandriaDatabase.py`:**
- Property mapping loading pattern
- OPTIMADE filter construction
- CIF file generation with pymatgen
- Temporary directory creation

**From `CodDatabase.py`:**
- Error handling for API calls
- Logger integration
- Input validation in `retrieve()`

**From `AlexandriaAPIHelper.py` and `CodAPIHelper.py`:**
- HTTP request handling with requests library
- JSON response parsing
- Logging conventions

### 4.4 Dependencies

**Required (already in environment):**
- `requests`: HTTP requests
- `pymatgen`: Structure conversion to CIF
- `pytest`: Testing framework
- `json`: JSON parsing

**No additional dependencies needed.**

### 4.5 File Path Handling

Use absolute paths for CIF file outputs:
```python
import tempfile

self.output_dir = tempfile.mkdtemp(prefix="materialsproject_")
# Output: /tmp/materialsproject_abc123/
```

Return full file paths in `retrieve()` for UI/backend consumption.

---

## 5. Summary

| Component | Details |
|-----------|---------|
| **Property Mappings** | 13 common properties + 2 r2SCAN thermodynamic properties + 1 chemical system filter = **16 total queryable properties** |
| **Code Files** | 2 files (Database + APIHelper) + init + README |
| **Test Files** | Unit tests + Integration tests with real API |
| **Dependencies** | None (use existing) |
| **API Endpoint** | `https://optimade.materialsproject.org/v1/` (public, no auth) |
| **Special Handling** | None (GGA+U variants excluded due to API queryability issues) |
| **Code Pattern** | Identical to Alexandria/COD |
| **Verification** | All properties tested against live API (March 5, 2026) |

---

## 6. Checklist for Implementation

- [ ] Update `property_mappings.json` with MP properties
- [ ] Create `MaterialsprojectDatabase.py`
- [ ] Create `MaterialsprojectAPIHelper.py`
- [ ] Create `__init__.py` in Materialsproject folder
- [ ] Create `README.md` in Materialsproject folder
- [ ] Create unit test file
- [ ] Create integration test file
- [ ] Test property mapping loading
- [ ] Test filter construction
- [ ] Test API queries (basic, filters, thermodynamic)
- [ ] Test CIF file generation and validation
- [ ] Verify integration with DatabaseFactory
- [ ] Documentation complete
- [ ] Code review & testing passed

