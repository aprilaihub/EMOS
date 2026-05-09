"""
Focused integration tests for CHGNet Predictor via Docker container.

Prerequisites:
- CHGNet Docker container must be running:
    docker compose up -d --build chgnet
- Quick check container status:
    docker compose ps chgnet

Run with: pytest tests/integration/test_chgnet_sanity.py -v
"""

import json
import time
from pathlib import Path

import pytest
import requests

from Information_Units.Predictors.Chgnet.ChgnetPredictor import ChgnetPredictor


pytestmark = [pytest.mark.integration, pytest.mark.network, pytest.mark.slow]


@pytest.fixture
def cif_files():
    """Provide paths to CIF test fixtures."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cif_files"
    return {
        "al2o3_path": str(fixtures_dir / "Al2O3.cif"),
        "invalid_path": str(fixtures_dir / "invalid.cif"),
    }


@pytest.fixture(scope="module")
def predictor():
    """Instantiate the CHGNet predictor once for this module."""
    return ChgnetPredictor(predictor_name="test_chgnet_integration")


@pytest.fixture(scope="module", autouse=True)
def wait_for_chgnet_service_ready(predictor):
    """Wait for CHGNet Docker API to become healthy before tests run."""
    timeout_s = 180
    poll_s = 2
    health_timeout_s = 3
    deadline = time.time() + timeout_s
    last_error = None
    consecutive_connection_errors = 0
    max_connection_errors_before_fail = 3

    while time.time() < deadline:
        try:
            response = requests.get(
                f"{predictor.api_url}/health",
                timeout=health_timeout_s,
            )
            consecutive_connection_errors = 0
            if response.status_code == 200:
                ChgnetPredictor._health_cache = {
                    "healthy": True,
                    "checked_at": time.time(),
                }
                return
            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
        except requests.exceptions.ConnectionError as exc:
            last_error = str(exc)
            consecutive_connection_errors += 1
            if consecutive_connection_errors >= max_connection_errors_before_fail:
                pytest.fail(
                    f"CHGNet service is unreachable at {predictor.api_url} "
                    f"after {consecutive_connection_errors} attempts. "
                    "Start it with: docker compose up -d --build chgnet"
                )
        except Exception as exc:
            last_error = str(exc)
            consecutive_connection_errors = 0

        time.sleep(poll_s)

    pytest.fail(
        f"CHGNet service did not become healthy within {timeout_s}s at {predictor.api_url}. "
        f"Last error: {last_error}. "
        "Start it with: docker compose up -d --build chgnet"
    )


def assert_prediction_envelope(result):
    assert isinstance(result, dict)
    assert result.get("status") in {"ok", "error"}
    assert isinstance(result.get("properties"), dict)
    assert isinstance(result.get("warnings"), list)
    assert "error" in result


def assert_ok_prediction(result):
    assert_prediction_envelope(result)
    assert result["status"] == "ok"
    assert result["error"] is None

    props = result["properties"]
    assert isinstance(props.get("num_atoms"), int)
    assert props["num_atoms"] > 0

    assert isinstance(props.get("energy"), (int, float))

    assert isinstance(props.get("forces"), list)
    assert len(props["forces"]) == props["num_atoms"]
    assert len(props["forces"][0]) == 3

    stress = props.get("stress")
    assert isinstance(stress, list)
    # CHGNet may expose stress either as a 6-vector or 3x3 tensor.
    assert len(stress) in {3, 6}


def test_container_is_healthy(predictor):
    assert predictor.is_healthy(), (
        f"CHGNet container not reachable at {predictor.api_url}. "
        "Start it with: docker compose up -d --build chgnet"
    )


def test_predict_valid_input_returns_ok_and_relaxation(cif_files, predictor):
    result = predictor.predict([Path(cif_files["al2o3_path"]).read_text()])
    assert result["source"] == "chgnet"
    assert len(result["results"]) == 1

    first = result["results"][0]
    assert_ok_prediction(first)

    props = first["properties"]
    assert isinstance(props.get("relaxed_energy"), (int, float))
    assert isinstance(props.get("relaxed_structure"), list)
    assert len(props["relaxed_structure"]) == props["num_atoms"]
    assert isinstance(props.get("relaxed_cell"), list)
    assert len(props["relaxed_cell"]) == 3
    assert isinstance(props.get("relaxed_cif"), str)
    assert "data_" in props["relaxed_cif"]


def test_predict_invalid_cif_returns_structured_error(cif_files, predictor):
    result = predictor.predict([Path(cif_files["invalid_path"]).read_text()])
    assert result["source"] == "chgnet"
    assert len(result["results"]) == 1
    first = result["results"][0]
    assert_prediction_envelope(first)
    assert first["status"] == "error"
    assert isinstance(first["error"], str) and first["error"]


def test_predict_output_is_json_serializable(cif_files, predictor):
    result = predictor.predict([Path(cif_files["al2o3_path"]).read_text()])
    serialized = json.dumps(result, default=str)
    deserialized = json.loads(serialized)

    assert isinstance(deserialized, dict)
    assert deserialized["source"] == "chgnet"
    assert deserialized["results"][0]["status"] in {"ok", "error"}