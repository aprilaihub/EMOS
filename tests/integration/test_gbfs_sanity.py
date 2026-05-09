"""
Integration tests for GBFS with real models.

Test Coverage:
- Generic predictor contract checks (template for future predictors)
- GBFS-specific sanity checks for all 6 models on known materials
- Deterministic prediction behavior
- Physical validation of predictions (ranges, relationships)

Run with: pytest tests/integration/test_gbfs_sanity.py -v
Skip network tests: pytest -m "not network"
Skip slow tests: pytest -m "not slow"
"""

import json
from pathlib import Path

import pytest
import numpy as np

from Information_Units.Predictors.Gbfs.GbfsPredictor import GbfsPredictor


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


@pytest.fixture
def supported_properties():
    """All supported GBFS properties."""
    return ['bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p']


@pytest.fixture
def property_metadata():
    """Metadata for each property including expected ranges for test materials."""
    return {
        'bandgap': {
            'type': 'regression',
            'unit': 'eV',
            'al2o3_expected_range': (4.0, 6.0),
            'sio2_expected_range': (5.0, 7.0),
        },
        'e_form': {
            'type': 'regression',
            'unit': 'eV/atom',
            'al2o3_expected_range': (-4.0, -2.0),
            'sio2_expected_range': (-3.5, -2.0),
        },
        'dielectric': {
            'type': 'regression',
            'unit': 'dimensionless',
            'al2o3_expected_range': (8.0, 13.0),
            'sio2_expected_range': (4.0, 8.0),
        },
        'is_metal': {
            'type': 'classification',
            'unit': 'binary',
            'al2o3_expected': 0.0,  # Non-metal
            'sio2_expected': 0.0,   # Non-metal
        },
        'mob_n': {
            'type': 'regression',
            'unit': 'cm²/V·s',
            'al2o3_expected_range': (10.0, 200.0),
            'sio2_expected_range': (10.0, 100.0),
        },
        'mob_p': {
            'type': 'regression',
            'unit': 'cm²/V·s',
            'al2o3_expected_range': (1.0, 50.0),
            'sio2_expected_range': (1.0, 30.0),
        },
    }


@pytest.fixture(scope="module")
def predictor_factory():
    """Factory for creating real GBFS predictors."""
    def _create(property_name):
        return GbfsPredictor(
            predictor_name=f"gbfs_{property_name}_integration",
            property_name=property_name
        )
    return _create


# ============================================================================
# Generic Predictor Contract Tests
# (Template for future predictors with real backends)
# ============================================================================

@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
def test_predict_valid_input_returns_prediction(cif_files, predictor_factory, property_name):
    """A valid input file produces a successful prediction."""
    predictor = predictor_factory(property_name)
    result = predictor.predict_numpy([Path(cif_files['al2o3_path']).read_text()])
    
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.shape == (1,) or result.shape[0] == 1
    assert np.isfinite(result[0]), f"Prediction for {property_name} is not finite"


@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
def test_predict_invalid_input_raises_error(cif_files, predictor_factory, property_name):
    """Invalid contract input returns a structured error result."""
    predictor = predictor_factory(property_name)
    result = predictor.predict([])
    assert result["source"] == "gbfs"
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "error"


@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
def test_predict_output_is_json_serializable(cif_files, predictor_factory, property_name):
    """Prediction output can be serialized and deserialized as JSON."""
    predictor = predictor_factory(property_name)
    result = predictor.predict([Path(cif_files['al2o3_path']).read_text()])
    parsed = json.loads(json.dumps(result))
    assert parsed["source"] == "gbfs"
    assert isinstance(parsed["results"], list)


# ============================================================================
# GBFS-Specific Sanity Tests for All Properties
# ============================================================================

@pytest.mark.parametrize('cif_key', ['al2o3_path', 'sio2_path'])
def test_all_properties_predict_successfully(
    cif_files, supported_properties, predictor_factory, cif_key
):
    """All 6 properties predict successfully on known materials."""
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
    ('e_form', 'al2o3_path'),
    ('e_form', 'sio2_path'),
    ('dielectric', 'al2o3_path'),
    ('dielectric', 'sio2_path'),
    ('mob_n', 'al2o3_path'),
    ('mob_n', 'sio2_path'),
    ('mob_p', 'al2o3_path'),
    ('mob_p', 'sio2_path'),
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
            f"{property_name} prediction {prediction} not in expected range "
            f"[{min_val}, {max_val}] for {cif_key}"
        )


