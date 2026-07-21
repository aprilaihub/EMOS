import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from Information_Units.Predictors.Gbfs.GbfsClient import GbfsClient, GbfsPredictor
from Information_Units.Predictors.Gbfs2d.Gbfs2dClient import Gbfs2dClient, Gbfs2dPredictor
from Information_Units.Predictors.PredictorFactory import predictor_factory
from Information_Units.service_urls import normalise_service_url


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        ("emos-model", "http://emos-model:8000"),
        ("emos-model:9000", "http://emos-model:9000"),
        ("http://localhost:8100/", "http://localhost:8100"),
        ("https://models.example/api/", "https://models.example/api"),
        ("", "http://localhost:8100"),
    ],
)
def test_normalise_service_url(raw_url, expected):
    assert normalise_service_url(raw_url, "http://localhost:8100") == expected


def test_predictor_factory_uses_http_only_gbfs_clients():
    assert predictor_factory["gbfs"] is GbfsPredictor
    assert predictor_factory["gbfs_2d"] is Gbfs2dPredictor
    assert GbfsClient is GbfsPredictor
    assert Gbfs2dClient is Gbfs2dPredictor
    assert "Information_Units.Predictors.Gbfs.GbfsPredictor" not in sys.modules
    assert "Information_Units.Predictors.Gbfs2d.Gbfs2dPredictor" not in sys.modules


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_gbfs_client_translates_cif_to_container_batch_request(monkeypatch):
    monkeypatch.delenv("GBFS_PRED_API_URL", raising=False)
    cif = Path("tests/fixtures/cif_files/Al2O3.cif").read_text()
    payload = {
        "predictions": {
            "bandgap": {"prediction": 1.2},
            "dielectric": {"prediction": 3.4},
            "e_form": {"prediction": -1.0},
            "is_metal": {"prediction": 0.1},
            "mob_n": {"prediction": 20.0},
            "mob_p": {"prediction": 10.0},
        }
    }
    with patch(
        "Information_Units.Predictors.ContainerPredictorClient.requests.post",
        return_value=_response(payload),
    ) as post:
        result = GbfsClient().predict([cif])

    assert post.call_args.args[0] == "http://localhost:8200/batch-predict"
    assert post.call_args.kwargs["json"]["structure"]["@class"] == "Structure"
    assert result["results"][0]["status"] == "ok"
    assert result["results"][0]["properties"]["bandgap"] == 1.2


def test_gbfs2d_client_maps_api_properties(monkeypatch):
    monkeypatch.delenv("GBFS2D_API_URL", raising=False)
    cif = Path("tests/fixtures/cif_files/Al2O3.cif").read_text()
    payload = {
        "is_vdw_layered": True,
        "predictions": {
            "bandgap": {"prediction": 2.1},
            "is_metal": {"prediction": 0.0},
            "is_stable": {"prediction": 0.9},
        },
    }
    with patch(
        "Information_Units.Predictors.ContainerPredictorClient.requests.post",
        return_value=_response(payload),
    ):
        result = Gbfs2dClient().predict([cif])

    assert result["results"][0]["properties"] == {
        "bandgap": 2.1,
        "is_metal": 0.0,
        "is_stable": 0.9,
        "is_vdw_layered": True,
    }


def test_container_availability_requires_ready_and_info():
    responses = [
        _response({"status": "ready"}),
        _response({"version": "1.0", "supported_properties": ["bandgap"]}),
    ]
    with patch(
        "Information_Units.Predictors.ContainerPredictorClient.requests.get",
        side_effect=responses,
    ) as get:
        availability = GbfsClient().availability()

    assert availability == {
        "available": True,
        "service": "gbfs",
        "models": ["bandgap"],
        "version": "1.0",
    }
    assert get.call_args_list[0].args[0].endswith("/ready")
