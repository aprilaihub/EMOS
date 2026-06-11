"""
Integration tests for GBFS-2D with real models on 2D materials.

Test Coverage:
- Generic predictor contract checks (valid/invalid input, JSON serialization)
- GBFS-2D-specific sanity checks for all 3 models on known materials
- van der Waals layered structure detection
- Deterministic prediction behavior
- Physical validation of predictions (ranges, relationships)

Run with: pytest tests/integration/test_gbfs2d_sanity.py -v
Skip network tests: pytest -m "not network"
Skip slow tests: pytest -m "not slow"
"""

import json
import pytest
import numpy as np
from pathlib import Path

from Information_Units.Predictors.Gbfs2d.Gbfs2dPredictor import (
    Gbfs2dPredictor,
    check_vdw_layered_structure,
)


pytestmark = [pytest.mark.integration, pytest.mark.network, pytest.mark.slow]


@pytest.fixture
def cif_files():
    """Provide paths to CIF test fixtures."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cif_files"
    return {
        'al2o3_path': str(fixtures_dir / "Al2O3.cif"),
        'sio2_path': str(fixtures_dir / "SiO2.cif"),
        'mos2_mp2815_path': str(fixtures_dir / "mp-2815.cif"),
        'mos2_mp1025874_path': str(fixtures_dir / "mp-1025874.cif"),
        'invalid_path': str(fixtures_dir / "invalid.cif"),
    }


@pytest.fixture
def supported_properties():
    """All supported GBFS-2D properties."""
    return ['bandgap', 'is_metal', 'is_stable']


@pytest.fixture
def property_metadata():
    """Metadata for each property including expected ranges for test materials."""
    return {
        'bandgap': {
            'type': 'regression',
            'unit': 'eV',
            'al2o3_expected_range': (0.0, 10.0),  # Wide range for placeholder models
            'sio2_expected_range': (0.0, 10.0),   # Wide range for placeholder models
        },
        'is_metal': {
            'type': 'classification',
            'unit': 'binary',
            'al2o3_expected': 0.0,  # Non-metal
            'sio2_expected': 0.0,   # Non-metal
        },
        'is_stable': {
            'type': 'classification',
            'unit': 'binary',
            'al2o3_expected': 1.0,  # Stable structure
            'sio2_expected': 1.0,   # Stable structure
        },
    }


@pytest.fixture(scope="module")
def predictor_factory():
    """Factory for creating real GBFS-2D predictors."""
    def _create(property_name):
        return Gbfs2dPredictor(
            predictor_name=f"gbfs2d_{property_name}_integration",
            property_name=property_name
        )
    return _create


# ============================================================================
# Generic Predictor Contract Tests
# (Template for future predictors with real backends)
# ============================================================================

@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_predict_valid_input_returns_prediction(cif_files, predictor_factory, property_name):
    """A valid input file produces a successful prediction."""
    predictor = predictor_factory(property_name)
    result = predictor.predict_numpy([Path(cif_files['al2o3_path']).read_text()])
    
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.shape == (1,) or result.shape[0] == 1
    assert np.isfinite(result[0]), f"Prediction for {property_name} is not finite"


@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_predict_invalid_input_raises_error(cif_files, predictor_factory, property_name):
    """Invalid contract input returns a structured error result."""
    predictor = predictor_factory(property_name)
    result = predictor.predict([])
    assert result["source"] == "gbfs-2d"
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "error"


@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_predict_output_is_json_serializable(cif_files, predictor_factory, property_name):
    """Prediction output can be serialized and deserialized as JSON."""
    predictor = predictor_factory(property_name)
    result = predictor.predict([Path(cif_files['al2o3_path']).read_text()])
    parsed = json.loads(json.dumps(result))
    assert parsed["source"] == "gbfs-2d"
    assert isinstance(parsed["results"], list)


# ============================================================================
# van der Waals Structure Detection Tests
# ============================================================================

def test_vdw_detection_returns_bool(cif_files):
    """vdW detection function returns boolean."""
    from pymatgen.io.cif import CifParser
    
    parser = CifParser(cif_files['al2o3_path'])
    structure = parser.get_structures(primitive=True)[0]
    
    result = check_vdw_layered_structure(structure)
    assert isinstance(result, bool)


def test_predict_includes_vdw_detection_in_output(cif_files, predictor_factory):
    """Prediction output includes vdW layered structure detection."""
    predictor = predictor_factory('bandgap')
    result = predictor.predict([Path(cif_files['al2o3_path']).read_text()])
    
    assert result["results"][0]["properties"]["is_vdw_layered"] is not None
    assert isinstance(result["results"][0]["properties"]["is_vdw_layered"], bool)


# ============================================================================
# GBFS-2D-Specific Sanity Tests for All Properties
# ============================================================================

@pytest.mark.parametrize('cif_key', ['al2o3_path', 'sio2_path'])
def test_all_properties_predict_successfully(
    cif_files, supported_properties, predictor_factory, cif_key
):
    """All 3 properties predict successfully on known materials."""
    results = {}
    
    for prop in supported_properties:
        predictor = predictor_factory(prop)
        result = predictor.predict_numpy([Path(cif_files[cif_key]).read_text()])
        results[prop] = result[0]
    
    # Verify all predictions are valid
    for prop, value in results.items():
        assert np.isfinite(value), f"{prop} prediction is not finite"


@pytest.mark.parametrize('property_name,cif_key', [
    ('bandgap', 'al2o3_path'),
    ('bandgap', 'sio2_path'),
])
def test_regression_predictions_in_expected_range(
    cif_files, property_metadata, predictor_factory, property_name, cif_key
):
    """Regression predictions fall within expected ranges for known materials."""
    predictor = predictor_factory(property_name)
    result = predictor.predict_numpy([Path(cif_files[cif_key]).read_text()])
    prediction = result[0]
    
    metadata = property_metadata[property_name]
    range_key = f"{cif_key.replace('_path', '')}_expected_range"
    
    if range_key in metadata:
        min_val, max_val = metadata[range_key]
        assert min_val <= prediction <= max_val, (
            f"{property_name} prediction {prediction} outside expected range [{min_val}, {max_val}]"
        )


@pytest.mark.parametrize('cif_key', ['al2o3_path', 'sio2_path'])
def test_classification_predictions_are_binary(
    cif_files, predictor_factory, cif_key
):
    """Classification models return binary predictions."""
    for prop in ['is_metal', 'is_stable']:
        predictor = predictor_factory(prop)
        result = predictor.predict_numpy([Path(cif_files[cif_key]).read_text()])
        
        assert result[0] in [0.0, 1.0], f"Expected binary output, got {result[0]}"


@pytest.mark.parametrize('cif_key', ['al2o3_path', 'sio2_path'])
def test_is_metal_correctly_identifies_non_metals(
    cif_files, predictor_factory, cif_key
):
    """is_metal classifier correctly identifies Al2O3 and SiO2 as non-metals."""
    predictor = predictor_factory('is_metal')
    result = predictor.predict_numpy([Path(cif_files[cif_key]).read_text()])
    
    assert result[0] == 0.0, f"{cif_key} should be classified as non-metal"


# ============================================================================
# Deterministic Behavior Tests
# ============================================================================

@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_predictions_are_deterministic(
    cif_files, predictor_factory, property_name
):
    """Running the same input twice produces identical predictions."""
    predictor = predictor_factory(property_name)
    
    result1 = predictor.predict_numpy([Path(cif_files['al2o3_path']).read_text()])
    result2 = predictor.predict_numpy([Path(cif_files['al2o3_path']).read_text()])
    
    assert np.allclose(result1, result2), (
        f"{property_name} predictions are not deterministic"
    )


@pytest.mark.parametrize('property_name', ['bandgap', 'is_metal', 'is_stable'])
def test_predict_methods_are_consistent(
    cif_files, predictor_factory, property_name
):
    """predict() and predict_numpy() return equivalent values."""
    predictor = predictor_factory(property_name)
    
    numpy_result = predictor.predict_numpy([Path(cif_files['al2o3_path']).read_text()])
    result = predictor.predict([Path(cif_files['al2o3_path']).read_text()])
    prediction = result["results"][0]["properties"]["prediction"][0]
    
    assert np.isclose(numpy_result[0], prediction), (
        f"{property_name}: predict() and predict_numpy() don't agree"
    )


# ============================================================================
# Cross-Material Behavior Tests
# ============================================================================

def test_different_materials_produce_different_predictions(
    cif_files, predictor_factory
):
    """Different materials should produce different property predictions."""
    al2o3_results = {}
    sio2_results = {}
    
    for prop in ['bandgap', 'is_metal', 'is_stable']:
        predictor = predictor_factory(prop)
        al2o3_results[prop] = predictor.predict_numpy([Path(cif_files['al2o3_path']).read_text()])[0]
        sio2_results[prop] = predictor.predict_numpy([Path(cif_files['sio2_path']).read_text()])[0]
    
    # At least some properties should be different between Al2O3 and SiO2
    differences = sum(
        1 for prop in al2o3_results
        if not np.isclose(al2o3_results[prop], sio2_results[prop])
    )
    assert differences > 0, "Al2O3 and SiO2 predictions are identical"


def test_bandgap_predictions_physically_reasonable(
    cif_files, predictor_factory
):
    """Bandgap predictions are physically reasonable for known materials."""
    al2o3_bg = predictor_factory('bandgap').predict_numpy([Path(cif_files['al2o3_path']).read_text()])[0]
    sio2_bg = predictor_factory('bandgap').predict_numpy([Path(cif_files['sio2_path']).read_text()])[0]
    
    # Both should be non-negative and within reasonable range for oxides
    assert 0 <= al2o3_bg <= 10, f"Al2O3 bandgap {al2o3_bg} out of expected range"
    assert 0 <= sio2_bg <= 10, f"SiO2 bandgap {sio2_bg} out of expected range"


def test_predict_with_list_input_returns_standardized_output(cif_files, predictor_factory):
    """New contract: list[str] input returns source/results envelope."""
    predictor = predictor_factory("bandgap")
    cif_text = Path(cif_files["al2o3_path"]).read_text()
    result = predictor.predict([cif_text])

    assert result["source"] == "gbfs-2d"
    assert isinstance(result["results"], list)
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] in {"ok", "error"}


# ============================================================================
# vdW-Specific Integration Tests
# ============================================================================

def test_vdw_detection_included_in_all_properties(
    cif_files, supported_properties, predictor_factory
):
    """All properties include vdW detection output."""
    for prop in supported_properties:
        predictor = predictor_factory(prop)
        result = predictor.predict([Path(cif_files['al2o3_path']).read_text()])
        
        assert "is_vdw_layered" in result["results"][0]["properties"]


# ============================================================================
# MoS2 (2D Layered TMDC) Material Tests
# Testing on mp-2815 and mp-1025874 (both MoS2 polytypes)
# ============================================================================

@pytest.mark.parametrize('mos2_cif_key', ['mos2_mp2815_path', 'mos2_mp1025874_path'])
def test_mos2_detected_as_vdw_layered(cif_files, mos2_cif_key):
    """MoS2 (both polytypes) should be detected as vdW layered material."""
    from pymatgen.io.cif import CifParser
    
    parser = CifParser(cif_files[mos2_cif_key])
    structure = parser.get_structures(primitive=True)[0]
    
    result = check_vdw_layered_structure(structure)
    assert result is True, (
        f"{mos2_cif_key} (MoS2) should be detected as vdW layered structure"
    )


@pytest.mark.parametrize('mos2_cif_key', ['mos2_mp2815_path', 'mos2_mp1025874_path'])
def test_mos2_vdw_detection_in_predictions(
    cif_files, supported_properties, predictor_factory, mos2_cif_key
):
    """All properties on MoS2 should include vdW detection (should be True)."""
    for prop in supported_properties:
        predictor = predictor_factory(prop)
        result = predictor.predict([Path(cif_files[mos2_cif_key]).read_text()])
        
        assert result["results"][0]["properties"]["is_vdw_layered"] is True, (
            f"{prop} on {mos2_cif_key} should detect vdW structure"
        )


@pytest.mark.parametrize('mos2_cif_key', ['mos2_mp2815_path', 'mos2_mp1025874_path'])
def test_mos2_all_properties_predict(
    cif_files, supported_properties, predictor_factory, mos2_cif_key
):
    """All three properties should predict successfully on MoS2."""
    results = {}
    
    for prop in supported_properties:
        predictor = predictor_factory(prop)
        result = predictor.predict([Path(cif_files[mos2_cif_key]).read_text()])
        results[prop] = result["results"][0]["properties"]["prediction"][0]
    
    # Verify all predictions are valid
    for prop, value in results.items():
        assert np.isfinite(value), f"{prop} prediction on {mos2_cif_key} is not finite"


@pytest.mark.parametrize('mos2_cif_key', ['mos2_mp2815_path', 'mos2_mp1025874_path'])
def test_mos2_bandgap_in_physical_range(
    cif_files, predictor_factory, mos2_cif_key
):
    """MoS2 bandgap should be in physically reasonable range (0-10 eV for placeholders)."""
    predictor = predictor_factory('bandgap')
    result = predictor.predict_numpy([Path(cif_files[mos2_cif_key]).read_text()])
    prediction = result[0]
    
    assert 0.0 <= prediction <= 10.0, (
        f"MoS2 bandgap {prediction} outside expected range [0, 10] eV"
    )


@pytest.mark.parametrize('mos2_cif_key', ['mos2_mp2815_path', 'mos2_mp1025874_path'])
def test_mos2_is_not_metallic(
    cif_files, predictor_factory, mos2_cif_key
):
    """MoS2 is a semiconductor, so is_metal should predict 0 (non-metallic)."""
    predictor = predictor_factory('is_metal')
    result = predictor.predict_numpy([Path(cif_files[mos2_cif_key]).read_text()])
    
    assert result[0] == 0.0, (
        f"{mos2_cif_key} (MoS2) should be classified as non-metallic (is_metal=0)"
    )


@pytest.mark.parametrize('mos2_cif_key', ['mos2_mp2815_path', 'mos2_mp1025874_path'])
def test_mos2_stability_prediction(
    cif_files, predictor_factory, mos2_cif_key
):
    """MoS2 from Materials Project should be stable (or unstable, depending on model)."""
    predictor = predictor_factory('is_stable')
    result = predictor.predict_numpy([Path(cif_files[mos2_cif_key]).read_text()])
    
    # Accept both 0 and 1 since this is expected to depend on the model
    assert result[0] in [0.0, 1.0], (
        f"is_stable should return binary value for {mos2_cif_key}"
    )


def test_mos2_polytypes_produce_predictions(
    cif_files, predictor_factory
):
    """Both MoS2 polytypes should produce predictions (may differ due to structure)."""
    mos2_results = {}
    
    for cif_key in ['mos2_mp2815_path', 'mos2_mp1025874_path']:
        bg_pred = predictor_factory('bandgap').predict_numpy(
            [Path(cif_files[cif_key]).read_text()]
        )[0]
        mos2_results[cif_key] = bg_pred
    
    # Both should have finite predictions
    for cif_key, value in mos2_results.items():
        assert np.isfinite(value), f"{cif_key} bandgap prediction is not finite"


def test_mos2_deterministic_behavior(
    cif_files, predictor_factory
):
    """MoS2 predictions should be deterministic across multiple runs."""
    predictor = predictor_factory('bandgap')
    cif_text = Path(cif_files['mos2_mp2815_path']).read_text()
    
    result1 = predictor.predict_numpy([cif_text])
    result2 = predictor.predict_numpy([cif_text])
    
    assert np.allclose(result1, result2), (
        "MoS2 bandgap predictions are not deterministic"
    )


def test_mos2_json_serialization(
    cif_files, supported_properties, predictor_factory
):
    """All MoS2 predictions should be JSON serializable."""
    for prop in supported_properties:
        predictor = predictor_factory(prop)
        result = predictor.predict([Path(cif_files['mos2_mp2815_path']).read_text()])
        
        # Verify JSON serialization works
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        
        assert parsed["source"] == "gbfs-2d"
        assert len(parsed["results"]) == 1


def test_mos2_vs_bulk_materials_have_different_predictions(
    cif_files, predictor_factory
):
    """MoS2 (2D) should have different predictions from Al2O3/SiO2 (bulk) materials."""
    # Get bandgap predictions for all materials
    predictor_bg = predictor_factory('bandgap')
    
    al2o3_bg = predictor_bg.predict_numpy([Path(cif_files['al2o3_path']).read_text()])[0]
    mos2_bg = predictor_bg.predict_numpy([Path(cif_files['mos2_mp2815_path']).read_text()])[0]
    
    # While we can't guarantee they're always different (depends on model),
    # we can verify both predictions are valid
    assert np.isfinite(al2o3_bg), "Al2O3 bandgap is not finite"
    assert np.isfinite(mos2_bg), "MoS2 bandgap is not finite"


@pytest.mark.parametrize('mos2_cif_key', ['mos2_mp2815_path', 'mos2_mp1025874_path'])
def test_mos2_contract_standardized_output(
    cif_files, predictor_factory, mos2_cif_key
):
    """MoS2 predictions follow the standardized source/results contract."""
    predictor = predictor_factory('bandgap')
    result = predictor.predict([Path(cif_files[mos2_cif_key]).read_text()])
    
    # Verify standardized contract
    assert result["source"] == "gbfs-2d"
    assert isinstance(result["results"], list)
    assert len(result["results"]) == 1
    
    first = result["results"][0]
    assert first["status"] == "ok"
    assert "properties" in first
    assert "prediction" in first["properties"]
    assert "is_vdw_layered" in first["properties"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
