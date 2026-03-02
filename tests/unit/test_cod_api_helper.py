"""
Unit tests for COD OPTIMADE API Helper.

These tests verify the CodAPIHelper class functionality using mocked responses.
Tests are fast and isolated from external dependencies.

Run with: pytest tests/unit/test_cod_api_helper.py -v
"""

import pytest
from Information_Units.Databases.Cod.CodAPIHelper import CodAPIHelper


def _make_helper():
    """Create a CodAPIHelper instance for testing."""
    return CodAPIHelper("https://www.crystallography.net/cod/optimade/v1/")


# ============================================================================
# Filter Building Tests
# ============================================================================

@pytest.mark.unit
def test_build_filter_single_element():
    """Verify single element filter is built correctly."""
    helper = _make_helper()
    assert helper.build_filter("Fe") == 'elements HAS "Fe"'


@pytest.mark.unit
def test_build_filter_formula_elements_and():
    """Verify chemical formula is parsed into AND condition."""
    helper = _make_helper()
    assert helper.build_filter("Al2O3") == '(elements HAS "Al" AND elements HAS "O")'


@pytest.mark.unit
def test_build_filter_with_structure_filters():
    """Verify structure properties are combined with element filters."""
    helper = _make_helper()
    filters = helper.map_properties({"nelements": 2})
    assert helper.build_filter("Fe", filters) == 'elements HAS "Fe" AND nelements = 2'


@pytest.mark.unit
def test_build_filter_with_range():
    """Verify range filters generate correct comparison operators."""
    helper = _make_helper()
    filters = helper.map_properties({"nelements": [1, 3]})
    assert helper.build_filter("Fe", filters) == 'elements HAS "Fe" AND nelements >= 1 AND nelements <= 3'


# ============================================================================
# API Fetching Tests (Mocked)
# ============================================================================

@pytest.mark.unit
def test_fetch_from_api_host_unreachable(monkeypatch):
    """Verify no API calls made when host is unreachable."""
    helper = _make_helper()
    monkeypatch.setattr(helper, "is_host_reachable", lambda: False)
    
    result = helper.fetch_from_api("Fe", 1, {})
    
    assert result == []


@pytest.mark.unit
def test_fetch_from_api_success(monkeypatch, sample_fe_structure):
    """Verify successful API fetch returns structure data."""
    helper = _make_helper()
    monkeypatch.setattr(helper, "is_host_reachable", lambda: True)
    
    class MockResponse:
        def json(self):
            return {"data": [sample_fe_structure]}
        
        def raise_for_status(self):
            pass
    
    import requests
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: MockResponse())
    
    result = helper.fetch_from_api("Fe", 1, {})
    
    assert len(result) == 1
    assert result[0]["attributes"]["chemical_formula_reduced"] == "Fe"
    assert result[0]["attributes"]["nelements"] == 1
    assert result[0]["attributes"]["natoms"] == 2


@pytest.mark.unit
def test_fetch_from_api_with_pagination(monkeypatch):
    """Verify pagination correctly fetches multiple pages."""
    helper = _make_helper()
    monkeypatch.setattr(helper, "is_host_reachable", lambda: True)
    
    # Mock time.sleep to speed up test
    import time
    monkeypatch.setattr(time, "sleep", lambda x: None)
    
    class MockResponse:
        def __init__(self, data):
            self.data = data
        
        def json(self):
            return {"data": self.data}
        
        def raise_for_status(self):
            pass
    
    call_count = [0]
    
    def mock_get(*args, **kwargs):
        call_count[0] += 1
        # First call returns 10 results, second returns 5 results
        if call_count[0] == 1:
            return MockResponse([{"id": str(i), "attributes": {}} for i in range(10)])
        else:
            return MockResponse([{"id": str(i + 10), "attributes": {}} for i in range(5)])
    
    import requests
    monkeypatch.setattr(requests, "get", mock_get)
    
    result = helper.fetch_from_api("Fe", 12, {})
    
    assert len(result) == 12
    assert call_count[0] == 2


@pytest.mark.unit
def test_fetch_from_api_empty_response(monkeypatch):
    """Verify empty list returned when no results found."""
    helper = _make_helper()
    monkeypatch.setattr(helper, "is_host_reachable", lambda: True)
    
    class MockResponse:
        def json(self):
            return {"data": []}
        
        def raise_for_status(self):
            pass
    
    import requests
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: MockResponse())
    
    result = helper.fetch_from_api("NonExistentElement", 10, {})
    
    assert result == []


@pytest.mark.unit
def test_fetch_from_api_respects_limit(monkeypatch):
    """Verify API respects the limit parameter."""
    helper = _make_helper()
    monkeypatch.setattr(helper, "is_host_reachable", lambda: True)
    
    class MockResponse:
        def json(self):
            return {"data": [{"id": str(i), "attributes": {}} for i in range(20)]}
        
        def raise_for_status(self):
            pass
    
    import requests
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: MockResponse())
    
    result = helper.fetch_from_api("Fe", 5, {})
    
    assert len(result) == 5
