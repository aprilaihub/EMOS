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
from pathlib import Path
from .conftest import (
    validate_cif_file,
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
@pytest.mark.parametrize("query,expected_elements,filters,expected_nperiodic_dimensions,expected_nelements_range", [
    ("Fe", ["Fe"], {}, None, None),
    ("Al2O3", ["Al", "O"], {}, None, None),
    ("Fe2O3", ["Fe", "O"], {}, None, None),
    ("Fe", ["Fe"], {"nelements": [1, 3]}, None, (1, 3)),
    ("Al2O3", ["Al", "O"], {"nelements": [2, 5]}, None, (2, 5)),
    ("Fe", ["Fe"], {"nperiodic_dimensions": 3}, 3, None),
])
def test_alexandria_retrieve_structures(
    query,
    expected_elements,
    filters,
    expected_nperiodic_dimensions,
    expected_nelements_range,
):
    """Verify Alexandria returns valid CIF files for various material queries and property filters."""
    from Information_Units.Databases.Alexandria.AlexandriaDatabase import AlexandriaDatabase
    
    db = AlexandriaDatabase()
    retrieve_params = {'query': query, 'limit': 3}
    retrieve_params.update(filters)
    results = db.retrieve(retrieve_params)
    
    assert isinstance(results, list) and len(results) > 0, \
        f"No structures found for {query} with filters {filters}"
    
    for path in results:
        assert Path(path).exists()
        assert path.endswith('.cif')
        
        content = validate_cif_file(path)
        
        # Verify all expected elements present
        for elem in expected_elements:
            assert elem in content, f"{elem} not found in {path}"
        
        # Verify formula contains expected elements
        formula = extract_formula_from_cif(content)
        if formula:
            for elem in expected_elements:
                assert elem in formula, f"{elem} not in formula: {formula}"

    # For nperiodic_dimensions cases, verify dimensionality in the CIF files
    # This validates filters without making a second API call (avoiding rate-limiting)
    if expected_nperiodic_dimensions is not None or expected_nelements_range is not None:
        for path in results:
            content = validate_cif_file(path)
            
            if expected_nelements_range is not None:
                min_nelements, max_nelements = expected_nelements_range
                nelements = extract_nelements_from_cif(content)
                assert nelements >= min_nelements and nelements <= max_nelements, \
                    f"nelements {nelements} not in range [{min_nelements}, {max_nelements}] for {path}"
            
            if expected_nperiodic_dimensions is not None:
                nperiodic = extract_nperiodic_dimensions_from_cif(content)
                assert nperiodic == expected_nperiodic_dimensions, \
                    f"nperiodic_dimensions {nperiodic} != {expected_nperiodic_dimensions} for {path}"


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
    assert isinstance(result, list)
    assert len(result) <= limit
