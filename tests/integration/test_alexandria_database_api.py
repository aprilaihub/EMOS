"""
Integration tests for Alexandria Database with real API calls.

These tests call the actual Alexandria OPTIMADE API and verify real-world behavior.
Marked with @pytest.mark.network to skip in offline environments.

Run with: pytest tests/integration/test_alexandria_database_api.py -v
Skip network tests: pytest -m "not network"
"""

import pytest
from pathlib import Path


def _validate_cif_file(path):
    """Validate CIF file has correct structure and content."""
    with open(path, 'r') as f:
        content = f.read()
    
    # Check required CIF format fields
    assert 'data_' in content, "Missing CIF data block"
    assert '_cell_length_a' in content, "Missing lattice parameter"
    assert '_atom_site_label' in content or '_atom_site_type_symbol' in content, \
        "Missing atomic site information"
    
    return content


def _extract_formula_from_cif(content):
    """Extract chemical formula from CIF file."""
    for line in content.split('\n'):
        # Try _chemical_formula_sum first
        if line.startswith('_chemical_formula_sum'):
            parts = line.split("'")
            if len(parts) >= 2:
                return parts[1].strip()
        # Try _chemical_formula_structural
        if line.startswith('_chemical_formula_structural'):
            parts = line.split("'")
            if len(parts) >= 2:
                return parts[1].strip()
    return None


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
        
        content = _validate_cif_file(path)
        
        # Verify all expected elements present
        for elem in expected_elements:
            assert elem in content, f"{elem} not found in {path}"
        
        # Verify formula contains expected elements
        formula = _extract_formula_from_cif(content)
        if formula:
            for elem in expected_elements:
                assert elem in formula, f"{elem} not in formula: {formula}"

    # For nperiodic_dimensions cases, verify dimensionality in raw OPTIMADE entries
    # returned for the same query/filters (ensures filter is applied end-to-end).
    if expected_nperiodic_dimensions is not None or expected_nelements_range is not None:
        mapped_filters = db.api_helper.map_properties(filters)
        raw_entries = db.api_helper.fetch_from_api(query, 3, mapped_filters)
        assert len(raw_entries) > 0

        if expected_nelements_range is not None:
            min_nelements, max_nelements = expected_nelements_range
            for entry in raw_entries:
                nelements = entry.get('attributes', {}).get('nelements')
                assert nelements is not None
                assert min_nelements <= nelements <= max_nelements

        if expected_nperiodic_dimensions is not None:
            for entry in raw_entries:
                nperiodic = entry.get('attributes', {}).get('nperiodic_dimensions')
                assert nperiodic == expected_nperiodic_dimensions


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
