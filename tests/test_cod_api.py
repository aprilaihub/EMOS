import pytest

from Information_Units.Databases.Cod.CodAPIHelper import CodAPIHelper


def _make_helper():
    return CodAPIHelper("https://www.crystallography.net/cod/optimade/v1/")


def test_build_filter_single_element():
    helper = _make_helper()
    assert helper.build_filter("Fe") == 'elements HAS "Fe"'


def test_build_filter_formula_elements_and():
    helper = _make_helper()
    assert helper.build_filter("Al2O3") == '(elements HAS "Al" AND elements HAS "O")'


def test_build_filter_with_structure_filters():
    helper = _make_helper()
    filters = helper.map_properties({"nelements": 2})
    assert helper.build_filter("Fe", filters) == 'elements HAS "Fe" AND nelements = 2'


def test_build_filter_with_range():
    helper = _make_helper()
    filters = helper.map_properties({"nelements": [1, 3]})
    assert helper.build_filter("Fe", filters) == 'elements HAS "Fe" AND nelements >= 1 AND nelements <= 3'


def test_fetch_from_api_host_unreachable(monkeypatch):
    helper = _make_helper()

    monkeypatch.setattr(helper, "is_host_reachable", lambda: False)

    # If host is unreachable, no network calls should be made and result is empty.
    result = helper.fetch_from_api("Fe", 1, {})
    assert result == []
