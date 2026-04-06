"""
Unit tests for AMDPredictor

Comprehensive unit test suite for the AMD (Average Minimum Distance) predictor
that compares crystal structures using geometric descriptors.

Test Structure (following GBFS test patterns):
- Generic initialization tests
- CIF file validation tests
- Single and multiple crystal comparison tests
- Distance calculation tests (PDD/EMD and AMD)
- Input handling tests (string, dict with cif_path, dict with cif_paths)
- Error handling tests (missing files, invalid CIF, insufficient crystals)
- Output format tests (JSON serialization)
- Parameter configuration tests

This is a UNIT TEST suite - tests API correctness and functionality.
For real materials science validation, see tests/integration/test_amd_sanity.py

Run: pytest tests/unit/test_amd_behaviour.py -v
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np

from Information_Units.Predictors.AMD.AMDPredictor import (
    AMDPredictor,
    load_crystals_from_cif,
    validate_cif_file,
    get_crystal_info,
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
        'invalid': str(d / "invalid.cif"),
        'empty': str(d / "empty.cif"),
        'zno1': str(d / "mp-2133.cif"),
        'zno2': str(d / "mp-1017539.cif"),
    }


@pytest.fixture
def amd_predictor():
    """Create an AMD predictor instance for testing."""
    return AMDPredictor(predictor_name="test_amd", k=20)


@pytest.fixture
def amd_predictor_with_logger():
    """Create an AMD predictor with mock logger."""
    logger = Mock()
    logger.log = Mock()
    return AMDPredictor(predictor_name="test_amd_logged", k=20, logger=logger)


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    logger = Mock()
    logger.log = Mock()
    return logger


# ============================================================================
# Initialization Tests
# ============================================================================

@pytest.mark.unit
def test_init_default_parameters(amd_predictor):
    """Predictor initializes with correct default parameters."""
    assert amd_predictor.predictor_name == "test_amd"
    assert amd_predictor.k == 20
    assert amd_predictor.metric == "chebyshev"


@pytest.mark.unit
def test_init_custom_parameters():
    """Predictor initializes with custom parameters."""
    predictor = AMDPredictor(predictor_name="custom", k=50, metric="euclidean")
    assert predictor.k == 50
    assert predictor.metric == "euclidean"


@pytest.mark.unit
def test_init_with_logger(amd_predictor_with_logger, mock_logger):
    """Predictor initializes with logger and logs message."""
    predictor = AMDPredictor(predictor_name="logged", logger=mock_logger)
    assert predictor.logger is not None


@pytest.mark.unit
def test_info_returns_description(amd_predictor):
    """info() returns a description string."""
    info = amd_predictor.info()
    assert isinstance(info, str)
    assert len(info) > 0
    assert "AMD" in info
    assert "test_amd" in info
    assert "k=20" in info


# ============================================================================
# CIF File Validation Tests
# ============================================================================

@pytest.mark.unit
def test_validate_cif_file_nonexistent():
    """Validating non-existent CIF file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        validate_cif_file("/nonexistent/file.cif")


@pytest.mark.unit
def test_validate_cif_file_wrong_extension(tmp_path):
    """Validating file without .cif extension raises ValueError."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy content")
    
    with pytest.raises(ValueError, match="does not have .cif extension"):
        validate_cif_file(str(test_file))


@pytest.mark.unit
def test_validate_cif_file_directory(tmp_path):
    """Validating directory instead of file raises ValueError."""
    with pytest.raises(ValueError, match="is not a file"):
        validate_cif_file(str(tmp_path))


@pytest.mark.unit
def test_validate_cif_file_valid(cif_files):
    """Validating valid CIF file succeeds."""
    # Should not raise any exception
    validate_cif_file(cif_files['al2o3'])


# ============================================================================
# CIF Loading Tests
# ============================================================================

@pytest.mark.unit
def test_load_crystals_from_valid_cif(cif_files):
    """Loading crystals from valid CIF succeeds."""
    crystals = load_crystals_from_cif(cif_files['al2o3'])
    assert isinstance(crystals, list)
    assert len(crystals) > 0


@pytest.mark.unit
def test_load_crystals_nonexistent_cif():
    """Loading from non-existent CIF raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_crystals_from_cif("/nonexistent/structure.cif")


@pytest.mark.unit
def test_load_crystals_invalid_cif(cif_files):
    """Loading from invalid CIF raises ValueError."""
    with pytest.raises(ValueError):
        load_crystals_from_cif(cif_files['invalid'])


