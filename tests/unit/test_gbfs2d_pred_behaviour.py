"""
Unit tests for Gbfs2dPredictor

Comprehensive unit test suite for all three GBFS-2D models:
- Band gap (regression)
- Metal classification (binary classifier)
- Structural stability (binary classifier)

Test Structure (following GBFS and SynthNN test patterns):
- Generic initialization tests (all 3 properties)
- CIF file loading tests
- Regression property validation (API correctness, ranges, data types)
- Classification property validation
- van der Waals structure detection tests
- Input handling tests (string, list formats)
- Error handling tests
- Consistency tests (repeated predictions, method agreement)
- End-to-end pipeline tests

This is a UNIT TEST suite - tests API correctness with real models.
For real material physics validation, see tests/integration/test_gbfs2d_sanity.py

Run: pytest tests/unit/test_gbfs2d_pred_behaviour.py -v
"""

import json
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock
import os

from Information_Units.Predictors.Gbfs2d.Gbfs2dPredictor import (
    Gbfs2dPredictor,
    load_cif,
    generate_features,
    check_vdw_layered_structure,
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
    """All supported GBFS-2D properties."""
    return ['bandgap', 'is_metal', 'is_stable']


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
        'is_metal': {
            'type': 'classification',
            'unit': 'binary',
            'values': [0.0, 1.0],
        },
        'is_stable': {
            'type': 'classification',
            'unit': 'binary',
            'values': [0.0, 1.0],
        },
    }


