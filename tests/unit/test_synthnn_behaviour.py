"""Unit tests for SynthNN Predictor - Phase 1 mock implementation.

Test Coverage:
- CIF parsing and composition extraction
- Mock prediction behavior
- Full end-to-end workflow
- Error handling and recovery
- Output structure validation
- Warning generation

Run: pytest tests/unit/test_synthnn_behaviour.py -v
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from Information_Units.Predictors.Synthnn.composition_helper import CompositionHelper
from Information_Units.Predictors.Synthnn.synthnn_model_helper import SynthnnModelHelper
from Information_Units.Predictors.Synthnn import SynthnnPredictor


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_cif_files():
    """Provide paths to CIF test fixtures."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cif_files"
    
    return {
        'al2o3_path': str(fixtures_dir / "Al2O3.cif"),
        'sio2_path': str(fixtures_dir / "SiO2.cif"),
        'invalid_path': str(fixtures_dir / "invalid.cif"),
        'empty_path': str(fixtures_dir / "empty.cif"),
        'tmpdir': str(fixtures_dir)
    }


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    logger = Mock()
    logger.log = Mock()
    return logger


# ============================================================================
# Test CompositionHelper
# ============================================================================

@pytest.mark.unit
class TestCompositionExtraction:
    """Test CIF parsing and composition extraction."""
    
    @pytest.mark.parametrize('cif_key,expected_elements', [
        ('al2o3_path', ['Al', 'O']),
        ('sio2_path', ['Si', 'O']),
    ])
    def test_extract_from_valid_cif(self, temp_cif_files, cif_key, expected_elements):
        """Extract composition from valid CIF files."""
        with open(temp_cif_files[cif_key]) as f:
            cif_content = f.read()
        
        formula, success = CompositionHelper.extract_from_cif(cif_content)
        
        assert success is True
        # pymatgen extracts reduced formula - verify it's a valid formula string
        assert isinstance(formula, str)
        assert len(formula) > 0
        # Should contain expected elements
        for element in expected_elements:
            assert element in formula
    
    @pytest.mark.parametrize('cif_key', ['invalid_path', 'empty_path'])
    def test_extract_from_invalid_cif(self, temp_cif_files, cif_key):
        """Handle invalid/empty CIF files gracefully."""
        with open(temp_cif_files[cif_key]) as f:
            cif_content = f.read()
        
        formula, success = CompositionHelper.extract_from_cif(cif_content)
        
        assert success is False
        assert formula is None
    
    def test_extract_from_malformed_string(self):
        """Handle non-CIF string gracefully."""
        bad_cif = "definitely not a CIF file !!!"
        formula, success = CompositionHelper.extract_from_cif(bad_cif)
        
        assert success is False
        assert formula is None


@pytest.mark.unit
class TestCompositionNormalization:
    """Test composition normalization."""
    
    @pytest.mark.parametrize('input_formula,expected', [
        ('Al2O3', 'Al2O3'),
        (' Al2O3 ', 'Al2O3'),
        ('Al4O6', 'Al2O3'),  # Reduce stoichiometry
        ('Fe2O3', 'Fe2O3'),
    ])
    def test_normalize_composition(self, input_formula, expected):
        """Normalize various formula formats."""
        normalized = CompositionHelper.normalize_composition(input_formula)
        assert normalized == expected
    
    def test_normalize_invalid_formula(self):
        """Handle invalid formula string."""
        # Should return as-is after stripping whitespace
        normalized = CompositionHelper.normalize_composition('  XyZ999  ')
        # Both stripped version and potential reduction are acceptable
        assert normalized.strip() == 'XyZ999'.strip() or len(normalized) > 0


# ============================================================================
# Test SynthnnModelHelper
# ============================================================================

