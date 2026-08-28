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
from Information_Units.property_mappings.property_loader import load_source_property_mapping
from Information_Units.service_urls import normalise_service_url


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_DEFAULT_API_URL = "http://localhost:8300"
_DEFAULT_TIMEOUT = 600  # seconds


class MattersimPredictor(BasePredictor):
    """Client-side interface to the containerised MatterSim service."""

    # All possible output properties that MatterSim can produce
    OUTPUT_PROPERTIES = (
        'energy', 'forces', 'stress',
        'num_atoms',
        'relaxed_energy', 'relaxed_forces', 'relaxed_stress', 'relaxed_cif',
        'relaxed_structure', 'relaxed_cell'
    )

    # Class-level health cache shared across instances
    _health_cache: dict = {"healthy": None, "checked_at": 0.0}
    _HEALTH_CACHE_TTL = 120  # seconds — only re-check health every 2 minutes

    def __init__(self, predictor_name='mattersim', logger=None):
        super().__init__(predictor_name, logger)
        self.source = "mattersim"
        self.api_url = normalise_service_url(
            os.getenv("MATTERSIM_API_URL"),
            _DEFAULT_API_URL,
        )
        self.timeout = int(os.getenv("MATTERSIM_TIMEOUT", _DEFAULT_TIMEOUT))
        
        # Load and validate property mappings
        self._mapped_output_properties = self._load_mapped_output_properties()
        self._check_output_properties_in_mapping({prop: None for prop in self.OUTPUT_PROPERTIES})
        
        if self.logger:
            self.logger.log(
                f"Initialized MatterSim predictor with {len(self.OUTPUT_PROPERTIES)} possible output properties",
                'info'
            )

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

    # ------------------------------------------------------------------
    # Property Mapping Validation
    # ------------------------------------------------------------------

    def _load_mapped_output_properties(self) -> set:
        """Load MatterSim output properties from modular property mapping files."""
        try:
            source_mapping = load_source_property_mapping(source='mattersim', source_type='predictors')
        except Exception as e:
            raise RuntimeError(f"Failed to load modular MatterSim property mappings: {str(e)}") from e

        mapped = set()
        for prop_name, ms_info in source_mapping.items():
            if isinstance(ms_info, dict) and ms_info.get('predictable'):
                mapped.add(prop_name)

        return mapped

    def _check_output_properties_in_mapping(self, properties: dict) -> None:
        """Ensure all declared OUTPUT_PROPERTIES are in the MatterSim mapping."""
        missing = sorted(set(properties.keys()) - self._mapped_output_properties)
        if missing:
            raise ValueError(
                "MatterSim output properties missing in modular property mappings: "
                + ", ".join(missing)
            )

    def _validate_and_filter_properties(self, properties: dict) -> dict:
        """Validate that all properties in result are declared, then return filtered dict."""
        undeclared = sorted(set(properties.keys()) - self._mapped_output_properties)
        if undeclared:
            raise ValueError(
                "MatterSim result contains undeclared properties: " + ", ".join(undeclared)
            )
        return properties

    # ------------------------------------------------------------------
    # BasePredictor interface
    # ------------------------------------------------------------------


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
                properties = self._normalize_properties(properties, idx, output_dir=options.get("output_dir"))

                results.append(
                    {
                        "index": idx,
                        "cif_input": cif_string,
                        "status": result.get("status", "ok"),
                        "properties": self._validate_and_filter_properties(properties),
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

    def _normalize_properties(self, properties: dict, index: int, output_dir: str | None = None) -> dict:
        """Normalize transport-only MatterSim fields into the public predictor schema."""
        normalized = dict(properties)
        normalized.pop("cell", None)
        normalized.pop("positions", None)
        normalized.pop("atomic_numbers", None)
        relaxed_cif_string = normalized.pop("relaxed_cif_string", None)

        if relaxed_cif_string:
            if output_dir:
                normalized["relaxed_cif"] = self._save_relaxed_cif(
                    cif_string=relaxed_cif_string,
                    cif_filename=f"structure_{index}.cif",
                    output_dir=output_dir,
                )
            else:
                normalized.setdefault("relaxed_cif", relaxed_cif_string)

        return normalized

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

    def availability(self) -> dict[str, Any]:
        """Return container readiness and advertised MatterSim capabilities."""
        result: dict[str, Any] = {
            "available": False,
            "service": "mattersim",
            "models": [],
        }
        try:
            health_response = requests.get(f"{self.api_url}/health", timeout=10)
            health_response.raise_for_status()
            info_response = requests.get(f"{self.api_url}/info", timeout=10)
            info_response.raise_for_status()
            info = info_response.json()
            result["available"] = True
            result["models"] = info.get("models", [info.get("name", "mattersim")])
            result["version"] = info.get("version")
            result["capabilities"] = info.get("capabilities", [])
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: service check failed"
        return result

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
