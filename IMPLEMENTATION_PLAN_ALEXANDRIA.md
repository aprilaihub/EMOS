# Alexandria Dataset Integration: Detailed Implementation Plan

**Project**: Add Alexandria (PBEsol) OPTIMADE-backed database to EMOS  
**Branch**: `feature/alexandria-dataset`  
**Date Created**: March 3, 2026  
**Status**: Ready for development

---

## PART 1: CONSOLIDATED DIFFERENCE MATRIX

### 1.1 Base Configuration
- **COD Base URL**: `https://www.crystallography.net/cod/optimade/v1/`
- **Alexandria Base URL**: `https://alexandria.icams.rub.de/pbesol/v1/` (PBEsol variant)
- **API Version**: Both use OPTIMADE v1.1.0 (compatible)
- **Dataset Focus**: PBEsol → band gap accuracy for electronics materials

### 1.2 Pagination Limits (CRITICAL)
- **COD**:
  - API max page_limit: 100
  - Code uses: 10 per request (conservative)
- **Alexandria**:
  - API max page_limit: 500
  - Code should use: **100 per request** (balance of speed/safety)
  - **Use case**: Faster pagination than COD without hitting rate limits

### 1.3 Response Field Strictness (GOTCHA #1)
- **COD**: Permissive (unknown fields → returns null)
- **Alexandria**: **Strict (unknown fields → HTTP 400 Bad Request)**
  - **Implication**: Must build Alexandria-specific response_fields allowlist
  - **Action**: Do NOT reuse COD's hardcoded response_fields string
  - **Safe fields** (both support): `id, elements, nelements, lattice_vectors, species_at_sites, cartesian_site_positions, chemical_formula_reduced, last_modified, type, nperiodic_dimensions`

### 1.4 Property Mapping Structure
- **Shared OPTIMADE fields**: Both COD and Alexandria support core properties
- **Provider-specific fields**:
  - COD: `_cod_*` (crystallography metadata)
  - Alexandria: `_alexandria_band_gap`, `_alexandria_formation_energy_per_atom`, `_alexandria_space_group`, `_alexandria_stress_tensor`, etc.
- **Action**: Extend `property_mappings.json` with `"alexandria"` block per property

### 1.5 Structure Data Format (IDENTICAL)
- Lattice vectors, species encoding, atomic positions: **same format as COD**
- Conversion logic (`convert_to_structure()`, `save_cif_from_structure()`): **100% reusable**

### 1.6 Filter Building (MOSTLY REUSABLE)
- Composition filter: `elements HAS "Fe"` (identical)
- Range filter: `nelements >= 1 AND nelements <= 5` (identical)
- **Key difference**: Must validate requested filter properties exist in Alexandria before building (to avoid 400 error)

---

## PART 2: PHASE 1 IMPLEMENTATION (Core Retrieval Pipeline)

### Phase 1 Goal
Implement working Alexandria retrieval pipeline with PBEsol endpoint. Users can query materials but property mapping is basic (shared fields only).

### Phase 1 Tasks

#### **Task 1.1: Create AlexandriaAPIHelper.py**
**File**: `Information_Units/Databases/Alexandria/AlexandriaAPIHelper.py`

**Steps**:
1. Clone `CodAPIHelper.py` as template
2. Replace class name: `CodAPIHelper` → `AlexandriaAPIHelper`
3. Update docstrings: references to COD → Alexandria
4. **Critical changes**:
   - `self.property_mapping` key: change from `"cod"` to `"alexandria"` in `_load_property_mapping()`
   - `page_limit = 10` → `page_limit = 100` (line ~108 equivalent)
   - `response_fields` string: **Do NOT hardcode**; instead call helper method to build from `/info/structures` endpoint
5. Keep identical:
   - `fetch_from_api()` pagination loop (reuse page_offset logic)
   - `build_filter()` composition and range filter logic
   - `convert_to_structure()` (full reuse)
   - `save_cif_from_structure()` (full reuse)
   - `is_host_reachable()` (reuse, just change base_url)

**New method to add**:
```python
def _build_response_fields(self) -> str:
    """
    Build response_fields string dynamically from Alexandria /info/structures.
    Ensures only safe, supported fields are requested (avoids 400 errors).
    
    Safe baseline: id, elements, nelements, lattice_vectors, species_at_sites,
                   cartesian_site_positions, chemical_formula_reduced, last_modified,
                   type, nperiodic_dimensions
    
    Returns:
        str: Comma-separated response_fields string
    """
    # Try to fetch supported fields from /info/structures endpoint
    # Fallback to safe baseline if unavailable
```

