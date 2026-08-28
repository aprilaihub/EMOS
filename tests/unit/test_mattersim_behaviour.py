"""Unit tests for MatterSim Predictor Docker client.

Test Coverage:
- Generic predictor interface and response envelope
- HTTP interaction behavior with mocked requests
- Error handling for missing files, unhealthy service, and request failures
- Output CIF persistence behavior

Run: pytest tests/unit/test_mattersim_behaviour.py -v
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from Information_Units.Predictors.Mattersim import MattersimPredictor


# ============================================================================
# Fixtures
# ============================================================================

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


def assert_prediction_envelope(result):
    assert isinstance(result, dict)
    assert result.get("status") in {"ok", "error"}
    assert isinstance(result.get("properties"), dict)
    assert isinstance(result.get("warnings"), list)
    assert "error" in result


# ============================================================================
# Generic Predictor Interface Tests
# ============================================================================

@pytest.mark.unit
def test_init_stores_name_and_logger(mock_logger):
    predictor = MattersimPredictor(predictor_name="test_mattersim", logger=mock_logger)
    assert predictor.predictor_name == "test_mattersim"
    assert predictor.logger is mock_logger


@pytest.mark.unit
def test_info_returns_metadata_when_container_reachable(mock_logger):
    predictor = MattersimPredictor(logger=mock_logger)
    payload = {
        "name": "MatterSim",
        "version": "1.0.0",
        "description": "desc",
        "capabilities": ["energy", "forces"],
    }
    with patch("Information_Units.Predictors.Mattersim.MattersimPredictor.requests.get", return_value=_mock_response(payload=payload)):
        info = predictor.info()

    assert "MatterSim" in info
    assert "energy" in info


@pytest.mark.unit
def test_info_falls_back_when_container_unreachable(mock_logger):
    predictor = MattersimPredictor(logger=mock_logger)
    with patch("Information_Units.Predictors.Mattersim.MattersimPredictor.requests.get", side_effect=requests.ConnectionError("down")):
        info = predictor.info()

    assert "container unreachable" in info


@pytest.mark.unit
def test_predict_missing_cif_param_returns_error(mock_logger):
    predictor = MattersimPredictor(logger=mock_logger)
    result = predictor.predict([])

    assert result["source"] == "mattersim"
    assert isinstance(result["results"], list)
    assert result["results"][0]["status"] == "error"
    assert "Missing required input" in result["results"][0]["error"]


@pytest.mark.unit
def test_predict_empty_input_returns_error(mock_logger):
    predictor = MattersimPredictor(logger=mock_logger)
    result = predictor.predict([])

    assert result["source"] == "mattersim"
    assert isinstance(result["results"], list)
    assert result["results"][0]["status"] == "error"
    assert "Missing required input" in result["results"][0]["error"]


@pytest.mark.unit
def test_predict_unhealthy_container_returns_error(mock_logger, sample_cif_file):
    predictor = MattersimPredictor(logger=mock_logger)
    with patch.object(MattersimPredictor, "is_healthy", return_value=False):
        result = predictor.predict([sample_cif_file.read_text()])

    assert result["source"] == "mattersim"
    assert result["results"][0]["status"] == "error"
    assert "not reachable" in result["results"][0]["error"]


@pytest.mark.unit
def test_predict_success_returns_ok_envelope(mock_logger, sample_cif_file):
    predictor = MattersimPredictor(logger=mock_logger)

    api_result = {
        "status": "ok",
        "properties": {
            "energy": -10.0,
            "forces": [[0.0, 0.0, 0.0]],
            "stress": [0, 0, 0, 0, 0, 0],
            "num_atoms": 1,
            "cell": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "positions": [[0, 0, 0]],
            "atomic_numbers": [13],
        },
        "warnings": [],
        "error": None,
    }

    with patch.object(MattersimPredictor, "is_healthy", return_value=True), patch(
        "Information_Units.Predictors.Mattersim.MattersimPredictor.requests.post",
        return_value=_mock_response(payload=api_result),
    ) as post_mock:
        result = predictor.predict([sample_cif_file.read_text()])

    assert result["source"] == "mattersim"
    assert result["results"][0]["status"] == "ok"
    assert "cell" not in result["results"][0]["properties"]
    assert "positions" not in result["results"][0]["properties"]
    assert "atomic_numbers" not in result["results"][0]["properties"]

    sent_payload = post_mock.call_args.kwargs["json"]
    assert sent_payload["compute_energy"] is True
    assert sent_payload["compute_forces"] is True
    assert sent_payload["compute_stress"] is True
    assert sent_payload["relax"] is True
    assert sent_payload["relax_atoms"] is True
    assert sent_payload["relax_cell"] is True


@pytest.mark.unit
def test_predict_output_is_json_serializable(mock_logger, sample_cif_file):
    predictor = MattersimPredictor(logger=mock_logger)

    api_result = {
        "status": "ok",
        "properties": {"num_atoms": 1, "cell": [], "positions": [], "atomic_numbers": []},
        "warnings": [],
        "error": None,
    }

    with patch.object(MattersimPredictor, "is_healthy", return_value=True), patch(
        "Information_Units.Predictors.Mattersim.MattersimPredictor.requests.post",
        return_value=_mock_response(payload=api_result),
    ):
        result = predictor.predict([sample_cif_file.read_text()])

    serialized = json.dumps(result)
    assert isinstance(json.loads(serialized), dict)


# ============================================================================
# MatterSim-specific HTTP/Error Behavior
# ============================================================================

@pytest.mark.unit
def test_predict_timeout_returns_error(mock_logger, sample_cif_file):
    predictor = MattersimPredictor(logger=mock_logger)

    with patch.object(MattersimPredictor, "is_healthy", return_value=True), patch(
        "Information_Units.Predictors.Mattersim.MattersimPredictor.requests.post",
        side_effect=requests.Timeout(),
    ):
        result = predictor.predict([sample_cif_file.read_text()])

    assert result["source"] == "mattersim"
    assert result["results"][0]["status"] == "error"
    assert "timed out" in result["results"][0]["error"]


@pytest.mark.unit
def test_predict_http_error_returns_error(mock_logger, sample_cif_file):
    predictor = MattersimPredictor(logger=mock_logger)

    with patch.object(MattersimPredictor, "is_healthy", return_value=True), patch(
        "Information_Units.Predictors.Mattersim.MattersimPredictor.requests.post",
        side_effect=requests.RequestException("boom"),
    ):
        result = predictor.predict([sample_cif_file.read_text()])

    assert result["source"] == "mattersim"
    assert result["results"][0]["status"] == "error"
    assert "HTTP error" in result["results"][0]["error"]


@pytest.mark.unit
def test_predict_saves_relaxed_cif_when_output_dir_set(mock_logger, sample_cif_file, tmp_path):
    predictor = MattersimPredictor(logger=mock_logger)

    api_result = {
        "status": "ok",
        "properties": {
            "num_atoms": 1,
            "cell": [],
            "positions": [],
            "atomic_numbers": [],
            "relaxed_cif_string": "data_x\n_cell_length_a 1\n",
        },
        "warnings": [],
        "error": None,
    }

    with patch.object(MattersimPredictor, "is_healthy", return_value=True), patch(
        "Information_Units.Predictors.Mattersim.MattersimPredictor.requests.post",
        return_value=_mock_response(payload=api_result),
    ):
        result = predictor.predict(
            [sample_cif_file.read_text()],
            output_dir=str(tmp_path),
        )

    first = result["results"][0]
    assert first["status"] == "ok"
    assert "relaxed_cif" in first["properties"]
    assert "relaxed_cif_string" not in first["properties"]
    assert Path(first["properties"]["relaxed_cif"]).exists()


@pytest.mark.unit
def test_is_healthy_caches_result(mock_logger):
    predictor = MattersimPredictor(logger=mock_logger)
    MattersimPredictor._health_cache = {"healthy": None, "checked_at": 0.0}

    with patch("Information_Units.Predictors.Mattersim.MattersimPredictor.requests.get", return_value=_mock_response(status_code=200)) as get_mock:
        assert predictor.is_healthy() is True
        assert predictor.is_healthy() is True

    # Second call should use cache and not hit requests.get again.
    assert get_mock.call_count == 1


@pytest.mark.unit
def test_predict_with_list_input_returns_standardized_output(mock_logger):
    predictor = MattersimPredictor(logger=mock_logger)
    api_result = {
        "status": "ok",
        "properties": {"energy": -1.0},
        "warnings": [],
        "error": None,
    }
    with patch.object(MattersimPredictor, "is_healthy", return_value=True), patch(
        "Information_Units.Predictors.Mattersim.MattersimPredictor.requests.post",
        return_value=_mock_response(payload=api_result),
    ):
        result = predictor.predict(["data_test\n_cell_length_a 5.0\n"])

    assert result["source"] == "mattersim"
    assert isinstance(result["results"], list)
    assert result["results"][0]["status"] == "ok"
