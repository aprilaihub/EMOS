"""Integration checks for the containerized GBFS-2D service."""

from pathlib import Path

import pytest

from Information_Units.Predictors.Gbfs2d.Gbfs2dClient import Gbfs2dClient


pytestmark = [pytest.mark.integration, pytest.mark.network, pytest.mark.slow]


@pytest.fixture(scope="module")
def client():
    predictor = Gbfs2dClient()
    if not predictor.availability()["available"]:
        pytest.skip("GBFS-2D container is not ready")
    return predictor


def test_gbfs2d_container_advertises_all_properties(client):
    assert set(client.availability()["models"]) == set(client.property_map)


def test_gbfs2d_container_predicts_from_cif(client):
    cif = Path("tests/fixtures/cif_files/mp-2815.cif").read_text()
    result = client.predict([cif])

    assert result["source"] == "gbfs-2d"
    assert result["results"][0]["status"] == "ok"
    assert set(result["results"][0]["properties"]) == {
        "bandgap",
        "is_metal",
        "is_stable",
        "is_vdw_layered",
    }


def test_gbfs2d_container_reports_invalid_cif(client):
    result = client.predict(["not a cif"])
    assert result["results"][0]["status"] == "error"
