"""
Unit tests for Stability Consensus Analysis feature.

Tests cover:
- Stability threshold evaluation for databases (hull distance, energy above hull)
- Stability threshold evaluation for predictors (max relaxed force)
- Consensus summary computation
- Error handling and edge cases
"""

import json

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
            'queries': {'energy_above_hull_r2scan': [0.0, 0.05]},
            'entries': [{'energy_above_hull_r2scan': 0.02}],
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
            'queries': {'energy_above_hull_r2scan': [0.0, 0.05]},
            'entries': [{'energy_above_hull_r2scan': 0.15}],
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
            'queries': {'hull_distance': [0.0, 0.05]},
            'entries': [{'hull_distance': 0.03}],
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

    def test_evaluate_threshold_filtered_no_matches_reports_not_found(self):
        """Test threshold-filtered no-match responses are classified as not_found."""
        feature = StabilityConsensusAnalysisFeature()

        db_result = {
            'source': 'alexandria',
            'queries': {'hull_distance': [0.0, 0.05]},
            'entries': [],
            'cif_strings': []
        }

        result = feature._evaluate_database_stability('alexandria', db_result)

        assert result['status'] == 'not_found'
        assert 'Not found' in result['stability']
        assert result['num_matches'] == 0
    
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
        """Test evaluation of stable structure (predictor - negative DeltaHf)."""
        feature = StabilityConsensusAnalysisFeature()
        element_fractions = {'Li': 0.5, 'O': 0.5}
        element_order = ['Li', 'O']
        
        pred_result = {
            'source': 'mattersim',
            'results': [
                {
                    'index': 0,
                    'status': 'success',
                    'properties': {
                        'relaxed_energy': -8.8,
                        'num_atoms': 4,
                    },
                    'error': None
                },
                {
                    'index': 1,
                    'status': 'success',
                    'properties': {
                        'relaxed_energy': -4.0,
                        'num_atoms': 2,
                    },
                    'error': None
                },
                {
                    'index': 2,
                    'status': 'success',
                    'properties': {
                        'relaxed_energy': -4.4,
                        'num_atoms': 2,
                    },
                    'error': None
                }
            ]
        }
        
        result = feature._evaluate_predictor_stability('mattersim', pred_result, element_fractions, element_order)
        
        assert result['status'] == 'success'
        assert '✅' in result['stability']
        assert result['raw_value'] == -0.1
        assert result['threshold'] == 0.0
    
    def test_evaluate_unstable_predictor(self):
        """Test evaluation of unstable structure (predictor - positive DeltaHf)."""
        feature = StabilityConsensusAnalysisFeature()
        element_fractions = {'Li': 0.5, 'O': 0.5}
        element_order = ['Li', 'O']
        
        pred_result = {
            'source': 'chgnet',
            'results': [
                {
                    'index': 0,
                    'status': 'success',
                    'properties': {
                        'relaxed_energy': -7.6,
                        'num_atoms': 4,
                    },
                    'error': None
                },
                {
                    'index': 1,
                    'status': 'success',
                    'properties': {
                        'relaxed_energy': -4.0,
                        'num_atoms': 2,
                    },
                    'error': None
                },
                {
                    'index': 2,
                    'status': 'success',
                    'properties': {
                        'relaxed_energy': -4.4,
                        'num_atoms': 2,
                    },
                    'error': None
                }
            ]
        }
        
        result = feature._evaluate_predictor_stability('chgnet', pred_result, element_fractions, element_order)
        
        assert result['status'] == 'success'
        assert '❌' in result['stability']
        assert result['raw_value'] == 0.2
    
    def test_evaluate_predictor_error(self):
        """Test evaluation when predictor fails."""
        feature = StabilityConsensusAnalysisFeature()
        element_fractions = {'Li': 0.5, 'O': 0.5}
        element_order = ['Li', 'O']
        
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
        
        result = feature._evaluate_predictor_stability('mattersim', pred_result, element_fractions, element_order)
        
        assert result['status'] == 'prediction_error'
        assert result['stability'] is None
        assert result['error'] == 'Invalid structure for relaxation'
    
    def test_evaluate_no_results(self):
        """Test evaluation when predictor returns no results."""
        feature = StabilityConsensusAnalysisFeature()
        element_fractions = {'Li': 0.5, 'O': 0.5}
        element_order = ['Li', 'O']
        
        pred_result = {
            'source': 'mattersim',
            'results': []
        }
        
        result = feature._evaluate_predictor_stability('mattersim', pred_result, element_fractions, element_order)
        
        assert result['status'] == 'no_results'
        assert result['stability'] is None
    
    def test_evaluate_metric_unavailable_predictor(self):
        """Test evaluation when predictor energy is unavailable."""
        feature = StabilityConsensusAnalysisFeature()
        element_fractions = {'Li': 0.5, 'O': 0.5}
        element_order = ['Li', 'O']
        
        pred_result = {
            'source': 'mattersim',
            'results': [
                {
                    'index': 0,
                    'status': 'success',
                    'properties': {},
                    'error': None
                }
            ]
        }
        
        result = feature._evaluate_predictor_stability('mattersim', pred_result, element_fractions, element_order)
        
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

    def test_plot_data_includes_not_found_as_error_count(self):
        """Test plot data tracks not_found entries as grey/error segments."""
        feature = StabilityConsensusAnalysisFeature()

        results_per_cif = [
            {
                'sources': {
                    'materialsproject': {'stability': '✅ Stable'},
                    'alexandria': {'stability': '⚠️ Not found'},
                    'mattersim': {'stability': '❌ Unstable'},
                }
            }
        ]

        plot_data = feature._compute_source_plot_data(results_per_cif)

        assert plot_data['materialsproject']['stable_count'] == 1
        assert plot_data['alexandria']['error_count'] == 1
        assert plot_data['alexandria']['error_pct'] == 100.0
        assert plot_data['mattersim']['unstable_count'] == 1


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


class TestCancellation:
    """Test cancellation of an active stability analysis."""

    def test_cancel_sets_the_signal(self):
        feature = StabilityConsensusAnalysisFeature()

        response = feature.cancel()

        assert response['status'] == 'cancelled'
        assert feature._cancel_event.is_set()

    def test_cancel_stops_the_batch_before_the_next_cif(self, monkeypatch):
        feature = StabilityConsensusAnalysisFeature()
        processed = []

        def process_one(cif_name, *_args):
            processed.append(cif_name)
            feature.cancel()
            return {
                'cif_name': cif_name,
                'sources': {},
                'summary': feature._compute_consensus_summary({}),
            }

        monkeypatch.setattr(feature, '_process_single_cif', process_one)
        result = feature.process_feature({
            'cif_files': [
                {'name': 'first.cif', 'content': 'first'},
                {'name': 'second.cif', 'content': 'second'},
            ],
        })

        assert result['status'] == 'cancelled'
        assert processed == ['first.cif']

    def test_stream_returns_a_formatted_cancelled_result(self):
        feature = StabilityConsensusAnalysisFeature()
        feature.cancel()

        events = list(feature.process_feature_stream({'cif_file': 'unused'}))
        payload = json.loads(events[-1].split('data: ', 1)[1])

        assert events[0].startswith('event: log\n')
        assert payload['status'] == 'cancelled'
        assert payload['downloadResultsJson'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
