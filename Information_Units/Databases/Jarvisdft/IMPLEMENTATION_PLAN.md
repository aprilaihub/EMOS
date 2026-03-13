## Plan: Implement JARVIS DFT Database

Implement full JARVIS DFT database retrieval following the Alexandria pattern — create a `JarvisdftAPIHelper` (mirroring `AlexandriaAPIHelper`), flesh out `JarvisdftDatabase.retrieve()`, add JARVIS DFT property mappings to `property_mappings.json`, and replicate the Alexandria test suite (unit + integration) for JARVIS DFT.

---

### Phase 1: Property Mappings
1. ~~Query JARVIS DFT OPTIMADE `/info/structures` endpoint to discover available properties and their prefixes~~ **DONE** — prefix is `_jarvis_*` (e.g. `_jarvis_optb88vdw_bandgap`, `_jarvis_formation_energy_peratom`). Full attribute list discovered from live API.
2. Add `"jarvisdft"` entries to relevant properties in `Information_Units/property_mappings.json` — each with `name`, `retrievable`, `range_support`
3. Map common properties where applicable (`band_gap`, `formation_energy_per_atom`, `energy`, etc.) and add JARVIS-unique properties (optical, solar cell, thermoelectric, piezoelectric, exfoliation, superconductivity, etc.) as new top-level entries

**Discovered JARVIS DFT properties** (prefix `_jarvis_`):
- Electronic: `optb88vdw_bandgap`, `mbj_bandgap`, `hse_gap`, `spillage`
- Energetic: `optb88vdw_total_energy`, `formation_energy_peratom`, `ehull`, `exfoliation_energy`
- Structural: `spg_number`, `spg_symbol`, `density`, `nat`, `crys`, `dimensionality`
- Dielectric: `epsx`, `epsy`, `epsz`, `mepsx`, `mepsy`, `mepsz`
- Transport: `n-Seebeck`, `p-Seebeck`, `ncond`, `pcond`, `nkappa`, `pkappa`, `n-powerfact`, `p-powerfact`
- Mechanical: `elastic_tensor`, `bulk_modulus_kv`, `shear_modulus_gv`, `poisson`
- Piezoelectric: `dfpt_piezo_max_dij`, `dfpt_piezo_max_eij`, `dfpt_piezo_max_dielectric`, `dfpt_piezo_max_dielectric_ionic`, `dfpt_piezo_max_dielectric_electronic`
- Magnetic: `magmom_oszicar`, `magmom_outcar`
- Solar: `slme`
- Superconductivity: `Tc_supercon`
- Other: `efg`, `max_efg`, `max_ir_mode`, `min_ir_mode`, `modes`, `avg_elec_mass`, `avg_hole_mass`, `maxdiff_bz`, `maxdiff_mesh`, `func`, `icsd`, `jid`

### Phase 2: JarvisdftAPIHelper (*new file*)
4. Create `Information_Units/Databases/Jarvisdft/JarvisdftAPIHelper.py` modeled on `Information_Units/Databases/Alexandria/AlexandriaAPIHelper.py`
5. Key adaptations from Alexandria:
   - **Base URL**: `https://jarvis.nist.gov/optimade/jarvisdft/v1/`
   - **`_load_property_mapping()`**: Filter for `"jarvisdft"` key instead of `"alexandria"`
   - **`_build_response_fields()`**: Query JARVIS `/info/structures` for supported fields
   - **Pagination** (**CRITICAL DIFFERENCE from Alexandria**):
     - JARVIS uses **page-number based** pagination (`page=1`, `page=2`, …) — NOT offset-based (`page_offset`) like Alexandria
     - Server enforces a **hard cap of 20 entries per page** — the `page_limit` parameter is **ignored** by the server
     - Set `page_limit = 20` in code to match actual server behavior
     - Paginate by incrementing `page` number or following `links.next` URL
     - Stop when `links.next is None` or `len(all_results) >= limit`
   - **Filter building**: Same OPTIMADE filter composition logic — JARVIS uses identical OPTIMADE filter syntax
   - **No-filter behavior**: JARVIS returns **0 results** when no filter is provided (unlike Alexandria) — `fetch_from_api` must always include a filter
   - **`convert_to_structure()` + `save_cif_from_structure()`**: Reuse verbatim — both produce standard OPTIMADE JSON
   - **Rate limiting**: `time.sleep(1.0)` between pages (adjust if needed)

**Pagination comparison:**

| | Alexandria | JARVIS DFT |
|---|---|---|
| Pagination param | `page_offset` (offset-based) | `page` (page-number based) |
| Page size control | Client chooses `page_limit` (up to 100) | **Fixed at 20**, server ignores `page_limit` |
| How to get next page | Increment `page_offset += page_limit` | Follow `links.next` URL or increment `page` number |
| No-filter behavior | Returns results | Returns **0 results** |

All 12 methods mirror Alexandria: `__init__`, `_load_property_mapping`, `_build_response_fields`, `map_properties`, `_validate_filter_properties`, `fetch_from_api`, `is_host_reachable`, `build_filter`, `_build_composition_filter`, `_build_structure_filters`, `convert_to_structure`, `save_cif_from_structure`

