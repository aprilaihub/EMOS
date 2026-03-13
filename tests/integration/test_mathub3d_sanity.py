"""
Integration tests for MatHub-3d Database with real data and API calls.

These tests load the actual MatHub-3d.json from the zip archive and
cross-reference via COD/Materials Project OPTIMADE APIs.
Marked with @pytest.mark.network to skip in offline environments.

Run with: pytest tests/integration/test_mathub3d_sanity.py -v
Skip network tests: pytest -m "not network"
"""

import pytest
import time
from pathlib import Path
from .conftest import (
    validate_cif_file,
    extract_formula_from_cif,
    extract_nelements_from_cif,
)


@pytest.fixture(autouse=True)
def rate_limit_delay():
    """Add delay between tests to avoid COD/MP API rate limiting."""
    time.sleep(4.0)
    yield


# ============================================================================
# Local Data Loading Tests (no network required)
# ============================================================================

@pytest.mark.integration
def test_mathub3d_loads_data():
    """Verify MatHub-3d.json loads from zip with expected entry count."""
    from Information_Units.Databases.Mathub3d.Mathub3dHelper import Mathub3dHelper

    helper = Mathub3dHelper()
    data = helper.load_data()
    assert isinstance(data, list)
    assert len(data) > 70000, f"Expected 74K+ entries, got {len(data)}"


@pytest.mark.integration
def test_mathub3d_data_has_expected_fields():
    """Verify loaded entries contain expected fields."""
    from Information_Units.Databases.Mathub3d.Mathub3dHelper import Mathub3dHelper

    helper = Mathub3dHelper()
    data = helper.load_data()
    entry = data[0]

    required_fields = ['formula', 'elements', 'nelements', 'spacegroup',
                       'before_a', 'before_b', 'before_c']
    for field in required_fields:
        assert field in entry, f"Missing required field: {field}"


@pytest.mark.integration
@pytest.mark.parametrize("query,min_results", [
    ("Fe", 100),
    ("Al2O3", 1),
    ("Si", 100),
    ("Ni", 100),
])
def test_mathub3d_formula_filtering(query, min_results):
    """Verify formula filtering returns expected number of results from real data."""
    from Information_Units.Databases.Mathub3d.Mathub3dHelper import Mathub3dHelper

    helper = Mathub3dHelper()
    data = helper.load_data()
    results = helper.filter_by_formula(data, query)
    assert len(results) >= min_results, \
        f"Expected at least {min_results} results for '{query}', got {len(results)}"


@pytest.mark.integration
def test_mathub3d_property_filtering_real_data():
    """Verify property filtering works against real dataset."""
    from Information_Units.Databases.Mathub3d.Mathub3dHelper import Mathub3dHelper

    helper = Mathub3dHelper()
    data = helper.load_data()

    # Filter for entries with band gap between 1.0 and 2.0 eV
    results = helper.filter_by_formula(data, 'Fe')
    results = helper.filter_by_properties(results, {"gap": [1.0, 2.0]})
    assert len(results) > 0, "Expected Fe entries with band gap in [1.0, 2.0]"

    for entry in results:
        assert 1.0 <= entry['gap'] <= 2.0


@pytest.mark.integration
def test_mathub3d_property_mapping_loaded():
    """Verify property mapping loads correctly from property_mappings.json."""
    from Information_Units.Databases.Mathub3d.Mathub3dHelper import Mathub3dHelper

    helper = Mathub3dHelper()
    assert len(helper.property_mapping) > 0
    assert 'band_gap' in helper.property_mapping
    assert helper.property_mapping['band_gap']['name'] == 'gap'


# ============================================================================
# Full Retrieval Tests (network required: COD/MP cross-referencing)
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
@pytest.mark.parametrize("query,expected_elements,filters", [
    ("Fe2O3", ["Fe", "O"], {}),
    ("Al2O3", ["Al", "O"], {}),
    ("Si", ["Si"], {"band_gap": [0.5, 2.0]}),
])
def test_mathub3d_retrieve_structures(
    query,
    expected_elements,
    filters,
):
    """Verify MatHub-3d returns valid CIF files for various material queries."""
    from Information_Units.Databases.Mathub3d.Mathub3dDatabase import Mathub3dDatabase

    db = Mathub3dDatabase()
    retrieve_params = {'query': query, 'limit': 2}
    retrieve_params.update(filters)
    results = db.retrieve(retrieve_params)

    assert isinstance(results, list), f"Expected list, got {type(results)}"

    if len(results) > 0:
        for path in results:
            assert Path(path).exists(), f"CIF file not found: {path}"
            assert path.endswith('.cif')

            content = validate_cif_file(path)

            # Verify expected elements present in CIF
            formula = extract_formula_from_cif(content)
            if formula:
                for elem in expected_elements:
                    assert elem in formula or elem in content, \
                        f"{elem} not found in CIF for {query}"


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
@pytest.mark.parametrize("limit", [1, 3])
def test_mathub3d_retrieve_performance(benchmark, limit):
    """Benchmark retrieval performance for different result limits."""
    from Information_Units.Databases.Mathub3d.Mathub3dDatabase import Mathub3dDatabase

    db = Mathub3dDatabase()

    result = benchmark(db.retrieve, {'query': 'Fe2O3', 'limit': limit})

    assert isinstance(result, list)
    assert len(result) <= limit
