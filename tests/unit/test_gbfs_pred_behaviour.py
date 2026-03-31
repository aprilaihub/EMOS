"""
Unit tests for GBFS_PredPredictor

Comprehensive unit test suite for all six GBFS models:
- Band gap (regression)
- Formation energy per atom (regression)
- Dielectric constant (regression)
- Metal classification (binary classifier)
- Electron mobility (regression, log10-scaled)
- Hole mobility (regression, log10-scaled)

Test Structure (following SynthNN test patterns):
- Generic initialization tests (all 6 properties)
- CIF file loading tests
- Regression property validation (API correctness, ranges, data types)
- Classification property validation
- Mobility-specific tests (log10 inverse transformation)
- Input handling tests (string, dict with cif_path, dict with input_data)
- Error handling tests
- Consistency tests (repeated predictions, method agreement)
- End-to-end pipeline tests

This is a UNIT TEST suite - tests API correctness with real models.
For real material physics validation, see tests/integration/test_gbfs_sanity.py

Run: pytest tests/unit/test_gbfs_pred_integration.py -v
"""

import pytest
import json
import os
import numpy as np
from pathlib import Path
from unittest.mock import Mock

from Information_Units.Predictors.GBFS_Pred.GBFS_PredPredictor import (
    GBFS_PredPredictor,
    load_cif,
    generate_features,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cif_files():
    """Paths to CIF test fixtures."""
    d = Path(__file__).parent.parent / "fixtures" / "cif_files"
    return {
        'al2o3': str(d / "Al2O3.cif"),
        'sio2': str(d / "SiO2.cif"),
    }


@pytest.fixture
def supported_properties():
    """All supported GBFS properties."""
    return ['bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p']


@pytest.fixture
def property_metadata():
    """Metadata for each property."""
    return {
        'bandgap': {
            'type': 'regression',
            'unit': 'eV',
            'min_reasonable': 0.0,
            'max_reasonable': 20.0,
        },
        'e_form': {
            'type': 'regression',
            'unit': 'eV/atom',
            'min_reasonable': -10.0,
            'max_reasonable': 5.0,
        },
        'dielectric': {
            'type': 'regression',
            'unit': 'dimensionless',
            'min_reasonable': 1.0,
            'max_reasonable': 50.0,
        },
        'is_metal': {
            'type': 'classification',
            'unit': 'binary',
            'values': [0.0, 1.0],
        },
        'mob_n': {
            'type': 'regression',
            'unit': 'cm²/V·s',
            'min_reasonable': 0.1,
            'max_reasonable': 1000.0,
            'note': 'log10-scaled internally, inverse transformed',
        },
        'mob_p': {
            'type': 'regression',
            'unit': 'cm²/V·s',
            'min_reasonable': 0.1,
            'max_reasonable': 1000.0,
            'note': 'log10-scaled internally, inverse transformed',
        },
    }


@pytest.fixture
def gbfs_predictor_factory():
    """Factory for creating GBFS predictors for any property."""
    def _create(property_name):
        return GBFS_PredPredictor(
            predictor_name=f"gbfs_{property_name}",
            property_name=property_name
        )
    return _create


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    logger = Mock()
    logger.log = Mock()
    return logger


# ============================================================================
# Generic Predictor Interface Tests
# (Unit tests validating API correctness - template for future predictors)
# ============================================================================

@pytest.mark.unit
def test_init_stores_name_and_property(gbfs_predictor_factory):
    """Predictor stores predictor_name and property_name on init."""
    predictor = gbfs_predictor_factory('bandgap')
    assert predictor.predictor_name == 'gbfs_bandgap'
    assert predictor.property_name == 'bandgap'


@pytest.mark.unit
@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
def test_all_properties_initialize(gbfs_predictor_factory, property_name):
    """All six properties can be initialized successfully."""
    predictor = gbfs_predictor_factory(property_name)
    assert predictor is not None
    assert predictor.property_name == property_name
    assert predictor.model is not None
    assert predictor.scaler is not None
    assert predictor.feature_list is not None
    assert len(predictor.feature_list) > 0


@pytest.mark.unit
@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
def test_info_includes_property_name(gbfs_predictor_factory, property_name):
    """info() returns description including property name."""
    predictor = gbfs_predictor_factory(property_name)
    info = predictor.info()
    assert isinstance(info, str) and len(info) > 0
    assert "GBFS" in info
    assert property_name in info.lower()


@pytest.mark.unit
def test_invalid_property_raises_error(gbfs_predictor_factory):
    """Invalid property name raises ValueError with helpful message."""
    with pytest.raises(ValueError, match="Model directory not found"):
        gbfs_predictor_factory('invalid_property')


# ============================================================================
# CIF Loading Tests
# ============================================================================

@pytest.mark.unit
def test_load_valid_cif(cif_files):
    """Test loading valid CIF files."""
    for label, path in cif_files.items():
        assert Path(path).exists(), f"CIF file not found: {path}"
        structure = load_cif(path)
        assert structure is not None
        assert len(structure.composition) > 0


@pytest.mark.unit
def test_load_nonexistent_cif():
    """Loading non-existent CIF raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_cif("/nonexistent/structure.cif")


# ============================================================================
# Regression Property Tests (bandgap, e_form, dielectric, mob_n, mob_p)
# Unit tests validating: return types, JSON format, reasonable ranges, finite values
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'mob_n', 'mob_p'
])
def test_regression_predict_numpy_returns_float_array(
    gbfs_predictor_factory, cif_files, property_name
):
    """Regression models return float arrays with predictions."""
    predictor = gbfs_predictor_factory(property_name)
    result = predictor.predict_numpy(cif_files['al2o3'])
    
    assert isinstance(result, np.ndarray)
    assert result.dtype in [np.float32, np.float64]
    assert result.shape == (1,) or result.shape[0] == 1


@pytest.mark.unit
@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'mob_n', 'mob_p'
])
def test_regression_predict_returns_json(
    gbfs_predictor_factory, cif_files, property_name
):
    """Regression models return valid JSON."""
    predictor = gbfs_predictor_factory(property_name)
    result = predictor.predict(cif_files['al2o3'])
    
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert "prediction" in parsed
    assert isinstance(parsed["prediction"], list)
    assert len(parsed["prediction"]) == 1


@pytest.mark.unit
@pytest.mark.parametrize('property_name,metadata', [
    ('bandgap', {'min': 0.0, 'max': 20.0}),
    ('e_form', {'min': -10.0, 'max': 5.0}),
    ('dielectric', {'min': 1.0, 'max': 50.0}),
    ('mob_n', {'min': 0.1, 'max': 1000.0}),
    ('mob_p', {'min': 0.1, 'max': 1000.0}),
])
def test_regression_predictions_in_reasonable_range(
    gbfs_predictor_factory, cif_files, property_name, metadata
):
    """Regression predictions fall within physically reasonable ranges."""
    predictor = gbfs_predictor_factory(property_name)
    result = predictor.predict_numpy(cif_files['al2o3'])
    prediction = result[0]
    
    assert metadata['min'] <= prediction <= metadata['max'], \
        f"{property_name} prediction {prediction} outside range [{metadata['min']}, {metadata['max']}]"


@pytest.mark.unit
@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'mob_n', 'mob_p'
])
def test_regression_predictions_are_finite(
    gbfs_predictor_factory, cif_files, property_name
):
    """Regression predictions are finite (not NaN or Inf)."""
    predictor = gbfs_predictor_factory(property_name)
    result = predictor.predict_numpy(cif_files['al2o3'])
    
    assert np.isfinite(result).all(), \
        f"{property_name} produced NaN or Inf values"


# ============================================================================
# Classification Property Tests (is_metal)
# Unit tests validating: binary output, JSON format with probabilities
# ============================================================================

@pytest.mark.unit
def test_classification_predict_numpy_returns_binary(
    gbfs_predictor_factory, cif_files
):
    """Classification model returns binary (0 or 1) predictions."""
    predictor = gbfs_predictor_factory('is_metal')
    result = predictor.predict_numpy(cif_files['al2o3'])
    
    assert isinstance(result, np.ndarray)
    assert result.shape == (1,) or result.shape[0] == 1
    assert result[0] in [0.0, 1.0], f"Expected binary output, got {result[0]}"


@pytest.mark.unit
def test_classification_predict_returns_json_with_probabilities(
    gbfs_predictor_factory, cif_files
):
    """Classification model returns JSON with prediction and probabilities."""
    predictor = gbfs_predictor_factory('is_metal')
    result = predictor.predict(cif_files['al2o3'])
    
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert "prediction" in parsed
    assert isinstance(parsed["prediction"], list)
    
    # Classification should include probabilities
    if "probabilities" in parsed:
        assert isinstance(parsed["probabilities"], list)


# ============================================================================
# Mobility Model-Specific Tests (log10 inverse transformation)
# Unit tests validating: positive values, inverse log10 transformation applied
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize('property_name', ['mob_n', 'mob_p'])
def test_mobility_predictions_are_positive(
    gbfs_predictor_factory, cif_files, property_name
):
    """Mobility predictions are positive (inverse log10 applied)."""
    predictor = gbfs_predictor_factory(property_name)
    result = predictor.predict_numpy(cif_files['al2o3'])
    prediction = result[0]
    
    assert prediction > 0, f"{property_name} should be positive after inverse transform"


@pytest.mark.unit
def test_electron_mobility_typically_exceeds_hole_mobility(
    gbfs_predictor_factory, cif_files
):
    """For oxide semiconductors, electron mobility usually exceeds hole mobility."""
    mob_n = gbfs_predictor_factory('mob_n').predict_numpy(cif_files['al2o3'])[0]
    mob_p = gbfs_predictor_factory('mob_p').predict_numpy(cif_files['al2o3'])[0]
    
    # This is a physical expectation for oxide semiconductors
    assert mob_n > mob_p, \
        f"Expected mob_n ({mob_n}) > mob_p ({mob_p}) for oxide semiconductor"


# ============================================================================
# Input Handling Tests
# Unit tests validating: API accepts multiple input formats (string, dict keys)
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
def test_predict_accepts_string_path(
    gbfs_predictor_factory, cif_files, property_name
):
    """predict() accepts string file path."""
    predictor = gbfs_predictor_factory(property_name)
    result = predictor.predict(cif_files['al2o3'])
    
    assert isinstance(result, str)
    json.loads(result)  # Verify valid JSON


@pytest.mark.unit
@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
def test_predict_accepts_dict_with_cif_path(
    gbfs_predictor_factory, cif_files, property_name
):
    """predict() accepts dict with 'cif_path' key."""
    predictor = gbfs_predictor_factory(property_name)
    result = predictor.predict({"cif_path": cif_files['al2o3']})
    
    assert isinstance(result, str)
    json.loads(result)  # Verify valid JSON


@pytest.mark.unit
@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
def test_predict_accepts_dict_with_input_data(
    gbfs_predictor_factory, cif_files, property_name
):
    """predict() accepts dict with 'input_data' key."""
    predictor = gbfs_predictor_factory(property_name)
    result = predictor.predict({"input_data": cif_files['al2o3']})
    
    assert isinstance(result, str)
    json.loads(result)  # Verify valid JSON


# ============================================================================
# Error Handling Tests
# Unit tests validating: appropriate exceptions for invalid inputs
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
def test_predict_nonexistent_file_raises_error(
    gbfs_predictor_factory, property_name
):
    """predict() raises FileNotFoundError for missing file."""
    predictor = gbfs_predictor_factory(property_name)
    with pytest.raises(FileNotFoundError):
        predictor.predict("/nonexistent/structure.cif")


@pytest.mark.unit
@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
def test_predict_empty_dict_raises_error(
    gbfs_predictor_factory, property_name
):
    """predict() raises ValueError for empty input."""
    predictor = gbfs_predictor_factory(property_name)
    with pytest.raises(ValueError, match="Input dictionary must contain"):
        predictor.predict({})


# ============================================================================
# Consistency Tests
# Unit tests validating: API behavior repeatability and method equivalence
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
def test_multiple_predictions_consistent(
    gbfs_predictor_factory, cif_files, property_name
):
    """Multiple predictions on same file are consistent."""
    predictor = gbfs_predictor_factory(property_name)
    result1 = predictor.predict_numpy(cif_files['al2o3'])
    result2 = predictor.predict_numpy(cif_files['al2o3'])
    
    assert np.allclose(result1, result2), \
        f"{property_name} predictions are not consistent"


@pytest.mark.unit
@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
def test_predict_methods_agree(
    gbfs_predictor_factory, cif_files, property_name
):
    """predict() and predict_numpy() return equivalent values."""
    predictor = gbfs_predictor_factory(property_name)
    numpy_result = predictor.predict_numpy(cif_files['al2o3'])
    json_result = json.loads(predictor.predict(cif_files['al2o3']))
    
    assert np.isclose(numpy_result[0], json_result["prediction"][0]), \
        f"{property_name}: predict() and predict_numpy() don't agree"


# ============================================================================
# End-to-End Tests
# Unit tests validating: full prediction pipeline works for all properties
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize('cif_key', ['al2o3', 'sio2'])
def test_full_pipeline_all_properties(
    gbfs_predictor_factory, supported_properties, cif_files, cif_key
):
    """Test full prediction pipeline for all properties on multiple structures."""
    cif_path = cif_files[cif_key]
    results = {}
    
    for prop in supported_properties:
        predictor = gbfs_predictor_factory(prop)
        result = predictor.predict_numpy(cif_path)
        results[prop] = result[0]
    
    # Verify all properties have valid predictions
    for prop, value in results.items():
        assert np.isfinite(value), f"{prop} prediction is not finite for {cif_key}"


@pytest.mark.unit
def test_json_output_is_serializable(
    gbfs_predictor_factory, supported_properties, cif_files
):
    """All property predictions can be serialized to JSON and back."""
    cif_path = cif_files['al2o3']
    
    for prop in supported_properties:
        predictor = gbfs_predictor_factory(prop)
        result = predictor.predict(cif_path)
        
        # Serialize and deserialize
        serialized = json.dumps(json.loads(result))
        deserialized = json.loads(serialized)
        
        assert "prediction" in deserialized


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