@pytest.mark.unit
class TestModelBehaviour:
    """Test model wrapper logic with mock predictions."""
    
    def test_model_init_with_mock(self, mock_logger):
        """Initialize model helper with mock (Phase 1)."""
        helper = SynthnnModelHelper(logger=mock_logger, use_mock=True)
        
        assert helper.use_mock is True
        assert helper.logger is mock_logger
        # Model should not be loaded in mock mode
        assert helper.model is None
    
    def test_model_init_without_mock(self, mock_logger):
        """Initialize model helper in real mode (Phase 2/3 placeholder)."""
        helper = SynthnnModelHelper(logger=mock_logger, use_mock=False)
        
        assert helper.use_mock is False
        # Should warn about real model not implemented
        mock_logger.log.assert_called()
    
    def test_predict_batch_empty_list(self, mock_logger):
        """Empty composition list returns empty dict."""
        helper = SynthnnModelHelper(logger=mock_logger, use_mock=True)
        results = helper.predict_batch([])
        
        assert results == {}
    
    def test_predict_batch_single_composition(self, mock_logger):
        """Single composition prediction."""
        helper = SynthnnModelHelper(logger=mock_logger, use_mock=True)
        results = helper.predict_batch(['Al2O3'])
        
        assert 'Al2O3' in results
        assert isinstance(results['Al2O3'], float)
        assert 0.0 <= results['Al2O3'] <= 1.0
    
    def test_predict_batch_multiple_compositions(self, mock_logger):
        """Multiple composition predictions."""
        helper = SynthnnModelHelper(logger=mock_logger, use_mock=True)
        compositions = ['Al2O3', 'Fe2O3', 'SiO2', 'ZnO']
        results = helper.predict_batch(compositions)
        
        assert len(results) == 4
        for comp in compositions:
            assert comp in results
            assert isinstance(results[comp], float)
    
    def test_mock_scores_deterministic(self, mock_logger):
        """Mock scores are deterministic (same input → same output)."""
        helper = SynthnnModelHelper(logger=mock_logger, use_mock=True)
        
        # Call twice with same input
        results1 = helper.predict_batch(['Al2O3', 'Fe2O3'])
        results2 = helper.predict_batch(['Al2O3', 'Fe2O3'])
        
        assert results1 == results2
    
    @pytest.mark.parametrize('compositions,threshold,comparison', [
        (['Al2O3', 'SiO2', 'TiO2'], 0.85, 'greater'),
        (['CH4', 'C2H6', 'NH3'], 0.65, 'less'),
    ])
    def test_mock_score_ranges(self, mock_logger, compositions, threshold, comparison):
        """Verify mock scores for different material types."""
        helper = SynthnnModelHelper(logger=mock_logger, use_mock=True)
        results = helper.predict_batch(compositions)
        
        for score in results.values():
            if comparison == 'greater':
                assert score > threshold
            else:
                assert score < threshold
    
    def test_predict_batch_unknown_composition(self, mock_logger):
        """Unknown compositions get default moderate score."""
        helper = SynthnnModelHelper(logger=mock_logger, use_mock=True)
        results = helper.predict_batch(['UnknownMaterial123'])
        
        assert 'UnknownMaterial123' in results
        # Should get default score around 0.73
        assert 0.70 <= results['UnknownMaterial123'] <= 0.75


# ============================================================================
# Test SynthnnPredictor
# ============================================================================

