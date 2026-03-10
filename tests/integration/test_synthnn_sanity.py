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
    assert isinstance(result.get('predictions'), dict)
    assert 'synthesizable' in result['predictions']
    assert 'synthesizability_score' in result['predictions']
    assert isinstance(result.get('warnings'), list)
    assert 'error' in result


def assert_ok_prediction(result):
    """Validate a successful prediction payload."""
    assert_prediction_envelope(result)
    assert result['status'] == 'ok'
    assert result['predictions']['synthesizable'] is not None
    assert result['predictions']['synthesizability_score'] is not None
    assert 0.0 <= result['predictions']['synthesizability_score'] <= 1.0
    assert result['error'] is None


def assert_error_prediction(result):
    """Validate a failed prediction payload."""
    assert_prediction_envelope(result)
    assert result['status'] == 'error'
    assert result['predictions']['synthesizable'] is None
    assert result['predictions']['synthesizability_score'] is None
    assert result['error'] is not None


# ============================================================================
# Generic Predictor Contract Tests
# (Template for future predictors with real backends)
# ============================================================================

def test_predict_valid_input_returns_ok_envelope(cif_files, predictor):
    """A valid input file produces a successful, well-formed result."""
    results = predictor.predict({'material.cif': cif_files['al2o3_path']})

    assert 'material.cif' in results
    assert_ok_prediction(results['material.cif'])


def test_predict_invalid_input_returns_error_envelope(cif_files, predictor):
    """An invalid input file produces a structured error result."""
    results = predictor.predict({'invalid.cif': cif_files['invalid_path']})

    assert 'invalid.cif' in results
    assert_error_prediction(results['invalid.cif'])


def test_predict_mixed_batch_preserves_successes_and_failures(cif_files, predictor):
    """A bad file does not prevent valid files in the same batch from succeeding."""
    input_data = {
        'Al2O3.cif': cif_files['al2o3_path'],
        'invalid.cif': cif_files['invalid_path'],
        'SiO2.cif': cif_files['sio2_path'],
    }
    results = predictor.predict(input_data)

    assert set(results.keys()) == set(input_data.keys())
    assert_ok_prediction(results['Al2O3.cif'])
    assert_ok_prediction(results['SiO2.cif'])
    assert_error_prediction(results['invalid.cif'])


def test_predict_output_is_json_serializable(cif_files, predictor):
    """Prediction output can be serialized and deserialized as JSON."""
    results = predictor.predict({
        'Al2O3.cif': cif_files['al2o3_path'],
        'invalid.cif': cif_files['invalid_path'],
    })

    serialized = json.dumps(results)
    deserialized = json.loads(serialized)

    assert isinstance(deserialized, dict)
    assert set(deserialized.keys()) == {'Al2O3.cif', 'invalid.cif'}


# ============================================================================
# SynthNN-Specific Sanity Tests
# ============================================================================

@pytest.mark.parametrize('cif_key,expected_score_range', [
    ('al2o3_path', (0.70, 1.0)),
    ('sio2_path', (0.70, 1.0)),
])
def test_known_synthesizable_materials_score_high(cif_files, predictor, cif_key, expected_score_range):
    """Known common oxides should receive high SynthNN synthesizability scores."""
    results = predictor.predict({'test.cif': cif_files[cif_key]})
    result = results['test.cif']

    assert_ok_prediction(result)

    score = result['predictions']['synthesizability_score']
    min_score, max_score = expected_score_range
    assert min_score <= score <= max_score, (
        f"Score {score} not in expected range [{min_score}, {max_score}]"
    )


def test_model_deterministic_predictions(cif_files, predictor):
    """Running the same input twice should produce the same score."""
    results1 = predictor.predict({'Al2O3.cif': cif_files['al2o3_path']})
    results2 = predictor.predict({'Al2O3.cif': cif_files['al2o3_path']})

    score1 = results1['Al2O3.cif']['predictions']['synthesizability_score']
    score2 = results2['Al2O3.cif']['predictions']['synthesizability_score']
    assert score1 == score2


def test_synthesizable_flag_follows_threshold(cif_files, predictor):
    """SynthNN uses the rule synthesizable == (score >= 0.70)."""
    results = predictor.predict({
        'Al2O3.cif': cif_files['al2o3_path'],
        'SiO2.cif': cif_files['sio2_path'],
    })

    for result in results.values():
        assert_ok_prediction(result)
        score = result['predictions']['synthesizability_score']
        assert result['predictions']['synthesizable'] is (score >= 0.70)
