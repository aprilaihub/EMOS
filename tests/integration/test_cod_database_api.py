"""
Integration tests for COD Database with real API calls.

These tests call the actual COD OPTIMADE API and verify real-world behavior.
Marked with @pytest.mark.network to skip in offline environments.

Run with: pytest tests/integration/test_cod_database_api.py -v
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
@pytest.mark.parametrize("query,expected_elements", [
    ("Fe", ["Fe"]),
    ("Al2O3", ["Al", "O"]),
    ("Fe2O3", ["Fe", "O"]),
])
def test_cod_retrieve_structures(query, expected_elements):
    """Verify COD returns valid CIF files for various material queries."""
    from Information_Units.Databases.Cod.CodDatabase import CodDatabase
    
    db = CodDatabase()
    results = db.retrieve({'query': query, 'limit': 3})
    
    assert isinstance(results, list) and len(results) > 0, \
        f"No structures found for {query}"
    
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



@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
@pytest.mark.parametrize("limit", [1, 10, 15])
def test_cod_retrieve_performance(benchmark, limit):
    """Benchmark retrieval performance for different result limits."""
    from Information_Units.Databases.Cod.CodDatabase import CodDatabase
    
    db = CodDatabase()
    
    # Measure time to retrieve structures
    result = benchmark(db.retrieve, {'query': 'Fe', 'limit': limit})
    
    # Verify results are valid
    assert isinstance(result, list)
    assert len(result) <= limit
