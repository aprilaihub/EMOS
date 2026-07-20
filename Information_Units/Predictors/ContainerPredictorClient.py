"""HTTP-only client base for containerized predictor services."""

from __future__ import annotations

import os
from typing import Any

import requests
from pymatgen.io.cif import CifParser

from Information_Units.Predictors.BasePredictor import BasePredictor
from Information_Units.service_urls import normalise_service_url


class ContainerPredictorClient(BasePredictor):
    """Translate EMOS CIF batches to a predictor container's HTTP API."""

    source = "container"
    service_name = "container"
    api_url_env = "PREDICTOR_API_URL"
    timeout_env = "PREDICTOR_TIMEOUT"
    default_api_url = "http://localhost:8000"
    default_timeout = 600
    property_map: dict[str, str] = {}
    readiness_path = "/ready"

    def __init__(self, predictor_name: str, logger=None):
        super().__init__(predictor_name, logger)
        self.api_url = normalise_service_url(
            os.getenv(self.api_url_env),
            self.default_api_url,
        )
        self.timeout = int(os.getenv(self.timeout_env, self.default_timeout))

    def info(self) -> str:
        try:
            response = requests.get(f"{self.api_url}/info", timeout=10)
            response.raise_for_status()
            data = response.json()
            properties = data.get("supported_properties", [])
            return f"{data.get('name', self.service_name)}: {', '.join(properties)}"
        except Exception as exc:
            return f"{self.service_name} container unavailable: {exc}"

    def availability(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "available": False,
            "service": self.service_name,
            "models": [],
        }
        try:
            ready_response = requests.get(f"{self.api_url}{self.readiness_path}", timeout=30)
            ready_response.raise_for_status()
            info_response = requests.get(f"{self.api_url}/info", timeout=10)
            info_response.raise_for_status()
            info = info_response.json()
            result["available"] = True
            result["models"] = info.get("supported_properties", [])
            result["version"] = info.get("version")
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: service check failed"
        return result

    def is_healthy(self) -> bool:
        return bool(self.availability()["available"])

    def predict(self, input_data: list[str]) -> dict[str, Any]:
        if not isinstance(input_data, list) or not input_data:
            return {
                "source": self.source,
                "results": [self._error_result(0, "", "Missing required input: list[str] of CIF strings")],
            }

        results = []
        for index, cif_string in enumerate(input_data):
            if not isinstance(cif_string, str) or not cif_string.strip():
                results.append(self._error_result(index, "", "Input item must be a non-empty CIF string"))
                continue

            try:
                parser = CifParser.from_str(cif_string)
                structures = parser.parse_structures(primitive=True)
                if not structures:
                    raise ValueError("No structure could be parsed from the CIF input")

                response = requests.post(
                    f"{self.api_url}/batch-predict",
                    json={"structure": structures[0].as_dict()},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                properties, warnings = self._translate_predictions(response.json())
                results.append(
                    {
                        "index": index,
                        "cif_input": cif_string,
                        "status": "ok",
                        "properties": properties,
                        "warnings": warnings,
                        "error": None,
                    }
                )
            except Exception as exc:
                results.append(self._error_result(index, cif_string, str(exc)))

        return {"source": self.source, "results": results}

    def _translate_predictions(self, payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        predictions = payload.get("predictions")
        if not isinstance(predictions, dict):
            raise ValueError("Container response is missing a predictions object")

        properties: dict[str, Any] = {}
        warnings: list[str] = []
        for api_name, output_name in self.property_map.items():
            prediction = predictions.get(api_name)
            if not isinstance(prediction, dict):
                properties[output_name] = None
                warnings.append(f"{api_name}: missing from container response")
            elif prediction.get("error"):
                properties[output_name] = None
                warnings.append(f"{api_name}: {prediction['error']}")
            else:
                properties[output_name] = prediction.get("prediction")

        self._add_service_properties(payload, properties)
        return properties, warnings

    def _add_service_properties(self, payload: dict[str, Any], properties: dict[str, Any]) -> None:
        return None

    @staticmethod
    def _error_result(index: int, cif_input: str, error: str) -> dict[str, Any]:
        return {
            "index": index,
            "cif_input": cif_input,
            "status": "error",
            "properties": {},
            "warnings": [],
            "error": error,
        }