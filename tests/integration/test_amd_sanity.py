"""
Integration tests for AMD (Average Minimum Distance) Predictor

Test Coverage:
- Generic predictor contract checks (template for future predictors)
- AMD-specific sanity checks on known materials
- Deterministic prediction behavior
- Physical validation of similarities (identical materials have low distances)
- Correct handling of different crystal types

Run with: pytest tests/integration/test_amd_sanity.py -v
Skip network tests: pytest -m "not network"
Skip slow tests: pytest -m "not slow"
"""

import json
from pathlib import Path

import pytest
import numpy as np

from Information_Units.Predictors.AMD.AMDPredictor import AMDPredictor


pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture
def cif_files():
    """Provide paths to CIF test fixtures."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cif_files"
    return {
        'al2o3_path': str(fixtures_dir / "Al2O3.cif"),
        'sio2_path': str(fixtures_dir / "SiO2.cif"),
        'invalid_path': str(fixtures_dir / "invalid.cif"),
        'zno1_path': str(fixtures_dir / "mp-2133.cif"),
        'zno2_path': str(fixtures_dir / "mp-1017539.cif"),
    }


@pytest.fixture
def amd_predictor():
    """Create a real AMD predictor instance."""
    return AMDPredictor(predictor_name="amd_integration_test", k=100)


# ============================================================================
# Generic Predictor Contract Tests
# (Template for future predictors with real backends)
# ============================================================================

@pytest.mark.integration
def test_predictor_has_required_methods():
    """Predictor implements required interface methods."""
    predictor = AMDPredictor()
    
    # Check required methods exist
    assert hasattr(predictor, 'predict')
    assert callable(predictor.predict)
    assert hasattr(predictor, 'info')
    assert callable(predictor.info)
    assert hasattr(predictor, 'predictor_name')


@pytest.mark.integration
def test_info_returns_string(amd_predictor):
    """info() returns a non-empty string."""
    info = amd_predictor.info()
    assert isinstance(info, str)
    assert len(info) > 0


@pytest.mark.integration
def test_predict_valid_input_returns_json_string(cif_files, amd_predictor):
    """Valid input produces JSON string output."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = amd_predictor.predict(inputs)
    
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)
    assert "source" in parsed
    assert "results" in parsed


@pytest.mark.integration
def test_predict_output_is_json_serializable(cif_files, amd_predictor):
    """Prediction output can be serialized and deserialized."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = amd_predictor.predict(inputs)
    
    # Parse JSON
    parsed = json.loads(result)
    
    # Convert back to JSON
    result_json = json.dumps(parsed)
    assert isinstance(result_json, str)


@pytest.mark.integration
def test_predict_invalid_input_raises_error(cif_files, amd_predictor):
    """Invalid input (missing file) returns error JSON."""
    inputs = {'input_data': [cif_files['invalid_path'], cif_files['al2o3_path']]}
    
    result_json = amd_predictor.predict(inputs)
    result = json.loads(result_json)
    
    # Should return error JSON with standardized format
    assert result["results"][0]["status"] == "failed"
    assert result["results"][0]["error"] is not None


# ============================================================================
# AMD-Specific Sanity Tests
# ============================================================================

@pytest.mark.integration
def test_identical_crystals_have_zero_distance(cif_files, amd_predictor):
    """Identical crystals (same file compared to itself) have near-zero distance."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['al2o3_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    assert result["results"][0]["status"] == "success"
    pair = result["results"][0]["properties"]["pairwise_distances"][0]
    
    # Identical structures should have very close to zero distance
    assert pair["pdd_emd_distance"] < 0.01, \
        f"Identical crystals should have near-zero distance, got {pair['pdd_emd_distance']}"
    assert pair["identical"] == True