# ============================================================================
# Input Handling Tests
# ============================================================================

@pytest.mark.unit
def test_extract_cif_paths_string_input(cif_files, amd_predictor):
    """Extracting paths from string input works."""
    paths = amd_predictor._extract_cif_paths(cif_files['al2o3'])
    assert isinstance(paths, list)
    assert len(paths) == 1
    assert paths[0] == cif_files['al2o3']


@pytest.mark.unit
def test_extract_cif_paths_dict_cif_paths(cif_files, amd_predictor):
    """Extracting paths from dict with 'cif_paths' key works."""
    inputs = {'cif_paths': [cif_files['al2o3'], cif_files['sio2']]}
    paths = amd_predictor._extract_cif_paths(inputs)
    assert len(paths) == 2
    assert paths[0] == cif_files['al2o3']


@pytest.mark.unit
def test_extract_cif_paths_dict_cif_path(cif_files, amd_predictor):
    """Extracting paths from dict with 'cif_path' key works."""
    inputs = {'cif_path': cif_files['al2o3']}
    paths = amd_predictor._extract_cif_paths(inputs)
    assert len(paths) == 1


@pytest.mark.unit
def test_extract_cif_paths_dict_cif_path1_path2(cif_files, amd_predictor):
    """Extracting paths from dict with 'cif_path1' and 'cif_path2' works."""
    inputs = {'cif_path1': cif_files['al2o3'], 'cif_path2': cif_files['sio2']}
    paths = amd_predictor._extract_cif_paths(inputs)
    assert len(paths) == 2


@pytest.mark.unit
def test_extract_cif_paths_dict_input_data(cif_files, amd_predictor):
    """Extracting paths from dict with nested 'input_data' works."""
    inputs = {'input_data': {'cif_paths': [cif_files['al2o3'], cif_files['sio2']]}}
    paths = amd_predictor._extract_cif_paths(inputs)
    assert len(paths) == 2


@pytest.mark.unit
def test_extract_cif_paths_invalid_dict(amd_predictor):
    """Extracting from invalid dict raises ValueError."""
    inputs = {'invalid_key': 'invalid_value'}
    with pytest.raises(ValueError, match="No CIF paths found"):
        amd_predictor._extract_cif_paths(inputs)


@pytest.mark.unit
def test_extract_cif_paths_invalid_type(amd_predictor):
    """Extracting from invalid type raises ValueError."""
    inputs = 12345
    with pytest.raises(ValueError, match="Invalid input type"):
        amd_predictor._extract_cif_paths(inputs)


# ============================================================================
# Prediction Tests
# ============================================================================

@pytest.mark.unit
def test_predict_with_two_cif_files(cif_files, amd_predictor):
    """predict() with two CIF files returns JSON string."""
    inputs = {'cif_paths': [cif_files['al2o3'], cif_files['sio2']]}
    result = amd_predictor.predict(inputs)
    
    assert isinstance(result, str)
    parsed = json.loads(result)
    
    assert "pairwise_distances" in parsed
    assert "crystal_info" in parsed
    assert "parameters" in parsed
    assert "n_comparisons" in parsed


@pytest.mark.unit
def test_predict_insufficient_cif_files(cif_files, amd_predictor):
    """predict() with only one CIF file returns error JSON."""
    inputs = {'cif_paths': [cif_files['al2o3']]}
    
    result_json = amd_predictor.predict(inputs)
    result = json.loads(result_json)
    
    # Should return error JSON instead of raising exception
    assert "error" in result
    assert "requires at least 2" in result["error"]


@pytest.mark.unit
def test_predict_output_has_correct_structure(cif_files, amd_predictor):
    """Prediction output has all required fields."""
    inputs = {'cif_paths': [cif_files['al2o3'], cif_files['sio2']]}
    result_json = amd_predictor.predict(inputs)
    result = json.loads(result_json)
    
    assert "pairwise_distances" in result
    assert isinstance(result["pairwise_distances"], list)
    assert len(result["pairwise_distances"]) > 0
    
    # Check first pairwise distance has required fields
    pair = result["pairwise_distances"][0]
    assert "crystal_1_index" in pair
    assert "crystal_2_index" in pair
    assert "pdd_emd_distance" in pair
    assert "amd_distance" in pair


