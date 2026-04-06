"""
Integration tests for Materials Project Database with real API calls.

These tests call the actual Materials Project OPTIMADE API and verify real-world behavior.
Marked with @pytest.mark.network to skip in offline environments.

Run with: pytest tests/integration/test_materialsproject_api_sanity.py -v
Skip network tests: pytest -m "not network"

Note: CIF parsing utilities are imported from conftest.py for code reuse.
"""

import pytest
import time
from Information_Units.Databases.Materialsproject.MaterialsprojectAPIHelper import MaterialsprojectAPIHelper
from .conftest import (
    validate_cif_string,
    extract_formula_from_cif,
    extract_nelements_from_cif,
    extract_nperiodic_dimensions_from_cif
)


@pytest.fixture(autouse=True)
def rate_limit_delay():
    """Add delay between tests to avoid Materials Project API rate limiting."""
    time.sleep(4.0)
    yield


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
    ("Fe", ["Fe"], {"energy_above_hull_r2scan": [0.0, 0.05]}, None, None, {"_mp_stability.r2scan.energy_above_hull": (0.0, 0.05)}),
    ("Al", ["Al"], {"formation_energy_r2scan": [-2.0, -0.5]}, None, None, {"_mp_stability.r2scan.formation_energy_per_atom": (-2.0, -0.5)}),
    # Combined filters
    ("Fe", ["Fe"], {"energy_above_hull_r2scan": [0.0, 0.05], "nelements": [1, 3]}, None, (1, 3), {"_mp_stability.r2scan.energy_above_hull": (0.0, 0.05)}),
])
def test_materialsproject_retrieve_structures(
    query,
    expected_elements,
    filters,
    expected_nperiodic_dimensions,
    expected_nelements_range,
    expected_props,
):
    """Verify Materials Project returns valid CIF files for various queries and property filters."""
    from Information_Units.Databases.Materialsproject.MaterialsprojectDatabase import MaterialsprojectDatabase
    
    db = MaterialsprojectDatabase()
    retrieve_params = {'query': query, 'limit': 3}
    retrieve_params.update(filters)
    payload = db.retrieve(retrieve_params)
    assert isinstance(payload, dict)
    assert payload.get("source") == "materialsproject"
    assert isinstance(payload.get("queries"), dict)
    results = payload.get("cif_strings", [])

    assert isinstance(results, list) and len(results) > 0, \
        f"No structures found for {query} with filters {filters}"
    
    # Validate CIF files exist and contain expected elements
    for i, content in enumerate(results):
        content = validate_cif_string(content)
        
        # Verify all expected elements present in composition
        for elem in expected_elements:
            assert elem in content, f"{elem} not found in CIF result #{i + 1}"
        
        # Verify formula contains expected elements
        formula = extract_formula_from_cif(content)
        if formula:
            for elem in expected_elements:
                assert elem in formula, f"{elem} not in formula: {formula}"

    # For structural property filters, verify constraints are met from CIF data
    if expected_nperiodic_dimensions is not None or expected_nelements_range is not None:
        for content in results:
            content = validate_cif_string(content)
            
            if expected_nelements_range is not None:
                min_nelements, max_nelements = expected_nelements_range
                nelements = extract_nelements_from_cif(content)
                assert nelements >= min_nelements and nelements <= max_nelements, \
                    f"nelements {nelements} not in range [{min_nelements}, {max_nelements}]"
            
            if expected_nperiodic_dimensions is not None:
                nperiodic = extract_nperiodic_dimensions_from_cif(content)
                assert nperiodic == expected_nperiodic_dimensions, \
                    f"nperiodic_dimensions {nperiodic} != {expected_nperiodic_dimensions}"


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
@pytest.mark.parametrize("limit", [1, 10, 15])
def test_materialsproject_retrieve_performance(benchmark, limit):
    """Benchmark retrieval performance for different result limits."""
    from Information_Units.Databases.Materialsproject.MaterialsprojectDatabase import MaterialsprojectDatabase
    
    db = MaterialsprojectDatabase()
    
    # Measure time to retrieve structures
    result = benchmark(db.retrieve, {'query': 'Fe', 'limit': limit})
    
    # Verify results are valid
    assert isinstance(result, dict)
    assert result.get("source") == "materialsproject"
    assert isinstance(result.get("queries"), dict)
    assert isinstance(result.get("cif_strings"), list)
    assert len(result.get("cif_strings", [])) <= limit
