"""
Unit tests for MaterialGenerationFeature.

Tests the Python-side feature class that orchestrates generators.
All generators are mocked — no Docker container or real generation needed.

Run with:  pytest tests/unit/test_material_generation_feature.py -v -m unit
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from Features.Materials_Exploration.MaterialGeneration.MaterialGenerationFeature import (
    MaterialGenerationFeature,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def logger():
    """A mock logger that records calls."""
    mock = MagicMock()
    mock.log = MagicMock()
    mock.logs = []

    def _log(message, level="info"):
        mock.logs.append({"message": message, "level": level})

    mock.log.side_effect = _log
    return mock


@pytest.fixture
def feature(logger):
    """A MaterialGenerationFeature with a mock logger."""
    return MaterialGenerationFeature(logger=logger)


def _make_mock_generator(generate_result=None, stream_events=None):
    """Create a mock generator with generate() and optionally generate_stream()."""
    gen = MagicMock()
    gen.generate.return_value = generate_result or {
        "status": "completed",
        "num_structures": 2,
        "structures": [{"lattice": {}}, {"lattice": {}}],
        "cif_strings": ["data_s1", "data_s2"],
        "debug_logs": ["[INFO] Generated 2 structures"],
    }
    if stream_events is not None:
        gen.generate_stream.return_value = iter(stream_events)
    else:
        # Remove generate_stream so hasattr check fails — tests sync fallback
        del gen.generate_stream
    return gen


# ============================================================================
# info()
# ============================================================================

@pytest.mark.unit
def test_info_returns_description(feature):
    """info() returns a non-empty descriptive string.

    PASS: string contains 'Material Generation'.
    FAIL: empty or unrelated string.
    """
    result = feature.info()
    assert "Material Generation" in result


# ============================================================================
# extract_inputs()
# ============================================================================

@pytest.mark.unit
def test_extract_inputs_all_keys(feature):
    """extract_inputs() extracts all expected keys from input data.

    PASS: returned dict has active_databases, active_generators,
          active_predictors, and generator_inputs.
    FAIL: missing keys or wrong values.
    """
    input_data = {
        "active_databases": [{"name": "COD", "value": "cod"}],
        "active_generators": [{"name": "MatterGen", "value": "mattergen"}],
        "active_predictors": [],
        "generator_inputs": {"mattergen": {"pretrained_name": "mattergen_base"}},
        "extra_key": "should be ignored",
    }
    result = feature.extract_inputs(input_data)
    assert result["active_generators"] == [{"name": "MatterGen", "value": "mattergen"}]
    assert result["generator_inputs"] == {"mattergen": {"pretrained_name": "mattergen_base"}}
    assert "extra_key" not in result


@pytest.mark.unit
def test_extract_inputs_defaults(feature):
    """extract_inputs() returns empty lists/dicts for missing keys.

    PASS: all values are empty but present.
    FAIL: KeyError or None values.
    """
    result = feature.extract_inputs({})
    assert result["active_databases"] == []
    assert result["active_generators"] == []
    assert result["active_predictors"] == []
    assert result["generator_inputs"] == {}


# ============================================================================
# process_feature() — synchronous
# ============================================================================

@pytest.mark.unit
def test_process_feature_no_generators(feature, logger):
    """process_feature() with no active generators returns empty results.

    PASS: status == 'completed', generation_results is empty dict.
    FAIL: error or non-empty results.
    """
    inputs = {
        "active_generators": [],
        "generator_inputs": {},
    }
    result = feature.process_feature(inputs)
    assert result["status"] == "completed"
    assert result["generation_results"] == {}


@pytest.mark.unit
def test_process_feature_calls_generator(feature):
    """process_feature() calls generate() on each active generator and collects results.

    PASS: generator.generate() called with correct params,
          result stored under the generator's key.
    FAIL: generate() not called, or result missing.
    """
    mock_gen = _make_mock_generator()

    with patch.dict(
        "Features.Materials_Exploration.MaterialGeneration.MaterialGenerationFeature.generator_registry",
        {"mattergen": mock_gen},
    ):
        inputs = {
            "active_generators": [{"name": "MatterGen", "value": "mattergen"}],
            "generator_inputs": {"mattergen": {"pretrained_name": "dft_band_gap", "batch_size": 4}},
        }
        result = feature.process_feature(inputs)

    assert "mattergen" in result["generation_results"]
    gen_result = result["generation_results"]["mattergen"]
    assert gen_result["status"] == "completed"
    assert gen_result["num_structures"] == 2
    mock_gen.generate.assert_called_once_with({"pretrained_name": "dft_band_gap", "batch_size": 4})


@pytest.mark.unit
def test_process_feature_generator_exception(feature, logger):
    """process_feature() catches generator exceptions and stores error result.

    PASS: generation_results[key]['status'] == 'error', no exception propagated.
    FAIL: exception raised to caller.
    """
    mock_gen = MagicMock()
    mock_gen.generate.side_effect = RuntimeError("GPU OOM")
    del mock_gen.generate_stream  # ensure no streaming

    with patch.dict(
        "Features.Materials_Exploration.MaterialGeneration.MaterialGenerationFeature.generator_registry",
        {"mattergen": mock_gen},
    ):
        inputs = {
            "active_generators": [{"name": "MatterGen", "value": "mattergen"}],
            "generator_inputs": {"mattergen": {}},
        }
        result = feature.process_feature(inputs)

    assert result["generation_results"]["mattergen"]["status"] == "error"
    assert "GPU OOM" in result["generation_results"]["mattergen"]["message"]


@pytest.mark.unit
def test_process_feature_unknown_generator(feature, logger):
    """process_feature() skips generators not found in factory or registry.

    PASS: no error, generation_results does not contain the unknown key.
    FAIL: exception raised.
    """
    with patch.dict(
        "Features.Materials_Exploration.MaterialGeneration.MaterialGenerationFeature.generator_registry",
        {},
        clear=True,
    ), patch.dict(
        "Features.Materials_Exploration.MaterialGeneration.MaterialGenerationFeature.generator_factory",
        {},
        clear=True,
    ):
        inputs = {
            "active_generators": [{"name": "Unknown", "value": "nonexistent_gen"}],
            "generator_inputs": {},
        }
        result = feature.process_feature(inputs)

    assert "nonexistent_gen" not in result["generation_results"]


@pytest.mark.unit
def test_process_feature_multiple_generators(feature):
    """process_feature() processes multiple generators and collects all results.

    PASS: generation_results has an entry for each generator.
    FAIL: missing entries.
    """
    mock_gen_a = _make_mock_generator(generate_result={
        "status": "completed", "num_structures": 1, "debug_logs": [],
    })
    mock_gen_b = _make_mock_generator(generate_result={
        "status": "completed", "num_structures": 3, "debug_logs": [],
    })

    with patch.dict(
        "Features.Materials_Exploration.MaterialGeneration.MaterialGenerationFeature.generator_registry",
        {"gen_a": mock_gen_a, "gen_b": mock_gen_b},
    ):
        inputs = {
            "active_generators": [
                {"name": "GenA", "value": "gen_a"},
                {"name": "GenB", "value": "gen_b"},
            ],
            "generator_inputs": {"gen_a": {}, "gen_b": {}},
        }
        result = feature.process_feature(inputs)

    assert result["generation_results"]["gen_a"]["num_structures"] == 1
    assert result["generation_results"]["gen_b"]["num_structures"] == 3


# ============================================================================
# process_feature_stream() — SSE streaming
# ============================================================================

@pytest.mark.unit
def test_process_feature_stream_yields_events(feature):
    """process_feature_stream() yields SSE-formatted log, progress, and result events.

    PASS: at least one 'event: log', one 'event: progress', and one
          'event: result' block are yielded.
    FAIL: missing event types or malformed SSE.
    """
    stream_events = [
        {"event": "log", "message": "Loading model", "level": "info"},
        {"event": "progress", "progress": 0.5, "message": "Step 500/1000"},
        {"event": "result", "status": "completed", "num_structures": 2,
         "structures": [], "cif_strings": [], "debug_logs": []},
        {"event": "done", "message": "Stream ended"},
    ]
    mock_gen = _make_mock_generator(stream_events=stream_events)

    with patch.dict(
        "Features.Materials_Exploration.MaterialGeneration.MaterialGenerationFeature.generator_registry",
        {"mattergen": mock_gen},
    ):
        inputs = {
            "active_generators": [{"name": "MatterGen", "value": "mattergen"}],
            "generator_inputs": {"mattergen": {"pretrained_name": "mattergen_base"}},
        }
        sse_blocks = list(feature.process_feature_stream(inputs))

    # Parse all SSE blocks
    events = []
    for block in sse_blocks:
        for line in block.strip().split("\n"):
            if line.startswith("event: "):
                events.append(line.split("event: ")[1])

    assert "log" in events
    assert "progress" in events
    assert "result" in events


@pytest.mark.unit
def test_process_feature_stream_sync_fallback(feature):
    """process_feature_stream() falls back to sync generate() when
    generate_stream is not available.

    PASS: yields log events and a result event via sync fallback.
    FAIL: error or no result.
    """
    mock_gen = _make_mock_generator()  # No generate_stream

    with patch.dict(
        "Features.Materials_Exploration.MaterialGeneration.MaterialGenerationFeature.generator_registry",
        {"mattergen": mock_gen},
    ):
        inputs = {
            "active_generators": [{"name": "MatterGen", "value": "mattergen"}],
            "generator_inputs": {"mattergen": {}},
        }
        sse_blocks = list(feature.process_feature_stream(inputs))

    # Should still get a result event at the end
    all_text = "".join(sse_blocks)
    assert "event: result" in all_text
    assert "event: log" in all_text
    mock_gen.generate.assert_called_once()


@pytest.mark.unit
def test_process_feature_stream_no_generators(feature):
    """process_feature_stream() with no generators yields log + result.

    PASS: result event has empty generation_results.
    FAIL: error event or exception.
    """
    inputs = {"active_generators": [], "generator_inputs": {}}
    sse_blocks = list(feature.process_feature_stream(inputs))
    all_text = "".join(sse_blocks)
    assert "event: result" in all_text
    # Parse the result data
    for block in sse_blocks:
        if "event: result" in block:
            data_line = [l for l in block.split("\n") if l.startswith("data: ")][0]
            data = json.loads(data_line[6:])
            assert data["generation_results"] == {}
            break


@pytest.mark.unit
def test_process_feature_stream_generator_exception(feature, logger):
    """process_feature_stream() catches generator exceptions and yields error logs.

    PASS: error log yielded, result event still contains error entry, no crash.
    FAIL: exception propagates.
    """
    mock_gen = MagicMock()
    mock_gen.generate_stream.side_effect = RuntimeError("Diffusion diverged")

    with patch.dict(
        "Features.Materials_Exploration.MaterialGeneration.MaterialGenerationFeature.generator_registry",
        {"mattergen": mock_gen},
    ):
        inputs = {
            "active_generators": [{"name": "MatterGen", "value": "mattergen"}],
            "generator_inputs": {"mattergen": {}},
        }
        sse_blocks = list(feature.process_feature_stream(inputs))

    all_text = "".join(sse_blocks)
    assert "event: result" in all_text
    assert "Diffusion diverged" in all_text


# ============================================================================
# format_outputs()
# ============================================================================

@pytest.mark.unit
def test_format_outputs_passthrough(feature):
    """format_outputs() returns its input unchanged (passthrough).

    PASS: input dict returned as-is.
    FAIL: data modified or wrapped.
    """
    data = {"status": "completed", "generation_results": {"mattergen": {}}}
    assert feature.format_outputs(data) is data


# ============================================================================
# Full process() template pattern
# ============================================================================

@pytest.mark.unit
def test_process_template_pattern(feature):
    """process() orchestrates extract_inputs → process_feature → format_outputs.

    PASS: returns formatted results dict with correct structure.
    FAIL: missing keys or wrong structure.
    """
    mock_gen = _make_mock_generator()

    with patch.dict(
        "Features.Materials_Exploration.MaterialGeneration.MaterialGenerationFeature.generator_registry",
        {"mattergen": mock_gen},
    ):
        input_data = {
            "active_generators": [{"name": "MatterGen", "value": "mattergen"}],
            "generator_inputs": {"mattergen": {"pretrained_name": "mattergen_base"}},
        }
        result = feature.process(input_data)

    assert result["status"] == "completed"
    assert "mattergen" in result["generation_results"]
