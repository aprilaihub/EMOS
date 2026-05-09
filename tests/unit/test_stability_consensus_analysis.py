"""
Unit tests for Stability Consensus Analysis feature.

Tests cover:
- Stability threshold evaluation for databases (hull distance, energy above hull)
- Stability threshold evaluation for predictors (max relaxed force)
- Consensus summary computation
- Error handling and edge cases
"""

import pytest
from Features.Materials_Exploration.StabilityConsensusAnalysis.StabilityConsensusAnalysisFeature import (
    StabilityConsensusAnalysisFeature
)


class TestStabilityThresholds:
    """Test stability evaluation thresholds."""
    
    def test_stability_thresholds_defined(self):
        """Verify stability thresholds are properly defined."""
        feature = StabilityConsensusAnalysisFeature()
        
        assert 'materialsproject' in feature.STABILITY_THRESHOLDS
        assert 'alexandria' in feature.STABILITY_THRESHOLDS
        assert 'mattersim' in feature.STABILITY_THRESHOLDS
        assert 'chgnet' in feature.STABILITY_THRESHOLDS
        
        # Verify each source has required fields
        for source, cfg in feature.STABILITY_THRESHOLDS.items():
            assert 'metric' in cfg
            assert 'threshold' in cfg
            assert 'unit' in cfg
            assert 'description' in cfg


class TestDatabaseStabilityEvaluation:
    """Test database stability evaluation logic."""
    
    def test_evaluate_stable_materialsproject(self):
        """Test evaluation of stable structure (Materials Project)."""
        feature = StabilityConsensusAnalysisFeature()
        
        db_result = {
            'source': 'materialsproject',
            'queries': {'energy_above_hull_r2scan': 0.02},  # Below 0.05 threshold
            'cif_strings': ['CIF_DATA_1']
        }
        
        result = feature._evaluate_database_stability('materialsproject', db_result)
        
        assert result['status'] == 'success'
        assert '✅' in result['stability']
        assert result['raw_value'] == 0.02
        assert result['threshold'] == 0.05
        assert result['num_matches'] == 1
    
    def test_evaluate_unstable_materialsproject(self):
        """Test evaluation of unstable structure (Materials Project)."""
        feature = StabilityConsensusAnalysisFeature()
        
        db_result = {
            'source': 'materialsproject',
            'queries': {'energy_above_hull_r2scan': 0.15},  # Above 0.05 threshold
            'cif_strings': ['CIF_DATA_1']
        }
        
        result = feature._evaluate_database_stability('materialsproject', db_result)
        
        assert result['status'] == 'success'
        assert '❌' in result['stability']
        assert result['raw_value'] == 0.15
    
    def test_evaluate_stable_alexandria(self):
        """Test evaluation of stable structure (Alexandria)."""
        feature = StabilityConsensusAnalysisFeature()
        
        db_result = {
            'source': 'alexandria',
            'queries': {'hull_distance': 0.03},  # Below 0.05 threshold
            'cif_strings': ['CIF_DATA_1']
        }
        
        result = feature._evaluate_database_stability('alexandria', db_result)
        
        assert result['status'] == 'success'
        assert '✅' in result['stability']
        assert result['raw_value'] == 0.03
    
    def test_evaluate_no_matches(self):
        """Test evaluation when no structures found."""
        feature = StabilityConsensusAnalysisFeature()
        
        db_result = {
            'source': 'materialsproject',
            'queries': {},
            'cif_strings': []
        }
        
        result = feature._evaluate_database_stability('materialsproject', db_result)
        
        assert result['status'] == 'no_matches'
        assert result['stability'] is None
    
    def test_evaluate_metric_unavailable(self):
        """Test evaluation when stability metric is unavailable."""
        feature = StabilityConsensusAnalysisFeature()
        
        db_result = {
            'source': 'materialsproject',
            'queries': {},  # Missing energy_above_hull_r2scan
            'cif_strings': ['CIF_DATA_1']
        }
        
        result = feature._evaluate_database_stability('materialsproject', db_result)
        
        assert result['status'] == 'metric_unavailable'
        assert result['stability'] is None


