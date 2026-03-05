"""
Unit tests for Materials Project OPTIMADE API Helper.

Minimal test suite verifying filter building and API fetching logic.
Uses mocked responses for isolated, fast testing.

Run with: pytest tests/unit/test_materialsproject_api_behaviour.py -v
"""

import pytest
from Information_Units.Databases.Materialsproject.MaterialsprojectAPIHelper import MaterialsprojectAPIHelper


def _make_helper():
    """Create a MaterialsprojectAPIHelper instance for testing."""
    return MaterialsprojectAPIHelper("https://api.materialsproject.org/optimade/v1/")


# ============================================================================
# Filter Building Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("elements,properties,expected", [
    ("Fe", {}, 'elements HAS "Fe"'),
    ("Al2O3", {}, '(elements HAS "Al" AND elements HAS "O")'),
    ("Fe", {"nelements": 2}, 'elements HAS "Fe" AND nelements = 2'),
    ("Fe", {"nelements": [1, 3]}, 'elements HAS "Fe" AND nelements >= 1 AND nelements <= 3'),
    ("Fe", {"energy_above_hull_r2scan": [0.0, 0.05]}, 'elements HAS "Fe" AND _mp_stability.r2scan.energy_above_hull >= 0.0 AND _mp_stability.r2scan.energy_above_hull <= 0.05'),
    ("Al", {"formation_energy_r2scan": [-2.0, -0.5]}, 'elements HAS "Al" AND _mp_stability.r2scan.formation_energy_per_atom >= -2.0 AND _mp_stability.r2scan.formation_energy_per_atom <= -0.5'),
    ("Fe", {"energy_above_hull_r2scan": [0.0, 0.05], "nelements": [1, 3]}, 'elements HAS "Fe" AND _mp_stability.r2scan.energy_above_hull >= 0.0 AND _mp_stability.r2scan.energy_above_hull <= 0.05 AND nelements >= 1 AND nelements <= 3'),
])
def test_build_filter_variations(elements, properties, expected):
    """Verify filter building with various element and property inputs."""
    helper = _make_helper()
    # First map standard property names to MP API field names
    filters = helper.map_properties(properties) if properties else {}
    # Then build the filter string
    result = helper.build_filter(elements, filters)
    assert result == expected


# ============================================================================
# API Fetching Tests
# ============================================================================

@pytest.mark.unit
def test_fetch_api_host_down(monkeypatch):
    """Verify no API calls when host is unreachable."""
    helper = _make_helper()
    monkeypatch.setattr(helper, "is_host_reachable", lambda: False)
    assert helper.fetch_from_api("Fe", 1, {}) == []


@pytest.mark.unit
def test_fetch_api_with_pagination_and_limit(monkeypatch):
    """Verify API handles pagination, respects limit, and processes empty results."""
    import time
    import requests
    
    helper = _make_helper()
    monkeypatch.setattr(helper, "is_host_reachable", lambda: True)
    monkeypatch.setattr(time, "sleep", lambda x: None)
    
    # Create mock response
    def make_response(data):
        class MockResponse:
            def json(self):
                return {"data": data}
            def raise_for_status(self):
                pass
        return MockResponse()
    
    # Test 1: Pagination
    # API returns 10 items per page, but we need 12 total.
    # Expected: Multiple API calls made to fetch across pages, all results combined.
    call_count = [0]
    def mock_paginated_get(*args, **kwargs):
        call_count[0] += 1
        data = [{"id": str(i), "attributes": {}} 
                for i in range(10 if call_count[0] == 1 else 5)]
        return make_response(data)
    
    monkeypatch.setattr(requests, "get", mock_paginated_get)
    result = helper.fetch_from_api("Fe", 12, {})
    assert len(result) == 12 and call_count[0] == 2
    
    # Test 2: Respects Limit
    # User requests only 5 items, even though more are available.
    # Expected: Stop fetching once limit reached, no unnecessary API calls.
    call_count[0] = 0
    result = helper.fetch_from_api("Fe", 5, {})
    assert len(result) == 5
    
    # Test 3: Empty Results
    # Search for non-existent material returns no data.
    # Expected: Return empty list gracefully, not an error.
    monkeypatch.setattr(requests, "get", lambda *a, **k: make_response([]))
    result = helper.fetch_from_api("NonExistent", 10, {})
    assert result == []
