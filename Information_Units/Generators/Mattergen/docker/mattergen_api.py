"""
MatterGen FastAPI Server
========================
Runs inside a Docker container and exposes MatterGen's generation capabilities
to the EMOS platform via HTTP.

Endpoints
---------
GET  /health          – liveness / readiness check
GET  /info            – model metadata
POST /generate        – generate crystal structures
GET  /results/{job}   – retrieve results of a completed generation job
"""

from __future__ import annotations

import io
import json
import logging
import os
import shutil
import tempfile
import time
import traceback
import uuid
from enum import Enum
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging setup — writes to stdout so `docker logs` picks it up
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("MATTERGEN_LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mattergen_api")

# ---------------------------------------------------------------------------
# MatterGen imports (available inside the container after pip install)
# ---------------------------------------------------------------------------
from pymatgen.core.structure import Structure
from pymatgen.core.lattice import Lattice
from pymatgen.io.cif import CifWriter

from mattergen.common.data.types import TargetProperty
from mattergen.common.utils.data_classes import MatterGenCheckpointInfo
from mattergen.generator import CrystalGenerator

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MatterGen API",
    description="Crystal structure generation powered by Microsoft MatterGen",
    version="1.0.0",
)

# Persistent output directory (Docker volume or bind mount)
OUTPUT_DIR = Path(os.getenv("MATTERGEN_OUTPUT_DIR", "/app/outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    """Parameters accepted by the /generate endpoint."""

    pretrained_name: Optional[str] = Field(
        "mattergen_base",
        description=(
            "Name of a pretrained model hosted on HuggingFace Hub. "
            "One of: mattergen_base, mp_20_base, dft_band_gap, "
            "dft_mag_density, ml_bulk_modulus, chemical_system_energy_above_hull, "
            "space_group.  Set to null if providing model_path."
        ),
    )
    model_path: Optional[str] = Field(
        None,
        description="Absolute path to a local checkpoint directory (inside the container).",
    )
    batch_size: int = Field(64, ge=1, description="Number of structures per batch.")
    num_batches: int = Field(1, ge=1, description="Number of batches to generate.")
    properties_to_condition_on: Optional[dict] = Field(
        None,
        description=(
            "Dict of property name → target value for conditional generation. "
            "Example: {'dft_band_gap': 1.5}"
        ),
    )
    target_compositions: Optional[list[dict[str, int]]] = Field(
        None,
        description=(
            "List of target compositions for CSP models. "
            "Each dict maps element symbol → atom count, e.g. [{'Si': 2, 'O': 4}]"
        ),
    )
    record_trajectories: bool = Field(
        True, description="Whether to store the diffusion trajectory."
    )
    diffusion_guidance_factor: Optional[float] = Field(
        None, description="Classifier-free guidance scale. None → default (0.0)."
    )


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class GenerateResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str
    num_structures: int = 0
    structures: list[dict] | None = None
    cif_strings: list[str] | None = None
    debug_logs: list[str] | None = None


# ---------------------------------------------------------------------------
# In-memory job store (sufficient for a single-container sidecar)
# ---------------------------------------------------------------------------
_jobs: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _structure_to_dict(structure: Structure) -> dict:
    """Convert a pymatgen Structure to a JSON-serialisable dict."""
    return json.loads(structure.to_json())


def _structure_to_cif(structure: Structure) -> str:
    """Convert a pymatgen Structure to a CIF-format string."""
    cifstr=structure.to(fmt='cif')
    return cifstr


def _run_generation(job_id: str, req: GenerateRequest) -> None:
    """Synchronous generation (called in the request thread for simplicity).
    For production, wrap in a background task / Celery worker.
    """
    _jobs[job_id]["status"] = JobStatus.running
    logs: list[str] = []

    def _log(msg: str, level: str = "info") -> None:
        """Log to both stdout (docker logs) and the in-memory list."""
        getattr(logger, level, logger.info)(f"[{job_id}] {msg}")
        logs.append(f"[{level.upper()}] {msg}")

    try:
        _log(f"Starting generation — model={req.pretrained_name or req.model_path}, "
             f"batch_size={req.batch_size}, num_batches={req.num_batches}")

        output_path = OUTPUT_DIR / job_id
        output_path.mkdir(parents=True, exist_ok=True)
        _log(f"Output directory: {output_path}")

        properties: TargetProperty = req.properties_to_condition_on or {}
        if properties:
            _log(f"Conditioning properties: {properties}")
        else:
            _log("No conditioning properties (unconditional generation)")

        config_overrides = [
            "++lightning_module.diffusion_module.model."
            "element_mask_func={_target_:'mattergen.denoiser.mask_disallowed_elements',_partial_:True}"
        ]

        t0 = time.time()

        if req.pretrained_name is not None:
            _log(f"Loading pretrained model from HuggingFace Hub: {req.pretrained_name}")
            checkpoint_info = MatterGenCheckpointInfo.from_hf_hub(
                req.pretrained_name,
                config_overrides=config_overrides,
            )
        else:
            _log(f"Loading local checkpoint: {req.model_path}")
            checkpoint_info = MatterGenCheckpointInfo(
                model_path=Path(req.model_path).resolve(),
                load_epoch="last",
                config_overrides=config_overrides,
                strict_checkpoint_loading=True,
            )

        t_load = time.time() - t0
        _log(f"Checkpoint loaded in {t_load:.1f}s")

        guidance = (
            req.diffusion_guidance_factor
            if req.diffusion_guidance_factor is not None
            else 0.0
        )
        _log(f"Creating CrystalGenerator (guidance_factor={guidance}, "
             f"record_trajectories={req.record_trajectories})")

        generator = CrystalGenerator(
            checkpoint_info=checkpoint_info,
            properties_to_condition_on=properties,
            batch_size=req.batch_size,
            num_batches=req.num_batches,
            record_trajectories=req.record_trajectories,
            diffusion_guidance_factor=guidance,
            target_compositions_dict=req.target_compositions or [],
        )

        _log("Starting diffusion generation...")
        t1 = time.time()
        structures: list[Structure] = generator.generate(output_dir=output_path)
        t_gen = time.time() - t1
        _log(f"Generation complete: {len(structures)} structure(s) in {t_gen:.1f}s")

        _log("Serialising structures to JSON and CIF...")
        results = [_structure_to_dict(s) for s in structures]
        cifs = [_structure_to_cif(s) for s in structures]

        # Log a brief summary per structure
        for i, s in enumerate(structures):
            formula = s.composition.reduced_formula
            sg = s.get_space_group_info()
            _log(f"  Structure {i}: {formula}, space group {sg[0]} ({sg[1]}), "
                 f"{s.num_sites} sites")

        t_total = time.time() - t0
        _log(f"Total wall time: {t_total:.1f}s")

        _jobs[job_id].update(
            {
                "status": JobStatus.completed,
                "num_structures": len(results),
                "structures": results,
                "cif_strings": cifs,
                "message": f"Generated {len(results)} structure(s) in {t_total:.1f}s.",
                "debug_logs": logs,
            }
        )

    except Exception as exc:
        _log(f"Generation FAILED: {exc}", "error")
        _log(traceback.format_exc(), "error")
        _jobs[job_id].update(
            {
                "status": JobStatus.failed,
                "message": f"Generation failed: {exc}",
                "traceback": traceback.format_exc(),
                "debug_logs": logs,
            }
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    logger.debug("Mattergen service health check requested")
    return {"status": "ok", "service": "mattergen", "message": "Mattergen OK"}


@app.get("/info")
def info():
    logger.debug("Info endpoint requested")
    return {
        "name": "MatterGen",
        "description": (
            "MatterGen is a diffusion-based generative model for inorganic "
            "crystal structures developed by Microsoft Research."
        ),
        "version": "1.0.3",
        "pretrained_models": [
            "mattergen_base",
            "mp_20_base",
            "dft_band_gap",
            "dft_mag_density",
            "ml_bulk_modulus",
            "chemical_system_energy_above_hull",
            "space_group",
        ],
        "capabilities": [
            "unconditional_generation",
            "property_conditioned_generation",
            "crystal_structure_prediction",
        ],
    }


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    """Generate crystal structures.

    Currently runs synchronously.  For long-running jobs, switch to a
    background task (FastAPI BackgroundTasks or Celery) and poll via
    GET /results/{job_id}.
    """
    logger.info("POST /generate — payload: %s", req.model_dump_json(indent=None))

    if req.pretrained_name is None and req.model_path is None:
        raise HTTPException(
            status_code=400,
            detail="Either pretrained_name or model_path must be provided.",
        )

    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"status": JobStatus.pending, "message": "Queued"}
    logger.info("Job %s created", job_id)

    # Synchronous for now
    _run_generation(job_id, req)

    job = _jobs[job_id]
    logger.info("Job %s finished — status=%s", job_id, job["status"])

    return GenerateResponse(
        job_id=job_id,
        status=job["status"],
        message=job["message"],
        num_structures=job.get("num_structures", 0),
        structures=job.get("structures"),
        cif_strings=job.get("cif_strings"),
        debug_logs=job.get("debug_logs"),
    )


@app.get("/results/{job_id}", response_model=GenerateResponse)
def get_results(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    logger.debug("GET /results/%s — status=%s", job_id, job["status"])
    return GenerateResponse(
        job_id=job_id,
        status=job["status"],
        message=job["message"],
        num_structures=job.get("num_structures", 0),
        structures=job.get("structures"),
        cif_strings=job.get("cif_strings"),
        debug_logs=job.get("debug_logs"),
    )


# ---------------------------------------------------------------------------
# Demo / testing endpoint — returns a hardcoded structure so the front-end
# can be developed without waiting for a real generation run.
# The structure is taken from data/mattergen/outputs/0f249ec2e65b/generated_crystals.extxyz
# ---------------------------------------------------------------------------

_DEMO_STRUCTURE = Structure(
    lattice=Lattice([
        [10.356451988220215, 0.0, 0.16560612618923187],
        [-2.4214442593693084, 9.319854048729752, -3.681112766265869],
        [0.0, 0.0, 11.25183391571045],
    ]),
    species=[
        "Sr", "Sr", "I", "Cs", "Sr", "I", "Cs", "I", "I", "Cs",
        "I", "Sr", "I", "I", "I", "I", "I", "Cs", "I", "I",
    ],
    coords=[
        [4.89878152, 9.27800329, 2.73218545],
        [2.20597701, 6.46096994, 6.99037194],
        [2.38055207, 7.48180384, 3.70299452],
        [2.63326627, 1.44135240, 8.48418443],
        [6.52382344, 5.54208093, -1.71133506],
        [5.90285078, 8.52808717, -0.38063449],
        [3.22416641, 3.96575405, 2.20541075],
        [5.26742997, 1.94922166, 4.96712937],
        [7.96304556, 8.44236862, 3.35836302],
        [-0.40622897, 9.15733615, -0.10823609],
        [7.32503800, 2.33721565, 8.66478728],
        [7.77087984, 1.05645209, 0.50339618],
        [-0.88914865, 6.43593992, 8.28276809],
        [5.47983506, 7.20897067, 6.73368996],
        [4.58091570, 0.27485338, 0.50484940],
        [3.29117519, 5.00603318, -1.51386601],
        [1.28103117, 3.65560166, 5.53127688],
        [8.08213535, 4.88278960, 4.93179978],
        [0.45591711, 1.88368216, 0.55892154],
        [7.00212069, 4.21551731, 1.25900193],
    ],
    coords_are_cartesian=True,
)

_DEMO_STRUCTURE_DICT = _structure_to_dict(_DEMO_STRUCTURE)
_DEMO_CIF_STRING = _structure_to_cif(_DEMO_STRUCTURE)
_DEMO_JOB_ID = "demo000000"


@app.post("/demo/generate", response_model=GenerateResponse)
def demo_generate():
    """Return a fake generation response for UI/integration testing.

    Uses a real structure from a previous MatterGen run so the data is
    physically meaningful.  No model loading or GPU work is performed.
    """
    logger.info("POST /demo/generate — returning canned response")

    formula = _DEMO_STRUCTURE.composition.reduced_formula
    n_sites = _DEMO_STRUCTURE.num_sites

    # Also store in the job store so /results/<id> works
    _jobs[_DEMO_JOB_ID] = {
        "status": JobStatus.completed,
        "message": f"Demo: 1 structure returned ({formula}, {n_sites} sites, from cached run 0f249ec2e65b).",
        "num_structures": 1,
        "structures": [_DEMO_STRUCTURE_DICT],
        "cif_strings": [_DEMO_CIF_STRING],
        "debug_logs": [
            "[INFO] Demo mode — no model was loaded.",
            f"[INFO] Returning cached structure: {formula} ({n_sites} sites).",
        ],
    }

    return GenerateResponse(
        job_id=_DEMO_JOB_ID,
        status=JobStatus.completed,
        message=_jobs[_DEMO_JOB_ID]["message"],
        num_structures=1,
        structures=[_DEMO_STRUCTURE_DICT],
        cif_strings=[_DEMO_CIF_STRING],
        debug_logs=_jobs[_DEMO_JOB_ID]["debug_logs"],
    )
