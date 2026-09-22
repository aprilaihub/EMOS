"""Offline checks for the documented Information Unit data contracts."""

from collections.abc import Mapping

import pytest


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
    assert all(isinstance(item, str) for item in output["cif_strings"]), "cif_strings must contain strings"


def _assert_generator_input(inputs):
    _assert_mapping(inputs, "Generator inputs")
    assert isinstance(inputs.get("batch_size"), int), "batch_size must be an integer"


def _assert_generator_output(output):
    _assert_mapping(output, "Generator output")
    _assert_string(output.get("status"), "status")
    _assert_string(output.get("source"), "source")
    assert isinstance(output.get("queries"), Mapping), "queries must be a dictionary"
    assert isinstance(output.get("cif_strings"), list), "cif_strings must be a list"
    assert all(isinstance(item, str) for item in output["cif_strings"]), "cif_strings must contain strings"


def _assert_predictor_input(input_data):
    assert isinstance(input_data, list), "Predictor input must be a list"
    assert all(isinstance(item, str) for item in input_data), "Predictor input must contain strings"


def _assert_predictor_output(output):
    _assert_mapping(output, "Predictor output")
    _assert_string(output.get("source"), "source")
    assert isinstance(output.get("results"), list), "results must be a list"
    for result in output["results"]:
        _assert_mapping(result, "Predictor result")
        assert isinstance(result.get("index"), int), "index must be an integer"
        _assert_string(result.get("status"), "status")
        assert isinstance(result.get("properties"), Mapping), "properties must be a dictionary"
        assert isinstance(result.get("warnings"), list), "warnings must be a list"
        assert all(isinstance(item, str) for item in result["warnings"]), "warnings must contain strings"
        assert result.get("error") is None or isinstance(result.get("error"), str), "error must be a string or None"
        _assert_string(result.get("cif_input"), "cif_input")


CONTRACTS = {
    "database": {"validate_input": _assert_database_input, "valid_input": {"target_compositions": "Al2O3", "batch_size": 2}, "validate_output": _assert_database_output, "valid_output": {"source": "example", "queries": {"target_compositions": "Al2O3", "batch_size": 2}, "cif_strings": ["data"]}},
    "generator": {"validate_input": _assert_generator_input, "valid_input": {"batch_size": 2}, "validate_output": _assert_generator_output, "valid_output": {"status": "completed", "source": "example", "queries": {"batch_size": 2}, "cif_strings": ["data"]}},
    "predictor": {"validate_input": _assert_predictor_input, "valid_input": ["data"], "validate_output": _assert_predictor_output, "valid_output": {"source": "example", "results": [{"index": 0, "status": "ok", "properties": {}, "warnings": [], "error": None, "cif_input": "data"}]}},
}


INVALID_CASES = [
    ("database-input-missing-composition", _assert_database_input, {"batch_size": 1}),
    ("database-output-missing-cifs", _assert_database_output, {"source": "example", "queries": {}}),
    ("generator-input-missing-batch-size", _assert_generator_input, {}),
    ("generator-output-missing-fields", _assert_generator_output, {"status": "completed"}),
    ("predictor-input-non-string-item", _assert_predictor_input, [1]),
    ("predictor-output-incomplete-result", _assert_predictor_output, {"source": "example", "results": [{"index": 0}]}),
]


@pytest.mark.unit
@pytest.mark.parametrize("contract_name", CONTRACTS, ids=CONTRACTS)
def test_valid_contract_examples(contract_name):
    contract = CONTRACTS[contract_name]
    contract["validate_input"](contract["valid_input"])
    contract["validate_output"](contract["valid_output"])


@pytest.mark.unit
@pytest.mark.parametrize("case_name,validator,value", INVALID_CASES, ids=[case[0] for case in INVALID_CASES])
def test_invalid_contract_examples_are_rejected(case_name, validator, value):
    with pytest.raises(AssertionError):
        validator(value)