class TestPredictorStabilityEvaluation:
    """Test predictor stability evaluation logic."""
    
    def test_evaluate_stable_predictor(self):
        """Test evaluation of stable structure (predictor - low forces)."""
        feature = StabilityConsensusAnalysisFeature()
        
        pred_result = {
            'source': 'mattersim',
            'results': [
                {
                    'index': 0,
                    'status': 'success',
                    'properties': {
                        'energy': -10.5,
                        'relaxed_energy': -10.45,
                        'forces': [[0.001, 0.002, 0.001], [0.002, 0.001, 0.002]],
                        'relaxed_forces': [[0.01, 0.02, 0.015], [0.02, 0.015, 0.025]],
                        'stress': [[0.1, 0.05, 0.02], [0.05, 0.1, 0.03], [0.02, 0.03, 0.1]],
                        'relaxed_stress': [[0.05, 0.02, 0.01], [0.02, 0.05, 0.01], [0.01, 0.01, 0.05]],
                        'num_atoms': 4,
                        'relaxed_cif': 'RELAXED_CIF_DATA'
                    },
                    'error': None
                }
            ]
        }
        
        result = feature._evaluate_predictor_stability('mattersim', pred_result)
        
        assert result['status'] == 'success'
        assert '✅' in result['stability']
        assert result['raw_value'] == 0.025  # max force is 0.025, below 0.05
        assert result['threshold'] == 0.05
    
    def test_evaluate_unstable_predictor(self):
        """Test evaluation of unstable structure (predictor - high forces)."""
        feature = StabilityConsensusAnalysisFeature()
        
        pred_result = {
            'source': 'chgnet',
            'results': [
                {
                    'index': 0,
                    'status': 'success',
                    'properties': {
                        'energy': -15.2,
                        'relaxed_energy': -14.8,
                        'forces': [[0.1, 0.15, 0.12]],
                        'relaxed_forces': [[0.12, 0.18, 0.15]],
                        'stress': [[0.5, 0.2, 0.1], [0.2, 0.5, 0.15], [0.1, 0.15, 0.5]],
                        'relaxed_stress': [[0.3, 0.1, 0.05], [0.1, 0.3, 0.08], [0.05, 0.08, 0.3]],
                        'num_atoms': 8,
                        'relaxed_cif': 'RELAXED_CIF_DATA'
                    },
                    'error': None
                }
            ]
        }
        
        result = feature._evaluate_predictor_stability('chgnet', pred_result)
        
        assert result['status'] == 'success'
        assert '❌' in result['stability']
        assert result['raw_value'] == 0.18  # max force is 0.18, above 0.05
    
    def test_evaluate_predictor_error(self):
        """Test evaluation when predictor fails."""
        feature = StabilityConsensusAnalysisFeature()
        
        pred_result = {
            'source': 'mattersim',
            'results': [
                {
                    'index': 0,
                    'status': 'error',
                    'properties': {},
                    'error': 'Invalid structure for relaxation'
                }
            ]
        }
        
        result = feature._evaluate_predictor_stability('mattersim', pred_result)
        
        assert result['status'] == 'prediction_error'
        assert result['stability'] is None
        assert result['error'] == 'Invalid structure for relaxation'
    
    def test_evaluate_no_results(self):
        """Test evaluation when predictor returns no results."""
        feature = StabilityConsensusAnalysisFeature()
        
        pred_result = {
            'source': 'mattersim',
            'results': []
        }
        
        result = feature._evaluate_predictor_stability('mattersim', pred_result)
        
        assert result['status'] == 'no_results'
        assert result['stability'] is None
    
    def test_evaluate_metric_unavailable_predictor(self):
        """Test evaluation when forces unavailable."""
        feature = StabilityConsensusAnalysisFeature()
        
        pred_result = {
            'source': 'mattersim',
            'results': [
                {
                    'index': 0,
                    'status': 'success',
                    'properties': {
                        'energy': -10.5,
                        'relaxed_energy': -10.45,
                        'relaxed_forces': [],  # Empty forces
                    },
                    'error': None
                }
            ]
        }
        
        result = feature._evaluate_predictor_stability('mattersim', pred_result)
        
        assert result['status'] == 'metric_unavailable'
        assert result['stability'] is None


