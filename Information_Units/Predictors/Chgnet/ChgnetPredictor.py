"""
ChgnetPredictor — EMOS ↔ CHGNet Docker interface
=================================================
This file lives on the host (EMOS backend) and communicates with the
CHGNet container over HTTP.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

from Information_Units.Predictors.BasePredictor import BasePredictor
from Information_Units.property_mappings.property_loader import load_source_property_mapping


_DEFAULT_API_URL = "http://localhost:8400"
_DEFAULT_TIMEOUT = 600


class ChgnetPredictor(BasePredictor):
    """Client-side interface to the containerized CHGNet service."""

    OUTPUT_PROPERTIES = (
        "energy",
        "forces",
        "stress",
        "num_atoms",
        "relaxed_energy",
        "relaxed_forces",
        "relaxed_stress",
        "relaxed_cif",
        "relaxed_structure",
        "relaxed_cell",
    )

    _health_cache: dict = {"healthy": None, "checked_at": 0.0}
    _HEALTH_CACHE_TTL = 120

    def __init__(self, predictor_name: str = "chgnet", logger=None):
        super().__init__(predictor_name, logger)
        self.source = "chgnet"
        self.api_url = os.getenv("CHGNET_API_URL", _DEFAULT_API_URL).rstrip("/")
        self.timeout = int(os.getenv("CHGNET_TIMEOUT", _DEFAULT_TIMEOUT))

        self._mapped_output_properties = self._load_mapped_output_properties()
        self._check_output_properties_in_mapping({prop: None for prop in self.OUTPUT_PROPERTIES})

        if self.logger:
            self.logger.log(
                f"Initialized CHGNet predictor with {len(self.OUTPUT_PROPERTIES)} possible output properties",
                "info",
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
                "CHGNet: Charge-informed graph neural network potential for predicting "
                "energy, forces, stress, and structure relaxation in inorganic crystals. "
                f"(container unreachable: {exc})"
            )

    def _load_mapped_output_properties(self) -> set:
        try:
            source_mapping = load_source_property_mapping(source="chgnet", source_type="predictors")
        except Exception as exc:
            raise RuntimeError(f"Failed to load modular CHGNet property mappings: {exc}") from exc

        mapped = set()
        for prop_name, prop_info in source_mapping.items():
            if isinstance(prop_info, dict) and prop_info.get("predictable"):
                mapped.add(prop_name)
        return mapped

    def _check_output_properties_in_mapping(self, properties: dict) -> None:
        missing = sorted(set(properties.keys()) - self._mapped_output_properties)
        if missing:
            raise ValueError(
                "CHGNet output properties missing in modular property mappings: " + ", ".join(missing)
            )

    def _validate_and_filter_properties(self, properties: dict) -> dict:
        undeclared = sorted(set(properties.keys()) - self._mapped_output_properties)
        if undeclared:
            raise ValueError(
                "CHGNet result contains undeclared properties: " + ", ".join(undeclared)
            )
        return properties

    def predict(self, input_data: list[str], **options: Any) -> Dict[str, Any]:
        if self.logger:
            self.logger.log("CHGNet: sending prediction request to container", "info")

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

        if not self.is_healthy():
            msg = (
                f"CHGNet container is not reachable at {self.api_url}. "
                "Start it with: docker compose up chgnet"
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
                "fmax": options.get("fmax", 0.1),
                "max_steps": options.get("max_steps", 500),
            }

            try:
                resp = requests.post(f"{self.api_url}/predict", json=payload, timeout=self.timeout)
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
                msg = f"CHGNet: request timed out after {self.timeout}s"
                ChgnetPredictor._health_cache["healthy"] = None
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
                msg = f"CHGNet: HTTP error — {exc}"
                ChgnetPredictor._health_cache["healthy"] = None
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
        if isinstance(input_data, list):
            return [item for item in input_data if isinstance(item, str) and item.strip()]
        return []

    def _normalize_properties(self, properties: dict, index: int, output_dir: str | None = None) -> dict:
        normalized = dict(properties)
        normalized.pop("magmom", None)
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

    def is_healthy(self) -> bool:
        now = time.time()
        cache = ChgnetPredictor._health_cache
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
            self.logger.log(f"CHGNet container health: {status}", "info")

        return healthy

    def _save_relaxed_cif(self, cif_string: str, cif_filename: str, output_dir: str) -> str:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        base_name = Path(cif_filename).stem
        relaxed_filepath = output_path / f"{base_name}_relaxed.cif"
        relaxed_filepath.write_text(cif_string)

        if self.logger:
            self.logger.log(f"Saved relaxed CIF to {relaxed_filepath}", "info")

        return str(relaxed_filepath)