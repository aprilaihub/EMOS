"""Unit tests for SynthNN Predictor - Phase 1 mock implementation.

Test Coverage:
- Generic predictor interface (template for future predictors)
- CIF parsing and composition extraction (SynthNN-specific)
- Mock prediction behavior (SynthNN-specific)
- SynthNN output contract (threshold, precision)

Run: pytest tests/unit/test_synthnn_behaviour.py -v
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from Information_Units.Predictors.Synthnn.composition_helper import CompositionHelper
from Information_Units.Predictors.Synthnn.synthnn_model_helper import SynthnnModelHelper
from Information_Units.Predictors.Synthnn import SynthnnPredictor


# ============================================================================
# Mock Functions
# ============================================================================

def mock_predict_batch(compositions):
    """
    Deterministic fallback scores for testing.

    Scoring rules:
    - Common synthesis oxides (Al2O3, SiO2, TiO2, …): 0.85–0.95
    - Organic/complex elements (C, N, H present): 0.55
    - Other simple inorganic materials: 0.73
    """
    common_high_score = {
        'Al2O3': 0.92, 'Fe2O3': 0.88, 'SiO2': 0.95,
        'TiO2': 0.90, 'ZnO': 0.87, 'MgO': 0.91,
        'CaO': 0.89, 'NaCl': 0.93,
    }
    results = {}
    for comp in compositions:
        if comp in common_high_score:
            results[comp] = common_high_score[comp]
        elif any(elem in comp for elem in ['C', 'N', 'H']):
            results[comp] = 0.55
        else:
            results[comp] = 0.73
    return results


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cif_files():
    """Paths to CIF test fixtures."""
    d = Path(__file__).parent.parent / "fixtures" / "cif_files"
    return {
        'al2o3_path':  str(d / "Al2O3.cif"),
        'sio2_path':   str(d / "SiO2.cif"),
        'invalid_path': str(d / "invalid.cif"),
        'empty_path':  str(d / "empty.cif"),
    }


@pytest.fixture
def mock_logger():
    logger = Mock()
    logger.log = Mock()
    return logger


@pytest.fixture
def mock_model_helper():
    """Patch SynthnnModelHelper so no real model is loaded."""
    def _mock_init(self, logger=None):
        self.logger = logger
        self.model = None

    with patch.object(SynthnnModelHelper, '__init__', _mock_init):
        with patch.object(SynthnnModelHelper, 'predict_batch', side_effect=mock_predict_batch):
            yield


def assert_prediction_envelope(result):
    """Standard response-envelope assertion, reusable across predictor tests."""
    assert isinstance(result, dict)
    assert result.get('status') in {'ok', 'error', 'partial', 'skipped'}
    assert isinstance(result.get('predictions'), dict)
    assert 'synthesizable' in result['predictions']
    assert 'synthesizability_score' in result['predictions']
    assert isinstance(result.get('warnings'), list)
    assert 'error' in result


# ============================================================================
# Generic Predictor Interface Tests
# (Template for any future predictor added to EMOS)
# ============================================================================

@pytest.mark.unit
def test_init_stores_name_and_logger(mock_logger, mock_model_helper):
    """Predictor stores predictor_name and logger on init."""
    predictor = SynthnnPredictor(predictor_name='test_synthnn', logger=mock_logger)
    assert predictor.predictor_name == 'test_synthnn'
    assert predictor.logger is mock_logger


@pytest.mark.unit
def test_info_returns_non_empty_description(mock_logger):
    """info() returns a non-empty string describing the predictor."""
    predictor = SynthnnPredictor(logger=mock_logger)
    info = predictor.info()
    assert isinstance(info, str) and len(info) > 0


@pytest.mark.unit
def test_predict_empty_input_returns_empty_dict(mock_logger):
    """predict({}) always returns an empty dict, never raises."""
    predictor = SynthnnPredictor(logger=mock_logger)
    assert predictor.predict({}) == {}


@pytest.mark.unit
@pytest.mark.parametrize('cif_key,expected_elements', [
    ('al2o3_path', ['Al', 'O']),
    ('sio2_path',  ['Si', 'O']),
])
def test_predict_valid_cif_returns_ok_envelope(cif_files, mock_logger, mock_model_helper, cif_key, expected_elements):
    """Valid CIF input yields a well-formed 'ok' envelope."""
    predictor = SynthnnPredictor(logger=mock_logger)
    results = predictor.predict({'material.cif': cif_files[cif_key]})

    assert 'material.cif' in results
    r = results['material.cif']
    assert_prediction_envelope(r)
    assert r['status'] == 'ok'
    assert r['predictions']['synthesizable'] is not None
    assert 0.0 <= r['predictions']['synthesizability_score'] <= 1.0
    assert r['error'] is None


@pytest.mark.unit
@pytest.mark.parametrize('label,path_key,expected_error_fragment', [
    ('missing.cif', None,           'File not found'),
    ('invalid.cif', 'invalid_path', None),
    ('empty.cif',   'empty_path',   None),
])
def test_predict_error_cases_return_error_envelope(cif_files, mock_logger, mock_model_helper, label, path_key, expected_error_fragment):
    """Files that cannot be parsed produce an 'error' envelope."""
    predictor = SynthnnPredictor(logger=mock_logger)
    path = '/nonexistent/missing.cif' if path_key is None else cif_files[path_key]
    results = predictor.predict({label: path})

    r = results[label]
    assert_prediction_envelope(r)
    assert r['status'] == 'error'
    assert r['predictions']['synthesizable'] is None
    assert r['predictions']['synthesizability_score'] is None
    assert r['error'] is not None
    if expected_error_fragment:
        assert expected_error_fragment in r['error']


@pytest.mark.unit
def test_predict_batch_preserves_all_keys(cif_files, mock_logger, mock_model_helper):
    """Every input key appears in the output dict, including failed files."""
    predictor = SynthnnPredictor(logger=mock_logger)
    input_data = {
        'Al2O3.cif':   cif_files['al2o3_path'],
        'SiO2.cif':    cif_files['sio2_path'],
        'invalid.cif': cif_files['invalid_path'],
    }
    results = predictor.predict(input_data)

    assert set(results.keys()) == set(input_data.keys())
    for r in results.values():
        assert_prediction_envelope(r)
    assert results['Al2O3.cif']['status'] == 'ok'
    assert results['SiO2.cif']['status'] == 'ok'
    assert results['invalid.cif']['status'] == 'error'


@pytest.mark.unit
def test_predict_output_is_json_serializable(cif_files, mock_logger, mock_model_helper):
    """Output can be serialized to JSON and deserialized without data loss."""
    predictor = SynthnnPredictor(logger=mock_logger)
    results = predictor.predict({
        'Al2O3.cif':   cif_files['al2o3_path'],
        'invalid.cif': cif_files['invalid_path'],
    })
    serialized = json.dumps(results)
    assert isinstance(json.loads(serialized), dict)


# ============================================================================
# SynthNN-Specific: CompositionHelper
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize('cif_key,expect_success,expected_elements', [
    ('al2o3_path',   True,  ['Al', 'O']),
    ('sio2_path',    True,  ['Si', 'O']),
    ('invalid_path', False, []),
    ('empty_path',   False, []),
])
def test_extract_from_cif(cif_files, cif_key, expect_success, expected_elements):
    """extract_from_cif returns (formula, True) on valid CIF, (None, False) otherwise."""
    with open(cif_files[cif_key]) as f:
        content = f.read()
    formula, success = CompositionHelper.extract_from_cif(content)

    assert success is expect_success
    if expect_success:
        assert isinstance(formula, str) and len(formula) > 0
        for el in expected_elements:
            assert el in formula
    else:
        assert formula is None


@pytest.mark.unit
def test_extract_from_malformed_string():
    """Non-CIF string yields (None, False) without raising."""
    formula, success = CompositionHelper.extract_from_cif("not a cif !!!")
    assert success is False
    assert formula is None


@pytest.mark.unit
@pytest.mark.parametrize('raw,expected', [
    ('Al2O3',   'Al2O3'),
    (' Al2O3 ', 'Al2O3'),
    ('Al4O6',   'Al2O3'),   # stoichiometry reduction
    ('Fe2O3',   'Fe2O3'),
])
def test_normalize_composition(raw, expected):
    """normalize_composition strips and reduces stoichiometry."""
    assert CompositionHelper.normalize_composition(raw) == expected


# ============================================================================
# SynthNN-Specific: ModelHelper
# ============================================================================

@pytest.mark.unit
def test_model_helper_init_stores_logger(mock_logger, mock_model_helper):
    helper = SynthnnModelHelper(logger=mock_logger)
    assert helper.logger is mock_logger
    assert helper.model is None   # no real model in unit tests


@pytest.mark.unit
@pytest.mark.parametrize('compositions,expected_count', [
    ([],                               0),
    (['Al2O3'],                        1),
    (['Al2O3', 'Fe2O3', 'SiO2', 'ZnO'], 4),
])
def test_predict_batch_returns_correct_count(mock_logger, mock_model_helper, compositions, expected_count):
    """predict_batch returns one score per composition, all in [0, 1]."""
    helper = SynthnnModelHelper(logger=mock_logger)
    results = helper.predict_batch(compositions)
    assert len(results) == expected_count
    for score in results.values():
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


@pytest.mark.unit
@pytest.mark.parametrize('compositions,threshold,comparison', [
    (['Al2O3', 'SiO2', 'TiO2'], 0.85, 'gt'),
    (['CH4',   'C2H6', 'NH3'],  0.65, 'lt'),
])
def test_mock_score_ranges(mock_logger, mock_model_helper, compositions, threshold, comparison):
    """Mock scores reflect material type: oxides high, organics low."""
    helper = SynthnnModelHelper(logger=mock_logger)
    results = helper.predict_batch(compositions)
    for score in results.values():
        if comparison == 'gt':
            assert score > threshold
        else:
            assert score < threshold

