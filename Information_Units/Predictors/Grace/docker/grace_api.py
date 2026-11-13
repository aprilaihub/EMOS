from __future__ import annotations

import logging
import os
import tempfile
import traceback
from io import StringIO
from pathlib import Path
from typing import Optional

from ase.io import read as ase_read, write as ase_write
from fastapi import FastAPI
from pydantic import BaseModel, Field


LOG_LEVEL = os.getenv("GRACE_LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("grace_api")

MODEL_NAME = os.getenv("GRACE_MODEL", "GRACE-3L-OMAT-large")

logger.info("Loading GRACE model %s...", MODEL_NAME)
try:
    from tensorpotential.calculator.foundation_models import GRACEModels, grace_fm
except Exception as exc:
    logger.error("Failed to import GRACE/tensorpotential: %s", exc)
    raise

_model_enum = getattr(GRACEModels, MODEL_NAME, None)
_calculator = grace_fm(_model_enum if _model_enum is not None else MODEL_NAME)
logger.info("GRACE model loaded successfully")

app = FastAPI(
    title="GRACE API",
    description="Material property prediction powered by GRACE foundation models",
    version="1.0.0",
)


class PredictRequest(BaseModel):
    cif_string: str = Field(..., description="CIF file contents as a string.")
    compute_energy: bool = Field(True, description="Compute total energy (eV).")
    compute_forces: bool = Field(True, description="Compute atomic forces (eV/A).")
    compute_stress: bool = Field(True, description="Compute stress tensor (GPa-like ASE stress units).")
    relax: bool = Field(False, description="Perform structure relaxation (currently ignored).")
    relax_atoms: bool = Field(False, description="Allow atomic positions to relax (currently ignored).")
    relax_cell: bool = Field(False, description="Allow cell parameters to relax (currently ignored).")


class PredictResponse(BaseModel):
    status: str
    properties: dict
    warnings: list[str]
    error: Optional[str] = None


def _load_atoms_from_cif_string(cif_string: str):
    """Load CIF via ASE from string safely."""
    try:
        return ase_read(StringIO(cif_string), format="cif")
    except Exception:
        # Fallback through temp file for parsers that require a path.
        tmp = tempfile.NamedTemporaryFile(suffix=".cif", delete=False, mode="w")
        try:
            tmp.write(cif_string)
            tmp.close()
            return ase_read(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)


@app.get("/health")
def health():
    return {"status": "ok", "service": "grace", "message": "GRACE OK"}


@app.get("/info")
def info():
    return {
        "name": "GRACE",
        "description": (
            "GRACE foundation-model interatomic potential for predicting "
            "energy, forces, and stress for crystal structures."
        ),
        "version": "1.0.0",
        "models": [MODEL_NAME],
        "capabilities": ["energy", "forces", "stress"],
    }


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    logger.info(
        "POST /predict — compute_energy=%s, forces=%s, stress=%s, relax=%s",
        req.compute_energy,
        req.compute_forces,
        req.compute_stress,
        req.relax,
    )

    properties: dict = {}
    warnings_list: list[str] = []

    try:
        atoms = _load_atoms_from_cif_string(req.cif_string)
        atoms.calc = _calculator

        properties["num_atoms"] = len(atoms)

        if req.compute_energy:
            energy = float(atoms.get_potential_energy())
            properties["energy"] = energy
            properties["relaxed_energy"] = energy

        if req.compute_forces:
            forces = atoms.get_forces()
            properties["forces"] = forces.tolist()
            properties["relaxed_forces"] = forces.tolist()

        if req.compute_stress:
            stress = atoms.get_stress(voigt=True)
            properties["stress"] = stress.tolist()
            properties["relaxed_stress"] = stress.tolist()

        properties["relaxed_cell"] = atoms.cell.tolist()
        properties["relaxed_structure"] = atoms.get_chemical_formula()

        # Keep API contract compatible with host-side normalizer.
        tmp = tempfile.NamedTemporaryFile(suffix=".cif", delete=False)
        try:
            tmp_path = tmp.name
            tmp.close()
            ase_write(tmp_path, atoms, format="cif")
            properties["relaxed_cif_string"] = Path(tmp_path).read_text(encoding="utf-8", errors="ignore")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        if req.relax or req.relax_atoms or req.relax_cell:
            warnings_list.append(
                "GRACE predictor currently reports single-point values; full geometry relaxation is not applied."
            )

        return PredictResponse(status="ok", properties=properties, warnings=warnings_list, error=None)

    except Exception as exc:
        error_msg = f"Unexpected error during prediction: {exc}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return PredictResponse(status="error", properties={}, warnings=[], error=error_msg)
