"""Unit tests for AFLOW AFLUX API helper."""

import pytest

from Information_Units.Databases.Aflow.AflowAPIHelper import AflowAPIHelper


@pytest.mark.unit
@pytest.mark.parametrize(
    "query,properties,expected",
    [
        ("Fe", {}, "species('Fe')"),
        ("Al2O3", {}, "species('Al','O')"),
        (
            "Fe",
            {"band_gap": [1.0, 3.0]},
            "species('Fe'),Egap(1.0*,*3.0)",
        ),
        (
            "Fe",
            {"space_group": [1, 230], "density": [1.0, 15.0]},
            "species('Fe'),spacegroup_relax(1*,*230),density(1.0*,*15.0)",
        ),
    ],
)
def test_build_filter_variations(query, properties, expected):
    helper = AflowAPIHelper("https://aflow.org/API/aflux/")
    filters = helper.map_properties(properties) if properties else {}
    assert helper.build_filter(query, filters) == expected


@pytest.mark.unit
def test_fetch_api_host_down(monkeypatch):
    helper = AflowAPIHelper("https://aflow.org/API/aflux/")
    monkeypatch.setattr(helper, "is_host_reachable", lambda: False)
    assert helper.fetch_from_api("Fe", 5, {}) == []


@pytest.mark.unit
def test_fetch_api_pagination_and_limit(monkeypatch):
    import requests
    import time

    helper = AflowAPIHelper("https://aflow.org/API/aflux/")
    monkeypatch.setattr(helper, "is_host_reachable", lambda: True)
    monkeypatch.setattr(time, "sleep", lambda _: None)

    class MockResponse:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

        def raise_for_status(self):
            return None

    calls = []

    def mock_get(*args, **kwargs):
        calls.append(kwargs.get("params", ""))
        if "paging(1," in kwargs.get("params", ""):
            return MockResponse(
                {
                    "1 of 8": {"auid": "a1", "aurl": "aflow/a1", "files": ["a1.cif"]},
                    "2 of 8": {"auid": "a2", "aurl": "aflow/a2", "files": ["a2.cif"]},
                    "3 of 8": {"auid": "a3", "aurl": "aflow/a3", "files": ["a3.cif"]},
                }
            )
        if "paging(2," in kwargs.get("params", ""):
            return MockResponse(
                {
                    "4 of 8": {"auid": "a4", "aurl": "aflow/a4", "files": ["a4.cif"]},
                    "5 of 8": {"auid": "a5", "aurl": "aflow/a5", "files": ["a5.cif"]},
                    "6 of 8": {"auid": "a6", "aurl": "aflow/a6", "files": ["a6.cif"]},
                }
            )
        return MockResponse([])

    monkeypatch.setattr(requests, "get", mock_get)

    result = helper.fetch_from_api("Fe", 5, {})
    assert len(result) == 5
    assert any("paging(1," in c for c in calls)
    assert any("paging(2," in c for c in calls)


@pytest.mark.unit
def test_unknown_filters_removed_before_query(monkeypatch):
    import requests
    import time

    helper = AflowAPIHelper("https://aflow.org/API/aflux/")
    monkeypatch.setattr(helper, "is_host_reachable", lambda: True)
    monkeypatch.setattr(time, "sleep", lambda _: None)

    class MockResponse:
        def json(self):
            return {"1 of 1": {"auid": "a1", "aurl": "aflow/a1", "files": ["a1.cif"]}}

        def raise_for_status(self):
            return None

    captured = []

    def mock_get(*args, **kwargs):
        captured.append(kwargs.get("params", ""))
        return MockResponse()

    monkeypatch.setattr(requests, "get", mock_get)

    helper.fetch_from_api("Fe", 1, {"Egap": [1.0, 3.0], "not_a_real_key": [0, 1]})

    assert captured
    assert "Egap(1.0*,*3.0)" in captured[0]
    assert "not_a_real_key" not in captured[0]


@pytest.mark.unit
def test_choose_cif_filename_prefer_primary():
    helper = AflowAPIHelper("https://aflow.org/API/aflux/")
    files = [
        "sample_sconv.cif",
        "sample_corner.cif",
        "sample.cif",
    ]
    assert helper._choose_cif_filename(files) == "sample.cif"


@pytest.mark.unit
def test_convert_to_structure_from_cif_download(monkeypatch):
    import requests

    helper = AflowAPIHelper("https://aflow.org/API/aflux/")

    cif_text = """
data_Si
_cell_length_a 5.431
_cell_length_b 5.431
_cell_length_c 5.431
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_symmetry_space_group_name_H-M 'P 1'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Si1 Si 0.0 0.0 0.0
""".strip()

    class MockResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    monkeypatch.setattr(requests, "get", lambda *a, **k: MockResponse(cif_text))

    entry = {
        "aurl": "aflowlib.duke.edu/AFLOWDATA/LIB3_WEB/Si/TEST",
        "files": ["Si.TEST.cif"],
    }
    structure = helper.convert_to_structure(entry)
    assert structure is not None
    assert structure.composition.reduced_formula == "Si"