**Validation checkpoint**:
- [ ] AlexandriaAPIHelper instantiates without errors
- [ ] `is_host_reachable()` returns True
- [ ] `_load_property_mapping()` loads "alexandria" block correctly

---

#### **Task 1.2: Update AlexandriaDatabase.py**
**File**: `Information_Units/Databases/Alexandria/AlexandriaDatabase.py`

**Current state**: Stub implementation  
**Target**: Full working retrieve() method

**Steps**:
1. Replace stub code with production implementation (mirror CodDatabase structure)
2. Set base URL permanently to PBEsol:
   ```python
   self.base_url = "https://alexandria.icams.rub.de/pbesol/v1/"
   ```
3. Instantiate `AlexandriaAPIHelper(self.base_url, logger=logger)`
4. Implement `retrieve(inputs: dict) -> list`:
   - Extract `query`, `limit`, and property filters from inputs
   - Call `api_helper.map_properties()` to convert standard → Alexandria property names
   - Call `api_helper.fetch_from_api(query, limit, filters)` to get raw OPTIMADE entries
   - Call `api_helper.convert_to_structure()` for each entry
   - Call `api_helper.save_cif_from_structure()` to save as CIF
   - Return list of CIF file paths
5. Update `info()`:
   ```python
   return "Alexandria (PBEsol): DFT-calculated materials database (415K structures, optimized for band gap accuracy)"
   ```

**Validation checkpoint**:
- [ ] AlexandriaDatabase instantiates correctly
- [ ] `info()` returns expected string
- [ ] `retrieve({'query': 'Fe', 'limit': 3})` returns list of 3 CIF paths (or fewer if not available)

---

#### **Task 1.3: Extend property_mappings.json**
**File**: `Information_Units/property_mappings.json`

**Current structure**:
```json
{
  "properties": {
    "elements": {
      "cod": { "name": "elements", "retrievable": true },
      ...
    }
  }
}
```

**Changes**:
1. For each existing property with `"cod"` block, add parallel `"alexandria"` block:
   ```json
   "elements": {
     "cod": { "name": "elements", "retrievable": true },
     "alexandria": { "name": "elements", "retrievable": true }
   }
   ```
2. Shared properties to map (Phase 1 minimum):
   - `elements`
   - `nelements`
   - `nperiodic_dimensions`
   - `chemical_formula_descriptive`
   - `last_modified`
   - `type`
3. Do NOT add Alexandria-specific properties yet (e.g., `_alexandria_band_gap`); defer to Phase 2

**Validation checkpoint**:
- [ ] JSON is valid (test with `python -m json.tool property_mappings.json`)
- [ ] All 6 shared properties have both "cod" and "alexandria" blocks
- [ ] `AlexandriaAPIHelper._load_property_mapping()` loads all 6 properties

---

#### **Task 1.4: Verify DatabaseFactory Registration**
**File**: `Information_Units/Databases/DatabaseFactory.py`

**Expected state**: Should already have:
```python
from Information_Units.Databases.Alexandria.AlexandriaDatabase import AlexandriaDatabase

database_factory = {
    "alexandria": AlexandriaDatabase,
    ...
}
```

**Action**: Verify no changes needed (should already be in place)

**Validation checkpoint**:
- [ ] `database_factory["alexandria"]` resolves to `AlexandriaDatabase` class
- [ ] Can instantiate: `db = database_factory["alexandria"]("alexandria", logger=None)`

---

### Phase 1 Testing Strategy

#### **Unit Tests: test_alexandria_api_helper.py**
**Location**: `tests/unit/test_alexandria_api_helper.py`

**Test cases** (clone from `test_cod_api_helper.py` with Alexandria-specific adjustments):

1. **test_load_property_mapping**
   - Verify "alexandria" block loads with 6+ properties
   - Confirm all marked as retrievable
   
2. **test_map_properties_basic**
   - Input: `{"elements": None, "nelements": 2}`
   - Expected output: `{"elements": None, "nelements": 2}` (passthrough since names match)
   
3. **test_build_filter_composition**
   - Input: `query="Fe"` → Expected: `'elements HAS "Fe"'`
   - Input: `query="Al2O3"` → Expected: `'(elements HAS "Al" AND elements HAS "O")'`
   
4. **test_build_filter_with_ranges**
   - Input: `query="Fe", filters={"nelements": [1, 3]}`
   - Expected: `'elements HAS "Fe" AND nelements >= 1 AND nelements <= 3'`
   