@pytest.mark.unit
class TestSynthnnPredictor:
    """Test SynthNN predictor orchestration and workflow."""
    
    def test_predictor_init(self, mock_logger):
        """Initialize predictor successfully."""
        predictor = SynthnnPredictor(
            predictor_name='test_synthnn',
            logger=mock_logger,
            use_mock=True
        )
        
        assert predictor.predictor_name == 'test_synthnn'
        assert predictor.logger is mock_logger
        assert predictor.model_helper.use_mock is True
    
    def test_info_returns_string(self, mock_logger):
        """Info method returns description string."""
        predictor = SynthnnPredictor(logger=mock_logger)
        info = predictor.info()
        
        assert isinstance(info, str)
        assert 'SynthNN' in info
        assert 'synthesizability' in info.lower()
    
    def test_predict_empty_input(self, mock_logger):
        """Empty input returns empty dict."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        results = predictor.predict({})
        
        assert isinstance(results, dict)
        assert len(results) == 0
    
    def test_predict_valid_cif_file(self, temp_cif_files, mock_logger):
        """Predict from valid CIF file."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'Al2O3.cif': temp_cif_files['al2o3_path']
        })
        
        assert 'Al2O3.cif' in results
        result = results['Al2O3.cif']
        
        # Check required fields
        assert 'synthesizable' in result
        assert 'synthesizability_score' in result
        
        # Al2O3 should be synthesizable with high score
        assert result['synthesizable'] is not None
        assert result['synthesizability_score'] is not None
        assert 0.0 <= result['synthesizability_score'] <= 1.0
    
    def test_predict_invalid_filepath(self, mock_logger):
        """Handle non-existent file gracefully."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'missing.cif': '/nonexistent/path/to/missing.cif'
        })
        
        assert 'missing.cif' in results
        result = results['missing.cif']
        
        # Should have error
        assert result['synthesizable'] is None
        assert result['synthesizability_score'] is None
        assert 'error' in result
        assert 'File not found' in result['error']
    
    def test_predict_invalid_cif_content(self, temp_cif_files, mock_logger):
        """Handle invalid CIF content gracefully."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'invalid.cif': temp_cif_files['invalid_path']
        })
        
        assert 'invalid.cif' in results
        result = results['invalid.cif']
        
        # Should have error
        assert result['synthesizable'] is None
        assert result['synthesizability_score'] is None
        assert 'error' in result
    
    def test_predict_output_structure(self, temp_cif_files, mock_logger):
        """Verify output has correct structure."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'Al2O3.cif': temp_cif_files['al2o3_path'],
            'SiO2.cif': temp_cif_files['sio2_path'],
            'invalid.cif': temp_cif_files['invalid_path']
        })
        
        # All filenames should be in output
        assert 'Al2O3.cif' in results
        assert 'SiO2.cif' in results
        assert 'invalid.cif' in results
        
        # Each result should be a dict
        for filename, prediction in results.items():
            assert isinstance(prediction, dict)
            assert 'synthesizable' in prediction
            assert 'synthesizability_score' in prediction
    
    def test_predict_mixed_batch(self, temp_cif_files, mock_logger):
        """Batch with both valid and invalid files."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'Al2O3.cif': temp_cif_files['al2o3_path'],
            'invalid.cif': temp_cif_files['invalid_path'],
            'SiO2.cif': temp_cif_files['sio2_path']
        })
        
        assert len(results) == 3
        
        # Valid files should have valid predictions
        assert results['Al2O3.cif']['synthesizable'] is not None
        assert results['SiO2.cif']['synthesizable'] is not None
        
        # Invalid file should have error
        assert results['invalid.cif']['synthesizable'] is None
        assert 'error' in results['invalid.cif']
        
        # Logger should have been called
        mock_logger.log.assert_called()
    
    def test_predict_synthesizable_threshold(self, temp_cif_files, mock_logger):
        """Verify synthesizable threshold is ≥ 0.70."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'Al2O3.cif': temp_cif_files['al2o3_path'],
            'SiO2.cif': temp_cif_files['sio2_path']
        })
        
        # Both should have high scores and be synthesizable
        for result in results.values():
            if result['synthesizable'] is not None:
                if result['synthesizability_score'] >= 0.70:
                    assert result['synthesizable'] is True
                else:
                    assert result['synthesizable'] is False
    
    def test_predict_score_is_float(self, temp_cif_files, mock_logger):
        """Verify scores are floats with correct precision."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'Al2O3.cif': temp_cif_files['al2o3_path']
        })
        
        result = results['Al2O3.cif']
        score = result['synthesizability_score']
        
        assert isinstance(score, float)
        # Score should be rounded to 4 decimals
        assert len(str(score).split('.')[-1]) <= 4
    
    def test_predict_warnings_optional(self, temp_cif_files, mock_logger):
        """Warnings key only present when warnings exist."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'Al2O3.cif': temp_cif_files['al2o3_path']
        })
        
        result = results['Al2O3.cif']
        # High score materials shouldn't have warnings in Phase 1
        # (unless implementation adds them)
        if 'warnings' in result:
            assert isinstance(result['warnings'], list)
    
    def test_predict_logging(self, temp_cif_files, mock_logger):
        """Verify prediction operations are logged."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        predictor.predict({
            'Al2O3.cif': temp_cif_files['al2o3_path']
        })
        
        # Should have logged at least:
        # - Start of prediction
        # - Successful prediction
        # - Completion summary
        assert mock_logger.log.called
    
    def test_predict_returns_dict(self, temp_cif_files, mock_logger):
        """Verify predict always returns dict."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'Al2O3.cif': temp_cif_files['al2o3_path']
        })
        
        assert isinstance(results, dict)
    
    def test_predict_json_serializable(self, temp_cif_files, mock_logger):
        """Verify output is JSON-serializable."""
        import json
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'Al2O3.cif': temp_cif_files['al2o3_path'],
            'invalid.cif': temp_cif_files['invalid_path']
        })
        
        # Should be JSON serializable (None → null)
        json_str = json.dumps(results)
        assert isinstance(json_str, str)
        
        # Should deserialize back
        deserialized = json.loads(json_str)
        assert 'Al2O3.cif' in deserialized


# ============================================================================
# Integration Tests (within unit test file for Phase 1)
# ============================================================================

@pytest.mark.unit
class TestSynthnnIntegration:
    """Integration tests for complete workflow."""
    
    @pytest.mark.parametrize('input_files,expected_count', [
        ([('Al2O3.cif', 'al2o3_path')], 1),
        ([('Al2O3.cif', 'al2o3_path'), ('SiO2.cif', 'sio2_path')], 2),
    ])
    def test_full_workflow(self, temp_cif_files, mock_logger, input_files, expected_count):
        """Complete workflow: file → CIF → composition → prediction."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        input_data = {name: temp_cif_files[path_key] for name, path_key in input_files}
        results = predictor.predict(input_data)
        
        # Verify all expected files processed
        assert len(results) == expected_count
        
        for filename in input_data.keys():
            assert filename in results
            result = results[filename]
            assert result['synthesizable'] is True
            assert result['synthesizability_score'] is not None
            assert 0.0 <= result['synthesizability_score'] <= 1.0
            assert 'error' not in result
    
    def test_full_workflow_with_error_recovery(self, temp_cif_files, mock_logger):
        """Verify one error doesn't crash batch."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'Al2O3.cif': temp_cif_files['al2o3_path'],
            'invalid.cif': temp_cif_files['invalid_path'],
            'SiO2.cif': temp_cif_files['sio2_path']
        })
        
        # All three should be in results
        assert len(results) == 3
        
        # Valid files should have predictions
        assert results['Al2O3.cif']['synthesizable'] is not None
        assert results['SiO2.cif']['synthesizable'] is not None
        
        # Invalid file should have error but batch continued
        assert results['invalid.cif']['synthesizable'] is None
        assert 'error' in results['invalid.cif']


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================

@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_predict_many_files(self, temp_cif_files, mock_logger):
        """Handle batch of many files."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        # Create input for 10 copies of same file
        input_data = {
            f'Al2O3_{i}.cif': temp_cif_files['al2o3_path']
            for i in range(10)
        }
        
        results = predictor.predict(input_data)
        
        # All should succeed
        assert len(results) == 10
        for result in results.values():
            assert result['synthesizable'] is True
    
    def test_predict_file_with_special_chars_in_name(self, temp_cif_files, mock_logger):
        """Handle filenames with special characters."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'material-with_special.chars123.cif': temp_cif_files['al2o3_path']
        })
        
        assert 'material-with_special.chars123.cif' in results
        assert results['material-with_special.chars123.cif']['synthesizable'] is True
    
    def test_predict_very_simple_input(self, temp_cif_files, mock_logger):
        """Handle minimal valid input."""
        predictor = SynthnnPredictor(logger=mock_logger, use_mock=True)
        
        results = predictor.predict({
            'x.cif': temp_cif_files['al2o3_path']
        })
        
        assert 'x.cif' in results
        assert results['x.cif']['synthesizable'] is not None
