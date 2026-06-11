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
from typing import Any, Dict, List

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
        self.source = "mattersim"
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

    def predict(self, input_data: list[str], **options: Any) -> Dict[str, Any]:
        """
        Predict material properties by calling the MatterSim container.

        Args:
            input_data (list[str]): CIF strings.
            **options (Any): Optional calculation parameters
                (compute/relax flags, output_dir).

        Returns:
            Dict[str, Any]: Prediction payload with shape:
                {
                    "source": "mattersim",
                    "results": [
                        {
                            "index": int,
                            "status": str,
                            "properties": dict[str, Any],
                            "warnings": list[str],
                            "error": str | None
                        }
                    ]
                }.
        """
        if self.logger:
            self.logger.log("MatterSim: sending prediction request to container", "info")

        cif_strings = self._extract_cif_strings(input_data)
        if not cif_strings:
            return {
                "source": self.source,
                "results": [
                    {
                        "index": 0,
                        "cif_input": "",
                        "status": "error",
                        "properties": {},
                        "warnings": [],
                        "error": "Missing required input: list[str] of CIF strings",
                    }
                ],
            }

        # Check container health once for the full batch
        if not self.is_healthy():
            msg = (
                f"MatterSim container is not reachable at {self.api_url}. "
                "Start it with: docker compose up mattersim"
            )
            if self.logger:
                self.logger.log(msg, "error")
            return {
                "source": self.source,
                "results": [
                    {
                        "index": idx,
                        "cif_input": cif_strings[idx] if idx < len(cif_strings) else "",
                        "status": "error",
                        "properties": {},
                        "warnings": [],
                        "error": msg,
                    }
                    for idx in range(len(cif_strings))
                ],
            }

        results: List[Dict[str, Any]] = []
        for idx, cif_string in enumerate(cif_strings):
            payload = {
                "cif_string": cif_string,
                "compute_energy": options.get("compute_energy", True),
                "compute_forces": options.get("compute_forces", True),
                "compute_stress": options.get("compute_stress", True),
                "relax": options.get("relax", True),
                "relax_atoms": options.get("relax_atoms", True),
                "relax_cell": options.get("relax_cell", True),
            }

            try:
                resp = requests.post(
                    f"{self.api_url}/predict",
                    json=payload,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                result = resp.json()

                properties = result.get("properties", {}) if isinstance(result, dict) else {}
                output_dir = options.get("output_dir")
                if output_dir and properties.get("relaxed_cif_string"):
                    relaxed_cif_path = self._save_relaxed_cif(
                        cif_string=properties["relaxed_cif_string"],
                        cif_filename=f"structure_{idx}.cif",
                        output_dir=output_dir,
                    )
                    properties["relaxed_cif"] = relaxed_cif_path
                    properties.pop("relaxed_cif_string", None)

                results.append(
                    {
                        "index": idx,
                        "cif_input": cif_string,
                        "status": result.get("status", "ok"),
                        "properties": properties,
                        "warnings": result.get("warnings", []),
                        "error": result.get("error"),
                    }
                )
            except requests.Timeout:
                msg = f"MatterSim: request timed out after {self.timeout}s"
                MattersimPredictor._health_cache["healthy"] = None
                results.append(
                    {
                        "index": idx,
                        "cif_input": cif_string,
                        "status": "error",
                        "properties": {},
                        "warnings": [],
                        "error": msg,
                    }
                )
            except requests.RequestException as exc:
                msg = f"MatterSim: HTTP error — {exc}"
                MattersimPredictor._health_cache["healthy"] = None
                results.append(
                    {
                        "index": idx,
                        "cif_input": cif_string,
                        "status": "error",
                        "properties": {},
                        "warnings": [],
                        "error": msg,
                    }
                )

        return {"source": self.source, "results": results}

    def _extract_cif_strings(self, input_data) -> List[str]:
        """Extract valid CIF strings from direct list input."""
        if isinstance(input_data, list):
            return [s for s in input_data if isinstance(s, str) and s.strip()]
        return []

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
