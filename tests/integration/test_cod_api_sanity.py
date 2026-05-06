"""
Integration tests for COD Database with real API calls.

These tests call the actual COD OPTIMADE API and verify real-world behavior.
Marked with @pytest.mark.network to skip in offline environments.

Run with: pytest tests/integration/test_cod_database_api.py -v
Skip network tests: pytest -m "not network"

Note: CIF parsing utilities are imported from conftest.py for code reuse.
"""

import pytest
import time
from Information_Units.Databases.Cod.CodAPIHelper import CodAPIHelper
from .conftest import (
    validate_cif_string,
    extract_formula_from_cif,
    extract_nelements_from_cif,
    extract_nperiodic_dimensions_from_cif
)


@pytest.fixture(autouse=True)
def rate_limit_delay():
    """Add delay between tests to avoid COD API rate limiting."""
    time.sleep(4.0)
    yield


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
@pytest.mark.parametrize("query,expected_elements,filters,expected_nperiodic_dimensions,expected_nelements_range", [
    ("Fe", ["Fe"], {}, None, None),
    ("Al2O3", ["Al", "O"], {}, None, None),
    ("Fe2O3", ["Fe", "O"], {}, None, None),
    ("Fe", ["Fe"], {"nelements": [1, 3]}, None, (1, 3)),
    ("Al2O3", ["Al", "O"], {"nelements": [2, 5]}, None, (2, 5)),
    ("Fe", ["Fe"], {"nperiodic_dimensions": 3}, 3, None),
])
def test_cod_retrieve_structures(
    query,
    expected_elements,
    filters,
    expected_nperiodic_dimensions,
    expected_nelements_range,
):
    """Verify COD returns valid CIF files for various material queries and property filters."""
    from Information_Units.Databases.Cod.CodDatabase import CodDatabase
    
    db = CodDatabase()
    retrieve_params = {'target_compositions': query, 'batch_size': 3}
    retrieve_params.update(filters)
    payload = db.retrieve(retrieve_params)
    assert isinstance(payload, dict)
    assert payload.get("source") == "cod"
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

    # For nperiodic_dimensions cases, verify dimensionality in the CIF files
    # This validates filters without making a second API call (avoiding rate-limiting)
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
def test_cod_retrieve_performance(benchmark, limit):
    """Benchmark retrieval performance for different result limits."""
    from Information_Units.Databases.Cod.CodDatabase import CodDatabase
    
    db = CodDatabase()
    
    # Measure time to retrieve structures
    result = benchmark(db.retrieve, {'target_compositions': 'Fe', 'batch_size': limit})
    
    # Verify results are valid
    assert isinstance(result, dict)
    assert result.get("source") == "cod"
    assert isinstance(result.get("queries"), dict)
    assert isinstance(result.get("cif_strings"), list)
    assert len(result.get("cif_strings", [])) <= limit
