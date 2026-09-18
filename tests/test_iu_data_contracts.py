"""Offline checks for the documented Information Unit data contracts."""

from collections.abc import Mapping

import pytest


DATABASE_INPUTS = {
    "target_compositions": "Al2O3",
    "batch_size": 2,
}
DATABASE_OUTPUT = {
    "source": "example",
    "queries": DATABASE_INPUTS,
    "cif_strings": ["data"],
}
GENERATOR_INPUTS = {"batch_size": 2}
GENERATOR_OUTPUT = {
    "status": "completed",
    "source": "example",
    "queries": GENERATOR_INPUTS,
    "cif_strings": ["data"],
}
PREDICTOR_INPUT = ["data"]
PREDICTOR_OUTPUT = {
    "source": "example",
    "results": [
        {
            "index": 0,
            "status": "ok",
            "properties": {},
            "warnings": [],
            "error": None,
            "cif_input": "data",
        }
    ],
}


def _assert_mapping(value, label):
    assert isinstance(value, Mapping), f"{label} must be a dictionary"


def _assert_string(value, label):
    assert isinstance(value, str), f"{label} must be a string"


def _assert_database_input(inputs):
    _assert_mapping(inputs, "Database inputs")
    _assert_string(inputs.get("target_compositions"), "target_compositions")
    assert isinstance(inputs.get("batch_size"), int), "batch_size must be an integer"


def _assert_database_output(output):
    _assert_mapping(output, "Database output")
    _assert_string(output.get("source"), "source")
    assert isinstance(output.get("queries"), Mapping), "queries must be a dictionary"
    assert isinstance(output.get("cif_strings"), list), "cif_strings must be a list"
    assert all(isinstance(item, str) for item in output["cif_strings"]), (
        "cif_strings must contain strings"
    )


def _assert_generator_input(inputs):
    _assert_mapping(inputs, "Generator inputs")
    assert isinstance(inputs.get("batch_size"), int), "batch_size must be an integer"


def _assert_generator_output(output):
    _assert_mapping(output, "Generator output")
    _assert_string(output.get("status"), "status")
    _assert_string(output.get("source"), "source")
    assert isinstance(output.get("queries"), Mapping), "queries must be a dictionary"
    assert isinstance(output.get("cif_strings"), list), "cif_strings must be a list"
    assert all(isinstance(item, str) for item in output["cif_strings"]), (
        "cif_strings must contain strings"
    )


def _assert_predictor_input(input_data):
    assert isinstance(input_data, list), "Predictor input must be a list"
    assert all(isinstance(item, str) for item in input_data), (
        "Predictor input must contain strings"
    )


def _assert_predictor_output(output):
    _assert_mapping(output, "Predictor output")
    _assert_string(output.get("source"), "source")
    assert isinstance(output.get("results"), list), "results must be a list"
    for result in output["results"]:
        _assert_mapping(result, "Predictor result")
        assert isinstance(result.get("index"), int), "index must be an integer"
        _assert_string(result.get("status"), "status")
        assert isinstance(result.get("properties"), Mapping), (
            "properties must be a dictionary"
        )
        assert isinstance(result.get("warnings"), list), "warnings must be a list"
        assert all(isinstance(item, str) for item in result["warnings"]), (
            "warnings must contain strings"
        )
        assert result.get("error") is None or isinstance(result.get("error"), str), (
            "error must be a string or None"
        )
        _assert_string(result.get("cif_input"), "cif_input")


@pytest.mark.unit
def test_database_contract():
    _assert_database_input(DATABASE_INPUTS)
    _assert_database_output(DATABASE_OUTPUT)


@pytest.mark.unit
def test_generator_contract():
    _assert_generator_input(GENERATOR_INPUTS)
    _assert_generator_output(GENERATOR_OUTPUT)


@pytest.mark.unit
def test_predictor_contract():
    _assert_predictor_input(PREDICTOR_INPUT)
    _assert_predictor_output(PREDICTOR_OUTPUT)


@pytest.mark.unit
@pytest.mark.parametrize(
    "validator, value",
    [
        (_assert_database_input, {"batch_size": 1}),
        (_assert_database_output, {"source": "example", "queries": {}}),
        (_assert_generator_input, {}),
        (_assert_generator_output, {"status": "completed"}),
        (_assert_predictor_input, [1]),
        (_assert_predictor_output, {"source": "example", "results": [{"index": 0}]}),
    ],
)
def test_contract_rejects_missing_or_wrong_fields(validator, value):
    with pytest.raises(AssertionError):
        validator(value)
