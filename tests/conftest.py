"""
Shared pytest configuration and fixtures for EMOS tests.

Fixtures defined here are automatically available to all test files.
"""

import pytest
import tempfile
import shutil
from pathlib import Path


# ============================================================================
# API Helper Fixtures
# ============================================================================

@pytest.fixture
def cod_helper():
    """Provide a CodAPIHelper instance for tests."""
    from Information_Units.Databases.Cod.CodAPIHelper import CodAPIHelper
    return CodAPIHelper("https://www.crystallography.net/cod/optimade/v1/")


# ============================================================================
# Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_output_dir():
    """
    Provide a temporary directory for test outputs.
    Automatically cleaned up after test completes.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="emos_test_"))
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@pytest.fixture
def sample_fe_structure():
    """Sample Fe structure data from OPTIMADE API."""
    return {
        "id": "1000000",
        "type": "structure",
        "attributes": {
            "chemical_formula_reduced": "Fe",
            "lattice_vectors": [[2.87, 0, 0], [0, 2.87, 0], [0, 0, 2.87]],
            "species": [
                {
                    "name": "Fe",
                    "chemical_symbols": ["Fe"],
                    "concentration": [1.0]
                }
            ],
            "species_at_sites": ["Fe", "Fe"],
            "cartesian_site_positions": [[0, 0, 0], [1.435, 1.435, 1.435]],
            "fractional_site_positions": [[0, 0, 0], [0.5, 0.5, 0.5]],
            "nelements": 1,
            "natoms": 2,
            "volume": 23.6,
            "spacegroup_number": 229,
            "spacegroup_symbol": "Im-3m"
        }
    }


@pytest.fixture
def sample_al2o3_structure():
    """Sample Al2O3 structure data from OPTIMADE API."""
    return {
        "id": "2000000",
        "type": "structure",
        "attributes": {
            "chemical_formula_reduced": "Al2O3",
            "lattice_vectors": [[4.76, 0, 0], [0, 4.76, 0], [0, 0, 13.0]],
            "species": [
                {"name": "Al", "chemical_symbols": ["Al"], "concentration": [0.4]},
                {"name": "O", "chemical_symbols": ["O"], "concentration": [0.6]}
            ],
            "species_at_sites": ["Al", "Al", "O", "O", "O"],
            "cartesian_site_positions": [[0, 0, 0], [2.38, 2.38, 6.5], [1.0, 2.0, 3.0], [0.5, 1.5, 9.0], [2.0, 0.5, 12.0]],
            "fractional_site_positions": [[0, 0, 0], [0.5, 0.5, 0.5], [0.2, 0.4, 0.23], [0.1, 0.3, 0.69], [0.42, 0.1, 0.92]],
            "nelements": 2,
            "natoms": 5,
            "volume": 294.9,
            "spacegroup_number": 155,
            "spacegroup_symbol": "R32/m"
        }
    }


# ============================================================================
# Pytest Markers Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (fast, mocked)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (slower, real dependencies)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "network: mark test as requiring network access"
    )
