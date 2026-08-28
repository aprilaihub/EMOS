"""Unit tests for DatabaseExtractorFeature."""

from unittest.mock import MagicMock, patch

import pytest

from Features.Materials_Exploration.DatabaseExtractor.DatabaseExtractorFeature import (
    DatabaseExtractorFeature,
)


class _FakeDatabase:
    def __init__(self, database_name="fake", logger=None):
        self.database_name = database_name
        self.logger = logger

    def retrieve(self, inputs):
        return {
            "source": self.database_name,
            "queries": inputs,
            "cif_strings": ["data_1", "data_2"],
        }


@pytest.fixture
def logger():
    mock = MagicMock()
    mock.log = MagicMock()
    return mock


@pytest.fixture
def feature(logger):
    return DatabaseExtractorFeature(logger=logger)


@pytest.mark.unit
def test_extract_inputs_reads_new_fields(feature):
    result = feature.extract_inputs(
        {
            "selectedProperties": ["band_gap", "formation_energy_r2scan"],
            "batchSize": 25,
            "retrievalMode": "strict",
            "queryValues": {"band_gap": [1.0, 2.0]},
            "targetCompositions": "Fe",
            "active_databases": [{"value": "materialsproject", "name": "Materials Project"}],
        }
    )

    assert result["selected_properties"] == ["band_gap", "formation_energy_r2scan"]
    assert result["batch_size"] == 25
    assert result["retrieval_mode"] == "strict"
    assert result["query_values"] == {"band_gap": [1.0, 2.0]}
    assert result["target_compositions"] == "Fe"


@pytest.mark.unit
def test_process_feature_strict_mode_skips_when_property_not_queryable(feature):
    common = {"properties": {"p1": {}, "p2": {}}}
    source_map = {"p1": {"name": "field_p1", "retrievable": True}}

    with patch(
        "Features.Materials_Exploration.DatabaseExtractor.DatabaseExtractorFeature.load_common_properties",
        return_value=common,
    ), patch(
        "Features.Materials_Exploration.DatabaseExtractor.DatabaseExtractorFeature.load_source_property_mapping",
        return_value=source_map,
    ), patch.dict(
        "Features.Materials_Exploration.DatabaseExtractor.DatabaseExtractorFeature.database_factory",
        {"fake_db": _FakeDatabase},
        clear=True,
    ):
        result = feature.process_feature(
            {
                "selected_properties": ["p1", "p2"],
                "batch_size": 5,
                "retrieval_mode": "strict",
                "query_values": {"p1": [0, 1], "p2": [1, 2]},
                "active_databases": [{"value": "fake_db", "name": "Fake DB"}],
            }
        )

    assert result["status"] == "completed"
    assert result["databases"] == {}
    assert len(result["skipped_databases"]) == 1
    assert result["skipped_databases"][0]["source"] == "fake_db"


@pytest.mark.unit
def test_process_feature_lenient_mode_queries_only_supported_properties(feature):
    common = {"properties": {"p1": {}, "p2": {}}}
    source_map = {
        "p1": {"name": "field_p1", "retrievable": True},
        "p2": {"name": "field_p2", "retrievable": False},
    }

    with patch(
        "Features.Materials_Exploration.DatabaseExtractor.DatabaseExtractorFeature.load_common_properties",
        return_value=common,
    ), patch(
        "Features.Materials_Exploration.DatabaseExtractor.DatabaseExtractorFeature.load_source_property_mapping",
        return_value=source_map,
    ), patch.dict(
        "Features.Materials_Exploration.DatabaseExtractor.DatabaseExtractorFeature.database_factory",
        {"fake_db": _FakeDatabase},
        clear=True,
    ):
        result = feature.process_feature(
            {
                "selected_properties": ["p1", "p2"],
                "batch_size": 7,
                "retrieval_mode": "lenient",
                "query_values": {"p1": [0, 1], "p2": [1, 2]},
                "target_compositions": "Fe",
                "active_databases": [{"value": "fake_db", "name": "Fake DB"}],
            }
        )

    db_result = result["databases"]["fake_db"]
    assert db_result["properties_used"] == ["p1"]
    assert db_result["properties_skipped"] == ["p2"]
    assert db_result["records_count"] == 2
    assert db_result["queries_applied"]["batch_size"] == 7
    assert db_result["queries_applied"]["target_compositions"] == "Fe"
    assert db_result["queries_applied"]["p1"] == [0, 1]
