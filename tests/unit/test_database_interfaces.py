"""
Unit tests for Database interfaces and base classes.

Tests verify that all database implementations follow the expected contract.
"""

import pytest


@pytest.mark.unit
def test_base_database_interface_exists():
    """Verify BaseDatabase class exists and has required methods."""
    from Information_Units.Databases.BaseDatabase import BaseDatabase
    
    # Check required methods
    assert hasattr(BaseDatabase, 'info')
    assert hasattr(BaseDatabase, 'retrieve')


@pytest.mark.unit
def test_cod_database_implements_interface():
    """Verify CodDatabase implements BaseDatabase interface."""
    from Information_Units.Databases.Cod.CodDatabase import CodDatabase
    from Information_Units.Databases.BaseDatabase import BaseDatabase
    
    # Check it's a subclass
    assert issubclass(CodDatabase, BaseDatabase)
    
    # Check required methods exist
    cod_db = CodDatabase()
    assert hasattr(cod_db, 'info')
    assert hasattr(cod_db, 'retrieve')
    assert callable(cod_db.info)
    assert callable(cod_db.retrieve)

