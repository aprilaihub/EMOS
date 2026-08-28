"""Integration checks for the containerized GBFS service."""

from pathlib import Path

import pytest

from Information_Units.Predictors.Gbfs.GbfsClient import GbfsClient


pytestmark = [pytest.mark.integration, pytest.mark.network, pytest.mark.slow]


@pytest.fixture(scope="module")
def client():
    predictor = GbfsClient()
    if not predictor.availability()["available"]:
        pytest.skip("GBFS container is not ready")
    return predictor


def test_gbfs_container_advertises_all_properties(client):
    assert set(client.availability()["models"]) == set(client.property_map)


def test_gbfs_container_predicts_from_cif(client):
    cif = Path("tests/fixtures/cif_files/Al2O3.cif").read_text()
    result = client.predict([cif])

    assert result["source"] == "gbfs"
    assert result["results"][0]["status"] == "ok"
    assert set(result["results"][0]["properties"]) == set(client.property_map.values())


def test_gbfs_container_reports_invalid_cif(client):
    result = client.predict(["not a cif"])
    assert result["results"][0]["status"] == "error"
