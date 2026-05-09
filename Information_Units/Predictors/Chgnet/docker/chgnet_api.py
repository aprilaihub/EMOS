from __future__ import annotations

import logging
import os
import tempfile
import traceback
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, Field
from pymatgen.core import Structure
from pymatgen.io.cif import CifWriter

from chgnet.model import CHGNet, StructOptimizer


LOG_LEVEL = os.getenv("CHGNET_LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("chgnet_api")

MODEL_NAME = os.getenv("CHGNET_MODEL_NAME", "0.3.0")
USE_DEVICE = os.getenv("CHGNET_DEVICE") or None

logger.info("Loading CHGNet model %s...", MODEL_NAME)
_model = CHGNet.load(model_name=MODEL_NAME, use_device=USE_DEVICE, verbose=False)
_relaxer = StructOptimizer(model=_model, use_device=USE_DEVICE)
logger.info("CHGNet loaded successfully")

app = FastAPI(
    title="CHGNet API",
    description="Material property prediction powered by CHGNet",
    version="1.0.0",
)


class PredictRequest(BaseModel):
    cif_string: str = Field(..., description="CIF file contents as a string.")
    compute_energy: bool = Field(True, description="Compute total energy (eV).")
    compute_forces: bool = Field(True, description="Compute atomic forces (eV/A).")
    compute_stress: bool = Field(True, description="Compute stress tensor (GPa).")
    relax: bool = Field(True, description="Perform structure relaxation.")
    relax_atoms: bool = Field(True, description="Allow atomic positions to relax.")
    relax_cell: bool = Field(True, description="Allow cell parameters to relax.")
    fmax: float = Field(0.1, description="Force convergence criterion (eV/A).")
    max_steps: int = Field(500, ge=1, description="Maximum relaxation steps.")


class PredictResponse(BaseModel):
    status: str
    properties: dict
    warnings: list[str]
    error: Optional[str] = None


def _load_structure_from_cif_string(cif_string: str) -> Structure:
    tmp = tempfile.NamedTemporaryFile(suffix=".cif", delete=False, mode="w")
    try:
        tmp.write(cif_string)
        tmp.close()
        return Structure.from_file(tmp.name)
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def _to_list(value):
    if value is None:
        return None
    if hasattr(value, "tolist"):
        return value.tolist()
    return value


def _predict_static(structure: Structure, req: PredictRequest) -> dict:
    task = "e"
    if req.compute_forces and req.compute_stress:
        task = "efs"
    elif req.compute_forces:
        task = "ef"
    elif req.compute_stress:
        task = "efs"

    prediction = _model.predict_structure(structure, task=task)
    num_atoms = len(structure)
    properties: dict = {"num_atoms": num_atoms}

    if req.compute_energy and "e" in prediction:
        properties["energy"] = float(prediction["e"]) * num_atoms
    if req.compute_forces and "f" in prediction:
        properties["forces"] = _to_list(prediction["f"])
    if req.compute_stress and "s" in prediction:
        properties["stress"] = _to_list(prediction["s"])

    return properties


def _relax_structure(structure: Structure, req: PredictRequest) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    if not req.relax_atoms:
        warnings.append("CHGNet does not support cell-only relaxation; skipping relaxation because relax_atoms=false")
        return {}, warnings

    result = _relaxer.relax(
        structure,
        fmax=req.fmax,
        steps=req.max_steps,
        relax_cell=req.relax_cell,
        verbose=False,
        assign_magmoms=False,
    )
    final_structure = result["final_structure"]
    trajectory = result["trajectory"]

    relaxed: dict = {
        "relaxed_energy": float(trajectory.energies[-1]),
        "relaxed_structure": final_structure.cart_coords.tolist(),
        "relaxed_cell": final_structure.lattice.matrix.tolist(),
        "relaxed_cif_string": str(CifWriter(final_structure)),
    }

    if getattr(trajectory, "forces", None):
        relaxed["relaxed_forces"] = np.asarray(trajectory.forces[-1]).tolist()
    if getattr(trajectory, "stresses", None):
        relaxed["relaxed_stress"] = np.asarray(trajectory.stresses[-1]).tolist()

    return relaxed, warnings


@app.get("/health")
def health():
    return {"status": "ok", "service": "chgnet", "message": "CHGNet OK"}


@app.get("/info")
def info():
    return {
        "name": "CHGNet",
        "description": (
            "CHGNet is a charge-informed graph neural network potential for "
            "predicting energy, forces, stress, and fast structure relaxation."
        ),
        "version": str(getattr(_model, "version", MODEL_NAME)),
        "capabilities": ["energy", "forces", "stress", "relaxation"],
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

    try:
        structure = _load_structure_from_cif_string(req.cif_string)
        properties = _predict_static(structure, req)
        warnings_list: list[str] = []

        if req.relax:
            relax_results, relax_warnings = _relax_structure(structure, req)
            properties.update(relax_results)
            warnings_list.extend(relax_warnings)

        return PredictResponse(status="ok", properties=properties, warnings=warnings_list, error=None)
    except Exception as exc:
        error_msg = f"Unexpected error during prediction: {exc}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return PredictResponse(status="error", properties={}, warnings=[], error=error_msg)