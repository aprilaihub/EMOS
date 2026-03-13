"""
Unit tests for MatHub-3d Helper and Database.

Minimal test suite verifying data loading, filtering, property mapping,
and CIF cross-referencing logic. Uses mocked data for isolated, fast testing.

Run with: pytest tests/unit/test_mathub3d_behaviour.py -v
"""

import pytest
import json
from tests.fixtures.mock_data import (
    MATHUB3D_FE_ENTRY,
    MATHUB3D_AL2O3_ENTRY,
    MATHUB3D_NI_ENTRY,
)
from Information_Units.Databases.Mathub3d.Mathub3dHelper import Mathub3dHelper


MOCK_DATA = [MATHUB3D_FE_ENTRY, MATHUB3D_AL2O3_ENTRY, MATHUB3D_NI_ENTRY]


def _make_helper(monkeypatch):
    """Create a Mathub3dHelper with mocked data loading (no zip file access)."""
    helper = Mathub3dHelper.__new__(Mathub3dHelper)
    helper.logger = None
    helper._data = MOCK_DATA
    helper._zip_path = '/fake/path.zip'
    helper.property_mapping = helper._load_property_mapping()
    return helper


# ============================================================================
# Formula Filtering Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("query,expected_formulas", [
    ("Fe", ["Fe2O3"]),
    ("Al2O3", ["Al2O3"]),
    ("O", ["Fe2O3", "Al2O3"]),
    ("Ni", ["Ni3Sn"]),
    ("Sn", ["Ni3Sn"]),
    ("Ti", []),
    ("", ["Fe2O3", "Al2O3", "Ni3Sn"]),
])
def test_filter_by_formula(monkeypatch, query, expected_formulas):
    """Verify formula filtering returns entries containing all queried elements."""
    helper = _make_helper(monkeypatch)
    results = helper.filter_by_formula(MOCK_DATA, query)
    result_formulas = [e['formula'] for e in results]
    assert result_formulas == expected_formulas


@pytest.mark.unit
@pytest.mark.parametrize("query,expected_elements", [
    ("Fe", ["Fe"]),
    ("Al2O3", ["Al", "O"]),
    ("NaCl", ["Na", "Cl"]),
    ("", []),
])
def test_parse_elements(monkeypatch, query, expected_elements):
    """Verify formula parsing extracts correct element symbols."""
    helper = _make_helper(monkeypatch)
    elements = helper.parse_elements(query)
    assert sorted(elements) == sorted(expected_elements)


# ============================================================================
# Property Filtering Tests
# ============================================================================

@pytest.mark.unit
def test_filter_by_range(monkeypatch):
    """Verify range filter [min, max] works correctly."""
    helper = _make_helper(monkeypatch)
    # band gap between 1.0 and 5.0 → only Fe2O3 (gap=1.8)
    results = helper.filter_by_properties(MOCK_DATA, {"gap": [1.0, 5.0]})
    assert len(results) == 1
    assert results[0]['formula'] == 'Fe2O3'


@pytest.mark.unit
def test_filter_by_exact_value(monkeypatch):
    """Verify exact value filter works correctly."""
    helper = _make_helper(monkeypatch)
    results = helper.filter_by_properties(MOCK_DATA, {"spacegroup": 194})
    assert len(results) == 1
    assert results[0]['formula'] == 'Ni3Sn'


@pytest.mark.unit
def test_filter_by_boolean(monkeypatch):
    """Verify boolean filter works correctly."""
    helper = _make_helper(monkeypatch)
    results = helper.filter_by_properties(MOCK_DATA, {"is_magnetic": True})
    assert len(results) == 2
    formulas = [e['formula'] for e in results]
    assert 'Fe2O3' in formulas
    assert 'Ni3Sn' in formulas


@pytest.mark.unit
def test_filter_excludes_none_values(monkeypatch):
    """Verify entries with None values for filtered property are excluded."""
    helper = _make_helper(monkeypatch)
    # Ni3Sn has energy=None, should be excluded
    results = helper.filter_by_properties(MOCK_DATA, {"energy": [-100, 0]})
    formulas = [e['formula'] for e in results]
    assert 'Ni3Sn' not in formulas