class TestConsensusSummary:
    """Test consensus summary computation."""
    
    def test_all_stable_consensus(self):
        """Test consensus when all sources agree: stable."""
        feature = StabilityConsensusAnalysisFeature()
        
        sources = {
            'materialsproject': {'stability': '✅ Stable'},
            'alexandria': {'stability': '✅ Stable'},
            'mattersim': {'stability': '✅ Stable'},
            'chgnet': {'stability': '✅ Stable'},
        }
        
        summary = feature._compute_consensus_summary(sources)
        
        assert 'All sources agree: Stable' in summary['consensus']
        assert summary['stable_count'] == 4
        assert summary['unstable_count'] == 0
    
    def test_all_unstable_consensus(self):
        """Test consensus when all sources agree: unstable."""
        feature = StabilityConsensusAnalysisFeature()
        
        sources = {
            'materialsproject': {'stability': '❌ Unstable'},
            'alexandria': {'stability': '❌ Unstable'},
            'mattersim': {'stability': '❌ Unstable'},
            'chgnet': {'stability': '❌ Unstable'},
        }
        
        summary = feature._compute_consensus_summary(sources)
        
        assert 'All sources agree: Unstable' in summary['consensus']
        assert summary['stable_count'] == 0
        assert summary['unstable_count'] == 4
    
    def test_mixed_consensus(self):
        """Test consensus with mixed opinions."""
        feature = StabilityConsensusAnalysisFeature()
        
        sources = {
            'materialsproject': {'stability': '✅ Stable'},
            'alexandria': {'stability': '✅ Stable'},
            'mattersim': {'stability': '❌ Unstable'},
            'chgnet': {'stability': '❌ Unstable'},
        }
        
        summary = feature._compute_consensus_summary(sources)
        
        assert 'Mixed opinion' in summary['consensus']
        assert summary['stable_count'] == 2
        assert summary['unstable_count'] == 2
    
    def test_consensus_with_errors(self):
        """Test consensus computation with error sources."""
        feature = StabilityConsensusAnalysisFeature()
        
        sources = {
            'materialsproject': {'stability': '✅ Stable'},
            'alexandria': {'stability': 'Error'},
            'mattersim': {'stability': '❌ Unstable'},
        }
        
        summary = feature._compute_consensus_summary(sources)
        
        assert summary['stable_count'] == 1
        assert summary['unstable_count'] == 1
        assert summary['error_count'] == 1
    
    def test_empty_sources_consensus(self):
        """Test consensus with no sources."""
        feature = StabilityConsensusAnalysisFeature()
        
        sources = {}
        
        summary = feature._compute_consensus_summary(sources)
        
        assert summary['total_sources'] == 0
        assert 'Insufficient data' in summary['consensus']


class TestInputExtraction:
    """Test input extraction from frontend data."""
    
    def test_extract_inputs(self):
        """Test proper extraction of input parameters."""
        feature = StabilityConsensusAnalysisFeature()
        
        input_data = {
            'cif_file': 'cif_content_here',
            'active_databases': [
                {'value': 'materialsproject', 'name': 'Materials Project'}
            ],
            'active_predictors': [
                {'value': 'mattersim', 'name': 'MatterSim'}
            ]
        }
        
        extracted = feature.extract_inputs(input_data)
        
        assert extracted['cif_file'] == 'cif_content_here'
        assert len(extracted['active_databases']) == 1
        assert len(extracted['active_predictors']) == 1
    
    def test_extract_inputs_defaults(self):
        """Test that defaults are used for missing inputs."""
        feature = StabilityConsensusAnalysisFeature()
        
        input_data = {}
        
        extracted = feature.extract_inputs(input_data)
        
        assert extracted['cif_file'] == ''
        assert extracted['active_databases'] == []
        assert extracted['active_predictors'] == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
