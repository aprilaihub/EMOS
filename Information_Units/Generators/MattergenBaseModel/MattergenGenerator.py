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
import re
import time
from typing import Any, Generator, Optional

import requests

from Information_Units.Generators.BaseGenerator import BaseGenerator


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_DEFAULT_API_URL = "http://localhost:8100"
_DEFAULT_TIMEOUT = 600  # seconds


def _normalise_api_url(raw_url: str) -> str:
    """Ensure MATTERGEN_API_URL is a valid absolute HTTP(S) URL."""
    candidate = (raw_url or _DEFAULT_API_URL).strip().rstrip("/")
    if not candidate:
        return _DEFAULT_API_URL
    if "://" not in candidate:
        candidate = f"http://{candidate}"
    return candidate



class MattergenGenerator(BaseGenerator):
    """Client-side interface to the containerised MatterGen service."""

    # Class-level health cache shared across instances
    _health_cache: dict = {"healthy": None, "checked_at": 0.0}
    _HEALTH_CACHE_TTL = 120  # seconds — only re-check health every 2 minutes

    def __init__(self, generator_name: str = "mattergen", logger=None):
        super().__init__(generator_name, logger)
        self.api_url = _normalise_api_url(os.getenv("MATTERGEN_API_URL", _DEFAULT_API_URL))
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

    def generate(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Generate crystal structures by calling the MatterGen container.

        Parameters
        ----------
        inputs : dict[str, Any]
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
        dict[str, Any]
            ``{"job_id": ..., "status": ..., "message": ...,
            "num_structures": ..., "structures": [...]}``
        """
        if self.logger:
            self.logger.log("MatterGen: sending generation request to container", "info")
        queries = self._normalise_queries(inputs)

        # ---- check health first ----
        if not self.is_healthy():
            msg = (
                f"MatterGen container is not reachable at {self.api_url}. "
                "Start it with: docker compose up mattergen"
            )
            if self.logger:
                self.logger.log(msg, "error")
            return {
                "status": "error",
                "message": msg,
                "source": self.generator_name,
                "queries": queries,
                "cif_strings": [],
            }

        # ---- demo shortcut: call /demo/generate, skip payload build ----
        if inputs.get("pretrained_name") == "demo":
            if self.logger:
                self.logger.log("MatterGen: using demo endpoint (fake response)", "info")
            try:
                resp = requests.post(
                    f"{self.api_url}/demo/generate",
                    timeout=30,
                )
                resp.raise_for_status()
                result = self._enrich_result(resp.json(), queries)
                if self.logger:
                    self.logger.log(
                        f"MatterGen demo: {result.get('num_structures', 0)} structure(s)",
                        "info",
                    )
                return result
            except requests.RequestException as exc:
                msg = f"MatterGen demo: HTTP error — {exc}"
                if self.logger:
                    self.logger.log(msg, "error")
                return {
                    "status": "error",
                    "message": msg,
                    "source": self.generator_name,
                    "queries": queries,
                    "cif_strings": [],
                }

        # ---- build request payload ----
        payload = self._build_payload(inputs)

        # ---- call the container ----
        try:
            resp = requests.post(
                f"{self.api_url}/generate",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            result = self._enrich_result(resp.json(), queries)


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
            # Invalidate health cache so next call re-checks
            MattergenGenerator._health_cache["healthy"] = None
            return {
                "status": "error",
                "message": msg,
                "source": self.generator_name,
                "queries": queries,
                "cif_strings": [],
            }

        except requests.RequestException as exc:
            msg = f"MatterGen: HTTP error — {exc}"
            if self.logger:
                self.logger.log(msg, "error")
            # Invalidate health cache so next call re-checks
            MattergenGenerator._health_cache["healthy"] = None
            return {
                "status": "error",
                "message": msg,
                "source": self.generator_name,
                "queries": queries,
                "cif_strings": [],
            }

    # ------------------------------------------------------------------
    # Streaming generation — SSE bridge
    # ------------------------------------------------------------------

    def generate_stream(self, inputs: dict) -> Generator[dict, None, None]:
        """Generate crystal structures, yielding SSE events as they arrive.

        Each yielded dict has an ``"event"`` key (``log``, ``progress``,
        ``result``, ``error``, ``done``) and event-specific payload keys.

        Falls back to the synchronous ``generate()`` method (wrapped as a
        single ``result`` event) if the container doesn't support streaming
        or if the call fails.
        """
        if self.logger:
            self.logger.log("MatterGen: sending streaming generation request", "info")
        queries = self._normalise_queries(inputs)

        # Health check
        if not self.is_healthy():
            msg = (
                f"MatterGen container is not reachable at {self.api_url}. "
                "Start it with: docker compose up mattergen"
            )
            if self.logger:
                self.logger.log(msg, "error")
            yield {
                "event": "error",
                "message": msg,
                "source": self.generator_name,
                "queries": queries,
            }
            yield {"event": "done", "message": "Stream ended"}
            return

        # Demo shortcut — not streamable, just wrap the sync response
        if inputs.get("pretrained_name") == "demo":
            if self.logger:
                self.logger.log("MatterGen: using demo endpoint (no streaming)", "info")
            yield {"event": "log", "message": "Demo mode — no streaming", "level": "info"}
            try:
                resp = requests.post(f"{self.api_url}/demo/generate", timeout=30)
                resp.raise_for_status()
                result = self._enrich_result(resp.json(), queries)
                result["event"] = "result"
                yield result
            except requests.RequestException as exc:
                yield {
                    "event": "error",
                    "message": f"MatterGen demo: HTTP error — {exc}",
                    "source": self.generator_name,
                    "queries": queries,
                }
            yield {"event": "done", "message": "Stream ended"}
            return

        # Build payload (same shape as generate())
        payload = self._build_payload(inputs)

        # Call the streaming endpoint
        try:
            resp = requests.post(
                f"{self.api_url}/generate/stream",
                json=payload,
                stream=True,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            if self.logger:
                self.logger.log(f"MatterGen: stream request failed — {exc}", "error")
            MattergenGenerator._health_cache["healthy"] = None
            yield {
                "event": "error",
                "message": f"MatterGen stream request failed: {exc}",
                "source": self.generator_name,
                "queries": queries,
            }
            yield {"event": "done", "message": "Stream ended"}
            return

        # Parse the SSE stream
        current_event = "log"
        current_data_lines: list[str] = []

        for raw_line in resp.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line  # already decoded

            if line.startswith("event: "):
                current_event = line[7:].strip()
                continue

            if line.startswith("data: "):
                current_data_lines.append(line[6:])
                continue

            if line == "" and current_data_lines:
                # End of an SSE block — parse and yield
                data_str = "\n".join(current_data_lines)
                current_data_lines = []
                try:
                    data = json.loads(data_str)
                    if current_event == "result" and isinstance(data, dict):
                        data = self._enrich_result(data, queries)
                    data["event"] = current_event
                    yield data
                except json.JSONDecodeError:
                    yield {"event": "log", "message": data_str, "level": "warning"}
                current_event = "log"

        # Flush any remaining data
        if current_data_lines:
            data_str = "\n".join(current_data_lines)
            try:
                data = json.loads(data_str)
                if current_event == "result" and isinstance(data, dict):
                    data = self._enrich_result(data, queries)
                data["event"] = current_event
                yield data
            except json.JSONDecodeError:
                yield {"event": "log", "message": data_str, "level": "warning"}

    def _normalise_queries(self, inputs: Optional[dict]) -> dict:
        """Return caller-provided generation inputs in a stable dict shape."""
        if not isinstance(inputs, dict):
            return {}
        return {k: v for k, v in inputs.items() if v is not None}

    def _build_payload(self, inputs: Optional[dict]) -> dict[str, Any]:
        """Translate EMOS IU-style inputs into the MatterGen API request payload."""
        inputs = inputs or {}
        payload = {
            "pretrained_name": inputs.get("pretrained_name", "mattergen_base"),
            "batch_size": int(inputs.get("batch_size", 64)),
            "num_batches": int(inputs.get("num_batches", 1)),
            "record_trajectories": inputs.get("record_trajectories", True),
        }

        if inputs.get("model_path"):
            payload["model_path"] = inputs["model_path"]
            payload["pretrained_name"] = None

        target_compositions = self._normalise_target_compositions(inputs.get("target_compositions"))
        if target_compositions:
            payload["target_compositions"] = target_compositions

        properties = self._normalise_conditioning_properties(inputs)
        if properties:
            payload["properties_to_condition_on"] = properties

        if inputs.get("diffusion_guidance_factor") is not None:
            payload["diffusion_guidance_factor"] = float(inputs["diffusion_guidance_factor"])

        return payload

    def _normalise_conditioning_properties(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Collect property-conditioning inputs while excluding transport/meta fields."""
        explicit = inputs.get("properties_to_condition_on")
        if isinstance(explicit, dict) and explicit:
            return explicit

        excluded = {
            "pretrained_name",
            "model_path",
            "batch_size",
            "num_batches",
            "record_trajectories",
            "target_compositions",
            "diffusion_guidance_factor",
        }
        props: dict[str, Any] = {}
        for key, value in inputs.items():
            if key in excluded or value is None or value == "":
                continue
            props[key] = value
        return props

    def _normalise_target_compositions(self, raw: Any) -> Optional[list[dict[str, int]]]:
        """Accept IU contract text input and convert it to MatterGen composition dicts."""
        if raw is None:
            return None

        if isinstance(raw, list):
            # Already in API-native shape.
            return raw

        if isinstance(raw, str):
            text = raw.strip()
            if not text:
                return None

            parsed: list[dict[str, int]] = []
            for token in text.split(","):
                formula = token.strip()
                if not formula:
                    continue
                comp = self._formula_to_count_dict(formula)
                if comp:
                    parsed.append(comp)
                elif self.logger:
                    self.logger.log(
                        f"MatterGen: ignoring invalid composition token '{formula}'",
                        "warning",
                    )

            return parsed or None

        if self.logger:
            self.logger.log(
                "MatterGen: unsupported target_compositions format; expected string or list",
                "warning",
            )
        return None

    def _formula_to_count_dict(self, formula: str) -> Optional[dict[str, int]]:
        """Parse simple chemical formulas like Fe, Al2O3, GaAs into element counts."""
        matches = list(re.finditer(r"([A-Z][a-z]?)(\d*)", formula))
        if not matches:
            return None

        consumed = "".join(m.group(0) for m in matches)
        if consumed != formula:
            return None

        counts: dict[str, int] = {}
        for match in matches:
            element = match.group(1)
            count = int(match.group(2)) if match.group(2) else 1
            counts[element] = counts.get(element, 0) + count

        return counts or None

    def _enrich_result(self, result: Any, queries: dict) -> dict:
        """Attach consistent metadata fields to generation results."""
        if not isinstance(result, dict):
            result = {"status": "error", "message": "Invalid generator response type"}
        if "source" not in result:
            result["source"] = self.generator_name
        if "queries" not in result or not isinstance(result.get("queries"), dict):
            result["queries"] = dict(queries)
        if "cif_strings" not in result or not isinstance(result.get("cif_strings"), list):
            result["cif_strings"] = []
        return result

    # ------------------------------------------------------------------
    # Extra helpers (not part of BaseGenerator but useful for the UI)
    # ------------------------------------------------------------------

    def is_healthy(self) -> bool:
        """Return True if the MatterGen container is reachable.

        Results are cached for ``_HEALTH_CACHE_TTL`` seconds so that
        rapid-fire calls (e.g. multiple generators processed in a row)
        do not flood the container with health-check requests.
        """
        now = time.time()
        cache = MattergenGenerator._health_cache
        if cache["healthy"] is not None and (now - cache["checked_at"]) < self._HEALTH_CACHE_TTL:
            return cache["healthy"]

        try:
            resp = requests.get(f"{self.api_url}/health", timeout=5)
            healthy = resp.status_code == 200
        except Exception:
            healthy = False

        cache["healthy"] = healthy
        cache["checked_at"] = now
        return healthy

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

    def cancel_generation(self, job_id: str) -> dict:
        """Ask the container to cancel a running generation job.

        Parameters
        ----------
        job_id : str
            The job identifier returned in the SSE stream's events.

        Returns
        -------
        dict
            ``{"status": "cancelled", ...}`` on success, or
            ``{"status": "error", "message": "..."}`` on failure.
        """
        if self.logger:
            self.logger.log(f"MatterGen: requesting cancellation for job {job_id}", "info")
        try:
            resp = requests.post(
                f"{self.api_url}/cancel/{job_id}",
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json()
            if self.logger:
                self.logger.log(f"MatterGen: cancel response — {result}", "info")
            return result
        except requests.RequestException as exc:
            msg = f"MatterGen: cancel request failed — {exc}"
            if self.logger:
                self.logger.log(msg, "error")
            return {"status": "error", "message": msg}
