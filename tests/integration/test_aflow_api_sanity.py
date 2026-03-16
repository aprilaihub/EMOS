"""
Integration tests for AFLOW database with real AFLUX API calls.

These tests mirror the Alexandria integration style:
- Parameterized query/filter matrix
- API-level property range validation
- End-to-end CIF retrieval validation
"""

import time
from pathlib import Path

import pytest

from .conftest import (
    extract_formula_from_cif,
    extract_nelements_from_cif,
    extract_nperiodic_dimensions_from_cif,
    validate_cif_file,
)


@pytest.fixture(autouse=True)
def rate_limit_delay():
    """Add delay between tests to avoid stressing AFLOW endpoints."""
    time.sleep(2.0)
    yield


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
@pytest.mark.parametrize(
    "query,expected_elements,filters,expected_nperiodic_dimensions,expected_nelements_range,expected_props",
    [
        # Basic compound queries without property filters.
        ("Al2O3", ["Al", "O"], {}, None, None, None),
        ("SiO2", ["Si", "O"], {}, None, None, None),
        ("Fe2O3", ["Fe", "O"], {}, None, None, None),
        # Structural property filters.
        ("Al2O3", ["Al", "O"], {"nelements": [2, 3]}, None, (2, 3), None),
        ("SiO2", ["Si", "O"], {"nelements": [2, 3]}, None, (2, 3), None),
        # Electronic/energetic/mechanical property filters.
        ("SiO2", ["Si", "O"], {"band_gap": [0.0, 12.0]}, None, None, {"Egap": (0.0, 12.0)}),
        ("Al2O3", ["Al", "O"], {"density": [0.0, 30.0]}, None, None, {"density": (0.0, 30.0)}),
        ("Al2O3", ["Al", "O"], {"bulk_modulus": [0.0, 1000.0]}, None, None, {"ael_bulk_modulus_vrh": (0.0, 1000.0)}),
        # Combined filters.
        (
            "Al2O3",
            ["Al", "O"],
            {"density": [0.0, 30.0], "nelements": [2, 3]},
            None,
            (2, 3),
            {"density": (0.0, 30.0)},
        ),
    ],
)
def test_aflow_retrieve_structures(
    query,
    expected_elements,
    filters,
    expected_nperiodic_dimensions,
    expected_nelements_range,
    expected_props,
):
    from Information_Units.Databases.Aflow.AflowAPIHelper import AflowAPIHelper
    from Information_Units.Databases.Aflow.AflowDatabase import AflowDatabase

    # API-level validation with mapped filters.
    helper = AflowAPIHelper("https://aflow.org/API/aflux/")
    mapped_filters = helper.map_properties(filters)
    api_results = helper.fetch_from_api(query, 3, mapped_filters)
    assert len(api_results) > 0, f"No API results for query={query}, filters={filters}"

    if expected_props:
        for entry in api_results:
            for prop_name, (min_val, max_val) in expected_props.items():
                value = entry.get(prop_name)
                if value is not None:
                    assert min_val <= value <= max_val, (
                        f"Property {prop_name}={value} outside range [{min_val}, {max_val}]"
                    )

    # End-to-end through database retrieve() and CIF write.
    db = AflowDatabase()
    params = {"query": query, "limit": 3}
    params.update(filters)
    results = db.retrieve(params)

    assert isinstance(results, list) and len(results) > 0

    for path in results:
        assert Path(path).exists()
        assert path.endswith(".cif")

        content = validate_cif_file(path)
        for elem in expected_elements:
            assert elem in content, f"{elem} not present in CIF content"

        formula = extract_formula_from_cif(content)
        if formula:
            for elem in expected_elements:
                assert elem in formula, f"{elem} not present in formula {formula}"

    if expected_nperiodic_dimensions is not None or expected_nelements_range is not None:
        for path in results:
            content = validate_cif_file(path)

            if expected_nelements_range is not None:
                min_nelements, max_nelements = expected_nelements_range
                nelements = extract_nelements_from_cif(content)
                assert min_nelements <= nelements <= max_nelements, (
                    f"nelements {nelements} not in range [{min_nelements}, {max_nelements}]"
                )

            if expected_nperiodic_dimensions is not None:
                nperiodic = extract_nperiodic_dimensions_from_cif(content)
                assert nperiodic == expected_nperiodic_dimensions, (
                    f"nperiodic_dimensions {nperiodic} != {expected_nperiodic_dimensions}"
                )


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
def test_aflow_broad_element_smoke():
    """Single broad element search kept as a smoke test only."""
    from Information_Units.Databases.Aflow.AflowDatabase import AflowDatabase

    db = AflowDatabase()
    results = db.retrieve({"query": "Fe", "limit": 1})
    assert isinstance(results, list)
    assert len(results) <= 1


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
@pytest.mark.parametrize("limit", [1, 5, 10])
def test_aflow_retrieve_performance(benchmark, limit):
    from Information_Units.Databases.Aflow.AflowDatabase import AflowDatabase

    db = AflowDatabase()
    result = benchmark(db.retrieve, {"query": "Al2O3", "limit": limit})

    assert isinstance(result, list)
    assert len(result) <= limit
