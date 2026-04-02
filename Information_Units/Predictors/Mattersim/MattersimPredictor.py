"""
MattersimPredictor — EMOS ↔ MatterSim Docker interface
=======================================================
This file lives on the **host** (EMOS backend) and communicates with the
MatterSim container over HTTP.

The MatterSim container runs a FastAPI server (see ``docker/mattersim_api.py``)
and is started via ``docker compose up mattersim``.

Environment variables
---------------------
MATTERSIM_API_URL : str
    Base URL of the MatterSim container API.
    Default: ``http://localhost:8300``
MATTERSIM_TIMEOUT : int
    HTTP request timeout in seconds (prediction can be slow on CPU).
    Default: ``600``
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict

import requests

from Information_Units.Predictors.BasePredictor import BasePredictor


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_DEFAULT_API_URL = "http://localhost:8300"
_DEFAULT_TIMEOUT = 600  # seconds


class MattersimPredictor(BasePredictor):
    """Client-side interface to the containerised MatterSim service."""

    # Class-level health cache shared across instances
    _health_cache: dict = {"healthy": None, "checked_at": 0.0}
    _HEALTH_CACHE_TTL = 120  # seconds — only re-check health every 2 minutes

    def __init__(self, predictor_name='mattersim', logger=None):
        super().__init__(predictor_name, logger)
        self.api_url = os.getenv("MATTERSIM_API_URL", _DEFAULT_API_URL).rstrip("/")
        self.timeout = int(os.getenv("MATTERSIM_TIMEOUT", _DEFAULT_TIMEOUT))

    # ------------------------------------------------------------------
    # BasePredictor interface
    # ------------------------------------------------------------------

    def info(self) -> str:
        """Return model metadata from the container, or a fallback string."""
        try:
            resp = requests.get(f"{self.api_url}/info", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return (
                f"{data['name']} v{data['version']} — {data['description']}\n"
                f"Capabilities: {', '.join(data.get('capabilities', []))}"
            )
        except Exception as exc:
            return (
                "MatterSim: Microsoft's Machine Learning Interatomic Potential (MLIP) "
                "for predicting properties of inorganic crystals. Supports energy, "
                "forces, stress calculations and structure relaxation. "
                f"(container unreachable: {exc})"
            )

    def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict material properties by calling the MatterSim container.

        Args:
            input_data (dict): Input parameters.
                Expected keys:
                {
                    'cif_file': '/path/to/structure.cif',              # REQUIRED
                    'compute_energy': True,                            # Optional (default: True)
                    'compute_forces': True,                            # Optional (default: True)
                    'compute_stress': True,                            # Optional (default: True)
                    'relax': True,                                     # Optional (default: True)
                    'relax_atoms': True,                               # Optional (default: True)
                    'relax_cell': True,                                # Optional (default: True)
                    'output_dir': '/path/to/output'                    # Optional: save relaxed CIF
                }

        Returns:
            dict: ``{"status": ..., "properties": {...}, "warnings": [...], "error": ...}``
        """
        if self.logger:
            self.logger.log("MatterSim: sending prediction request to container", "info")

        # Validate input
        if not input_data or 'cif_file' not in input_data:
            error_msg = "Missing required parameter: 'cif_file'"
            if self.logger:
                self.logger.log(error_msg, 'error')
            return {'status': 'error', 'properties': {}, 'warnings': [], 'error': error_msg}

        cif_filepath = input_data['cif_file']
        cif_path = Path(cif_filepath)

        # Validate file exists on host
        if not cif_path.exists():
            error_msg = f"File not found: {cif_filepath}"
            if self.logger:
                self.logger.log(error_msg, 'error')
            return {'status': 'error', 'properties': {}, 'warnings': [], 'error': error_msg}

        # Check container health
        if not self.is_healthy():
            msg = (
                f"MatterSim container is not reachable at {self.api_url}. "
                "Start it with: docker compose up mattersim"
            )
            if self.logger:
                self.logger.log(msg, "error")
            return {'status': 'error', 'properties': {}, 'warnings': [], 'error': msg}

        # Read CIF file contents to send as string
        try:
            cif_string = cif_path.read_text()
        except Exception as e:
            error_msg = f"Failed to read CIF file: {e}"
            if self.logger:
                self.logger.log(error_msg, 'error')
            return {'status': 'error', 'properties': {}, 'warnings': [], 'error': error_msg}

        # Build request payload
        payload = {
            "cif_string": cif_string,
            "compute_energy": input_data.get("compute_energy", True),
            "compute_forces": input_data.get("compute_forces", True),
            "compute_stress": input_data.get("compute_stress", True),
            "relax": input_data.get("relax", True),
            "relax_atoms": input_data.get("relax_atoms", True),
            "relax_cell": input_data.get("relax_cell", True),
        }

        if self.logger:
            self.logger.log(f"MatterSim prediction starting for: {cif_filepath}", 'info')

        # Call the container
        try:
            resp = requests.post(
                f"{self.api_url}/predict",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            result = resp.json()

            if self.logger:
                self.logger.log(
                    f"MatterSim: prediction complete (status={result.get('status')})",
                    "info",
                )

            # Save relaxed CIF locally if output_dir provided and container returned one
            output_dir = input_data.get("output_dir")
            if output_dir and result.get("properties", {}).get("relaxed_cif_string"):
                relaxed_cif_path = self._save_relaxed_cif(
                    cif_string=result["properties"]["relaxed_cif_string"],
                    cif_filename=cif_path.name,
                    output_dir=output_dir,
                )
                result["properties"]["relaxed_cif"] = relaxed_cif_path
                # Remove the raw CIF string from the result (it can be large)
                result["properties"].pop("relaxed_cif_string", None)

            return result

        except requests.Timeout:
            msg = f"MatterSim: request timed out after {self.timeout}s"
            if self.logger:
                self.logger.log(msg, "error")
            MattersimPredictor._health_cache["healthy"] = None
            return {'status': 'error', 'properties': {}, 'warnings': [], 'error': msg}

        except requests.RequestException as exc:
            msg = f"MatterSim: HTTP error — {exc}"
            if self.logger:
                self.logger.log(msg, "error")
            MattersimPredictor._health_cache["healthy"] = None
            return {'status': 'error', 'properties': {}, 'warnings': [], 'error': msg}

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def is_healthy(self) -> bool:
        """Return True if the MatterSim container is reachable.

        Results are cached for ``_HEALTH_CACHE_TTL`` seconds so that
        rapid-fire calls do not flood the container with health-check requests.
        """
        now = time.time()
        cache = MattersimPredictor._health_cache
        if cache["healthy"] is not None and (now - cache["checked_at"]) < self._HEALTH_CACHE_TTL:
            return cache["healthy"]

        try:
            resp = requests.get(f"{self.api_url}/health", timeout=10)
            healthy = resp.status_code == 200
        except Exception:
            healthy = False

        cache["healthy"] = healthy
        cache["checked_at"] = now

        if self.logger:
            status = "reachable" if healthy else "unreachable"
            self.logger.log(f"MatterSim container health: {status}", "info")

        return healthy

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _save_relaxed_cif(self, cif_string: str, cif_filename: str, output_dir: str) -> str:
        """Save relaxed CIF string (returned by container) to a local file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        base_name = Path(cif_filename).stem
        relaxed_filepath = output_path / f"{base_name}_relaxed.cif"
        relaxed_filepath.write_text(cif_string)

        if self.logger:
            self.logger.log(f"Saved relaxed CIF to {relaxed_filepath}", "info")

        return str(relaxed_filepath)
