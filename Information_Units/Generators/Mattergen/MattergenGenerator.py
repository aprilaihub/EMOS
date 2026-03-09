"""
MattergenGenerator — EMOS ↔ MatterGen Docker interface
=======================================================
This file lives on the **host** (EMOS backend) and communicates with the
MatterGen container over HTTP.  

The MatterGen container runs a FastAPI server (see ``docker/mattergen_api.py``)
and is started via ``docker compose up mattergen``.

Environment variables
---------------------
MATTERGEN_API_URL : str
    Base URL of the MatterGen container API.
    Default: ``http://localhost:8100``
MATTERGEN_TIMEOUT : int
    HTTP request timeout in seconds (generation can be slow on CPU).
    Default: ``600``
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

import requests

from Information_Units.Generators.BaseGenerator import BaseGenerator


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_DEFAULT_API_URL = "http://localhost:8100"
_DEFAULT_TIMEOUT = 600  # seconds

_MODEL_PROPERTIES_MAP = {"chemical_system":["chemical_system"],
                         "chemical_system_energy_above_hull":["chemical_system", "energy_above_hull"],
                         "dft_band_gap":["dft_band_gap"],
                         "dft_mag_density":["dft_mag_density"],
                         "dft_mag_density_hhi_score":["dft_mag_density", "hhi_score"],
                         "ml_bulk_modulus":["ml_bulk_modulus"],
                         "space_group":["space_group"]}

class MattergenGenerator(BaseGenerator):
    """Client-side interface to the containerised MatterGen service."""

    def __init__(self, generator_name: str = "mattergen", logger=None):
        super().__init__(generator_name, logger)
        self.api_url = os.getenv("MATTERGEN_API_URL", _DEFAULT_API_URL).rstrip("/")
        self.timeout = int(os.getenv("MATTERGEN_TIMEOUT", _DEFAULT_TIMEOUT))

    # ------------------------------------------------------------------
    # BaseGenerator interface
    # ------------------------------------------------------------------

    def info(self) -> str:
        """Return model metadata from the container, or a fallback string."""
        try:
            resp = requests.get(f"{self.api_url}/info", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return (
                f"{data['name']} v{data['version']} — {data['description']}\n"
                f"Pretrained models: {', '.join(data.get('pretrained_models', []))}\n"
                f"Capabilities: {', '.join(data.get('capabilities', []))}"
            )
        except Exception as exc:
            return (
                "MatterGen is a diffusion-based generative model for inorganic "
                f"crystal structures (container unreachable: {exc})."
            )

    def generate(self, inputs: dict) -> dict:
        """
        Generate crystal structures by calling the MatterGen container.

        Parameters
        ----------
        inputs : dict
            Accepted keys (all optional except that at least one of
            ``pretrained_name`` / ``model_path`` must be set):

            - **pretrained_name** (str) – HuggingFace model name.
              Default ``"mattergen_base"``.
            - **model_path** (str) – path *inside the container* to a
              local checkpoint directory.
            - **batch_size** (int) – structures per batch. Default ``64``.
            - **num_batches** (int) – number of batches. Default ``1``.
            - **properties_to_condition_on** (dict) – e.g.
              ``{"dft_band_gap": 1.5}``.
            - **target_compositions** (list[dict]) – e.g.
              ``[{"Si": 2, "O": 4}]``.
            - **record_trajectories** (bool) – Default ``True``.
            - **diffusion_guidance_factor** (float | None).

        Returns
        -------
        dict
            ``{"job_id": ..., "status": ..., "message": ...,
            "num_structures": ..., "structures": [...]}``
        """
        if self.logger:
            self.logger.log("MatterGen: sending generation request to container", "info")

        # ---- check health first ----
        if not self.is_healthy():
            msg = (
                f"MatterGen container is not reachable at {self.api_url}. "
                "Start it with: docker compose up mattergen"
            )
            if self.logger:
                self.logger.log(msg, "error")
            return {"status": "error", "message": msg}

        # ---- build request payload ----
        payload = {
            "pretrained_name": inputs.get("pretrained_name", "mattergen_base"),
            "batch_size": int(inputs.get("batch_size", 64)),
            "num_batches": int(inputs.get("num_batches", 1)),
            "record_trajectories": inputs.get("record_trajectories", True),
        }

        if inputs.get("model_path"):
            payload["model_path"] = inputs["model_path"]
            payload["pretrained_name"] = None

        if inputs.get("properties_to_condition_on"):
            payload["properties_to_condition_on"] = inputs["properties_to_condition_on"]

        if inputs.get("target_compositions"):
            payload["target_compositions"] = inputs["target_compositions"]

        if inputs.get("diffusion_guidance_factor") is not None:
            payload["diffusion_guidance_factor"] = float(inputs["diffusion_guidance_factor"])

        # ---- call the container ----
        try:
            resp = requests.post(
                f"{self.api_url}/generate",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            result = resp.json()

            print(resp)


            if self.logger:
                self.logger.log(
                    f"MatterGen: generated {result.get('num_structures', 0)} structure(s)",
                    "info",
                )
            return result

        except requests.Timeout:
            msg = f"MatterGen: request timed out after {self.timeout}s"
            if self.logger:
                self.logger.log(msg, "error")
            return {"status": "error", "message": msg}

        except requests.RequestException as exc:
            msg = f"MatterGen: HTTP error — {exc}"
            if self.logger:
                self.logger.log(msg, "error")
            return {"status": "error", "message": msg}

    # ------------------------------------------------------------------
    # Extra helpers (not part of BaseGenerator but useful for the UI)
    # ------------------------------------------------------------------

    def is_healthy(self) -> bool:
        """Return True if the MatterGen container is reachable."""
        try:
            resp = requests.get(f"{self.api_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_available_models(self) -> list[str]:
        """Return the list of pretrained model names from the container."""
        try:
            resp = requests.get(f"{self.api_url}/info", timeout=10)
            resp.raise_for_status()
            return resp.json().get("pretrained_models", [])
        except Exception:
            return []

    def get_results(self, job_id: str) -> dict:
        """Poll results for a previously submitted job."""
        try:
            resp = requests.get(f"{self.api_url}/results/{job_id}", timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            return {"status": "error", "message": str(exc)}