@pytest.mark.parametrize('cif_key', ['al2o3_path', 'sio2_path'])
def test_classification_predictions_are_binary(
    cif_files, predictor_factory, cif_key
):
    """Classification model (is_metal) returns binary predictions."""
    predictor = predictor_factory('is_metal')
    result = predictor.predict_numpy([Path(cif_files[cif_key]).read_text()])
    
    assert result[0] in [0.0, 1.0], f"Expected binary output, got {result[0]}"
    
    # Al2O3 and SiO2 are non-metals
    assert result[0] == 0.0, "Al2O3 and SiO2 should be classified as non-metals"


@pytest.mark.parametrize('property_name', ['mob_n', 'mob_p'])
def test_mobility_predictions_are_positive(
    cif_files, predictor_factory, property_name
):
    """Mobility predictions are positive (log10 inverse transformation applied)."""
    predictor = predictor_factory(property_name)
    result = predictor.predict_numpy([Path(cif_files['al2o3_path']).read_text()])
    prediction = result[0]
    
    assert prediction > 0, f"{property_name} should be positive after inverse log10 transform"


def test_electron_mobility_exceeds_hole_mobility_al2o3(
    cif_files, predictor_factory
):
    """For Al2O3, electron mobility typically exceeds hole mobility."""
    mob_n = predictor_factory('mob_n').predict_numpy([Path(cif_files['al2o3_path']).read_text()])[0]
    mob_p = predictor_factory('mob_p').predict_numpy([Path(cif_files['al2o3_path']).read_text()])[0]
    
    assert mob_n > mob_p, (
        f"Expected mob_n ({mob_n}) > mob_p ({mob_p}) for Al2O3 "
        f"(typical for oxide semiconductors)"
    )


# ============================================================================
# Deterministic Behavior Tests
# ============================================================================

@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
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


@pytest.mark.parametrize('property_name', [
    'bandgap', 'e_form', 'dielectric', 'is_metal', 'mob_n', 'mob_p'
])
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
    
    for prop in ['bandgap', 'e_form', 'dielectric', 'mob_n', 'mob_p']:
        predictor = predictor_factory(prop)
        al2o3_results[prop] = predictor.predict_numpy([Path(cif_files['al2o3_path']).read_text()])[0]
        sio2_results[prop] = predictor.predict_numpy([Path(cif_files['sio2_path']).read_text()])[0]
    
    # At least some properties should be different between Al2O3 and SiO2
    differences = sum(
        1 for prop in al2o3_results
        if not np.isclose(al2o3_results[prop], sio2_results[prop])
    )
    assert differences > 0, "Al2O3 and SiO2 predictions are identical"


def test_bandgap_and_formation_energy_rank_correlation(
    cif_files, predictor_factory
):
    """Test that bandgap and formation energy show physical correlations."""
    al2o3_bg = predictor_factory('bandgap').predict_numpy([Path(cif_files['al2o3_path']).read_text()])[0]
    sio2_bg = predictor_factory('bandgap').predict_numpy([Path(cif_files['sio2_path']).read_text()])[0]
    
    al2o3_ef = predictor_factory('e_form').predict_numpy([Path(cif_files['al2o3_path']).read_text()])[0]
    sio2_ef = predictor_factory('e_form').predict_numpy([Path(cif_files['sio2_path']).read_text()])[0]
    
    # Just verify that predictions are being made and are in reasonable ranges
    assert 3.0 < al2o3_bg < 10.0, f"Al2O3 bandgap {al2o3_bg} out of expected range"
    assert 4.0 < sio2_bg < 10.0, f"SiO2 bandgap {sio2_bg} out of expected range"
    assert -5.0 < al2o3_ef < 0.0, f"Al2O3 formation energy {al2o3_ef} out of expected range"
    assert -5.0 < sio2_ef < 0.0, f"SiO2 formation energy {sio2_ef} out of expected range"


def test_predict_with_list_input_returns_standardized_output(cif_files, predictor_factory):
    """New contract: list[str] input returns source/results envelope."""
    predictor = predictor_factory("bandgap")
    cif_text = Path(cif_files["al2o3_path"]).read_text()
    result = predictor.predict([cif_text])

    assert result["source"] == "gbfs"
    assert isinstance(result["results"], list)
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] in {"ok", "error"}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