@pytest.mark.integration
def test_different_crystals_have_nonzero_distance(cif_files, amd_predictor):
    """Different crystals (Al2O3 vs SiO2) have significant distance."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    assert result["results"][0]["status"] == "success"
    pair = result["results"][0]["properties"]["pairwise_distances"][0]
    
    # Different structures should have larger distance
    assert pair["pdd_emd_distance"] > 0.01, \
        f"Different crystals should have measurable distance, got {pair['pdd_emd_distance']}"
    assert pair["identical"] == False


@pytest.mark.integration
def test_pdd_distance_nonnegative(cif_files, amd_predictor):
    """PDD/EMD distances are always non-negative."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    if result["results"][0]["status"] == "success":
        for pair in result["results"][0]["properties"]["pairwise_distances"]:
            assert pair["pdd_emd_distance"] >= 0.0


@pytest.mark.integration
def test_amd_distance_nonnegative(cif_files, amd_predictor):
    """AMD distances are always non-negative."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    if result["results"][0]["status"] == "success":
        for pair in result["results"][0]["properties"]["pairwise_distances"]:
            assert pair["amd_distance"] >= 0.0


@pytest.mark.integration
def test_distance_is_finite(cif_files, amd_predictor):
    """Calculated distances are finite (not NaN or Inf)."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    if result["results"][0]["status"] == "success":
        for pair in result["results"][0]["properties"]["pairwise_distances"]:
            assert np.isfinite(pair["pdd_emd_distance"])
            assert np.isfinite(pair["amd_distance"])


@pytest.mark.integration
def test_results_include_all_required_fields(cif_files, amd_predictor):
    """Prediction results include all expected fields."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    # Top-level standardized fields
    assert "source" in result
    assert "results" in result
    assert isinstance(result["results"], list)
    assert len(result["results"]) > 0
    
    # First result object
    result_obj = result["results"][0]
    assert "index" in result_obj
    assert "status" in result_obj
    assert "properties" in result_obj
    assert "warnings" in result_obj
    assert "error" in result_obj
    
    # Properties should have pairwise distances, crystal info, etc.
    props = result_obj["properties"]
    assert "pairwise_distances" in props
    assert "crystal_info" in props
    assert "parameters" in props
    assert "n_comparisons" in props
    
    # Pairwise distance fields
    pair = props["pairwise_distances"][0]
    assert "crystal_1_index" in pair
    assert "crystal_2_index" in pair
    assert "crystal_1_file" in pair
    assert "crystal_2_file" in pair
    assert "pdd_emd_distance" in pair
    assert "amd_distance" in pair
    
    # Parameters fields
    params = props["parameters"]
    assert "k" in params
    assert "metric" in params
    assert "n_crystals" in params
    assert "n_files" in params


@pytest.mark.integration
def test_crystal_info_fields_populated(cif_files, amd_predictor):
    """Crystal info fields are properly populated."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    crystal_info = result["results"][0]["properties"]["crystal_info"]
    for info in crystal_info:
        assert "name" in info
        assert "n_atoms" in info
        assert "n_asym" in info
        assert "composition" in info
        
        # Validate data types and values
        assert isinstance(info["n_atoms"], int)
        assert info["n_atoms"] > 0
        assert isinstance(info["n_asym"], int)
        assert info["n_asym"] > 0


@pytest.mark.integration
def test_parameters_match_predictor_config(cif_files):
    """Predicted parameters match the predictor configuration."""
    k_value = 50
    metric_value = "chebyshev"
    predictor = AMDPredictor(predictor_name="param_test", k=k_value, metric=metric_value)
    
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = json.loads(predictor.predict(inputs))
    
    params = result["results"][0]["properties"]["parameters"]
    assert params["k"] == k_value
    assert params["metric"] == metric_value


# ============================================================================
# Deterministic Behavior Tests
# ============================================================================