5. **test_page_limit_enforcement**
   - Mock API call with `page_limit=100` (Alexandria's recommended)
   - Verify request is formed correctly
   
6. **test_response_fields_safe_list**
   - Verify only safe fields are in response_fields string
   - Confirm no COD-specific fields included

7. **test_convert_to_structure_basic**
   - Use real or mock OPTIMADE entry with lattice, species, positions
   - Verify returns valid pymatgen Structure
   
8. **test_save_cif_from_structure**
   - Verify CIF file created in output directory
   - Confirm file is readable and has valid format

**Run**: `pytest tests/unit/test_alexandria_api_helper.py -v`

#### **Integration Tests: test_alexandria_database_api.py**
**Location**: `tests/integration/test_alexandria_database_api.py`

**Prerequisites**: Network access to Alexandria API endpoint required

**Test cases**:

1. **test_alexandria_host_reachable**
   - `api_helper.is_host_reachable()` → True
   
2. **test_alexandria_retrieve_structures_simple**
   - Query: `'Fe'`, limit: 3
   - Expected: 3 CIF files returned
   - Verify files exist and contain crystal data
   
3. **test_alexandria_retrieve_with_range_filter**
   - Query: `{'query': 'Fe', 'limit': 5, 'nelements': [1, 3]}`
   - Expected: 5 structures with 1–3 unique elements
   - Verify filters applied correctly
   
4. **test_alexandria_pagination_correctness**
   - Request limit: 150
   - Expected: 2 API calls (100 + 50 items)
   - Verify total returned ≤ 150
   
5. **test_alexandria_no_structures_found**
   - Query: `'NonExistentElement123'`
   - Expected: Empty list, no errors
   
6. **test_database_retrieve_returns_paths**
   - `db.retrieve({'query': 'O', 'limit': 2})`
   - Expected: List of CIF file paths (should exist on disk)

**Markers**: Use `@pytest.mark.integration`, `@pytest.mark.network`, `@pytest.mark.slow`  
**Run**: `pytest tests/integration/test_alexandria_database_api.py -v`

#### **Smoke Test: Manual Verification**
```bash
cd /home/soe/EMOS
python -c "
from Information_Units.Databases.DatabaseFactory import database_factory
db = database_factory['alexandria']('alexandria')
print('Info:', db.info())
results = db.retrieve({'query': 'Fe', 'limit': 2})
print(f'Retrieved {len(results)} structures')
for path in results:
    print(f'  - {path}')
"
```

**Expected output**:
```
Info: Alexandria (PBEsol): DFT-calculated materials database...
Retrieved 2 structures
  - /tmp/alexandria_xxx/Fe_...cif
  - /tmp/alexandria_xxx/Fe_...cif
```

---

## PART 3: PHASE 2 IMPLEMENTATION (Property Mapping & Advanced Filtering)

### Phase 2 Goal
Add Alexandria-specific properties (`_alexandria_band_gap`, etc.) to mapping and enable advanced queries. Support provider-specific filters while maintaining COD compatibility.

### Phase 2 Tasks

#### **Task 2.1: Extend property_mappings.json with Alexandria Properties**
**File**: `Information_Units/property_mappings.json`

**New properties to add**:
```json
"band_gap": {
  "cod": { "name": "", "retrievable": false },
  "alexandria": { "name": "_alexandria_band_gap", "retrievable": true, "range_support": true }
}
,
"formation_energy_per_atom": {
  "cod": { "name": "", "retrievable": false },
  "alexandria": { "name": "_alexandria_formation_energy_per_atom", "retrievable": true, "range_support": true }
}
,
"space_group_symbol": {
  "cod": { "name": "spacegroup_symbol", "retrievable": true, "range_support": false },
  "alexandria": { "name": "_alexandria_space_group", "retrievable": true, "range_support": false }
}
```

**Validation checkpoint**:
- [ ] JSON is still valid
- [ ] AlexandriaAPIHelper loads all new Alexandria properties
- [ ] Properties with `"retrievable": false` for one provider don't break filter building

---

#### **Task 2.2: Enhance Filter Validation in AlexandriaAPIHelper**
**File**: `Information_Units/Databases/Alexandria/AlexandriaAPIHelper.py`

**New method**:
```python
def _validate_filter_properties(self, filters: dict) -> dict:
    """
    Validate that all requested filter properties are retrievable in Alexandria.
    Log warnings for unsupported properties; return cleaned filters.
    
    Args:
        filters: Dict with mapped property names
    
    Returns:
        dict: Validated filters with only retrievable properties
    """
    validated = {}
    for prop_name, value in filters.items():
        # Check if property is marked retrievable for alexandria
        is_valid = False
        for std_name, prop_info in self.property_mapping.items():
            if prop_info['name'] == prop_name and prop_info.get('retrievable'):
                is_valid = True
                break
        
        if is_valid:
            validated[prop_name] = value
        else:
            if self.logger:
                self.logger.log(f"Warning: Property '{prop_name}' not retrievable in Alexandria, skipping")
    
    return validated
```

**Update `fetch_from_api()`**:
```python
# Before building filter query, validate properties
filters = self._validate_filter_properties(filters)
optimade_filter = self.build_filter(query, filters)
```

**Validation checkpoint**:
- [ ] Non-retrievable properties are filtered before API call
- [ ] Warnings logged for skipped properties
- [ ] No 400 errors from invalid filters

---

#### **Task 2.3: Update AlexandriaDatabase.retrieve() Docstring**
**File**: `Information_Units/Databases/Alexandria/AlexandriaDatabase.py`

**Update docstring to document Alexandria-specific properties**:
```python
def retrieve(self, inputs: dict) -> list:
    """
    Retrieve materials from Alexandria (PBEsol) using OPTIMADE API.

    Args:
        inputs (dict): Query parameters
            - query: Material query (e.g., 'Fe', 'Al2O3')
            - limit: Max number of results (default: 10)
            - Additional keys are standard property filters:
              
              Shared properties (COD + Alexandria):
              - nelements: [min, max] - number of unique elements
              - nperiodic_dimensions: int - periodicity
              
              Alexandria-specific properties:
              - band_gap: [min, max] (eV) - electronic band gap
              - formation_energy_per_atom: [min, max] (eV/atom) - formation energy
              - space_group_symbol: str - space group symbol
            
            Example (band gap filter):
              db.retrieve({
                  'query': 'Al2O3',
                  'limit': 5,
                  'band_gap': [2.0, 6.0]
              })

    Returns:
        list: Paths to saved CIF files
    """
```

---

#### **Task 2.4: Create Integration Tests for Phase 2**
**File**: `tests/integration/test_alexandria_database_advanced.py` (new file)

**Test cases**:

1. **test_alexandria_band_gap_range_filter**
   - Query with `'band_gap': [1.0, 3.0]`
   - Verify returned structures have computed band gaps
   
2. **test_alexandria_formation_energy_filter**
   - Query with `'formation_energy_per_atom': [-1.0, 0.0]`
   - Verify structures returned with energy info
   
3. **test_alexandria_space_group_filter**
   - Query with `'space_group_symbol': 'P1'`
   - Verify space group metadata in results
   
4. **test_alexandria_combined_filters**
   - Query: `'Fe'` + `'nelements': [1, 3]` + `'band_gap': [0.5, 2.0]`
   - Verify multiple filters combined with AND
   
5. **test_alexandria_unsupported_property_skipped**
   - Query with property not in Alexandria mapping
   - Expected: Property silently skipped, query still runs

**Run**: `pytest tests/integration/test_alexandria_database_advanced.py -v`

---

#### **Task 2.5: Update Documentation**
**File**: `docs/information_units/databases.md`

**Update Alexandria section with detailed info**:
```markdown
### Alexandria - DFT Materials Database (PBEsol)
**ID**: `alexandria`

Curated DFT-calculated materials database using PBEsol functional, optimized for band gap accuracy in semiconductors and optoelectronic materials.

**Capabilities**:
- 415K structures (PBEsol-calculated)
- Formation energies and phase stability
- Electronic properties (band gaps, DOS)
- Stress tensors and other DFT outputs

**Input Parameters**:
- `query`: Material formula or element
- `limit`: Max number of results
- `nelements`: [min, max] - number of unique elements
- `formation_energy_per_atom`: [min, max] - eV/atom
- `band_gap`: [min, max] - electronic band gap (eV)

**Example**:
```python
db = database_factory["alexandria"]("alexandria")
results = db.retrieve({
    'query': 'Al2O3',
    'limit': 5,
    'band_gap': [2.0, 6.0]
})
```

**Output Format**:
- CIF files with crystal structures
- DFT-calculated properties
```

**File**: `Information_Units/Databases/Alexandria/README.md`

**Update to describe capabilities**:
```markdown
# Alexandria Database (PBEsol)

Provides access to the Alexandria database, a collection of DFT-calculated crystal structures and properties using the PBEsol functional.

## Overview

The Alexandria database contains 415K structures calculated with DFT using PBEsol functional. This functional is optimized for band gap predictions in semiconductors and is ideal for EMOS electronics applications.

## Key Methods

- `info()`: Returns description and capabilities
- `retrieve(params)`: Retrieves materials matching criteria

## Supported Properties

Standard OPTIMADE properties and Alexandria-specific computed properties available via property filtering.
```

---

## PART 4: VALIDATION CHECKLIST

### Pre-Implementation Checklist
- [ ] Git branch `feature/alexandria-dataset` is checked out
- [ ] All team members aware of PBEsol (vs PBE) choice and electronics focus
- [ ] Understanding of GOTCHA #1: Alexandria strict response_fields validation

### Phase 1 Completion Checklist
- [ ] AlexandriaAPIHelper.py created and functional
- [ ] AlexandriaDatabase.py updated with full retrieve() implementation
- [ ] property_mappings.json extended with "alexandria" block for 6 shared properties
- [ ] All Phase 1 unit tests pass: `pytest tests/unit/test_alexandria_api_helper.py -v`
- [ ] All Phase 1 integration tests pass: `pytest tests/integration/test_alexandria_database_api.py -v`
- [ ] Manual smoke test successful
- [ ] COD tests still pass (no regression): `pytest tests/unit/test_cod_api_helper.py -v`
- [ ] Git commit with message: "Phase 1: Alexandria (PBEsol) core retrieval pipeline"

### Phase 2 Completion Checklist
- [ ] property_mappings.json extended with Alexandria-specific properties (band_gap, formation_energy, etc.)
- [ ] AlexandriaAPIHelper._validate_filter_properties() implemented
- [ ] AlexandriaDatabase.retrieve() docstring updated with new property filters
- [ ] Phase 2 integration tests pass: `pytest tests/integration/test_alexandria_database_advanced.py -v`
- [ ] Documentation updated (databases.md, README.md)
- [ ] All tests still green (full suite)
- [ ] Git commit with message: "Phase 2: Alexandria advanced property mapping and filtering"

### Merge Checklist
- [ ] Feature branch: `feature/alexandria-dataset`
- [ ] All tests passing on branch
- [ ] Code review approval (if applicable)
- [ ] Rebase on main (no conflicts)
- [ ] Create PR and merge to main

---

## PART 5: QUICK REFERENCE: CODE SNIPPETS

### Initialize Alexandria in a Feature
```python
from Information_Units.Databases.DatabaseFactory import database_factory

db = database_factory["alexandria"]("alexandria", logger=self.logger)
results = db.retrieve({
    'query': 'Al2O3',
    'limit': 10,
    'band_gap': [2.0, 5.0]
})
```

### Response Fields Safe List
```
id,elements,nelements,lattice_vectors,species_at_sites,cartesian_site_positions,
fractional_site_positions,chemical_formula_reduced,last_modified,type,nperiodic_dimensions
```

### Example OPTIMADE Filter Built
```
elements HAS "Fe" AND nelements >= 1 AND nelements <= 3 AND _alexandria_band_gap >= 1.0 AND _alexandria_band_gap <= 2.0
```

### AlexandriaAPIHelper Configuration Defaults
```python
self.base_url = "https://alexandria.icams.rub.de/pbesol/v1/"
page_limit = 100  # Alexandria max is 500; we use 100 for balance
time.sleep(1.0)   # Between pages (rate limiting)
timeout = 30      # API request timeout
```

---

## PART 6: KNOWN RISKS & MITIGATIONS

| Risk | Mitigation |
|------|-----------|
| Alexandria strict response_fields → 400 errors | Build allowlist dynamically from /info/structures; never hardcode COD's list |
| Band gap values null/missing in some entries | Gracefully skip entries; log warnings; return empty structure list if no valid data |
| PBEsol dataset smaller than COD (415K vs 531K) | Acceptable trade-off; band gap accuracy preferred for electronics |
| Rate limiting on repeated queries | Maintain 1.0s sleep between API pages; log all API calls for debugging |
| Network timeout during large retrieval | Use timeout=30; retry logic; catch and return partial results |

---

## PART 7: NEXT STEPS FOR NEW CONVERSATION

Start with:
1. **Read this plan in full** to understand architecture
2. **Task 1.1**: Create AlexandriaAPIHelper.py (largest code addition)
3. **Task 1.2**: Update AlexandriaDatabase.py
4. **Task 1.3**: Extend property_mappings.json
5. **Run Phase 1 tests** and validate
6. **Only then**: Move to Phase 2 for advanced properties

**Success criteria**: Can query Alexandria and retrieve CIF files like COD, with strict response_field validation working correctly.

---

**End of Implementation Plan**
