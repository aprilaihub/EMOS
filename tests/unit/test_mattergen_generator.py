"""
Unit tests for MattergenGenerator.

Tests the host-side HTTP client that communicates with the MatterGen
Docker container.  All network calls are mocked — no running container
is required.

Run with:  pytest tests/unit/test_mattergen_generator.py -v -m unit
"""

import json
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from Information_Units.Generators.MattergenBaseModel.MattergenGenerator import (
    MattergenGenerator,
    _DEFAULT_API_URL,
    _DEFAULT_TIMEOUT,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def _reset_health_cache():
    """Reset the class-level health cache before every test."""
    MattergenGenerator._health_cache = {"healthy": None, "checked_at": 0.0}
    yield
    MattergenGenerator._health_cache = {"healthy": None, "checked_at": 0.0}


@pytest.fixture
def generator():
    """A MattergenGenerator with a mock logger."""
    logger = MagicMock()
    logger.log = MagicMock()
    return MattergenGenerator(generator_name="mattergen", logger=logger)


# Helper: build a requests.Response-like object
def _mock_response(status_code=200, json_data=None, text="", raise_for_status=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    if raise_for_status:
        resp.raise_for_status.side_effect = raise_for_status
    else:
        resp.raise_for_status.return_value = None
    return resp


# ============================================================================
# Constructor & Configuration
# ============================================================================

@pytest.mark.unit
def test_default_configuration():
    """Constructor uses default API URL and timeout when env vars are absent.

    PASS: api_url == _DEFAULT_API_URL, timeout == _DEFAULT_TIMEOUT.
    FAIL: values differ from defaults.
    """
    gen = MattergenGenerator()
    assert gen.api_url == _DEFAULT_API_URL
    assert gen.timeout == _DEFAULT_TIMEOUT


@pytest.mark.unit
def test_env_override_configuration(monkeypatch):
    """Constructor reads MATTERGEN_API_URL and MATTERGEN_TIMEOUT from env.

    PASS: api_url and timeout match env values.
    FAIL: env vars ignored.
    """
    monkeypatch.setenv("MATTERGEN_API_URL", "http://custom:9999/")
    monkeypatch.setenv("MATTERGEN_TIMEOUT", "120")
    gen = MattergenGenerator()
    assert gen.api_url == "http://custom:9999"  # trailing slash stripped
    assert gen.timeout == 120


# ============================================================================
# info()
# ============================================================================

@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_info_success(mock_get, generator):
    """info() returns formatted model metadata when the container responds.

    PASS: returned string contains model name, version, and pretrained models.
    FAIL: raises exception or returns fallback string.
    """
    mock_get.return_value = _mock_response(json_data={
        "name": "MatterGen",
        "version": "1.0.3",
        "description": "Diffusion model for crystals",
        "pretrained_models": ["mattergen_base", "dft_band_gap"],
        "capabilities": ["unconditional_generation"],
    })
    result = generator.info()
    assert "MatterGen" in result
    assert "1.0.3" in result
    assert "mattergen_base" in result


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_info_fallback_on_error(mock_get, generator):
    """info() returns a human-readable fallback when the container is down.

    PASS: no exception raised; result contains 'container unreachable'.
    FAIL: raises or returns empty string.
    """
    mock_get.side_effect = ConnectionError("refused")
    result = generator.info()
    assert "container unreachable" in result.lower() or "unreachable" in result.lower()


# ============================================================================
# is_healthy() — caching behaviour
# ============================================================================

@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_is_healthy_true(mock_get, generator):
    """is_healthy() returns True when container responds 200.

    PASS: True returned, HTTP GET called.
    FAIL: False returned despite 200.
    """
    mock_get.return_value = _mock_response(status_code=200)
    assert generator.is_healthy() is True
    mock_get.assert_called_once()


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_is_healthy_false(mock_get, generator):
    """is_healthy() returns False when container is unreachable.

    PASS: False returned.
    FAIL: True returned or exception raised.
    """
    mock_get.side_effect = ConnectionError("refused")
    assert generator.is_healthy() is False


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_is_healthy_cache_hit(mock_get, generator):
    """is_healthy() uses cached result within TTL window.

    PASS: second call does NOT issue another HTTP request.
    FAIL: two HTTP requests made.
    """
    mock_get.return_value = _mock_response(status_code=200)
    generator.is_healthy()
    generator.is_healthy()
    # Should only be called once due to caching
    assert mock_get.call_count == 1


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_is_healthy_cache_expired(mock_get, generator):
    """is_healthy() re-checks after TTL expires.

    PASS: second call after TTL issues a new HTTP request.
    FAIL: still using stale cache.
    """
    mock_get.return_value = _mock_response(status_code=200)
    generator.is_healthy()
    # Simulate cache expiry
    MattergenGenerator._health_cache["checked_at"] = time.time() - 999
    generator.is_healthy()
    assert mock_get.call_count == 2


# ============================================================================
# generate() — synchronous
# ============================================================================

@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_generate_unhealthy_container(mock_get, generator):
    """generate() returns error dict when container health check fails.

    PASS: result['status'] == 'error', no POST issued.
    FAIL: attempts to POST or raises exception.
    """
    mock_get.side_effect = ConnectionError("refused")
    result = generator.generate({"pretrained_name": "mattergen_base"})
    assert result["status"] == "error"
    assert "not reachable" in result["message"]
    assert result["source"] == "mattergen"
    assert result["queries"] == {"pretrained_name": "mattergen_base"}
    assert result["cif_strings"] == []


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.post")
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_generate_demo_shortcut(mock_get, mock_post, generator):
    """generate() routes to /demo/generate when pretrained_name=='demo'.

    PASS: POST sent to /demo/generate, result forwarded.
    FAIL: POST sent to /generate or error returned.
    """
    mock_get.return_value = _mock_response(status_code=200)  # health check
    mock_post.return_value = _mock_response(json_data={
        "status": "completed",
        "num_structures": 1,
        "structures": [{"lattice": {}}],
        "cif_strings": ["data_demo"],
    })
    result = generator.generate({"pretrained_name": "demo"})
    assert result["status"] == "completed"
    assert result["num_structures"] == 1
    assert result["source"] == "mattergen"
    assert result["queries"] == {"pretrained_name": "demo"}
    assert result["cif_strings"] == ["data_demo"]
    # Verify it hit /demo/generate
    call_url = mock_post.call_args[0][0]
    assert "/demo/generate" in call_url


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.post")
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_generate_builds_correct_payload(mock_get, mock_post, generator):
    """generate() sends correct JSON payload with all parameters.

    PASS: POST body contains pretrained_name, batch_size, num_batches,
          properties_to_condition_on, and diffusion_guidance_factor.
    FAIL: missing or incorrect keys in payload.
    """
    mock_get.return_value = _mock_response(status_code=200)
    mock_post.return_value = _mock_response(json_data={
        "status": "completed",
        "num_structures": 4,
    })

    inputs = {
        "pretrained_name": "dft_band_gap",
        "batch_size": 4,
        "num_batches": 2,
        "properties_to_condition_on": {"dft_band_gap": 1.5},
        "diffusion_guidance_factor": 2.0,
    }
    generator.generate(inputs)

    # Inspect the payload sent to requests.post
    call_kwargs = mock_post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert payload["pretrained_name"] == "dft_band_gap"
    assert payload["batch_size"] == 4
    assert payload["num_batches"] == 2
    assert payload["properties_to_condition_on"] == {"dft_band_gap": 1.5}
    assert payload["diffusion_guidance_factor"] == 2.0


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.post")
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_generate_model_path_overrides_pretrained(mock_get, mock_post, generator):
    """generate() sets pretrained_name=None when model_path is given.

    PASS: payload has model_path set and pretrained_name is None.
    FAIL: both are set, or model_path missing.
    """
    mock_get.return_value = _mock_response(status_code=200)
    mock_post.return_value = _mock_response(json_data={"status": "completed"})

    generator.generate({"model_path": "/models/custom", "batch_size": 1})

    payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
    assert payload["model_path"] == "/models/custom"
    assert payload["pretrained_name"] is None


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.post")
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_generate_timeout_handling(mock_get, mock_post, generator):
    """generate() returns error dict and invalidates health cache on timeout.

    PASS: result['status'] == 'error', health cache cleared.
    FAIL: exception raised or cache not invalidated.
    """
    import requests as real_requests
    mock_get.return_value = _mock_response(status_code=200)
    mock_post.side_effect = real_requests.Timeout("timed out")

    result = generator.generate({"pretrained_name": "mattergen_base"})
    assert result["status"] == "error"
    assert "timed out" in result["message"].lower()
    assert result["source"] == "mattergen"
    assert result["queries"] == {"pretrained_name": "mattergen_base"}
    assert result["cif_strings"] == []
    # Cache should be invalidated
    assert MattergenGenerator._health_cache["healthy"] is None


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.post")
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_generate_http_error_handling(mock_get, mock_post, generator):
    """generate() returns error dict on HTTP error (e.g. 500).

    PASS: result['status'] == 'error', health cache cleared.
    FAIL: exception propagates.
    """
    import requests as real_requests
    mock_get.return_value = _mock_response(status_code=200)
    mock_post.side_effect = real_requests.ConnectionError("connection refused")

    result = generator.generate({"pretrained_name": "mattergen_base"})
    assert result["status"] == "error"
    assert result["source"] == "mattergen"
    assert result["queries"] == {"pretrained_name": "mattergen_base"}
    assert result["cif_strings"] == []
    assert MattergenGenerator._health_cache["healthy"] is None


# ============================================================================
# generate_stream() — SSE streaming
# ============================================================================

def _mock_streaming_response(lines):
    """Build a mock response whose iter_lines() yields given strings."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.iter_lines.return_value = iter(lines)
    return resp


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_generate_stream_unhealthy(mock_get, generator):
    """generate_stream() yields error + done when container is down.

    PASS: exactly 2 events yielded — 'error' then 'done'.
    FAIL: no events, or wrong event types.
    """
    mock_get.side_effect = ConnectionError("refused")
    events = list(generator.generate_stream({"pretrained_name": "mattergen_base"}))
    assert len(events) == 2
    assert events[0]["event"] == "error"
    assert events[0]["source"] == "mattergen"
    assert events[0]["queries"] == {"pretrained_name": "mattergen_base"}
    assert events[1]["event"] == "done"


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.post")
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_generate_stream_demo_fallback(mock_get, mock_post, generator):
    """generate_stream() wraps sync demo response for demo mode.

    PASS: yields log, result, and done events.
    FAIL: attempts to call /generate/stream for demo.
    """
    mock_get.return_value = _mock_response(status_code=200)
    mock_post.return_value = _mock_response(json_data={
        "status": "completed",
        "num_structures": 1,
    })

    events = list(generator.generate_stream({"pretrained_name": "demo"}))
    event_types = [e["event"] for e in events]
    assert "log" in event_types
    assert "result" in event_types
    assert "done" in event_types
    result_event = next(e for e in events if e["event"] == "result")
    assert result_event["source"] == "mattergen"
    assert result_event["queries"] == {"pretrained_name": "demo"}
    assert result_event["cif_strings"] == []
    # Verify it called /demo/generate, not /generate/stream
    call_url = mock_post.call_args[0][0]
    assert "/demo/generate" in call_url


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.post")
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_generate_stream_parses_sse_events(mock_get, mock_post, generator):
    """generate_stream() correctly parses SSE event/data lines from the container.

    PASS: yielded dicts have correct 'event' keys and parsed JSON payloads.
    FAIL: events not parsed, or data garbled.
    """
    mock_get.return_value = _mock_response(status_code=200)

    # Simulate SSE stream lines (as they come from iter_lines)
    sse_lines = [
        "event: log",
        'data: {"message": "Loading model", "level": "info"}',
        "",  # end of SSE block
        "event: progress",
        'data: {"progress": 0.5, "message": "Diffusion step 500/1000 (50%)"}',
        "",
        "event: result",
        'data: {"status": "completed", "num_structures": 2}',
        "",
        "event: done",
        'data: {"message": "Stream ended"}',
        "",
    ]
    mock_post.return_value = _mock_streaming_response(sse_lines)

    events = list(generator.generate_stream({"pretrained_name": "mattergen_base"}))

    assert len(events) == 4
    assert events[0]["event"] == "log"
    assert events[0]["message"] == "Loading model"
    assert events[1]["event"] == "progress"
    assert events[1]["progress"] == 0.5
    assert events[2]["event"] == "result"
    assert events[2]["num_structures"] == 2
    assert events[2]["source"] == "mattergen"
    assert events[2]["queries"] == {"pretrained_name": "mattergen_base"}
    assert events[2]["cif_strings"] == []
    assert events[3]["event"] == "done"


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.post")
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_generate_stream_request_failure(mock_get, mock_post, generator):
    """generate_stream() yields error + done on connection failure to /generate/stream.

    PASS: 'error' event with failure message, then 'done'.
    FAIL: exception raised.
    """
    import requests as real_requests
    mock_get.return_value = _mock_response(status_code=200)
    mock_post.side_effect = real_requests.ConnectionError("refused")

    events = list(generator.generate_stream({"pretrained_name": "mattergen_base"}))
    assert events[0]["event"] == "error"
    assert events[0]["source"] == "mattergen"
    assert events[0]["queries"] == {"pretrained_name": "mattergen_base"}
    assert events[-1]["event"] == "done"
    assert MattergenGenerator._health_cache["healthy"] is None


# ============================================================================
# get_available_models()
# ============================================================================

@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_get_available_models_success(mock_get, generator):
    """get_available_models() returns model list from /info.

    PASS: list of model name strings returned.
    FAIL: empty list despite valid response.
    """
    mock_get.return_value = _mock_response(json_data={
        "pretrained_models": ["mattergen_base", "dft_band_gap", "ml_bulk_modulus"],
    })
    models = generator.get_available_models()
    assert models == ["mattergen_base", "dft_band_gap", "ml_bulk_modulus"]


@pytest.mark.unit
@patch("Information_Units.Generators.MattergenBaseModel.MattergenGenerator.requests.get")
def test_get_available_models_fallback(mock_get, generator):
    """get_available_models() returns empty list when container is unreachable.

    PASS: empty list, no exception.
    FAIL: exception raised.
    """
    mock_get.side_effect = ConnectionError("refused")
    assert generator.get_available_models() == []
