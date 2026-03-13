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
# Local Data Tests (no network required)
# ============================================================================

@pytest.mark.integration
def test_mathub3d_loads_data():
    """Verify MatHub-3d.json loads from zip with expected entry count and fields."""
    from Information_Units.Databases.Mathub3d.Mathub3dHelper import Mathub3dHelper

    helper = Mathub3dHelper()
    data = helper.load_data()
    assert isinstance(data, list)
    assert len(data) > 70000, f"Expected 74K+ entries, got {len(data)}"

    required_fields = ['formula', 'elements', 'nelements', 'spacegroup',
                       'before_a', 'before_b', 'before_c']
    for field in required_fields:
        assert field in data[0], f"Missing required field: {field}"


@pytest.mark.integration
def test_mathub3d_formula_and_property_filtering():
    """Verify formula and property filtering on real data."""
    from Information_Units.Databases.Mathub3d.Mathub3dHelper import Mathub3dHelper

    helper = Mathub3dHelper()
    data = helper.load_data()

    # Formula filtering
    fe_results = helper.filter_by_formula(data, 'Fe')
    assert len(fe_results) >= 100

    # Property filtering on top of formula results
    filtered = helper.filter_by_properties(fe_results, {"gap": [1.0, 2.0]})
    assert len(filtered) > 0
    for entry in filtered:
        assert 1.0 <= entry['gap'] <= 2.0


# ============================================================================
# Full Retrieval Tests (network required: COD/MP cross-referencing)
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
@pytest.mark.parametrize("query,expected_elements,filters", [
    # Basic queries without property filters
    ("Fe2O3", ["Fe", "O"], {}),
    ("Al2O3", ["Al", "O"], {}),
    # Structural property filters
    ("Fe", ["Fe"], {"nelements": [1, 3]}),
    ("Si", ["Si"], {"density": [1.0, 5.0]}),
    # Electronic property filters
    ("Si", ["Si"], {"band_gap": [0.5, 2.0]}),
    # Combined filters
    ("Fe", ["Fe"], {"band_gap": [1.0, 3.0], "nelements": [2, 4]}),
])
def test_mathub3d_retrieve_structures(query, expected_elements, filters):
    """Verify MatHub-3d returns valid CIF files for various material queries."""
    from Information_Units.Databases.Mathub3d.Mathub3dDatabase import Mathub3dDatabase

    db = Mathub3dDatabase()
    retrieve_params = {'query': query, 'limit': 2}
    retrieve_params.update(filters)
    results = db.retrieve(retrieve_params)

    assert isinstance(results, list) and len(results) > 0, \
        f"No structures found for {query} with filters {filters}"

    for path in results:
        assert Path(path).exists(), f"CIF file not found: {path}"
        assert path.endswith('.cif')

        content = validate_cif_file(path)

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
