"""
MatterSim FastAPI Server
========================
Runs inside a Docker container and exposes MatterSim's prediction capabilities
to the EMOS platform via HTTP.

Endpoints
---------
GET  /health    - liveness / readiness check
GET  /info      - model metadata
POST /predict   - predict material properties from a CIF string
"""

from __future__ import annotations

import logging
import os
import tempfile
import traceback
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("MATTERSIM_LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mattersim_api")

# ---------------------------------------------------------------------------
# MatterSim / ASE imports (available inside the container)
# ---------------------------------------------------------------------------
from ase.filters import UnitCellFilter
from ase.io import read as ase_read, write as ase_write
from ase.optimize import BFGS

from mattersim.forcefield import MatterSimCalculator

# Pre-load the calculator once at startup
logger.info("Loading MatterSim calculator...")
_calculator = MatterSimCalculator()
logger.info("MatterSim calculator loaded successfully")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MatterSim API",
    description="Material property prediction powered by Microsoft MatterSim",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class PredictRequest(BaseModel):
    """Parameters accepted by the /predict endpoint."""

    cif_string: str = Field(
        ..., description="CIF file contents as a string."
    )
    compute_energy: bool = Field(True, description="Compute total energy (eV).")
    compute_forces: bool = Field(True, description="Compute atomic forces (eV/A).")
    compute_stress: bool = Field(True, description="Compute stress tensor (GPa).")
    relax: bool = Field(True, description="Perform structure relaxation.")
    relax_atoms: bool = Field(True, description="Allow atomic positions to relax.")
    relax_cell: bool = Field(True, description="Allow cell parameters to relax.")
    fmax: float = Field(0.01, description="Force convergence criterion (eV/A).")
    max_steps: int = Field(100, ge=1, description="Maximum relaxation steps.")


class PredictResponse(BaseModel):
    status: str
    properties: dict
    warnings: list[str]
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_atoms_from_cif_string(cif_string: str):
    """Write CIF string to temp file, load with ASE, return Atoms object."""
    tmp = tempfile.NamedTemporaryFile(suffix=".cif", delete=False, mode="w")
    try:
        tmp.write(cif_string)
        tmp.close()

        # Try pymatgen first (more robust), fall back to ASE
        try:
            from pymatgen.core import Structure
            from pymatgen.io.ase import AseAtomsAdaptor

            struct = Structure.from_file(tmp.name)
            atoms = AseAtomsAdaptor.get_atoms(struct)
            logger.info("Loaded structure via PyMatGen (%d atoms)", len(atoms))
        except Exception:
            atoms = ase_read(tmp.name)
            logger.info("Loaded structure via ASE (%d atoms)", len(atoms))

        return atoms
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def _relax_structure(atoms, relax_atoms, relax_cell, fmax, max_steps):
    """Run BFGS relaxation and return results dict."""
    results = {}

    if relax_cell:
        dyn_atoms = UnitCellFilter(atoms)
    else:
        dyn_atoms = atoms

    relaxer = BFGS(dyn_atoms, trajectory=None)
    relaxer.run(fmax=fmax, steps=max_steps)

    results["relaxed_energy"] = float(atoms.get_potential_energy())
    results["relaxed_structure"] = atoms.get_positions().tolist()
    results["relaxed_cell"] = atoms.get_cell().tolist()

    try:
        results["relaxed_forces"] = atoms.get_forces().tolist()
    except Exception:
        pass

    try:
        results["relaxed_stress"] = atoms.get_stress().tolist()
    except Exception:
        pass

    # Generate relaxed CIF string
    tmp = tempfile.NamedTemporaryFile(suffix=".cif", delete=False, mode="w")
    try:
        tmp.close()
        ase_write(tmp.name, atoms, format="cif")
        results["relaxed_cif_string"] = Path(tmp.name).read_text()
    except Exception:
        results["relaxed_cif_string"] = None
    finally:
        Path(tmp.name).unlink(missing_ok=True)

    return results


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    logger.debug("Health check requested")
    return {"status": "ok", "service": "mattersim", "message": "MatterSim OK"}


@app.get("/info")
def info():
    logger.debug("Info endpoint requested")
    return {
        "name": "MatterSim",
        "description": (
            "MatterSim is a Machine Learning Interatomic Potential (MLIP) "
            "for predicting properties of inorganic crystals, developed by "
            "Microsoft Research."
        ),
        "version": "1.0.0",
        "capabilities": [
            "energy",
            "forces",
            "stress",
            "relaxation",
        ],
    }


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    """Predict material properties from a CIF string."""
    logger.info("POST /predict — compute_energy=%s, forces=%s, stress=%s, relax=%s",
                req.compute_energy, req.compute_forces, req.compute_stress, req.relax)

    properties: dict = {}
    warnings_list: list[str] = []

    try:
        # Load structure
        atoms = _load_atoms_from_cif_string(req.cif_string)
        atoms.calc = _calculator

        # Basic structural info
        properties["num_atoms"] = len(atoms)
        properties["cell"] = atoms.get_cell().tolist()
        properties["positions"] = atoms.get_positions().tolist()
        properties["atomic_numbers"] = atoms.get_atomic_numbers().tolist()

        # Energy
        if req.compute_energy:
            try:
                energy = atoms.get_potential_energy()
                properties["energy"] = float(energy)
                logger.info("Energy = %.6f eV", energy)
            except Exception as e:
                w = f"Energy calculation failed: {e}"
                warnings_list.append(w)
                logger.warning(w)

        # Forces
        if req.compute_forces:
            try:
                properties["forces"] = atoms.get_forces().tolist()
                logger.info("Computed atomic forces")
            except Exception as e:
                w = f"Force calculation failed: {e}"
                warnings_list.append(w)
                logger.warning(w)

        # Stress
        if req.compute_stress:
            try:
                properties["stress"] = atoms.get_stress().tolist()
                logger.info("Computed stress tensor")
            except Exception as e:
                w = f"Stress calculation failed: {e}"
                warnings_list.append(w)
                logger.warning(w)

        # Relaxation
        if req.relax:
            try:
                relax_results = _relax_structure(
                    atoms,
                    relax_atoms=req.relax_atoms,
                    relax_cell=req.relax_cell,
                    fmax=req.fmax,
                    max_steps=req.max_steps,
                )
                properties.update(relax_results)
                logger.info("Relaxation complete: E=%.6f eV",
                            relax_results.get("relaxed_energy", float("nan")))
            except Exception as e:
                w = f"Relaxation failed: {e}"
                warnings_list.append(w)
                logger.warning(w)

        logger.info("Prediction complete (status=ok)")
        return PredictResponse(
            status="ok",
            properties=properties,
            warnings=warnings_list,
            error=None,
        )

    except Exception as exc:
        error_msg = f"Unexpected error during prediction: {exc}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return PredictResponse(
            status="error",
            properties={},
            warnings=[],
            error=error_msg,
        )
