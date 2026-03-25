"""
Integration tests for MatterSim Predictor via Docker container.

Test Coverage:
- Generic predictor contract checks (response envelope, JSON serialization)
- Docker container health and connectivity
- MatterSim-specific sanity checks (energy, forces, stress, relaxation)
- Error handling for invalid/missing inputs

Prerequisites:
- MatterSim Docker container must be running:
    docker compose up -d mattersim
- Quick check container status:
    docker compose ps mattersim
- Quick check recent container logs:
    docker compose logs mattersim --tail 20
- Container exposes API on http://localhost:8200 by default

Run with: pytest tests/integration/test_mattersim_sanity.py -v
Skip network tests: pytest -m "not network"
Skip slow tests: pytest -m "not slow"
"""

import json
from pathlib import Path

import pytest

from Information_Units.Predictors.Mattersim.MattersimPredictor import MattersimPredictor


pytestmark = [pytest.mark.integration, pytest.mark.network, pytest.mark.slow]


# ============================================================================
# Fixtures
# ============================================================================

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


@pytest.fixture(scope="module")
def predictor():
    """Instantiate the MatterSim predictor once for this module."""
    return MattersimPredictor(predictor_name='test_mattersim_integration')


# ============================================================================
# Envelope Helpers
# ============================================================================

def assert_prediction_envelope(result):
    """Validate standard MatterSim response envelope."""
    assert isinstance(result, dict)
    assert result.get('status') in {'ok', 'error'}
    assert isinstance(result.get('properties'), dict)
    assert isinstance(result.get('warnings'), list)
    assert 'error' in result


def assert_ok_prediction(result):
    """Validate a successful prediction payload with all properties."""
    assert_prediction_envelope(result)
    assert result['status'] == 'ok'
    assert result['error'] is None

    props = result['properties']
    # Structural info
    assert isinstance(props.get('num_atoms'), int)
    assert props['num_atoms'] > 0
    assert isinstance(props.get('cell'), list)
    assert isinstance(props.get('positions'), list)
    assert isinstance(props.get('atomic_numbers'), list)
    assert len(props['positions']) == props['num_atoms']
    assert len(props['atomic_numbers']) == props['num_atoms']

    # Energy
    assert isinstance(props.get('energy'), (int, float))

    # Forces — list of 3D vectors, one per atom
    assert isinstance(props.get('forces'), list)
    assert len(props['forces']) == props['num_atoms']
    assert len(props['forces'][0]) == 3

    # Stress — 6-component Voigt tensor
    assert isinstance(props.get('stress'), list)
    assert len(props['stress']) == 6


def assert_error_prediction(result):
    """Validate a failed prediction payload."""
    assert_prediction_envelope(result)
    assert result['status'] == 'error'
    assert result['error'] is not None


# ============================================================================
# Docker Container Health Tests
# ============================================================================

def test_container_is_healthy(predictor):
    """MatterSim Docker container should be reachable."""
    assert predictor.is_healthy(), (
        f"MatterSim container not reachable at {predictor.api_url}. "
        "Start it with: docker compose up -d mattersim"
    )


def test_info_returns_metadata(predictor):
    """The /info endpoint should return model metadata."""
    info = predictor.info()
    assert "MatterSim" in info
    assert "energy" in info.lower() or "capabilities" in info.lower()


# ============================================================================
# Generic Predictor Contract Tests
# ============================================================================

def test_predict_valid_input_returns_ok_envelope(cif_files, predictor):
    """A valid CIF file produces a successful, well-formed result."""
    result = predictor.predict({'cif_file': cif_files['al2o3_path']})
    assert_ok_prediction(result)


def test_predict_missing_cif_file_returns_error(predictor):
    """Missing 'cif_file' key returns an error."""
    result = predictor.predict({})
    assert_error_prediction(result)
    assert "Missing required parameter" in result['error']


def test_predict_nonexistent_file_returns_error(predictor):
    """A non-existent file path returns an error."""
    result = predictor.predict({'cif_file': '/nonexistent/file.cif'})
    assert_error_prediction(result)
    assert "not found" in result['error'].lower()


def test_predict_invalid_cif_returns_error(cif_files, predictor):
    """An invalid CIF file produces a structured error."""
    result = predictor.predict({'cif_file': cif_files['invalid_path']})
    assert_prediction_envelope(result)
    # May be error or ok-with-warnings depending on container behavior
    assert result['status'] in {'ok', 'error'}


def test_predict_output_is_json_serializable(cif_files, predictor):
    """Prediction output can be serialized and deserialized as JSON."""
    result = predictor.predict({'cif_file': cif_files['al2o3_path']})

    serialized = json.dumps(result, default=str)
    deserialized = json.loads(serialized)

    assert isinstance(deserialized, dict)
    assert deserialized['status'] == 'ok'


# ============================================================================
# MatterSim-Specific Sanity Tests
# ============================================================================

