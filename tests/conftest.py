"""
Shared pytest configuration for EMOS tests.
"""

import pytest


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
