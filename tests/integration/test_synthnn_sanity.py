"""
Integration tests for SynthNN Predictor with real model.

These tests use the actual SynthNN deep learning model and verify real predictions.
Marked with @pytest.mark.network (model requires TensorFlow) and @pytest.mark.slow.

Run with: pytest tests/integration/test_synthnn_sanity.py -v
Skip network tests: pytest -m "not network"
Skip slow tests: pytest -m "not slow"
"""

import pytest
import time
from pathlib import Path
from Information_Units.Predictors.Synthnn import SynthnnPredictor


@pytest.fixture
def cif_files():
    """Provide paths to CIF test fixtures."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cif_files"
    return {
        'al2o3_path': str(fixtures_dir / "Al2O3.cif"),
        'sio2_path': str(fixtures_dir / "SiO2.cif"),
        'invalid_path': str(fixtures_dir / "invalid.cif"),
        'empty_path': str(fixtures_dir / "empty.cif"),
    }


@pytest.fixture
def mock_logger():
    """Create a simple logger for tests."""
    from unittest.mock import Mock
    logger = Mock()
    logger.log = Mock()
    return logger


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
class TestSynthnnRealModel:
    """Integration tests with real SynthNN model."""
    
    def test_real_model_initialization(self, mock_logger):
        """Verify real model can be initialized without errors."""
        predictor = SynthnnPredictor(
            predictor_name='test_synthnn_real',
            logger=mock_logger
        )
        
        assert predictor is not None
        assert predictor.model_helper.model is not None
    
    @pytest.mark.parametrize('cif_key,expected_score_range', [
        ('al2o3_path', (0.70, 1.0)),  # Al2O3 should score high (common oxide)
        ('sio2_path', (0.70, 1.0)),   # SiO2 should score high (very common)
    ])
    def test_predict_known_materials(self, cif_files, mock_logger, cif_key, expected_score_range):
        """Verify model scores known synthesizable materials appropriately."""
        predictor = SynthnnPredictor(
            predictor_name='test_synthnn_known',
            logger=mock_logger
        )
        
        results = predictor.predict({
            'test.cif': cif_files[cif_key]
        })
        
        assert 'test.cif' in results
        result = results['test.cif']
        
        # Should have valid prediction
        assert result['synthesizable'] is not None
        assert result['synthesizability_score'] is not None
        
        # Score should be in expected range for common materials
        score = result['synthesizability_score']
        min_score, max_score = expected_score_range
        assert min_score <= score <= max_score, \
            f"Score {score} not in expected range [{min_score}, {max_score}]"
    
    def test_predict_multiple_materials(self, cif_files, mock_logger):
        """Test batch prediction with real model."""
        predictor = SynthnnPredictor(
            predictor_name='test_synthnn_batch',
            logger=mock_logger
        )
        
        results = predictor.predict({
            'Al2O3.cif': cif_files['al2o3_path'],
            'SiO2.cif': cif_files['sio2_path']
        })
        
        # Both should succeed
        assert len(results) == 2
        assert 'Al2O3.cif' in results
        assert 'SiO2.cif' in results
        
        # Both should have valid scores
        for filename, result in results.items():
            assert result['synthesizable'] is not None
            assert result['synthesizability_score'] is not None
            assert 0.0 <= result['synthesizability_score'] <= 1.0
    
    def test_predict_invalid_cif(self, cif_files, mock_logger):
        """Verify invalid CIF is handled gracefully with real model."""
        predictor = SynthnnPredictor(
            predictor_name='test_synthnn_invalid',
            logger=mock_logger,
            # Real model is used by default
        )
        
        results = predictor.predict({
            'invalid.cif': cif_files['invalid_path']
        })
        
        assert 'invalid.cif' in results
        result = results['invalid.cif']
        
        # Should have error, not crash
        assert result['synthesizable'] is None
        assert result['synthesizability_score'] is None
        assert 'error' in result
    
    def test_predict_mixed_batch_with_real_model(self, cif_files, mock_logger):
        """Verify batch with valid and invalid files works with real model."""
        predictor = SynthnnPredictor(
            predictor_name='test_synthnn_mixed',
            logger=mock_logger,
            # Real model is used by default
        )
        
        results = predictor.predict({
            'Al2O3.cif': cif_files['al2o3_path'],
            'invalid.cif': cif_files['invalid_path'],
            'SiO2.cif': cif_files['sio2_path']
        })
        
        assert len(results) == 3
        
        # Valid files should have predictions
        assert results['Al2O3.cif']['synthesizable'] is not None
        assert results['SiO2.cif']['synthesizable'] is not None
        
        # Invalid file should have error
        assert results['invalid.cif']['synthesizable'] is None
        assert 'error' in results['invalid.cif']
    
    def test_predict_output_structure(self, cif_files, mock_logger):
        """Verify output has correct structure with real model."""
        predictor = SynthnnPredictor(
            predictor_name='test_synthnn_structure',
            logger=mock_logger,
            # Real model is used by default
        )
        
        results = predictor.predict({
            'Al2O3.cif': cif_files['al2o3_path']
        })
        
        assert isinstance(results, dict)
        assert 'Al2O3.cif' in results
        
        result = results['Al2O3.cif']
        assert isinstance(result, dict)
        assert 'synthesizable' in result
        assert 'synthesizability_score' in result
        
        # Should be boolean or None
        assert isinstance(result['synthesizable'], (bool, type(None)))
        # Should be float or None
        assert isinstance(result['synthesizability_score'], (float, type(None)))
    
    def test_predict_json_serializable(self, cif_files, mock_logger):
        """Verify output is JSON-serializable with real model."""
        import json
        
        predictor = SynthnnPredictor(
            predictor_name='test_synthnn_json',
            logger=mock_logger,
            # Real model is used by default
        )
        
        results = predictor.predict({
            'Al2O3.cif': cif_files['al2o3_path'],
            'invalid.cif': cif_files['invalid_path']
        })
        
        # Should be JSON serializable
        json_str = json.dumps(results)
        assert isinstance(json_str, str)
        
        # Should deserialize back
        deserialized = json.loads(json_str)
        assert 'Al2O3.cif' in deserialized
        assert 'invalid.cif' in deserialized
    
    def test_predict_score_precision(self, cif_files, mock_logger):
        """Verify scores have reasonable precision."""
        predictor = SynthnnPredictor(
            predictor_name='test_synthnn_precision',
            logger=mock_logger,
            # Real model is used by default
        )
        
        results = predictor.predict({
            'Al2O3.cif': cif_files['al2o3_path']
        })
        
        result = results['Al2O3.cif']
        score = result['synthesizability_score']
        
        if score is not None:
            # Score should be a valid probability
            assert 0.0 <= score <= 1.0
            # Should be float type
            assert isinstance(score, float)


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
class TestSynthnnModelPerformance:
    """Test model performance and consistency."""
    
    def test_model_deterministic_predictions(self, cif_files, mock_logger):
        """Verify same input produces same output (deterministic behavior)."""
        predictor = SynthnnPredictor(
            predictor_name='test_synthnn_deterministic',
            logger=mock_logger,
            # Real model is used by default
        )
        
        # Predict twice
        results1 = predictor.predict({
            'Al2O3.cif': cif_files['al2o3_path']
        })
        
        results2 = predictor.predict({
            'Al2O3.cif': cif_files['al2o3_path']
        })
        
        # Should get same results
        score1 = results1['Al2O3.cif']['synthesizability_score']
        score2 = results2['Al2O3.cif']['synthesizability_score']
        
        assert score1 == score2, "Model should be deterministic"
    
    def test_model_reasonable_threshold(self, cif_files, mock_logger):
        """Verify synthesizable threshold is applied correctly."""
        predictor = SynthnnPredictor(
            predictor_name='test_synthnn_threshold',
            logger=mock_logger,
            # Real model is used by default
        )
        
        results = predictor.predict({
            'Al2O3.cif': cif_files['al2o3_path']
        })
        
        result = results['Al2O3.cif']
        
        # If score >= 0.70, should be synthesizable
        if result['synthesizability_score'] is not None:
            if result['synthesizability_score'] >= 0.70:
                assert result['synthesizable'] is True
            else:
                assert result['synthesizable'] is False
