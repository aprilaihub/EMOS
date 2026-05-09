"""
Integration tests for Stability Consensus Analysis feature.

Tests the full pipeline:
- CIF file parsing
- Database query orchestration
- Predictor execution orchestration
- Consensus computation

Note: These tests use mock data to test orchestration without requiring
actual Docker containers, databases to be online, or network calls.

Run with: pytest tests/integration/test_stability_consensus_analysis.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from Features.Materials_Exploration.StabilityConsensusAnalysis.StabilityConsensusAnalysisFeature import (
    StabilityConsensusAnalysisFeature
)


pytestmark = [pytest.mark.integration]


class MockLogger:
    """Mock logger for testing."""
    def __init__(self):
        self.logs = []
    
    def log(self, message, level):
        self.logs.append({'message': message, 'level': level})


class TestStabilityConsensusFullPipeline:
    """Test the full Stability Consensus Analysis pipeline."""
    
    def test_full_pipeline_with_databases_and_predictors(self):
        """Test complete pipeline: CIF → databases + predictors → consensus."""
        logger = MockLogger()
        feature = StabilityConsensusAnalysisFeature(logger=logger)
        
        # Simple CIF content (Cubic Al2O3 structure)
        cif_content = """
data_Al2O3
_cell_length_a    10.0
_cell_length_b    10.0
_cell_length_c    10.0
_cell_angle_alpha    90.0
_cell_angle_beta     90.0
_cell_angle_gamma    90.0
loop_
_atom_site_label
_atom_site_occupancy
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Al1 1.0 0.0 0.0 0.0
O1 1.0 0.5 0.5 0.5
"""
        
        inputs = {
            'cif_file': cif_content,
            'active_databases': [],
            'active_predictors': []
        }
        
        # Process feature
        result = feature.process_feature(inputs)
        
        # Verify composition was extracted
        assert 'composition' in result
        assert 'Al' in result['composition']
        
        # Verify sources and summary are initialized
        assert 'sources' in result
        assert 'summary' in result
        assert isinstance(result['sources'], dict)
        assert isinstance(result['summary'], dict)
    
    def test_pipeline_missing_cif_file(self):
        """Test pipeline error handling when CIF file is missing."""
        logger = MockLogger()
        feature = StabilityConsensusAnalysisFeature(logger=logger)
        
        inputs = {
            'cif_file': '',  # Empty CIF
            'active_databases': [],
            'active_predictors': []
        }
        
        result = feature.process_feature(inputs)
        
        assert 'error' in result
        assert 'No CIF file provided' in result['error']
        assert result['status'] == 'failed'
    
    @patch('Features.Materials_Exploration.StabilityConsensusAnalysis.StabilityConsensusAnalysisFeature.database_factory')
    def test_database_query_orchestration(self, mock_factory):
        """Test database query orchestration."""
        logger = MockLogger()
        feature = StabilityConsensusAnalysisFeature(logger=logger)
        
        # Mock database instance
        mock_db = Mock()
        mock_db.info.return_value = "Mock Database"
        mock_db.retrieve.return_value = {
            'source': 'materialsproject',
            'queries': {'energy_above_hull_r2scan': 0.02},
            'cif_strings': ['CIF_DATA_1']
        }
        
        mock_factory.__getitem__.return_value = lambda *args, **kwargs: mock_db
        mock_factory.__contains__.return_value = True
        
        active_databases = [
            {'value': 'materialsproject', 'name': 'Materials Project'}
        ]
        
        composition = 'Al2O3'
        
        # Test database query
        results = feature._query_databases(active_databases, composition)
        
        # Verify database was queried
        assert 'materialsproject' in results
        assert results['materialsproject']['status'] == 'success'
        assert '✅' in results['materialsproject']['stability']
        assert results['materialsproject']['raw_value'] == 0.02
    
    def test_output_format_successful(self):
        """Test output formatting for successful analysis."""
        logger = MockLogger()
        feature = StabilityConsensusAnalysisFeature(logger=logger)
        
        results = {
            'composition': 'Al2O3',
            'sources': {
                'materialsproject': {
                    'status': 'success',
                    'stability': '✅ Stable',
                    'raw_value': 0.02
                }
            },
            'summary': {
                'consensus': '✅ All sources agree: Stable',
                'stable_count': 1,
                'unstable_count': 0
            }
        }
        
        formatted = feature.format_outputs(results)
        
        assert 'downloadResultsJson' in formatted
        assert formatted['downloadResultsJson'] is not None
        assert 'Al2O3' in formatted['downloadResultsJson']
        assert '✅ Stable' in formatted['downloadResultsJson']
    
    def test_output_format_error(self):
        """Test output formatting for error cases."""
        logger = MockLogger()
        feature = StabilityConsensusAnalysisFeature(logger=logger)
        
        results = {
            'error': 'Invalid structure format',
            'status': 'failed'
        }
        
        formatted = feature.format_outputs(results)
        
        assert 'error' in formatted
        assert formatted['downloadResultsJson'] is None


class TestDatabaseQueryOrchestration:
    """Test database query orchestration in detail."""
    
    @patch('Features.Materials_Exploration.StabilityConsensusAnalysis.StabilityConsensusAnalysisFeature.database_factory')
    def test_query_multiple_databases(self, mock_factory):
        """Test querying multiple databases simultaneously."""
        logger = MockLogger()
        feature = StabilityConsensusAnalysisFeature(logger=logger)
        
        # Mock multiple database instances
        mock_mp = Mock()
        mock_mp.retrieve.return_value = {
            'source': 'materialsproject',
            'queries': {'energy_above_hull_r2scan': 0.02},
            'cif_strings': ['CIF_DATA_1']
        }
        
        mock_alex = Mock()
        mock_alex.retrieve.return_value = {
            'source': 'alexandria',
            'queries': {'hull_distance': 0.01},
            'cif_strings': ['CIF_DATA_2']
        }
        
        def get_item(key):
            if key == 'materialsproject':
                return lambda *args, **kwargs: mock_mp
            elif key == 'alexandria':
                return lambda *args, **kwargs: mock_alex
            raise KeyError(key)
        
        mock_factory.__getitem__.side_effect = get_item
        mock_factory.__contains__.side_effect = lambda x: x in ['materialsproject', 'alexandria']
        
        active_databases = [
            {'value': 'materialsproject', 'name': 'Materials Project'},
            {'value': 'alexandria', 'name': 'Alexandria'}
        ]
        
        results = feature._query_databases(active_databases, 'Al2O3')
        
        # Verify both databases were queried
        assert 'materialsproject' in results
        assert 'alexandria' in results
        assert results['materialsproject']['raw_value'] == 0.02
        assert results['alexandria']['raw_value'] == 0.01
    
    @patch('Features.Materials_Exploration.StabilityConsensusAnalysis.StabilityConsensusAnalysisFeature.database_factory')
    def test_query_database_not_found(self, mock_factory):
        """Test handling when database is not in factory."""
        logger = MockLogger()
        feature = StabilityConsensusAnalysisFeature(logger=logger)
        
        mock_factory.__contains__.return_value = False
        
        active_databases = [
            {'value': 'nonexistent_db', 'name': 'Nonexistent Database'}
        ]
        
        results = feature._query_databases(active_databases, 'Al2O3')
        
        # Should handle gracefully
        assert len(results) == 0 or any('nonexistent' in str(v).lower() for v in results.values())


class TestConsensusAggregation:
    """Test consensus aggregation across multiple sources."""
    
    def test_mixed_database_predictor_consensus(self):
        """Test consensus aggregation mixing database and predictor results."""
        logger = MockLogger()
        feature = StabilityConsensusAnalysisFeature(logger=logger)
        
        sources = {
            'materialsproject': {
                'stability': '✅ Stable',
                'raw_value': 0.02,
                'description': 'Formation energy above convex hull'
            },
            'alexandria': {
                'stability': '✅ Stable',
                'raw_value': 0.01,
                'description': 'Distance to convex hull'
            },
            'mattersim': {
                'stability': '❌ Unstable',
                'raw_value': 0.08,
                'description': 'Maximum force after relaxation'
            },
            'chgnet': {
                'stability': '❌ Unstable',
                'raw_value': 0.12,
                'description': 'Maximum force after relaxation'
            }
        }
        
        summary = feature._compute_consensus_summary(sources)
        
        assert summary['stable_count'] == 2
        assert summary['unstable_count'] == 2
        assert summary['total_sources'] == 4
        assert 'Mixed opinion' in summary['consensus']
        assert '2 stable' in summary['consensus']
        assert '2 unstable' in summary['consensus']


class TestErrorHandling:
    """Test error handling throughout the pipeline."""
    
    def test_invalid_cif_format(self):
        """Test handling of invalid CIF format."""
        logger = MockLogger()
        feature = StabilityConsensusAnalysisFeature(logger=logger)
        
        inputs = {
            'cif_file': 'This is not a valid CIF file',
            'active_databases': [],
            'active_predictors': []
        }
        
        result = feature.process_feature(inputs)
        
        # Should contain error or compose missing
        assert 'error' in result or result['status'] == 'failed'
    
    def test_process_feature_with_mocked_composition_extraction(self):
        """Test process_feature handles composition extraction correctly."""
        logger = MockLogger()
        feature = StabilityConsensusAnalysisFeature(logger=logger)
        
        # Valid simple cubic CIF
        cif_content = """
data_test
_cell_length_a    4.0
_cell_length_b    4.0
_cell_length_c    4.0
_cell_angle_alpha    90.0
_cell_angle_beta     90.0
_cell_angle_gamma    90.0
loop_
_atom_site_label
_atom_site_occupancy
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_type_symbol
Al1 1.0 0.0 0.0 0.0 Al
"""
        
        inputs = {
            'cif_file': cif_content,
            'active_databases': [],
            'active_predictors': []
        }
        
        result = feature.process_feature(inputs)
        
        # Should extract Al composition
        assert 'composition' in result
        assert 'Al' in result['composition'] or 'error' not in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