@pytest.mark.unit
def test_filter_combined(monkeypatch):
    """Verify combined filters narrow results correctly."""
    helper = _make_helper(monkeypatch)
    results = helper.filter_by_properties(
        MOCK_DATA,
        {"gap": [0.5, 3.0], "is_magnetic": True}
    )
    assert len(results) == 1
    assert results[0]['formula'] == 'Fe2O3'


# ============================================================================
# Property Mapping Tests
# ============================================================================

@pytest.mark.unit
def test_property_mapping_loaded(monkeypatch):
    """Verify mathub3d property mapping is loaded from property_mappings.json."""
    helper = _make_helper(monkeypatch)
    assert 'band_gap' in helper.property_mapping
    assert helper.property_mapping['band_gap']['name'] == 'gap'
    assert 'energy_per_atom' in helper.property_mapping
    assert 'bulk_modulus' in helper.property_mapping


@pytest.mark.unit
def test_map_properties(monkeypatch):
    """Verify standard property names are mapped to MatHub-3d field names."""
    helper = _make_helper(monkeypatch)
    mapped = helper.map_properties({'band_gap': [1.0, 3.0], 'nelements': 2})
    assert 'gap' in mapped
    assert mapped['gap'] == [1.0, 3.0]
    assert 'nelements' in mapped
    assert mapped['nelements'] == 2


@pytest.mark.unit
def test_map_properties_skips_unknown(monkeypatch):
    """Verify unknown property names are skipped during mapping."""
    helper = _make_helper(monkeypatch)
    mapped = helper.map_properties({'nonexistent_prop': 42})
    assert mapped == {}


# ============================================================================
# Lattice Extraction Tests
# ============================================================================

@pytest.mark.unit
def test_get_lattice_prefers_relaxed(monkeypatch):
    """Verify relaxed lattice params are preferred over initial."""
    helper = _make_helper(monkeypatch)
    lattice = helper.get_lattice(MATHUB3D_FE_ENTRY)
    assert lattice['a'] == 5.10  # after_a, not before_a (5.035)
    assert lattice['b'] == 5.10
    assert lattice['c'] == 13.85


@pytest.mark.unit
def test_get_lattice_falls_back_to_initial(monkeypatch):
    """Verify initial lattice used when relaxed is None."""
    helper = _make_helper(monkeypatch)
    lattice = helper.get_lattice(MATHUB3D_NI_ENTRY)
    assert lattice['a'] == 5.28  # before_a (after_a is None)
    assert lattice['b'] == 5.28
    assert lattice['c'] == 4.24


# ============================================================================
# Lazy Loading Tests
# ============================================================================

@pytest.mark.unit
def test_load_data_caches(monkeypatch, tmp_path):
    """Verify data is loaded once and cached on subsequent calls."""
    import zipfile

    # Create a minimal zip with JSON
    zip_path = tmp_path / "MatHub-3d.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr('MatHub-3d.json', json.dumps(MOCK_DATA))

    helper = Mathub3dHelper.__new__(Mathub3dHelper)
    helper.logger = None
    helper._data = None
    helper._zip_path = str(zip_path)
    helper.property_mapping = {}

    data1 = helper.load_data()
    assert len(data1) == 3
    data2 = helper.load_data()
    assert data1 is data2  # Same object reference = cached


# ============================================================================
# CIF Cross-Reference Tests
# ============================================================================