### Phase 3: JarvisdftDatabase (*modify existing stub*)
6. Update `Information_Units/Databases/Jarvisdft/JarvisdftDatabase.py`:
   - Import and instantiate `JarvisdftAPIHelper` in `__init__` (*depends on step 4*)
   - Set `self.base_url`, create temp output dir with `tempfile.mkdtemp(prefix="jarvisdft_")`
   - Implement `retrieve(inputs)` following `Information_Units/Databases/Alexandria/AlexandriaDatabase.py`: extract query/limit/filters → `map_properties()` → `fetch_from_api()` → `convert_to_structure()` → `save_cif_from_structure()` → return CIF paths
   - Update `info()` to reflect JARVIS DFT capabilities

### Phase 4: Unit Tests (*new file*)
7. Create `tests/unit/test_jarvisdft_api_behaviour.py` mirroring `tests/unit/test_alexandria_api_behaviour.py` (*depends on step 4*):
   - **`_make_helper(monkeypatch)`** — mock `_build_response_fields` for `JarvisdftAPIHelper`
   - **`test_build_filter_variations`** (parametrized) — OPTIMADE filters with JARVIS property names
   - **`test_fetch_api_host_down`** — empty list when unreachable
   - **`test_fetch_api_with_pagination_and_limit`** — 4 sub-tests: pagination, limit, empty results, unknown filter removal
   - **`test_response_fields_safe_list`** — mock `/info/structures`, verify only JARVIS-supported fields included

### Phase 5: Integration Tests (*new file*)
8. Create `tests/integration/test_jarvisdft_api_sanity.py` mirroring `tests/integration/test_alexandria_api_sanity.py` (*depends on steps 4, 6*):
   - **`rate_limit_delay`** fixture — `time.sleep(4.0)` between tests
   - **`test_jarvisdft_retrieve_structures`** (parametrized) — basic queries, structural filters, JARVIS-specific property filters, combined filters; validates CIF files, elements, formula, property ranges
   - **`test_jarvisdft_retrieve_performance`** (benchmarks) — limits 1, 10, 15
   - Reuses CIF utilities from `tests/integration/conftest.py` (`validate_cif_file`, `extract_formula_from_cif`, etc.)

---

### Relevant Files

| File | Action |
|------|--------|
| `Information_Units/property_mappings.json` | Modify — add `"jarvisdft"` entries |
| `Information_Units/Databases/Jarvisdft/JarvisdftAPIHelper.py` | **Create** — API helper |
| `Information_Units/Databases/Jarvisdft/JarvisdftDatabase.py` | Modify — flesh out `retrieve()` |
| `tests/unit/test_jarvisdft_api_behaviour.py` | **Create** — unit tests |
| `tests/integration/test_jarvisdft_api_sanity.py` | **Create** — integration tests |

**No changes needed to**: `Information_Units/Databases/DatabaseFactory.py` (already registered), `index.html` (checkbox exists), `tests/integration/conftest.py` (CIF utilities reused as-is)

### Verification
1. Query `https://jarvis.nist.gov/optimade/jarvisdft/v1/info/structures` to confirm supported fields and property prefixes
2. `pytest tests/unit/test_jarvisdft_api_behaviour.py -v -m unit` — all pass, no network
3. `pytest tests/integration/test_jarvisdft_api_sanity.py -v -m "integration and network"` — real API, valid CIFs
4. Verify `database_factory["jarvisdft"]` instantiates correctly
5. `pytest tests/ -v` — no regressions

### Decisions
- **Base URL**: `https://jarvis.nist.gov/optimade/jarvisdft/v1/` (confirmed)
- **Pagination**: **`page_limit=20` with page-number pagination** (`page=N`) — server hard cap is 20 entries per page regardless of requested `page_limit` (confirmed via live API testing)
- **Property prefix**: `_jarvis_*` (confirmed via `/info/structures` — e.g. `_jarvis_optb88vdw_bandgap`)
- **Properties**: Discover dynamically from `/info/structures` (confirmed) — 60+ JARVIS-specific attributes available
- **No SCAN variants**: JARVIS uses OptB88vdW functional (and MBJ, HSE for band gaps), not PBEsol/SCAN like Alexandria
- **No-filter behavior**: Must always provide a filter — JARVIS returns 0 results without one
- **Scope excludes**: Frontend changes, docs updates, e2e tests

### Further Considerations
1. ~~**Property prefix**: Need to confirm whether JARVIS uses `_jarvisdft_*` or `_jarvis_*` prefix~~ **RESOLVED** — prefix is `_jarvis_*`
2. **Rate limiting**: Start with 1s delay; adjust if HTTP 429 during integration tests
3. **Queryable properties**: JARVIS marks some properties as `_jarvis_queryable: true` (e.g. `nelements`, `elements`, `chemical_formula_reduced`, `nsites`) and others as `false` — filter building should respect this
