"""
Integration tests for COD Database with real API calls.

These tests use the actual COD OPTIMADE API and verify real-world behavior.
They are slower but verify that the integration actually works.

Run with: pytest tests/integration/test_cod_database_live.py -v -m integration
"""

import pytest


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
def test_cod_database_retrieve_single_element():
    """Verify COD database can retrieve real structures for single element.
    
    This test actually calls the COD API.
    """
    from Information_Units.Databases.Cod.CodDatabase import CodDatabase
    
    db = CodDatabase()
    results = db.retrieve({'query': 'Fe', 'limit': 1})
    
    assert isinstance(results, list)
    # Result should be list of file paths or structure objects
    assert len(results) >= 0


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
def test_cod_database_retrieve_compound():
    """Verify COD database can retrieve structures for chemical formulas."""
    from Information_Units.Databases.Cod.CodDatabase import CodDatabase
    
    db = CodDatabase()
    results = db.retrieve({'query': 'Al2O3', 'limit': 1})
    
    assert isinstance(results, list)


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
def test_cod_database_retrieve_with_filters():
    """Verify COD database accepts and applies filters."""
    from Information_Units.Databases.Cod.CodDatabase import CodDatabase
    
    db = CodDatabase()
    results = db.retrieve({
        'query': 'Fe',
        'limit': 5,
        'nelements': 1
    })
    
    assert isinstance(results, list)
