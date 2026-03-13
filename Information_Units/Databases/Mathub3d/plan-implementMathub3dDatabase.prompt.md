# Plan: Implement MatHub-3d Database

Implement the MatHub-3d database that filters materials from a local JSON dataset (74K entries), then cross-references COD + Materials Project via OPTIMADE to retrieve real CIF files — returning `list[str]` (CIF paths) consistent with all other databases. Includes `property_mappings.json` updates, a helper class, and full unit + integration tests.

---

**Steps**

### Phase 1: Property Mappings Update
1. **Update `Information_Units/property_mappings.json`** — Add `"mathub3d"` key to existing properties and add new property entries for 18 MatHub-3d fields (see RETRIEVAL_STRATEGY.md table). Each follows `{name, retrievable, range_support}`.

### Phase 2: Core Implementation — Helper
2. **Create `Information_Units/Databases/Mathub3d/Mathub3dHelper.py`** — Analogous to `CodAPIHelper`/`AlexandriaAPIHelper`:
   - `_load_data()` — Lazy-load `MatHub-3d.json` from the zip, cache in `self._data`
   - `_load_property_mapping()` — Read mathub3d entries from `property_mappings.json` (same pattern as `AlexandriaAPIHelper._load_property_mapping()`)
   - `parse_elements(query)` — Parse formula → element list (use pymatgen `Composition`, same as `_build_composition_filter` in other helpers)
   - `filter_by_formula(data, query)` — Filter entries where all queried elements are in entry's `elements` list
   - `filter_by_properties(data, filters, prop_map)` — Apply range `[min, max]`, exact scalar, and boolean filters using mapped field names
   - `get_lattice(entry)` — Prefer relaxed `after_a/b/c/alpha/beta/gamma`, fall back to `before_*`
   - `find_cif_match(entry, cod_db, mp_db, output_dir, tolerance=0.05)` — Query COD + MP by formula, compare lattice params of returned CIF files against MatHub-3d entry, return best CIF path or None. Uses `pymatgen.core.Structure.from_file()` for lattice comparison.

### Phase 3: Core Implementation — Database
3. **Replace stub in `Information_Units/Databases/Mathub3d/Mathub3dDatabase.py`** — Orchestrates full pipeline:
   - `__init__` — Create temp dir, instantiate `CodDatabase` + `MaterialsprojectDatabase` for cross-ref, create `Mathub3dHelper`
   - `retrieve(inputs)` — Extract `query`/`limit`/property filters → filter JSON → iterate entries calling `find_cif_match()` → stop once `limit` CIF matches collected → return `list[str]`

### Phase 4: Unit Tests
4. **Create `tests/unit/test_mathub3d_behaviour.py`** — All mocked, fast:
   - Formula filtering: parametrized for `"Fe"`, `"Al2O3"`, multi-element
   - Property filtering: range, exact, boolean
   - Property mapping from `property_mappings.json`
   - Lazy loading with mocked zipfile
   - CIF cross-reference: mock `CodDatabase.retrieve()` + `MaterialsprojectDatabase.retrieve()`, verify lattice matching logic
   - Output format: verify `list[str]` of `.cif` paths
   - All marked `@pytest.mark.unit`

### Phase 5: Integration Tests
5. **Create `tests/integration/test_mathub3d_sanity.py`** — Real data + real API:
   - Parametrized test cases with queries + property filters against real zip + COD/MP APIs
   - Validate CIF files exist and are valid (reuse `validate_cif_file`, `extract_formula_from_cif` from `tests/integration/conftest.py`)
   - `rate_limit_delay` fixture (COD + MP API calls under the hood)
   - Benchmark tests
   - All marked `@pytest.mark.integration`, `@pytest.mark.network`, `@pytest.mark.slow`

### Phase 6: Mock Data
6. **Update `tests/fixtures/mock_data.py`** — Add `MATHUB3D_FE_ENTRY` and `MATHUB3D_AL2O3_ENTRY` matching real JSON structure.

---

**Relevant files**
- `Information_Units/Databases/Mathub3d/Mathub3dDatabase.py` — Replace stub with full orchestrator
- `Information_Units/Databases/Mathub3d/Mathub3dHelper.py` — New: JSON loading, filtering, cross-referencing, lattice matching
- `Information_Units/property_mappings.json` — Add mathub3d entries for 18 properties
- `Information_Units/Databases/Cod/CodDatabase.py` — Used directly for CIF cross-reference
- `Information_Units/Databases/Materialsproject/MaterialsprojectDatabase.py` — Used directly for CIF cross-reference
- `Information_Units/Databases/DatabaseFactory.py` — Already registers mathub3d, no change
- `tests/unit/test_mathub3d_behaviour.py` — New: unit tests
- `tests/integration/test_mathub3d_sanity.py` — New: integration tests
- `tests/fixtures/mock_data.py` — Add mock entries

**Verification**
1. `pytest tests/unit/test_mathub3d_behaviour.py -v -m unit` — All pass (no network)
2. `pytest tests/integration/test_mathub3d_sanity.py -v -m integration` — All pass (needs network)
3. `pytest tests/integration/test_information_unit_interfaces.py -v` — MatHub-3d auto-discovered
4. Manual: `Mathub3dDatabase('mathub3d').retrieve({'query': 'Fe', 'limit': 3})` → returns list of CIF paths

**Decisions**
- **Output**: `list[str]` (CIF paths) — consistent with all other databases
- **CIF source**: Cross-reference COD + MP by formula + lattice parameter matching; entries with no match are skipped (not returned)
- **Lattice tolerance**: 5% fractional deviation. Prefer MP match (DFT→DFT lattice closer), fall back to COD
- **Limit on final output**: Iterate filtered entries until `limit` CIF matches collected
- **Helper class** for testable separation (analogous to `*APIHelper` in other DBs)
- **Lazy loading** of 52 MB JSON, cached after first call
- **Property mapping** from central `property_mappings.json`

**Further Considerations**
1. **Performance**: Each entry may trigger 2 API calls (COD + MP). For `limit=5`, worst case ~10+ API calls. Fine for small limits; a future caching layer could help for large-scale screening.
2. **Lattice preference**: Relaxed (`after_*`) preferred for matching; fall back to initial (`before_*`) when not available.