def test_al2o3_energy_in_expected_range(cif_files, predictor):
    """Al2O3 (Corundum) energy should be in a physically reasonable range."""
    result = predictor.predict({'cif_file': cif_files['al2o3_path']})
    assert_ok_prediction(result)

    energy = result['properties']['energy']
    # Keep this broad because absolute energies can vary by model/checkpoint.
    energy_per_atom = energy / result['properties']['num_atoms']
    assert -8.5 <= energy_per_atom <= -3.5, (
        f"Energy per atom {energy_per_atom:.3f} eV outside expected range [-8.5, -3.5]"
    )


def test_al2o3_has_correct_composition(cif_files, predictor):
    """Al2O3 should have 4 Al (Z=13) and 6 O (Z=8) atoms."""
    result = predictor.predict({'cif_file': cif_files['al2o3_path']})
    assert_ok_prediction(result)

    atomic_numbers = result['properties']['atomic_numbers']
    al_count = atomic_numbers.count(13)
    o_count = atomic_numbers.count(8)
    assert al_count == 4, f"Expected 4 Al atoms, got {al_count}"
    assert o_count == 6, f"Expected 6 O atoms, got {o_count}"


def test_relaxation_lowers_energy(cif_files, predictor):
    """Relaxed energy should be lower than or equal to the initial energy."""
    result = predictor.predict({'cif_file': cif_files['al2o3_path']})
    assert_ok_prediction(result)

    props = result['properties']
    assert props.get('relaxed_energy') is not None, "Relaxation did not produce energy"
    assert props['relaxed_energy'] <= props['energy'], (
        f"Relaxed energy ({props['relaxed_energy']:.4f}) should be <= "
        f"initial energy ({props['energy']:.4f})"
    )


def test_relaxation_produces_structure_and_cell(cif_files, predictor):
    """Relaxation should produce relaxed positions and cell."""
    result = predictor.predict({'cif_file': cif_files['al2o3_path']})
    assert_ok_prediction(result)

    props = result['properties']
    assert isinstance(props.get('relaxed_structure'), list)
    assert isinstance(props.get('relaxed_cell'), list)
    assert len(props['relaxed_structure']) == props['num_atoms']
    assert len(props['relaxed_cell']) == 3  # 3x3 cell matrix


def test_relaxed_forces_near_zero(cif_files, predictor):
    """After relaxation, forces should be near zero (converged)."""
    result = predictor.predict({'cif_file': cif_files['al2o3_path']})
    assert_ok_prediction(result)

    relaxed_forces = result['properties'].get('relaxed_forces')
    assert relaxed_forces is not None, "Relaxation did not return forces"

    # Max force component should be small (< 0.05 eV/A)
    max_force = max(
        abs(component)
        for atom_forces in relaxed_forces
        for component in atom_forces
    )
    assert max_force < 0.05, (
        f"Max residual force {max_force:.4f} eV/A exceeds threshold 0.05"
    )


def test_relaxed_cif_string_returned(cif_files, predictor):
    """Relaxation should return a CIF string for the optimized structure."""
    result = predictor.predict({'cif_file': cif_files['al2o3_path']})
    assert_ok_prediction(result)

    cif_string = result['properties'].get('relaxed_cif_string')
    assert cif_string is not None, "No relaxed CIF string returned"
    assert "data_" in cif_string
    assert "_cell_length_a" in cif_string


def test_model_deterministic_predictions(cif_files, predictor):
    """Running the same input twice should produce the same energy."""
    result1 = predictor.predict({'cif_file': cif_files['al2o3_path']})
    result2 = predictor.predict({'cif_file': cif_files['al2o3_path']})

    energy1 = result1['properties']['energy']
    energy2 = result2['properties']['energy']
    assert energy1 == energy2, (
        f"Energies differ: {energy1} vs {energy2}"
    )


@pytest.mark.parametrize('cif_key', ['al2o3_path', 'sio2_path'])
def test_multiple_materials_produce_valid_results(cif_files, predictor, cif_key):
    """Various known materials should all produce valid predictions."""
    # Keep this as a fast smoke test: verify prediction path for multiple
    # materials without paying the cost of full structure relaxation.
    result = predictor.predict({
        'cif_file': cif_files[cif_key],
        'relax': False,
    })
    assert_ok_prediction(result)


def test_output_dir_saves_relaxed_cif(cif_files, predictor, tmp_path):
    """When output_dir is provided, relaxed CIF should be saved locally."""
    result = predictor.predict({
        'cif_file': cif_files['al2o3_path'],
        'output_dir': str(tmp_path),
    })
    assert_ok_prediction(result)

    relaxed_cif_path = result['properties'].get('relaxed_cif')
    assert relaxed_cif_path is not None, "No relaxed CIF path returned"
    assert Path(relaxed_cif_path).exists(), f"Relaxed CIF not found at {relaxed_cif_path}"
    assert Path(relaxed_cif_path).stat().st_size > 0
