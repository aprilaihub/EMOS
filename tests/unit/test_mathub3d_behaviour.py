"""
Unit tests for MatHub-3d Helper and Database.

Run with: pytest tests/unit/test_mathub3d_behaviour.py -v
"""

import pytest
from tests.fixtures.mock_data import (
    MATHUB3D_FE_ENTRY,
    MATHUB3D_AL2O3_ENTRY,
    MATHUB3D_NI_ENTRY,
)
from Information_Units.Databases.Mathub3d.Mathub3dHelper import Mathub3dHelper


MOCK_DATA = [MATHUB3D_FE_ENTRY, MATHUB3D_AL2O3_ENTRY, MATHUB3D_NI_ENTRY]


def _make_helper():
    """Create a Mathub3dHelper with mocked data (no zip file access)."""
    helper = Mathub3dHelper.__new__(Mathub3dHelper)
    helper.logger = None
    helper._data = MOCK_DATA
    helper._zip_path = '/fake/path.zip'
    helper.property_mapping = helper._load_property_mapping()
    return helper


@pytest.mark.unit
@pytest.mark.parametrize("query,expected_formulas", [
    ("Fe", ["Fe2O3"]),
    ("O", ["Fe2O3", "Al2O3"]),
    ("Ti", []),
    ("", ["Fe2O3", "Al2O3", "Ni3Sn"]),
])
def test_filter_by_formula(query, expected_formulas):
    """Verify formula filtering returns entries containing all queried elements."""
    helper = _make_helper()
    results = helper.filter_by_formula(MOCK_DATA, query)
    assert [e['formula'] for e in results] == expected_formulas


@pytest.mark.unit
@pytest.mark.parametrize("filters,expected_formulas", [
    ({"gap": [1.0, 5.0]}, ["Fe2O3"]),
    ({"spacegroup": 194}, ["Ni3Sn"]),
    ({"is_magnetic": True}, ["Fe2O3", "Ni3Sn"]),
    ({"gap": [0.5, 3.0], "is_magnetic": True}, ["Fe2O3"]),
])
def test_filter_by_properties(filters, expected_formulas):
    """Verify range, exact, boolean, and combined property filters."""
    helper = _make_helper()
    results = helper.filter_by_properties(MOCK_DATA, filters)
    assert [e['formula'] for e in results] == expected_formulas


@pytest.mark.unit
def test_property_mapping():
    """Verify property mapping loads correctly and maps/skips as expected."""
    helper = _make_helper()
    assert helper.property_mapping['band_gap']['name'] == 'gap'

    mapped = helper.map_properties({'band_gap': [1.0, 3.0], 'nelements': 2})
    assert mapped == {'gap': [1.0, 3.0], 'nelements': 2}

    assert helper.map_properties({'nonexistent_prop': 42}) == {}


@pytest.mark.unit
@pytest.mark.parametrize("entry,expected_a", [
    (MATHUB3D_FE_ENTRY, 5.10),   # relaxed (after_a) preferred
    (MATHUB3D_NI_ENTRY, 5.28),   # falls back to initial (before_a)
])
def test_get_lattice(entry, expected_a):
    """Verify lattice extraction prefers relaxed params, falls back to initial."""
    helper = _make_helper()
    assert helper.get_lattice(entry)['a'] == expected_a


@pytest.mark.unit
def test_find_cif_match(tmp_path):
    """Verify CIF cross-referencing: match found and no-candidates case."""
    from pymatgen.core import Structure, Lattice

    helper = _make_helper()

    # Create a fake CIF with matching lattice
    lattice = Lattice.from_parameters(5.10, 5.10, 13.85, 90, 90, 120)
    structure = Structure(lattice, ["Fe", "O"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    cif_str = structure.to(fmt='cif')

    class MockDB:
        def retrieve(self, inputs):
            return {"source": "mock", "queries": inputs, "cif_strings": [cif_str]}

    class EmptyDB:
        def retrieve(self, inputs):
            return {"source": "mock", "queries": inputs, "cif_strings": []}

    # Match found
    result = helper.find_cif_match(MATHUB3D_FE_ENTRY, MockDB(), MockDB(), str(tmp_path))
    assert result == cif_str

    # No candidates → None
    assert helper.find_cif_match(MATHUB3D_FE_ENTRY, EmptyDB(), EmptyDB(), '/tmp') is None


@pytest.mark.unit
def test_database_retrieve(monkeypatch):
    """Verify retrieve returns standardized payload and respects limit."""
    from Information_Units.Databases.Mathub3d.Mathub3dDatabase import Mathub3dDatabase

    db = Mathub3dDatabase.__new__(Mathub3dDatabase)
    db.database_name = 'mathub3d'
    db.logger = None
    db.output_dir = '/tmp'
    helper = _make_helper()
    db.helper = helper
    db.cod_db = db.mp_db = None

    monkeypatch.setattr(helper, 'find_cif_match', lambda *a, **k: 'data_fake\n_cell_length_a 1.0')

    results = db.retrieve({'target_compositions': 'O', 'batch_size': 1})
    assert results["source"] == "mathub3d"
    assert results["queries"] == {'target_compositions': 'O', 'batch_size': 1}
    assert len(results["cif_strings"]) == 1

    monkeypatch.setattr(helper, 'find_cif_match', lambda *a, **k: None)
    empty = db.retrieve({'target_compositions': 'Unobtainium', 'batch_size': 5})
    assert empty["source"] == "mathub3d"
    assert empty["queries"] == {'target_compositions': 'Unobtainium', 'batch_size': 5}
    assert empty["cif_strings"] == []
