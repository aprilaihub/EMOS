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

import json
import threading
import time

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
            'queries': {'energy_above_hull_r2scan': [0.0, 0.05]},
            'entries': [{'energy_above_hull_r2scan': 0.02}],
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
                    'raw_value': 0.02,
                    'matched_entry_ids': ['mp-100', 'mp-200'],
                    'selected_entry_id': 'mp-200',
                }
            },
            'summary': {
                'consensus': '✅ All sources agree: Stable',
                'stable_count': 1,
                'unstable_count': 0
            },
            'plot_data': {'legacy': 'must not be downloaded'},
        }
        
        formatted = feature.format_outputs(results)
        
        assert 'downloadResultsJson' in formatted
        assert formatted['downloadResultsJson'] is not None
        assert 'Al2O3' in formatted['downloadResultsJson']
        assert '✅ Stable' in formatted['downloadResultsJson']
        downloaded = json.loads(formatted['downloadResultsJson'])
        assert 'plot_data' not in formatted
        assert 'plot_data' not in downloaded
        mp_result = downloaded['sources']['materialsproject']
        assert mp_result['matched_entry_ids'] == ['mp-100', 'mp-200']
        assert mp_result['selected_entry_id'] == 'mp-200'
    
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
            'queries': {'energy_above_hull_r2scan': [0.0, 0.05]},
            'entries': [{'energy_above_hull_r2scan': 0.02}],
            'cif_strings': ['CIF_DATA_1']
        }
        
        mock_alex = Mock()
        mock_alex.retrieve.return_value = {
            'source': 'alexandria',
            'queries': {'hull_distance': [0.0, 0.05]},
            'entries': [{'hull_distance': 0.01}],
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
        
        # Invalid CIF may be returned as a per-file failure in batch_summary
        assert (
            'error' in result
            or result.get('status') == 'failed'
            or result.get('batch_summary', {}).get('failed_files', 0) >= 1
        )
    
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


class TestCancellationFlow:
    """Exercise the same stream and cancel endpoints used by the UI."""

    def test_cancel_endpoint_stops_the_streamed_feature(self):
        from backend import app as backend_app

        started = threading.Event()
        streamed_events = []

        class SlowFeature(StabilityConsensusAnalysisFeature):
            def _process_single_cif(self, cif_name, *_args):
                started.set()
                while True:
                    self._check_cancelled()
                    time.sleep(0.01)

        def consume_stream():
            with backend_app.app.test_client() as client:
                response = client.post(
                    '/api/process/2/stream',
                    json={'cif_files': [{'name': 'slow.cif', 'content': 'unused'}]},
                    buffered=False,
                )
                streamed_events.extend(chunk.decode() for chunk in response.response)

        with patch.object(
            backend_app,
            'create_feature',
            side_effect=lambda *_args: SlowFeature(backend_app.logger),
        ):
            worker = threading.Thread(target=consume_stream)
            worker.start()
            try:
                assert started.wait(2), 'analysis did not start'
                with backend_app.app.test_client() as client:
                    cancel_response = client.post('/api/process/2/cancel')
                assert cancel_response.status_code == 200
                assert cancel_response.get_json()['status'] == 'cancelled'
                worker.join(2)
                assert not worker.is_alive(), 'analysis did not terminate after cancellation'
            finally:
                active = backend_app._active_features.get('2')
                if active is not None:
                    active.cancel()
                worker.join(2)
                backend_app._active_features.pop('2', None)

        result_events = [
            event for event in streamed_events
            if event.startswith('event: result')
        ]
        assert result_events
        result = json.loads(result_events[-1].split('data: ', 1)[1])
        assert result['status'] == 'cancelled'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
