"""
Unit tests for Alexandria OPTIMADE API Helper.

Minimal test suite verifying filter building and API fetching logic.
Uses mocked responses for isolated, fast testing.

Run with: pytest tests/unit/test_alexandria_api_helper.py -v
"""

import pytest
from Information_Units.Databases.Alexandria.AlexandriaAPIHelper import AlexandriaAPIHelper


def _make_helper(monkeypatch):
    """Create an AlexandriaAPIHelper instance for testing without network calls on init."""
    monkeypatch.setattr(
        AlexandriaAPIHelper,
        "_build_response_fields",
        lambda self: "id,elements,nelements,lattice_vectors,species_at_sites,cartesian_site_positions,chemical_formula_reduced,last_modified,type,nperiodic_dimensions,fractional_site_positions,species",
    )
    return AlexandriaAPIHelper("https://alexandria.icams.rub.de/pbesol/v1/")


# ============================================================================
# Filter Building Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("elements,properties,expected", [
    ("Fe", {}, 'elements HAS "Fe"'),
    ("Al2O3", {}, '(elements HAS "Al" AND elements HAS "O")'),
    ("Fe", {"nelements": 2}, 'elements HAS "Fe" AND nelements = 2'),
    ("Fe", {"nelements": [1, 3]}, 'elements HAS "Fe" AND nelements >= 1 AND nelements <= 3'),
    ("Fe", {"band_gap": [1.0, 3.0]}, 'elements HAS "Fe" AND _alexandria_band_gap >= 1.0 AND _alexandria_band_gap <= 3.0'),
    ("Al2O3", {"formation_energy_per_atom": [-1.0, 0.5]}, '(elements HAS "Al" AND elements HAS "O") AND _alexandria_formation_energy_per_atom >= -1.0 AND _alexandria_formation_energy_per_atom <= 0.5'),
    ("O", {"band_gap_scan": [0.5, 2.5]}, 'elements HAS "O" AND _alexandria_scan_band_gap >= 0.5 AND _alexandria_scan_band_gap <= 2.5'),
    ("Fe", {"band_gap": [1.0, 3.0], "hull_distance": [0.0, 0.1], "nelements": [1, 3]}, 'elements HAS "Fe" AND _alexandria_band_gap >= 1.0 AND _alexandria_band_gap <= 3.0 AND _alexandria_hull_distance >= 0.0 AND _alexandria_hull_distance <= 0.1 AND nelements >= 1 AND nelements <= 3'),
])
def test_build_filter_variations(monkeypatch, elements, properties, expected):
    """Verify filter building with various element and property inputs."""
    helper = _make_helper(monkeypatch)
    filters = helper.map_properties(properties) if properties else {}
    result = helper.build_filter(elements, filters)
    assert result == expected


# ============================================================================
# API Fetching Tests
# ============================================================================

@pytest.mark.unit
def test_fetch_api_host_down(monkeypatch):
    """Verify no API calls when host is unreachable."""
    helper = _make_helper(monkeypatch)
    monkeypatch.setattr(helper, "is_host_reachable", lambda: False)
    assert helper.fetch_from_api("Fe", 1, {}) == []


@pytest.mark.unit
def test_fetch_api_with_pagination_and_limit(monkeypatch):
    """Verify API handles pagination, respects limit, and processes empty results."""
    import time
    import requests
    
    helper = _make_helper(monkeypatch)
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
    # API returns 100 items per page (Alexandria's page_limit), but we need 120 total.
    # Expected: Multiple API calls made to fetch across pages, all results combined.
    call_count = [0]
    def mock_paginated_get(*args, **kwargs):
        call_count[0] += 1
        data = [{"id": str(i), "attributes": {}} 
                for i in range(100 if call_count[0] == 1 else 30)]
        return make_response(data)
    
    monkeypatch.setattr(requests, "get", mock_paginated_get)
    result = helper.fetch_from_api("Fe", 120, {})
    assert len(result) == 120 and call_count[0] == 2
    
    # Test 2: Respects Limit
    # User requests only 50 items, even though more are available.
    # Expected: Stop fetching once limit reached, no unnecessary API calls.
    call_count[0] = 0
    result = helper.fetch_from_api("Fe", 50, {})
    assert len(result) == 50
    
    # Test 3: Empty Results
    # Search for non-existent material returns no data.
    # Expected: Return empty list gracefully, not an error.
    monkeypatch.setattr(requests, "get", lambda *a, **k: make_response([]))
    result = helper.fetch_from_api("NonExistent", 10, {})
    assert result == []

    # Test 4: Unknown filter properties are removed before API call
    # Expected: API query contains only retrievable Alexandria filters.
    captured = []

    def mock_filtered_get(*args, **kwargs):
        captured.append(kwargs.get("params", {}).get("filter", ""))
        return make_response([{"id": "1", "attributes": {}}])

    monkeypatch.setattr(requests, "get", mock_filtered_get)
    result = helper.fetch_from_api(
        "Fe",
        1,
        {
            "_alexandria_band_gap": [1.0, 3.0],
            "unknown_property": [0, 1],
        },
    )
    assert len(result) == 1
    assert captured
    assert "_alexandria_band_gap >= 1.0 AND _alexandria_band_gap <= 3.0" in captured[0]
    assert "unknown_property" not in captured[0]


# ============================================================================
# Alexandria-Specific Tests
# ============================================================================

@pytest.mark.unit
def test_response_fields_safe_list(monkeypatch):
    """
    Verify safe response fields are selected from /info/structures output.
    
    Alexandria has strict field validation (HTTP 400 on unknown fields).
    This test ensures only supported fields are requested.
    """
    import requests

    class MockResponse:
        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

        def raise_for_status(self):
            return None

    supported = [
        "id",
        "elements",
        "nelements",
        "lattice_vectors",
        "species_at_sites",
        "cartesian_site_positions",
        "chemical_formula_reduced",
        "last_modified",
        "type",
        "nperiodic_dimensions",
        "fractional_site_positions",
        "species",
    ]

    def mock_get(url, **kwargs):
        if url.endswith("info/structures"):
            return MockResponse({
                "data": {
                    "output_fields_by_format": {
                        "optimade_json": supported
                    }
                }
            })
        return MockResponse({"data": []})

    monkeypatch.setattr(requests, "get", mock_get)
    helper = AlexandriaAPIHelper("https://alexandria.icams.rub.de/pbesol/v1/")

    for required in [
        "id",
        "elements",
        "nelements",
        "lattice_vectors",
        "species_at_sites",
        "cartesian_site_positions",
    ]:
        assert required in helper.response_fields

    # Verify COD-specific fields are NOT included
    assert "spacegroup_number" not in helper.response_fields
    assert "_cod_cell_formula_units_z" not in helper.response_fields