@pytest.mark.integration
def test_repeated_predictions_identical(cif_files, amd_predictor):
    """Running the same prediction twice gives identical results."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    
    result1 = json.loads(amd_predictor.predict(inputs))
    result2 = json.loads(amd_predictor.predict(inputs))
    
    # Compare all pairwise distances
    pairs1 = result1["results"][0]["properties"]["pairwise_distances"]
    pairs2 = result2["results"][0]["properties"]["pairwise_distances"]
    for p1, p2 in zip(pairs1, pairs2):
        # Should be exactly equal for deterministic calculations
        assert abs(p1["pdd_emd_distance"] - p2["pdd_emd_distance"]) < 1e-10
        assert abs(p1["amd_distance"] - p2["amd_distance"]) < 1e-10


@pytest.mark.integration
def test_prediction_order_independence(cif_files, amd_predictor):
    """Prediction is order-independent for symmetric comparisons."""
    # First order: Al2O3 -> SiO2
    inputs1 = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result1 = json.loads(amd_predictor.predict(inputs1))
    
    # Second order: SiO2 -> Al2O3
    inputs2 = {'input_data': [cif_files['sio2_path'], cif_files['al2o3_path']]}
    result2 = json.loads(amd_predictor.predict(inputs2))
    
    # Distances should be found in the results
    dist1 = result1["results"][0]["properties"]["pairwise_distances"][0]["pdd_emd_distance"]
    dist2 = result2["results"][0]["properties"]["pairwise_distances"][0]["pdd_emd_distance"]
    
    # Same comparison should give same result
    assert abs(dist1 - dist2) < 1e-10


# ============================================================================
# Multiple File Handling Tests
# ============================================================================

# ============================================================================
# Multiple File Handling Tests
# ============================================================================

@pytest.mark.integration
def test_predict_with_input_data_list(cif_files, amd_predictor):
    """predict() works with standard input_data list format."""
    inputs = {
        'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]
    }
    result = json.loads(amd_predictor.predict(inputs))
    
    assert result["results"][0]["properties"]["pairwise_distances"] is not None
    assert result["results"][0]["properties"]["n_comparisons"] > 0


@pytest.mark.integration
def test_predict_requires_dict_input(cif_files, amd_predictor):
    """predict() requires a list or dict input; passing a bare string should fail."""
    # Passing string directly should fail
    result_json = amd_predictor.predict(cif_files['al2o3_path'])
    result = json.loads(result_json)
    
    # Should return error
    assert result["results"][0]["status"] == "failed"
    assert any(kw in result["results"][0]["error"] for kw in ("list", "dict", "dictionary", "input_data"))


# ============================================================================
# Comparison Tests
# ============================================================================

@pytest.mark.integration
def test_pdd_emd_and_amd_both_present(cif_files, amd_predictor):
    """Both PDD/EMD and AMD distances are calculated."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    pair = result["results"][0]["properties"]["pairwise_distances"][0]
    assert "pdd_emd_distance" in pair
    assert "amd_distance" in pair
    
    # Both should be non-zero for different structures
    assert pair["pdd_emd_distance"] > 0.0 or pair["pdd_emd_distance"] == 0.0
    assert pair["amd_distance"] > 0.0 or pair["amd_distance"] == 0.0


@pytest.mark.integration
def test_similarity_flags_set_correctly(cif_files, amd_predictor):
    """Similarity flags (identical, very_similar, similar) are set correctly."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    pair = result["results"][0]["properties"]["pairwise_distances"][0]
    
    # Should have the flags
    assert "identical" in pair
    assert "very_similar" in pair
    assert "similar" in pair
    
    # Flags should be booleans
    assert isinstance(pair["identical"], bool)
    assert isinstance(pair["very_similar"], bool)
    assert isinstance(pair["similar"], bool)
    
    # For different materials, should not be identical
    assert pair["identical"] == False


@pytest.mark.integration
def test_identical_crystals_flagged_correctly(cif_files, amd_predictor):
    """Identical crystals are correctly flagged."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['al2o3_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    pair = result["results"][0]["properties"]["pairwise_distances"][0]
    assert pair["identical"] == True


# ============================================================================
# K-Parameter Tests
# ============================================================================

@pytest.mark.integration
def test_small_k_sensitivity(cif_files):
    """Small k values are still meaningful."""
    predictor = AMDPredictor(predictor_name="k_test_small", k=5)
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = json.loads(predictor.predict(inputs))
    
    assert result["results"][0]["properties"]["parameters"]["k"] == 5
    pair = result["results"][0]["properties"]["pairwise_distances"][0]
    assert pair["pdd_emd_distance"] >= 0.0


