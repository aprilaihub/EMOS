"""
Unit tests for GBFS_PredPredictor - Integration Tests
Tests the high-level prediction functionality
"""

import pytest
import json
import os
import numpy as np
from pathlib import Path

from Information_Units.Predictors.GBFS_Pred.GBFS_PredPredictor import (
    GBFS_PredPredictor,
    load_cif,
)


# Fixtures
@pytest.fixture
def gbfs_predictor():
    """Initialize GBFS predictor with bandgap model files."""
    bandgap_dir = Path(__file__).parent.parent.parent / "Information_Units" / "Predictors" / "GBFS_Pred" / "bandgap"
    
    return GBFS_PredPredictor(
        predictor_name="gbfs_test",
        model_path=str(bandgap_dir / "bandgap_model.pkl"),
        scaler_path=str(bandgap_dir / "bandgap_scaler.pkl"),
        feature_list_path=str(bandgap_dir / "bandgap_features.pkl")
    )


@pytest.fixture
def cif_file_path():
    """Path to test CIF file."""
    return Path(__file__).parent.parent / "fixtures" / "cif_files" / "Al2O3.cif"


# Tests
class TestGBFSPredictorInitialization:
    """Test predictor initialization and file loading."""
    
    def test_predictor_initializes(self, gbfs_predictor):
        """Test that predictor initializes successfully."""
        assert gbfs_predictor is not None
        assert gbfs_predictor.predictor_name == "gbfs_test"
        assert gbfs_predictor.model is not None
        assert gbfs_predictor.scaler is not None
        assert gbfs_predictor.feature_list is not None
    
    def test_feature_list_is_list(self, gbfs_predictor):
        """Test that feature_list is a proper Python list."""
        assert isinstance(gbfs_predictor.feature_list, list)
        assert len(gbfs_predictor.feature_list) > 0
    
    def test_predictor_info(self, gbfs_predictor):
        """Test predictor info method."""
        info = gbfs_predictor.info()
        assert isinstance(info, str)
        assert "GBFS_Pred" in info
        assert "LGBM" in info


class TestCIFLoading:
    """Test CIF file loading functionality."""
    
    def test_load_valid_cif(self, cif_file_path):
        """Test loading a valid CIF file."""
        assert cif_file_path.exists(), f"CIF file not found: {cif_file_path}"
        
        structure = load_cif(str(cif_file_path))
        assert structure is not None
        assert len(structure.composition) > 0
    
    def test_load_invalid_cif(self):
        """Test loading non-existent CIF file raises error."""
        with pytest.raises(FileNotFoundError):
            load_cif("/nonexistent/structure.cif")


class TestPrediction:
    """Test prediction functionality at high level."""
    
    def test_predict_numpy_returns_array(self, gbfs_predictor, cif_file_path):
        """Test predict_numpy returns numpy array with prediction."""
        result = gbfs_predictor.predict_numpy(str(cif_file_path))
        
        assert isinstance(result, np.ndarray)
        assert len(result.shape) == 1 or result.shape[0] == 1  # Single prediction value(s)
    
    def test_predict_numpy_is_numeric(self, gbfs_predictor, cif_file_path):
        """Test that prediction value is numeric."""
        result = gbfs_predictor.predict_numpy(str(cif_file_path))
        
        assert np.isfinite(result[0]).all(), "Prediction contains NaN or Inf"
    
    def test_predict_returns_json(self, gbfs_predictor, cif_file_path):
        """Test predict returns JSON string."""
        result = gbfs_predictor.predict(str(cif_file_path))
        
        assert isinstance(result, str)
        
        # Parse JSON to verify format
        parsed = json.loads(result)
        assert "prediction" in parsed
        assert isinstance(parsed["prediction"], list)
    
    def test_predict_with_string_input(self, gbfs_predictor, cif_file_path):
        """Test predict accepts string input."""
        result = gbfs_predictor.predict(str(cif_file_path))
        
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "prediction" in parsed
    
    def test_predict_with_dict_input_cif_path(self, gbfs_predictor, cif_file_path):
        """Test predict accepts dict input with cif_path key."""
        result = gbfs_predictor.predict({"cif_path": str(cif_file_path)})
        
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "prediction" in parsed
    
    def test_predict_with_dict_input_data_key(self, gbfs_predictor, cif_file_path):
        """Test predict accepts dict input with input_data key."""
        result = gbfs_predictor.predict({"input_data": str(cif_file_path)})
        
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "prediction" in parsed
    
    def test_predict_invalid_path_raises_error(self, gbfs_predictor):
        """Test predict raises FileNotFoundError for invalid path."""
        with pytest.raises(FileNotFoundError):
            gbfs_predictor.predict("/nonexistent/structure.cif")
    
    def test_predict_no_input_raises_error(self, gbfs_predictor):
        """Test predict raises ValueError when no input provided."""
        with pytest.raises(ValueError, match="No CIF file path provided"):
            gbfs_predictor.predict({})


class TestEndToEnd:
    """End-to-end integration tests."""
    
    def test_full_pipeline_al2o3(self, gbfs_predictor, cif_file_path):
        """Test full prediction pipeline on Al2O3 structure."""
        # Load structure
        structure = load_cif(str(cif_file_path))
        # Verify it's aluminum oxide (may be primitive or conventional cell)
        assert "Al" in structure.composition.formula and "O" in structure.composition.formula
        
        # Generate features and predict
        numpy_result = gbfs_predictor.predict_numpy(str(cif_file_path))
        json_result = gbfs_predictor.predict(str(cif_file_path))
        
        # Verify results - numpy result is 1D array of predictions
        assert numpy_result.shape == (1,) or len(numpy_result) == 1
        parsed_json = json.loads(json_result)
        assert len(parsed_json["prediction"]) == 1
        
        # Values should match
        assert np.isclose(numpy_result[0], parsed_json["prediction"][0])
    
    def test_multiple_predictions_consistent(self, gbfs_predictor, cif_file_path):
        """Test that multiple predictions on same file are consistent."""
        result1 = gbfs_predictor.predict_numpy(str(cif_file_path))
        result2 = gbfs_predictor.predict_numpy(str(cif_file_path))
        
        assert np.allclose(result1, result2), "Predictions are not consistent"
    
    def test_prediction_in_reasonable_range(self, gbfs_predictor, cif_file_path):
        """Test that band gap prediction is in reasonable physical range."""
        result = gbfs_predictor.predict_numpy(str(cif_file_path))
        prediction_value = result[0]
        
        # Band gap typically ranges from 0 to 20 eV
        assert -5 < prediction_value < 25, \
            f"Prediction {prediction_value} is outside expected band gap range"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
