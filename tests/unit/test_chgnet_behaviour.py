"""Unit tests for CHGNet Predictor Docker client."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from Information_Units.Predictors.Chgnet import ChgnetPredictor


@pytest.fixture
def mock_logger():
    logger = Mock()
    logger.log = Mock()
    return logger


@pytest.fixture
def sample_cif_file(tmp_path):
    cif_path = tmp_path / "sample.cif"
    cif_path.write_text("data_test\n_cell_length_a 5.0\n")
    return cif_path


def _mock_response(status_code=200, payload=None):
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = payload or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status_code}")
    else:
        resp.raise_for_status.return_value = None
    return resp


@pytest.mark.unit
def test_init_stores_name_and_logger(mock_logger):
    predictor = ChgnetPredictor(predictor_name="test_chgnet", logger=mock_logger)
    assert predictor.predictor_name == "test_chgnet"
    assert predictor.logger is mock_logger


@pytest.mark.unit
def test_info_returns_metadata_when_container_reachable(mock_logger):
    predictor = ChgnetPredictor(logger=mock_logger)
    payload = {
        "name": "CHGNet",
        "version": "0.3.0",
        "description": "desc",
        "capabilities": ["energy", "forces"],
    }
    with patch("Information_Units.Predictors.Chgnet.ChgnetPredictor.requests.get", return_value=_mock_response(payload=payload)):
        info = predictor.info()

    assert "CHGNet" in info
    assert "energy" in info


@pytest.mark.unit
def test_predict_missing_input_returns_error(mock_logger):
    predictor = ChgnetPredictor(logger=mock_logger)
    result = predictor.predict([])

    assert result["source"] == "chgnet"
    assert result["results"][0]["status"] == "error"


@pytest.mark.unit
def test_predict_success_returns_ok_envelope(mock_logger, sample_cif_file):
    predictor = ChgnetPredictor(logger=mock_logger)
    api_result = {
        "status": "ok",
        "properties": {
            "energy": -10.0,
            "forces": [[0.0, 0.0, 0.0]],
            "stress": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
            "num_atoms": 1,
        },
        "warnings": [],
        "error": None,
    }

    with patch.object(ChgnetPredictor, "is_healthy", return_value=True), patch(
        "Information_Units.Predictors.Chgnet.ChgnetPredictor.requests.post",
        return_value=_mock_response(payload=api_result),
    ) as post_mock:
        result = predictor.predict([sample_cif_file.read_text()])

    assert result["source"] == "chgnet"
    assert result["results"][0]["status"] == "ok"
    sent_payload = post_mock.call_args.kwargs["json"]
    assert sent_payload["compute_energy"] is True
    assert sent_payload["compute_forces"] is True
    assert sent_payload["compute_stress"] is True


@pytest.mark.unit
def test_predict_saves_relaxed_cif_when_output_dir_set(mock_logger, sample_cif_file, tmp_path):
    predictor = ChgnetPredictor(logger=mock_logger)
    api_result = {
        "status": "ok",
        "properties": {
            "num_atoms": 1,
            "relaxed_cif_string": "data_x\n_cell_length_a 1\n",
        },
        "warnings": [],
        "error": None,
    }

    with patch.object(ChgnetPredictor, "is_healthy", return_value=True), patch(
        "Information_Units.Predictors.Chgnet.ChgnetPredictor.requests.post",
        return_value=_mock_response(payload=api_result),
    ):
        result = predictor.predict([sample_cif_file.read_text()], output_dir=str(tmp_path))

    first = result["results"][0]
    assert first["status"] == "ok"
    assert "relaxed_cif" in first["properties"]
    assert Path(first["properties"]["relaxed_cif"]).exists()


@pytest.mark.unit
def test_predict_timeout_returns_error(mock_logger, sample_cif_file):
    predictor = ChgnetPredictor(logger=mock_logger)
    with patch.object(ChgnetPredictor, "is_healthy", return_value=True), patch(
        "Information_Units.Predictors.Chgnet.ChgnetPredictor.requests.post",
        side_effect=requests.Timeout(),
    ):
        result = predictor.predict([sample_cif_file.read_text()])

    assert result["results"][0]["status"] == "error"
    assert "timed out" in result["results"][0]["error"]


@pytest.mark.unit
def test_predict_output_is_json_serializable(mock_logger, sample_cif_file):
    predictor = ChgnetPredictor(logger=mock_logger)
    api_result = {
        "status": "ok",
        "properties": {"num_atoms": 1},
        "warnings": [],
        "error": None,
    }
    with patch.object(ChgnetPredictor, "is_healthy", return_value=True), patch(
        "Information_Units.Predictors.Chgnet.ChgnetPredictor.requests.post",
        return_value=_mock_response(payload=api_result),
    ):
        result = predictor.predict([sample_cif_file.read_text()])

    serialized = json.dumps(result)
    assert isinstance(json.loads(serialized), dict)