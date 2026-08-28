"""
Unit tests for JARVIS-DFT OPTIMADE API Helper.

Minimal test suite verifying filter building and API fetching logic.
Uses mocked responses for isolated, fast testing.

Run with: pytest tests/unit/test_jarvisdft_api_behaviour.py -v
"""

import pytest
from Information_Units.Databases.Jarvisdft.JarvisdftAPIHelper import JarvisdftAPIHelper


def _make_helper(monkeypatch):
    """Create a JarvisdftAPIHelper instance for testing without network calls on init."""
    monkeypatch.setattr(
        JarvisdftAPIHelper,
        "_build_response_fields",
        lambda self: "id,elements,nelements,lattice_vectors,species_at_sites,cartesian_site_positions,chemical_formula_reduced,last_modified,nsites,species,nperiodic_dimensions",
    )
    return JarvisdftAPIHelper("https://jarvis.nist.gov/optimade/jarvisdft/v1/")


# ============================================================================
# Filter Building Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("elements,properties,expected", [
    ("Fe", {}, 'elements HAS ALL "Fe"'),
    ("Al2O3", {}, 'elements HAS ALL "Al","O"'),
    ("Fe", {"nelements": 2}, 'elements HAS ALL "Fe" AND nelements = 2'),
    ("Fe", {"nelements": [1, 3]}, 'elements HAS ALL "Fe" AND nelements >= 1 AND nelements <= 3'),
    ("Fe", {"band_gap": [1.0, 3.0]}, 'elements HAS ALL "Fe" AND _jarvis_optb88vdw_bandgap >= 1.0 AND _jarvis_optb88vdw_bandgap <= 3.0'),
    ("Al2O3", {"formation_energy_per_atom": [-1.0, 0.5]}, 'elements HAS ALL "Al","O" AND _jarvis_formation_energy_peratom >= -1.0 AND _jarvis_formation_energy_peratom <= 0.5'),
    ("Si", {"mbj_bandgap": [0.5, 2.5]}, 'elements HAS ALL "Si" AND _jarvis_mbj_bandgap >= 0.5 AND _jarvis_mbj_bandgap <= 2.5'),
    ("Fe", {"band_gap": [1.0, 3.0], "hull_distance": [0.0, 0.1], "nelements": [1, 3]}, 'elements HAS ALL "Fe" AND _jarvis_optb88vdw_bandgap >= 1.0 AND _jarvis_optb88vdw_bandgap <= 3.0 AND _jarvis_ehull >= 0.0 AND _jarvis_ehull <= 0.1 AND nelements >= 1 AND nelements <= 3'),
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
    """Verify API handles page-number pagination, respects limit, and processes empty results."""
    import time
    import requests

    helper = _make_helper(monkeypatch)
    monkeypatch.setattr(helper, "is_host_reachable", lambda: True)
    monkeypatch.setattr(time, "sleep", lambda x: None)

    # Create mock response
    def make_response(data, has_next=True):
        class MockResponse:
            def json(self):
                links = {"next": "http://example.com/next"} if has_next else {"next": None}
                return {"data": data, "links": links}
            def raise_for_status(self):
                pass
        return MockResponse()

    # Test 1: Page-number pagination
    # JARVIS returns max 20 items per page. We need 45 total.
    # Expected: 3 pages (20 + 20 + 5), all results combined.
    call_count = [0]
    def mock_paginated_get(*args, **kwargs):
        call_count[0] += 1
        page = kwargs.get('params', {}).get('page', 1)
        if page <= 2:
            data = [{"id": str(i + (page - 1) * 20), "attributes": {}} for i in range(20)]
            return make_response(data, has_next=True)
        else:
            data = [{"id": str(i + 40), "attributes": {}} for i in range(10)]
            return make_response(data, has_next=False)

    monkeypatch.setattr(requests, "get", mock_paginated_get)
    result = helper.fetch_from_api("Fe", 45, {})
    assert len(result) == 45 and call_count[0] == 3

    # Test 2: Respects Limit
    # User requests only 10 items (less than one page of 20).
    # Expected: Stop after first page, return only 10.
    call_count[0] = 0
    def mock_full_page_get(*args, **kwargs):
        call_count[0] += 1
        data = [{"id": str(i), "attributes": {}} for i in range(20)]
        return make_response(data, has_next=True)

    monkeypatch.setattr(requests, "get", mock_full_page_get)
    result = helper.fetch_from_api("Fe", 10, {})
    assert len(result) == 10

    # Test 3: Empty Results
    # Search returns no data.
    # Expected: Return empty list gracefully.
    monkeypatch.setattr(requests, "get", lambda *a, **k: make_response([], has_next=False))
    result = helper.fetch_from_api("NonExistent", 10, {})
    assert result == []

    # Test 4: Unknown filter properties are removed before API call
    # Expected: API query contains only retrievable JARVIS-DFT filters.
    captured = []

    def mock_filtered_get(*args, **kwargs):
        captured.append(kwargs.get("params", {}).get("filter", ""))
        return make_response([{"id": "1", "attributes": {}}], has_next=False)

    monkeypatch.setattr(requests, "get", mock_filtered_get)
    result = helper.fetch_from_api(
        "Fe",
        1,
        {
            "_jarvis_optb88vdw_bandgap": [1.0, 3.0],
            "unknown_property": [0, 1],
        },
    )
    assert len(result) == 1
    assert captured
    assert "_jarvis_optb88vdw_bandgap >= 1.0 AND _jarvis_optb88vdw_bandgap <= 3.0" in captured[0]
    assert "unknown_property" not in captured[0]


# ============================================================================
# JARVIS-DFT-Specific Tests
# ============================================================================

@pytest.mark.unit
def test_response_fields_safe_list(monkeypatch):
    """
    Verify safe response fields are selected from /info/structures output.

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
        "nsites",
        "species",
        "nperiodic_dimensions",
        "structure_features",
    ]

    def mock_get(url, **kwargs):
        if url.endswith("info/structures"):
            return MockResponse({
                "data": {
                    "properties": {field: {} for field in supported}
                }
            })
        return MockResponse({"data": []})

    monkeypatch.setattr(requests, "get", mock_get)
    helper = JarvisdftAPIHelper("https://jarvis.nist.gov/optimade/jarvisdft/v1/")

    for required in [
        "id",
        "elements",
        "nelements",
        "lattice_vectors",
        "species_at_sites",
        "cartesian_site_positions",
    ]:
        assert required in helper.response_fields

    # Verify Alexandria-specific fields are NOT included
    assert "_alexandria_band_gap" not in helper.response_fields
    assert "_alexandria_formation_energy_per_atom" not in helper.response_fields