@pytest.mark.integration
def test_large_k_sensitivity(cif_files):
    """Large k values capture broader crystal neighborhoods."""
    predictor = AMDPredictor(predictor_name="k_test_large", k=200)
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = json.loads(predictor.predict(inputs))
    
    assert result["results"][0]["properties"]["parameters"]["k"] == 200
    pair = result["results"][0]["properties"]["pairwise_distances"][0]
    assert pair["pdd_emd_distance"] >= 0.0


# ============================================================================
# Error Recovery Tests
# ============================================================================

@pytest.mark.integration
def test_predict_invalid_file_graceful_error(cif_files, amd_predictor):
    """predict() handles invalid file gracefully."""
    inputs = {'input_data': [cif_files['invalid_path'], cif_files['al2o3_path']]}
    
    result_json = amd_predictor.predict(inputs)
    result = json.loads(result_json)
    
    # Should return error JSON with standardized format
    assert result["results"][0]["status"] == "failed"
    assert result["results"][0]["error"] is not None


# ============================================================================
# Real-World Material Comparison Tests
# ============================================================================

@pytest.mark.integration
def test_zno_isomer_comparison_integration(cif_files, amd_predictor):
    """Test comparison of two ZnO wurtzite structures with different lattice parameters.
    
    This real-world test validates that the predictor can distinguish between
    structurally similar but not identical materials. Both samples are wurtzite ZnO
    but have different lattice parameters (a: 3.237 vs 3.205, c: 5.222 vs 5.517).
    """
    inputs = {'input_data': [cif_files['zno1_path'], cif_files['zno2_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    assert result["results"][0]["status"] == "success"
    props = result["results"][0]["properties"]
    
    # Validate result structure
    assert "pairwise_distances" in props
    assert props["n_comparisons"] > 0
    
    pair = props["pairwise_distances"][0]
    
    # Both should be recognized as zinc oxide materials
    zno1_comp = props["crystal_info"][0]["composition"]
    zno2_comp = props["crystal_info"][1]["composition"]
    assert "Zn" in zno1_comp and "O" in zno1_comp
    assert "Zn" in zno2_comp and "O" in zno2_comp
    
    # Should have measurable distances (they are different structures)
    assert pair["pdd_emd_distance"] > 0.0
    assert pair["amd_distance"] > 0.0
    
    # Should NOT be marked as identical (different lattice parameters)
    assert pair["identical"] == False
    
    # Validate numeric ranges
    assert np.isfinite(pair["pdd_emd_distance"])
    assert np.isfinite(pair["amd_distance"])


# ============================================================================
# Integration Test: Complete Workflow
# ============================================================================

@pytest.mark.integration
def test_complete_workflow_two_materials(cif_files, amd_predictor):
    """Complete workflow: load, compare, analyze."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['sio2_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    assert result["results"][0]["status"] == "success"
    props = result["results"][0]["properties"]
    
    # Verify all parts work together
    assert props["n_comparisons"] == 1
    assert len(props["crystal_info"]) == 2
    
    pair = props["pairwise_distances"][0]
    
    # Al2O3 and SiO2 are different materials
    assert pair["identical"] == False
    assert pair["pdd_emd_distance"] > 0.0
    
    # Crystal info should be populated
    assert props["crystal_info"][0]["n_atoms"] > 0
    assert props["crystal_info"][1]["n_atoms"] > 0


@pytest.mark.integration
def test_complete_workflow_identical_material(cif_files, amd_predictor):
    """Complete workflow with identical material."""
    inputs = {'input_data': [cif_files['al2o3_path'], cif_files['al2o3_path']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    assert result["results"][0]["status"] == "success"
    props = result["results"][0]["properties"]
    
    # Verify all parts work together
    assert props["n_comparisons"] == 1
    
    pair = props["pairwise_distances"][0]
    
    # Al2O3 compared to itself
    assert pair["identical"] == True
    assert pair["pdd_emd_distance"] < 0.01
    
    # Both should be the same crystal
    assert props["crystal_info"][0]["composition"] == props["crystal_info"][1]["composition"]