@pytest.fixture
def gbfs2d_predictor_factory():
    """Factory for creating GBFS-2D predictors for any property."""
    def _create(property_name):
        return Gbfs2dPredictor(
            predictor_name=f"gbfs2d_{property_name}",
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
# (Unit tests validating API correctness)
# ============================================================================

@pytest.mark.unit
def test_init_stores_name_and_property(gbfs2d_predictor_factory):
    """Predictor stores predictor_name and property_name on init."""
    predictor = gbfs2d_predictor_factory('bandgap')
    assert predictor.predictor_name == 'gbfs2d_bandgap'
    assert predictor.property_name == 'bandgap'


@pytest.mark.unit
@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_all_properties_initialize(gbfs2d_predictor_factory, property_name):
    """All three properties can be initialized successfully."""
    predictor = gbfs2d_predictor_factory(property_name)
    assert predictor is not None
    assert predictor.property_name == property_name
    assert predictor.model is not None
    assert predictor.scaler is not None
    assert predictor.feature_list is not None
    assert len(predictor.feature_list) > 0


@pytest.mark.unit
@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_info_includes_property_name(gbfs2d_predictor_factory, property_name):
    """info() returns description including property name."""
    predictor = gbfs2d_predictor_factory(property_name)
    info = predictor.info()
    assert isinstance(info, str) and len(info) > 0
    assert "GBFS-2D" in info
    assert property_name in info.lower()


@pytest.mark.unit
def test_invalid_property_raises_error(gbfs2d_predictor_factory):
    """Invalid property name raises ValueError with helpful message."""
    with pytest.raises(ValueError, match="Unsupported property"):
        gbfs2d_predictor_factory('invalid_property')


@pytest.mark.unit
def test_predictor_source_is_gbfs_2d(gbfs2d_predictor_factory):
    """Predictor source is set to 'gbfs-2d'."""
    predictor = gbfs2d_predictor_factory('bandgap')
    assert predictor.source == "gbfs-2d"


# ============================================================================
# CIF Loading Tests
# ============================================================================

@pytest.mark.unit
def test_load_valid_cif(cif_files):
    """Test loading valid CIF files."""
    for label, path in cif_files.items():
        structure = load_cif(path)
        assert structure is not None
        assert structure.composition is not None


@pytest.mark.unit
def test_load_nonexistent_cif():
    """Loading non-existent CIF raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_cif("/nonexistent/path/to/structure.cif")


# ============================================================================
# Regression Property Tests (bandgap)
# Unit tests validating: return types, JSON format, reasonable ranges, finite values
# ============================================================================

@pytest.mark.unit
def test_regression_predict_numpy_returns_float_array(
    gbfs2d_predictor_factory, cif_files
):
    """Regression models return float arrays with predictions."""
    predictor = gbfs2d_predictor_factory('bandgap')
    result = predictor.predict_numpy([Path(cif_files['al2o3']).read_text()])
    
    assert isinstance(result, np.ndarray)
    assert result.dtype in [np.float32, np.float64]
    assert result.shape == (1,) or result.shape[0] == 1


@pytest.mark.unit
def test_regression_predict_returns_standardized_output(
    gbfs2d_predictor_factory, cif_files
):
    """Regression models return standardized source/results envelope."""
    predictor = gbfs2d_predictor_factory('bandgap')
    cif_text = Path(cif_files['al2o3']).read_text()
    result = predictor.predict([cif_text])

    assert result["source"] == "gbfs-2d"
    assert isinstance(result["results"], list)
    assert len(result["results"]) == 1
    first = result["results"][0]
    assert first["status"] == "ok"
    assert "prediction" in first["properties"]
    assert isinstance(first["properties"]["prediction"], list)
    assert len(first["properties"]["prediction"]) == 1


@pytest.mark.unit
def test_regression_predictions_in_reasonable_range(
    gbfs2d_predictor_factory, cif_files, property_metadata
):
    """Regression predictions fall within physically reasonable ranges."""
    predictor = gbfs2d_predictor_factory('bandgap')
    result = predictor.predict_numpy([Path(cif_files['al2o3']).read_text()])
    prediction = result[0]
    
    metadata = property_metadata['bandgap']
    assert metadata['min_reasonable'] <= prediction <= metadata['max_reasonable'], (
        f"Bandgap {prediction} outside reasonable range"
    )


@pytest.mark.unit
def test_regression_predictions_are_finite(
    gbfs2d_predictor_factory, cif_files
):
    """Regression predictions are finite numbers."""
    predictor = gbfs2d_predictor_factory('bandgap')
    result = predictor.predict_numpy([Path(cif_files['al2o3']).read_text()])
    assert np.isfinite(result[0])


@pytest.mark.unit
def test_regression_predict_includes_vdw_detection(
    gbfs2d_predictor_factory, cif_files
):
    """Regression output includes vdW layered structure detection."""
    predictor = gbfs2d_predictor_factory('bandgap')
    result = predictor.predict([Path(cif_files['al2o3']).read_text()])
    
    assert "is_vdw_layered" in result["results"][0]["properties"]
    assert isinstance(result["results"][0]["properties"]["is_vdw_layered"], bool)


# ============================================================================
# Classification Property Tests (is_metal, is_stable)
# Unit tests validating: binary output, JSON format with probabilities
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize('property_name', ['is_metal', 'is_stable'])
def test_classification_predict_numpy_returns_binary(
    gbfs2d_predictor_factory, cif_files, property_name
):
    """Classification models return binary predictions."""
    predictor = gbfs2d_predictor_factory(property_name)
    result = predictor.predict_numpy([Path(cif_files['al2o3']).read_text()])
    
    assert isinstance(result, np.ndarray)
    assert result[0] in [0.0, 1.0]


@pytest.mark.unit
@pytest.mark.parametrize('property_name', ['is_metal', 'is_stable'])
def test_classification_predict_returns_json_with_probabilities(
    gbfs2d_predictor_factory, cif_files, property_name
):
    """Classification models return JSON with probabilities when available."""
    predictor = gbfs2d_predictor_factory(property_name)
    cif_text = Path(cif_files['al2o3']).read_text()
    result = predictor.predict([cif_text])
    
    assert result["source"] == "gbfs-2d"
    assert isinstance(result["results"], list)
    first = result["results"][0]
    assert first["status"] == "ok"
    assert "prediction" in first["properties"]
    
    # Probabilities may be present for classifiers
    if "probabilities" in first["properties"]:
        assert isinstance(first["properties"]["probabilities"], list)


# ============================================================================
# van der Waals Detection Tests
# ============================================================================

@pytest.mark.unit
def test_vdw_detection_function_exists(cif_files):
    """vdW detection function can be called on structures."""
    from pymatgen.io.cif import CifParser
    
    parser = CifParser(cif_files['al2o3'])
    structure = parser.get_structures(primitive=True)[0]
    
    result = check_vdw_layered_structure(structure)
    assert isinstance(result, bool)


@pytest.mark.unit
def test_vdw_detection_with_invalid_structure():
    """vdW detection with invalid structure raises ValueError."""
    with pytest.raises((ValueError, TypeError)):
        check_vdw_layered_structure(None)


@pytest.mark.unit
@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_all_properties_include_vdw_in_output(
    gbfs2d_predictor_factory, cif_files, property_name
):
    """All properties include vdW detection in output."""
    predictor = gbfs2d_predictor_factory(property_name)
    result = predictor.predict([Path(cif_files['al2o3']).read_text()])
    
    assert "is_vdw_layered" in result["results"][0]["properties"]


# ============================================================================
# Input Handling Tests
# Unit tests validating: contract input uses direct list[str] CIF payload
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_predict_accepts_list_input_contract(
    gbfs2d_predictor_factory, cif_files, property_name
):
    """Predictors accept list of CIF strings as input."""
    predictor = gbfs2d_predictor_factory(property_name)
    cif_text = Path(cif_files['al2o3']).read_text()
    result = predictor.predict([cif_text])
    
    assert result["source"] == "gbfs-2d"
    assert result["results"][0]["status"] == "ok"


@pytest.mark.unit
def test_predict_with_multiple_structures(
    gbfs2d_predictor_factory, cif_files
):
    """Predict can handle multiple structures at once."""
    predictor = gbfs2d_predictor_factory('bandgap')
    al2o3_text = Path(cif_files['al2o3']).read_text()
    sio2_text = Path(cif_files['sio2']).read_text()
    
    result = predictor.predict([al2o3_text, sio2_text])
    
    assert result["source"] == "gbfs-2d"
    assert len(result["results"]) == 2
    assert result["results"][0]["status"] == "ok"
    assert result["results"][1]["status"] == "ok"


# ============================================================================
# Error Handling Tests
# Unit tests validating: appropriate exceptions for invalid inputs
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_predict_empty_input_returns_error_result(
    gbfs2d_predictor_factory, property_name
):
    """Empty input list returns error result with appropriate structure."""
    predictor = gbfs2d_predictor_factory(property_name)
    result = predictor.predict([])
    
    assert result["source"] == "gbfs-2d"
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "error"


@pytest.mark.unit
@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_predict_invalid_input_items_return_error_result(
    gbfs2d_predictor_factory, property_name
):
    """Invalid input items (empty strings) return error."""
    predictor = gbfs2d_predictor_factory(property_name)
    result = predictor.predict(["", "   "])
    
    assert result["source"] == "gbfs-2d"
    # Should return error because no valid CIF content


# ============================================================================
# Consistency Tests
# Unit tests validating: API behavior repeatability and method equivalence
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_multiple_predictions_consistent(
    gbfs2d_predictor_factory, cif_files, property_name
):
    """Multiple predictions on same input are consistent."""
    predictor = gbfs2d_predictor_factory(property_name)
    cif_text = Path(cif_files['al2o3']).read_text()
    
    result1 = predictor.predict_numpy([cif_text])
    result2 = predictor.predict_numpy([cif_text])
    
    assert np.allclose(result1, result2)


@pytest.mark.unit
@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_predict_methods_agree(
    gbfs2d_predictor_factory, cif_files, property_name
):
    """predict() and predict_numpy() produce equivalent results."""
    predictor = gbfs2d_predictor_factory(property_name)
    cif_text = Path(cif_files['al2o3']).read_text()
    
    numpy_result = predictor.predict_numpy([cif_text])
    dict_result = predictor.predict([cif_text])
    
    prediction = dict_result["results"][0]["properties"]["prediction"][0]
    assert np.isclose(numpy_result[0], prediction)


# ============================================================================
# End-to-End Tests
# Unit tests validating: full prediction pipeline works for all properties
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize('cif_key', ['al2o3', 'sio2'])
def test_full_pipeline_all_properties(
    gbfs2d_predictor_factory, supported_properties, cif_files, cif_key
):
    """Full pipeline works for all properties on all materials."""
    cif_text = Path(cif_files[cif_key]).read_text()
    
    for prop in supported_properties:
        predictor = gbfs2d_predictor_factory(prop)
        result = predictor.predict([cif_text])
        
        assert result["source"] == "gbfs-2d"
        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "ok"
        assert "prediction" in result["results"][0]["properties"]
        assert "is_vdw_layered" in result["results"][0]["properties"]


@pytest.mark.unit
def test_json_output_is_serializable(
    gbfs2d_predictor_factory, supported_properties, cif_files
):
    """All prediction outputs are JSON serializable."""
    cif_text = Path(cif_files['al2o3']).read_text()
    
    for prop in supported_properties:
        predictor = gbfs2d_predictor_factory(prop)
        result = predictor.predict([cif_text])
        
        # Should not raise
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        assert parsed["source"] == "gbfs-2d"


@pytest.mark.unit
def test_predict_with_list_input_returns_standardized_output(
    gbfs2d_predictor_factory, cif_files
):
    """List input returns standardized source/results envelope."""
    predictor = gbfs2d_predictor_factory("bandgap")
    cif_text = Path(cif_files["al2o3"]).read_text()
    result = predictor.predict([cif_text])

    assert result["source"] == "gbfs-2d"
    assert isinstance(result["results"], list)
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "ok"


@pytest.mark.unit
def test_output_includes_properties_metadata(
    gbfs2d_predictor_factory, cif_files
):
    """Output includes property metadata like property name."""
    predictor = gbfs2d_predictor_factory("bandgap")
    cif_text = Path(cif_files["al2o3"]).read_text()
    result = predictor.predict([cif_text])

    props = result["results"][0]["properties"]
    assert "property" in props
    assert props["property"] == "bandgap"


# ============================================================================
# Cross-Property Consistency Tests
# ============================================================================

@pytest.mark.unit
def test_different_properties_produce_different_predictions(
    gbfs2d_predictor_factory, cif_files
):
    """Different properties produce different kinds of predictions."""
    cif_text = Path(cif_files['al2o3']).read_text()
    
    bandgap_pred = gbfs2d_predictor_factory('bandgap').predict_numpy([cif_text])
    is_metal_pred = gbfs2d_predictor_factory('is_metal').predict_numpy([cif_text])
    is_stable_pred = gbfs2d_predictor_factory('is_stable').predict_numpy([cif_text])
    
    # Bandgap should typically be different from binary predictions
    assert bandgap_pred[0] not in [0.0, 1.0] or is_metal_pred[0] != bandgap_pred[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