@pytest.mark.unit
def test_find_cif_match_returns_path(monkeypatch, tmp_path):
    """Verify CIF cross-referencing returns a path when a match exists."""
    from pymatgen.core import Structure, Lattice

    helper = _make_helper(monkeypatch)

    # Create a fake CIF file with matching lattice
    lattice = Lattice.from_parameters(5.10, 5.10, 13.85, 90, 90, 120)
    structure = Structure(lattice, ["Fe", "O"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    cif_path = str(tmp_path / "Fe2O3_0.cif")
    structure.to(filename=cif_path, fmt='cif')

    # Mock database retrieve to return our fake CIF
    class MockDB:
        def retrieve(self, inputs):
            return [cif_path]

    result = helper.find_cif_match(
        MATHUB3D_FE_ENTRY, MockDB(), MockDB(), str(tmp_path)
    )
    assert result == cif_path


@pytest.mark.unit
def test_find_cif_match_no_candidates(monkeypatch):
    """Verify None returned when no CIF candidates exist."""
    helper = _make_helper(monkeypatch)

    class EmptyDB:
        def retrieve(self, inputs):
            return []

    result = helper.find_cif_match(
        MATHUB3D_FE_ENTRY, EmptyDB(), EmptyDB(), '/tmp'
    )
    assert result is None


@pytest.mark.unit
def test_find_cif_match_fallback_to_mp(monkeypatch, tmp_path):
    """Verify MP is preferred as fallback when no lattice match within tolerance."""
    from pymatgen.core import Structure, Lattice

    helper = _make_helper(monkeypatch)

    # Create CIF with very different lattice (won't match tolerance)
    lattice = Lattice.from_parameters(10.0, 10.0, 10.0, 90, 90, 90)
    structure = Structure(lattice, ["Fe", "O"], [[0, 0, 0], [0.5, 0.5, 0.5]])

    mp_path = str(tmp_path / "mp_Fe2O3.cif")
    cod_path = str(tmp_path / "cod_Fe2O3.cif")
    structure.to(filename=mp_path, fmt='cif')
    structure.to(filename=cod_path, fmt='cif')

    class MockMP:
        def retrieve(self, inputs):
            return [mp_path]

    class MockCOD:
        def retrieve(self, inputs):
            return [cod_path]

    result = helper.find_cif_match(
        MATHUB3D_FE_ENTRY, MockCOD(), MockMP(), str(tmp_path)
    )
    assert result == mp_path  # MP preferred as fallback


# ============================================================================
# Database-Level Tests
# ============================================================================

@pytest.mark.unit
def test_database_retrieve_returns_list(monkeypatch):
    """Verify Mathub3dDatabase.retrieve returns list of CIF paths."""
    from Information_Units.Databases.Mathub3d.Mathub3dDatabase import Mathub3dDatabase

    db = Mathub3dDatabase.__new__(Mathub3dDatabase)
    db.database_name = 'mathub3d'
    db.logger = None
    db.output_dir = '/tmp'

    # Mock helper
    helper = _make_helper(monkeypatch)
    db.helper = helper

    # Mock cross-reference databases
    class MockDB:
        def retrieve(self, inputs):
            return ['/tmp/fake.cif']

    db.cod_db = MockDB()
    db.mp_db = MockDB()

    # Mock find_cif_match to avoid actual file operations
    monkeypatch.setattr(helper, 'find_cif_match', lambda *a, **k: '/tmp/fake.cif')

    results = db.retrieve({'query': 'Fe', 'limit': 5})
    assert isinstance(results, list)
    assert all(isinstance(p, str) for p in results)


@pytest.mark.unit
def test_database_retrieve_respects_limit(monkeypatch):
    """Verify retrieve stops once limit CIF matches are collected."""
    from Information_Units.Databases.Mathub3d.Mathub3dDatabase import Mathub3dDatabase

    db = Mathub3dDatabase.__new__(Mathub3dDatabase)
    db.database_name = 'mathub3d'
    db.logger = None
    db.output_dir = '/tmp'

    helper = _make_helper(monkeypatch)
    db.helper = helper
    db.cod_db = None
    db.mp_db = None

    monkeypatch.setattr(helper, 'find_cif_match', lambda *a, **k: '/tmp/fake.cif')

    results = db.retrieve({'query': 'O', 'limit': 1})
    assert len(results) == 1


@pytest.mark.unit
def test_database_retrieve_empty_query(monkeypatch):
    """Verify empty query with no matches returns empty list."""
    from Information_Units.Databases.Mathub3d.Mathub3dDatabase import Mathub3dDatabase

    db = Mathub3dDatabase.__new__(Mathub3dDatabase)
    db.database_name = 'mathub3d'
    db.logger = None
    db.output_dir = '/tmp'

    helper = _make_helper(monkeypatch)
    db.helper = helper
    db.cod_db = None
    db.mp_db = None

    monkeypatch.setattr(helper, 'find_cif_match', lambda *a, **k: None)

    results = db.retrieve({'query': 'Unobtainium', 'limit': 5})
    assert results == []


@pytest.mark.unit
def test_database_info():
    """Verify info() returns non-empty description string."""
    from Information_Units.Databases.Mathub3d.Mathub3dDatabase import Mathub3dDatabase

    db = Mathub3dDatabase.__new__(Mathub3dDatabase)
    db.database_name = 'mathub3d'
    db.logger = None
    info = db.info()
    assert isinstance(info, str)
    assert len(info) > 0
    assert 'MatHub-3d' in info
