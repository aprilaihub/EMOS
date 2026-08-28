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
    assert isinstance(result.get('properties'), dict)
    assert 'synthesizable' in result['properties']
    assert 'synthesizability_score' in result['properties']
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
def test_predict_empty_input_returns_standardized_empty_results(mock_logger):
    """predict() returns standardized empty output for empty list input."""
    predictor = SynthnnPredictor(logger=mock_logger)
    assert predictor.predict([]) == {"source": "synthnn", "results": []}


@pytest.mark.unit
@pytest.mark.parametrize('cif_key,expected_elements', [
    ('al2o3_path', ['Al', 'O']),
    ('sio2_path',  ['Si', 'O']),
])
def test_predict_valid_cif_returns_ok_envelope(cif_files, mock_logger, mock_model_helper, cif_key, expected_elements):
    """Valid CIF input yields a well-formed 'ok' envelope."""
    predictor = SynthnnPredictor(logger=mock_logger)
    cif_text = Path(cif_files[cif_key]).read_text()
    output = predictor.predict([cif_text])

    assert output["source"] == "synthnn"
    assert len(output["results"]) == 1
    r = output["results"][0]
    assert_prediction_envelope(r)
    assert r['status'] == 'ok'
    assert r['properties']['synthesizable'] is not None
    assert 0.0 <= r['properties']['synthesizability_score'] <= 1.0
    assert r['error'] is None


@pytest.mark.unit
@pytest.mark.parametrize('path_key,expected_error_fragment', [
    ('invalid_path', "Failed to parse CIF"),
])
def test_predict_error_cases_return_error_envelope(cif_files, mock_logger, mock_model_helper, path_key, expected_error_fragment):
    """CIF strings that cannot be parsed produce an 'error' envelope."""
    predictor = SynthnnPredictor(logger=mock_logger)
    cif_text = Path(cif_files[path_key]).read_text()
    output = predictor.predict([cif_text])

    r = output["results"][0]
    assert_prediction_envelope(r)
    assert r['status'] == 'error'
    assert r['properties']['synthesizable'] is None
    assert r['properties']['synthesizability_score'] is None
    assert r['error'] is not None
    assert expected_error_fragment in r['error']


@pytest.mark.unit
def test_predict_batch_preserves_all_keys(cif_files, mock_logger, mock_model_helper):
    """Batch output preserves item count and status ordering."""
    predictor = SynthnnPredictor(logger=mock_logger)
    output = predictor.predict([
        Path(cif_files['al2o3_path']).read_text(),
        Path(cif_files['sio2_path']).read_text(),
        Path(cif_files['invalid_path']).read_text(),
    ])

    assert output["source"] == "synthnn"
    assert len(output["results"]) == 3
    for r in output["results"]:
        assert_prediction_envelope(r)
    assert output["results"][0]["status"] == 'ok'
    assert output["results"][1]["status"] == 'ok'
    assert output["results"][2]["status"] == 'error'


@pytest.mark.unit
def test_predict_output_is_json_serializable(cif_files, mock_logger, mock_model_helper):
    """Output can be serialized to JSON and deserialized without data loss."""
    predictor = SynthnnPredictor(logger=mock_logger)
    output = predictor.predict([
        Path(cif_files['al2o3_path']).read_text(),
        Path(cif_files['invalid_path']).read_text(),
    ])
    serialized = json.dumps(output)
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


# ============================================================================
# SynthNN-Specific: Output Contract
# ============================================================================

@pytest.mark.unit
def test_output_properties_are_registered_in_property_mappings(mock_logger, mock_model_helper):
    """All SynthNN output properties must be declared in modular property mappings."""
    predictor = SynthnnPredictor(logger=mock_logger)

    assert set(predictor.OUTPUT_PROPERTIES).issubset(predictor._mapped_output_properties)


@pytest.mark.unit
def test_checker_rejects_unmapped_output_properties(mock_logger, mock_model_helper):
    """Checker raises if predictor output contains a property not in mapping."""
    predictor = SynthnnPredictor(logger=mock_logger)

    with pytest.raises(ValueError, match="missing in modular property mappings"):
        predictor._check_output_properties_in_mapping({'not_in_mapping': 1})


@pytest.mark.unit
def test_synthesizable_flag_follows_threshold(cif_files, mock_logger, mock_model_helper):
    """synthesizable is True iff synthesizability_score ≥ 0.70."""
    predictor = SynthnnPredictor(logger=mock_logger)
    output = predictor.predict([
        Path(cif_files['al2o3_path']).read_text(),
        Path(cif_files['sio2_path']).read_text(),
    ])

    for result in output["results"]:
        if result['status'] == 'ok':
            score = result['properties']['synthesizability_score']
            assert result['properties']['synthesizable'] is (score >= 0.70)


@pytest.mark.unit
def test_score_is_float_with_bounded_precision(cif_files, mock_logger, mock_model_helper):
    """Score is a float rounded to at most 4 decimal places."""
    predictor = SynthnnPredictor(logger=mock_logger)
    output = predictor.predict([Path(cif_files['al2o3_path']).read_text()])

    score = output["results"][0]['properties']['synthesizability_score']
    assert isinstance(score, float)
    decimal_part = str(score).split('.')[-1] if '.' in str(score) else ''
    assert len(decimal_part) <= 4


@pytest.mark.unit
def test_predict_with_list_input_returns_standardized_output(cif_files, mock_logger, mock_model_helper):
    predictor = SynthnnPredictor(logger=mock_logger)
    cif_text = Path(cif_files["al2o3_path"]).read_text()
    result = predictor.predict([cif_text])

    assert result["source"] == "synthnn"
    assert isinstance(result["results"], list)
    assert result["results"][0]["status"] == "ok"