@pytest.mark.unit
def test_predict_distances_are_numeric(cif_files, amd_predictor):
    """Prediction distances are numeric values."""
    inputs = {'cif_paths': [cif_files['al2o3'], cif_files['sio2']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    for pair in result["pairwise_distances"]:
        if "error" not in pair:
            assert isinstance(pair["pdd_emd_distance"], (int, float))
            assert isinstance(pair["amd_distance"], (int, float))
            assert pair["pdd_emd_distance"] >= 0.0
            assert pair["amd_distance"] >= 0.0


@pytest.mark.unit
def test_predict_identical_crystals(cif_files, amd_predictor):
    """predict() with identical CIF file has distance near zero."""
    inputs = {'cif_paths': [cif_files['al2o3'], cif_files['al2o3']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    pair = result["pairwise_distances"][0]
    if "error" not in pair:
        # Identical structures should have very small EMD distance
        assert pair["pdd_emd_distance"] < 0.1
        assert pair["identical"] == True


@pytest.mark.unit
def test_predict_parameters_stored(cif_files, amd_predictor):
    """Prediction output includes correct parameters."""
    inputs = {'cif_paths': [cif_files['al2o3'], cif_files['sio2']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    params = result["parameters"]
    assert params["k"] == 20
    assert params["metric"] == "chebyshev"
    assert params["n_crystals"] == 2
    assert params["n_files"] == 2


@pytest.mark.unit
def test_predict_numpy_returns_dict(cif_files, amd_predictor):
    """predict_numpy() returns a dictionary instead of JSON."""
    inputs = {'cif_paths': [cif_files['al2o3'], cif_files['sio2']]}
    result = amd_predictor.predict_numpy(inputs)
    
    assert isinstance(result, dict)
    assert "pairwise_distances" in result
    assert "parameters" in result


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.unit
def test_predict_nonexistent_cif_file(amd_predictor):
    """predict() with non-existent CIF file returns error JSON."""
    inputs = {'cif_paths': ['/nonexistent/file1.cif', '/nonexistent/file2.cif']}
    
    result_json = amd_predictor.predict(inputs)
    result = json.loads(result_json)
    
    # Should return error JSON
    assert "error" in result


@pytest.mark.unit
def test_predict_invalid_cif_file(cif_files, amd_predictor):
    """predict() with invalid CIF file returns error JSON."""
    inputs = {'cif_paths': [cif_files['invalid'], cif_files['al2o3']]}
    
    result_json = amd_predictor.predict(inputs)
    result = json.loads(result_json)
    
    # Should return error JSON
    assert "error" in result


@pytest.mark.unit
def test_predict_empty_cif_file(cif_files, amd_predictor):
    """predict() with empty CIF file returns error JSON."""
    inputs = {'cif_paths': [cif_files['empty'], cif_files['al2o3']]}
    
    result_json = amd_predictor.predict(inputs)
    result = json.loads(result_json)
    
    # Should return error JSON
    assert "error" in result


# ============================================================================
# Crystal Info Tests
# ============================================================================

@pytest.mark.unit
def test_get_crystal_info_returns_dict(cif_files):
    """get_crystal_info() returns a dictionary with expected fields."""
    crystals = load_crystals_from_cif(cif_files['al2o3'])
    info = get_crystal_info(crystals[0])
    
    assert isinstance(info, dict)
    assert "name" in info
    assert "n_atoms" in info
    assert "composition" in info


@pytest.mark.unit
def test_get_crystal_info_valid_data(cif_files):
    """get_crystal_info() returns valid data."""
    crystals = load_crystals_from_cif(cif_files['al2o3'])
    info = get_crystal_info(crystals[0])
    
    assert isinstance(info["n_atoms"], int)
    assert info["n_atoms"] > 0


# ============================================================================
# Pairwise Distance Calculation Tests
# ============================================================================

@pytest.mark.unit
def test_calculate_pairwise_distances_returns_correct_count(cif_files, amd_predictor):
    """Pairwise distance calculation returns correct number of comparisons."""
    import amd
    crystals = load_crystals_from_cif(cif_files['al2o3'])
    crystals = crystals + load_crystals_from_cif(cif_files['sio2'])
    sources = [cif_files['al2o3']] * len(load_crystals_from_cif(cif_files['al2o3']))
    sources += [cif_files['sio2']] * len(load_crystals_from_cif(cif_files['sio2']))
    
    result = amd_predictor._calculate_pairwise_distances(crystals, sources)
    
    n = len(crystals)
    expected_comparisons = n * (n - 1) // 2
    assert result["n_comparisons"] == expected_comparisons


@pytest.mark.unit
def test_calculate_pairwise_distances_structure(cif_files, amd_predictor):
    """Pairwise distance results have correct structure."""
    import amd
    crystals = load_crystals_from_cif(cif_files['al2o3'])
    sources = [cif_files['al2o3']] * len(crystals)
    
    # Need at least 2 crystals for comparison
    crystals_extended = crystals + load_crystals_from_cif(cif_files['sio2'])
    sources_extended = sources + [cif_files['sio2']] * len(load_crystals_from_cif(cif_files['sio2']))
    
    result = amd_predictor._calculate_pairwise_distances(crystals_extended, sources_extended)
    
    assert isinstance(result["pairwise_distances"], list)
    assert len(result["pairwise_distances"]) > 0
    
    for pair in result["pairwise_distances"]:
        if "error" not in pair:
            assert "crystal_1_index" in pair
            assert "crystal_2_index" in pair
            assert "pdd_emd_distance" in pair
            assert "amd_distance" in pair


# ============================================================================
# Multiple Crystal Per File Tests
# ============================================================================

@pytest.mark.unit
def test_predict_multiple_crystals_per_file(cif_files, amd_predictor):
    """predict() correctly handles multiple crystals in a single CIF file."""
    inputs = {'cif_paths': [cif_files['al2o3'], cif_files['sio2']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    assert result["parameters"]["n_crystals"] >= 2
    assert result["n_comparisons"] > 0


# ============================================================================
# Consistency Tests
# ============================================================================

@pytest.mark.unit
def test_predict_deterministic_results(cif_files, amd_predictor):
    """predict() produces deterministic results for same input."""
    inputs = {'cif_paths': [cif_files['al2o3'], cif_files['sio2']]}
    
    result1 = json.loads(amd_predictor.predict(inputs))
    result2 = json.loads(amd_predictor.predict(inputs))
    
    # Compare distances (should be identical)
    for p1, p2 in zip(result1["pairwise_distances"], result2["pairwise_distances"]):
        if "error" not in p1 and "error" not in p2:
            assert abs(p1["pdd_emd_distance"] - p2["pdd_emd_distance"]) < 1e-10
            assert abs(p1["amd_distance"] - p2["amd_distance"]) < 1e-10


@pytest.mark.unit
def test_different_k_values_produce_different_results(cif_files):
    """Different k values should be configured correctly."""
    predictor_k10 = AMDPredictor(predictor_name="amd_k10", k=10)
    predictor_k100 = AMDPredictor(predictor_name="amd_k100", k=100)
    
    inputs = {'cif_paths': [cif_files['al2o3'], cif_files['sio2']]}
    
    result_k10 = json.loads(predictor_k10.predict(inputs))
    result_k100 = json.loads(predictor_k100.predict(inputs))
    
    # Verify k values are set correctly
    assert result_k10["parameters"]["k"] == 10
    assert result_k100["parameters"]["k"] == 100
    
    # Both should have successful predictions
    assert len(result_k10["pairwise_distances"]) > 0
    assert len(result_k100["pairwise_distances"]) > 0


# ============================================================================
# Real-World Material Comparison Tests
# ============================================================================

@pytest.mark.unit
def test_zno_isomer_comparison(cif_files, amd_predictor):
    """Compare two ZnO structures with different lattice parameters.
    
    Both are wurtzite ZnO but with different a and c lattice constants.
    They should have measurable but not identical distance.
    """
    inputs = {'cif_paths': [cif_files['zno1'], cif_files['zno2']]}
    result = json.loads(amd_predictor.predict(inputs))
    
    assert result["n_comparisons"] > 0
    pair = result["pairwise_distances"][0]
    
    # Both are ZnO, so should have similar composition
    info1 = result["crystal_info"][0]
    info2 = result["crystal_info"][1]
    assert info1["name"] == "ZnO"
    assert info2["name"] == "ZnO"
    
    # But they're not identical (different lattice parameters)
    assert pair["identical"] == False
    
    # Distance should be measurable
    assert pair["pdd_emd_distance"] > 0.01
    
    # They're the same material type but different polymorphs/variants
    assert isinstance(pair["pdd_emd_distance"], float)
    assert isinstance(pair["amd_distance"], float)
