"""
Integration tests for Alexandria Database with real API calls.

These tests call the actual Alexandria OPTIMADE API and verify real-world behavior.
Marked with @pytest.mark.network to skip in offline environments.

Run with: pytest tests/integration/test_alexandria_database_api.py -v
Skip network tests: pytest -m "not network"

Note: CIF parsing utilities are imported from conftest.py for code reuse.
"""

import pytest
import time
from .conftest import (
    validate_cif_string,
    extract_formula_from_cif,
    extract_nelements_from_cif,
    extract_nperiodic_dimensions_from_cif
)


@pytest.fixture(autouse=True)
def rate_limit_delay():
    """Add delay between tests to avoid Alexandria API rate limiting."""
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
    # Electronic property filters (PBEsol)
    ("Fe", ["Fe"], {"band_gap": [1.0, 3.0]}, None, None, {"_alexandria_band_gap": (1.0, 3.0)}),
    ("Al", ["Al"], {"formation_energy_per_atom": [-1.5, -0.5]}, None, None, {"_alexandria_formation_energy_per_atom": (-1.5, -0.5)}),
    # Thermodynamic stability filter
    ("Fe", ["Fe"], {"hull_distance": [0.0, 0.05]}, None, None, {"_alexandria_hull_distance": (0.0, 0.05)}),
    # Magnetic property filter
    ("Fe", ["Fe"], {"magnetization": [0.1, 10.0]}, None, None, {"_alexandria_magnetization": (0.1, 10.0)}),
    # SCAN variant filter
    ("O", ["O"], {"band_gap_scan": [0.5, 2.5]}, None, None, {"_alexandria_scan_band_gap": (0.5, 2.5)}),
    # Combined filters (PBEsol + SCAN)
    ("Fe", ["Fe"], {"band_gap": [1.0, 3.0], "formation_energy_per_atom": [-1.0, 0.0], "hull_distance": [0.0, 0.1]}, None, None, 
     {"_alexandria_band_gap": (1.0, 3.0), "_alexandria_formation_energy_per_atom": (-1.0, 0.0), "_alexandria_hull_distance": (0.0, 0.1)}),
])
def test_alexandria_retrieve_structures(
    query,
    expected_elements,
    filters,
    expected_nperiodic_dimensions,
    expected_nelements_range,
    expected_props,
):
    """Verify Alexandria returns valid CIF files with various queries and property filters.
    
    Tests both structural properties (encoded in CIF) and DFT properties (from API entries).
    """
    from Information_Units.Databases.Alexandria.AlexandriaDatabase import AlexandriaDatabase
    from Information_Units.Databases.Alexandria.AlexandriaAPIHelper import AlexandriaAPIHelper
    
    # Validate properties at API level before CIF retrieval
    if expected_props:
        helper = AlexandriaAPIHelper("https://alexandria.icams.rub.de/pbesol/v1/")
        mapped_filters = helper.map_properties(filters)
        api_results = helper.fetch_from_api(query, 3, mapped_filters)
        
        assert len(api_results) > 0, f"No API results for {query} with properties {filters}"
        
        # Validate filter was applied correctly at API level
        for entry in api_results:
            attrs = entry.get('attributes', {})
            for prop_name, (min_val, max_val) in expected_props.items():
                value = attrs.get(prop_name)
                if value is not None:
                    assert min_val <= value <= max_val, \
                        f"Property {prop_name}={value} outside range [{min_val}, {max_val}]"
    
    # Retrieve CIF files through database
    db = AlexandriaDatabase()
    retrieve_params = {'query': query, 'limit': 3}
    retrieve_params.update(filters)
    payload = db.retrieve(retrieve_params)
    assert isinstance(payload, dict)
    assert payload.get("source") == "alexandria"
    assert isinstance(payload.get("queries"), dict)
    results = payload.get("cif_strings", [])

    assert isinstance(results, list) and len(results) > 0, \
        f"No structures found for {query} with filters {filters}"
    
    for i, content in enumerate(results):
        content = validate_cif_string(content)
        
        # Verify all expected elements present
        for elem in expected_elements:
            assert elem in content, f"{elem} not found in CIF result #{i + 1}"
        
        # Verify formula contains expected elements
        formula = extract_formula_from_cif(content)
        if formula:
            for elem in expected_elements:
                assert elem in formula, f"{elem} not in formula: {formula}"

    # Validate structural properties in CIF files
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
def test_alexandria_retrieve_performance(benchmark, limit):
    """Benchmark retrieval performance for different result limits."""
    from Information_Units.Databases.Alexandria.AlexandriaDatabase import AlexandriaDatabase
    
    db = AlexandriaDatabase()
    
    # Measure time to retrieve structures
    result = benchmark(db.retrieve, {'query': 'Fe', 'limit': limit})
    
    # Verify results are valid
    assert isinstance(result, dict)
    assert result.get("source") == "alexandria"
    assert isinstance(result.get("queries"), dict)
    assert isinstance(result.get("cif_strings"), list)
    assert len(result.get("cif_strings", [])) <= limit
