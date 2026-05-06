"""
Integration tests for SynthNN Predictor with the real model.

Test Coverage:
- Generic predictor contract checks that can serve as a template for future predictors
- SynthNN-specific sanity checks for known materials and threshold behavior

Run with: pytest tests/integration/test_synthnn_sanity.py -v
Skip network tests: pytest -m "not network"
Skip slow tests: pytest -m "not slow"
"""

import json
from pathlib import Path

import pytest

from Information_Units.Predictors.Synthnn import SynthnnPredictor


pytestmark = [pytest.mark.integration, pytest.mark.network, pytest.mark.slow]


@pytest.fixture
def cif_files():
    """Provide paths to CIF test fixtures."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cif_files"
    return {
        'al2o3_path': str(fixtures_dir / "Al2O3.cif"),
        'sio2_path': str(fixtures_dir / "SiO2.cif"),
        'invalid_path': str(fixtures_dir / "invalid.cif"),
    }


@pytest.fixture(scope="module")
def predictor():
    """Instantiate the real SynthNN predictor once for this module."""
    return SynthnnPredictor(predictor_name='test_synthnn_integration')


def assert_prediction_envelope(result):
    """Validate standard predictor response envelope for a single file."""
    assert isinstance(result, dict)
    assert result.get('status') in {'ok', 'error', 'partial', 'skipped'}
    assert isinstance(result.get('properties'), dict)
    assert 'synthesizable' in result['properties']
    assert 'synthesizability_score' in result['properties']
    assert isinstance(result.get('warnings'), list)
    assert 'error' in result


def assert_ok_prediction(result):
    """Validate a successful prediction payload."""
    assert_prediction_envelope(result)
    assert result['status'] == 'ok'
    assert result['properties']['synthesizable'] is not None
    assert result['properties']['synthesizability_score'] is not None
    assert 0.0 <= result['properties']['synthesizability_score'] <= 1.0
    assert result['error'] is None


def assert_error_prediction(result):
    """Validate a failed prediction payload."""
    assert_prediction_envelope(result)
    assert result['status'] == 'error'
    assert result['properties']['synthesizable'] is None
    assert result['properties']['synthesizability_score'] is None
    assert result['error'] is not None


# ============================================================================
# Generic Predictor Contract Tests
# (Template for future predictors with real backends)
# ============================================================================

def test_predict_valid_input_returns_ok_envelope(cif_files, predictor):
    """A valid input file produces a successful, well-formed result."""
    results = predictor.predict([Path(cif_files['al2o3_path']).read_text()])

    assert results["source"] == "synthnn"
    assert len(results["results"]) == 1
    assert_ok_prediction(results["results"][0])


def test_predict_invalid_input_returns_error_envelope(cif_files, predictor):
    """An invalid input file produces a structured error result."""
    results = predictor.predict([Path(cif_files['invalid_path']).read_text()])

    assert results["source"] == "synthnn"
    assert len(results["results"]) == 1
    assert_error_prediction(results["results"][0])


def test_predict_mixed_batch_preserves_successes_and_failures(cif_files, predictor):
    """A bad file does not prevent valid files in the same batch from succeeding."""
    results = predictor.predict([
        Path(cif_files['al2o3_path']).read_text(),
        Path(cif_files['invalid_path']).read_text(),
        Path(cif_files['sio2_path']).read_text(),
    ])

    assert results["source"] == "synthnn"
    assert len(results["results"]) == 3
    assert_ok_prediction(results["results"][0])
    assert_error_prediction(results["results"][1])
    assert_ok_prediction(results["results"][2])


def test_predict_output_is_json_serializable(cif_files, predictor):
    """Prediction output can be serialized and deserialized as JSON."""
    results = predictor.predict([
        Path(cif_files['al2o3_path']).read_text(),
        Path(cif_files['invalid_path']).read_text(),
    ])

    serialized = json.dumps(results)
    deserialized = json.loads(serialized)

    assert isinstance(deserialized, dict)
    assert deserialized["source"] == "synthnn"
    assert len(deserialized["results"]) == 2


# ============================================================================
# SynthNN-Specific Sanity Tests
# ============================================================================

@pytest.mark.parametrize('cif_key,expected_score_range', [
    ('al2o3_path', (0.70, 1.0)),
    ('sio2_path', (0.70, 1.0)),
])
def test_known_synthesizable_materials_score_high(cif_files, predictor, cif_key, expected_score_range):
    """Known common oxides should receive high SynthNN synthesizability scores."""
    results = predictor.predict([Path(cif_files[cif_key]).read_text()])
    result = results["results"][0]

    assert_ok_prediction(result)

    score = result['properties']['synthesizability_score']
    min_score, max_score = expected_score_range
    assert min_score <= score <= max_score, (
        f"Score {score} not in expected range [{min_score}, {max_score}]"
    )


def test_model_deterministic_predictions(cif_files, predictor):
    """Running the same input twice should produce the same score."""
    cif_text = Path(cif_files['al2o3_path']).read_text()
    results1 = predictor.predict([cif_text])
    results2 = predictor.predict([cif_text])

    score1 = results1["results"][0]['properties']['synthesizability_score']
    score2 = results2["results"][0]['properties']['synthesizability_score']
    assert score1 == score2


def test_synthesizable_flag_follows_threshold(cif_files, predictor):
    """SynthNN uses the rule synthesizable == (score >= 0.70)."""
    results = predictor.predict([
        Path(cif_files['al2o3_path']).read_text(),
        Path(cif_files['sio2_path']).read_text(),
    ])

    for result in results["results"]:
        assert_ok_prediction(result)
        score = result['properties']['synthesizability_score']
        assert result['properties']['synthesizable'] is (score >= 0.70)


def test_predict_with_list_input_returns_standardized_output(cif_files, predictor):
    """New contract: list[str] input returns source/results envelope."""
    cif_text = Path(cif_files["al2o3_path"]).read_text()
    result = predictor.predict([cif_text])

    assert result["source"] == "synthnn"
    assert isinstance(result["results"], list)
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] in {"ok", "error"}
