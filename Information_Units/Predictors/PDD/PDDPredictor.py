"""PDD (Pointwise Distance Distribution) Predictor.

Computes the Pointwise Distance Distribution descriptor for one or many crystal
structures supplied as CIF text strings.  For a single structure the output is
the PDD matrix (k rows × k columns); for multiple structures the full k×k PDD
is returned per structure together with an inter-structure comparison matrix
based on the Earth-Mover's Distance (EMD).

Reference: https://github.com/dwiddo/average-minimum-distance
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import Any

import amd
import numpy as np

from Information_Units.Predictors.BasePredictor import BasePredictor
from Information_Units.property_mappings.property_loader import load_source_property_mapping


class PDDPredictor(BasePredictor):
    """Compute PDD descriptors for crystal structures.

    Input:  ``list[str]`` of CIF text strings (EMOS standard contract).
    Output: ``dict`` with ``"source"`` and ``"results"`` keys.

    Each result item carries:
    - ``pdd_vector``   – 1-D AMD vector (mean of PDD rows), shape ``(k,)``
    - ``pdd_matrix``   – Full PDD matrix as a nested list, shape ``(n_atoms, k)``

    Parameters
    ----------
    k : int
        Neighbourhood size for descriptor calculation (default 100).
    """

    SOURCE = "pdd"

    OUTPUT_PROPERTIES = (
        "pdd_vector",
        "pdd_matrix",
    )

    def __init__(self, predictor_name: str = "pdd", k: int = 100, logger=None):
        super().__init__(predictor_name=predictor_name, logger=logger)
        self.k = k
        self._cancelled = False
        self._cancel_lock = threading.Lock()
        self._mapped_output_properties = self._load_mapped_output_properties()
        self._check_output_properties_in_mapping()

    # ── property-mapping helpers ──────────────────────────────────────────────

    def _load_mapped_output_properties(self) -> set:
        try:
            source_mapping = load_source_property_mapping(source="pdd", source_type="predictors")
        except Exception as exc:
            raise RuntimeError(f"Failed to load PDD property mappings: {exc}") from exc
        return {
            name
            for name, cfg in source_mapping.items()
            if isinstance(cfg, dict) and cfg.get("predictable")
        }

    def _check_output_properties_in_mapping(self) -> None:
        missing = sorted(set(self.OUTPUT_PROPERTIES) - self._mapped_output_properties)
        if missing:
            raise ValueError(
                "PDD output properties missing in property mappings: " + ", ".join(missing)
            )

    # ── public API ────────────────────────────────────────────────────────────

    def info(self) -> str:
        return (
            f"PDD (Pointwise Distance Distribution) Predictor\n"
            f"Computes geometric crystal-structure descriptors using the "
            f"average-minimum-distance package.\n"
            f"Parameters: k={self.k}\n"
            f"Output per structure: pdd_vector and pdd_matrix."
        )

    def predict(self, input_data: list[str]) -> dict[str, Any]:
        """Compute PDD descriptors for one or more CIF strings.

        Parameters
        ----------
        input_data:
            List of CIF text strings.

        Returns
        -------
        dict matching the EMOS predictor output contract.
        """
        with self._cancel_lock:
            self._cancelled = False

        cif_strings = self._extract_cif_strings(input_data)

        if self.logger:
            self.logger.log(
                f"PDD prediction starting: {len(cif_strings)} CIF string(s), k={self.k}",
                "info",
            )
        if not cif_strings:
            return {"source": self.SOURCE, "results": []}

        results: list[dict] = []

        # ── Compute per-structure PDD descriptors ────────────────────────────
        for idx, cif_text in enumerate(cif_strings):
            if self._is_cancelled():
                if self.logger:
                    self.logger.log("PDD prediction cancelled.", "warning")
                break

            try:
                ps = self._load_single_crystal(cif_text, idx)
                pdd_mat = amd.PDD(ps, self.k)          # shape (n_atoms, k)
                amd_vec = np.mean(pdd_mat, axis=0)     # shape (k,)  — the AMD vector

                item = {
                    "index": idx,
                    "status": "ok",
                    "properties": {
                        "pdd_vector": amd_vec.tolist(),
                        "pdd_matrix": pdd_mat.tolist(),
                    },
                    "warnings": [],
                    "error": None,
                    "cif_input": cif_text,
                }
                results.append(item)

                if self.logger:
                    self.logger.log(
                        f"item[{idx}]: PDD computed — shape ({pdd_mat.shape[0]}×{self.k})",
                        "info",
                    )

            except Exception as exc:
                err_msg = f"PDD computation failed: {exc}"
                if self.logger:
                    self.logger.log(f"item[{idx}]: {err_msg}", "error")
                results.append({
                    "index": idx,
                    "status": "error",
                    "properties": {
                        "pdd_vector": None,
                        "pdd_matrix": None,
                    },
                    "warnings": [],
                    "error": err_msg,
                    "cif_input": cif_text,
                })

        if self.logger:
            ok_count = sum(1 for r in results if r["status"] == "ok")
            self.logger.log(
                f"PDD prediction complete: {ok_count}/{len(results)} successful.",
                "info",
            )

        return {"source": self.SOURCE, "results": results}

    def cancel(self) -> dict:
        """Signal the predictor to stop after the current structure."""
        with self._cancel_lock:
            self._cancelled = True
        if self.logger:
            self.logger.log("Cancel signal received — PDD will stop after current structure.", "warning")
        return {"status": "ok", "message": "Cancel signal sent to PDD predictor."}

    def _is_cancelled(self) -> bool:
        with self._cancel_lock:
            return self._cancelled

    def _extract_cif_strings(self, input_data) -> list[str]:
        if isinstance(input_data, list):
            return [s for s in input_data if isinstance(s, str) and s.strip()]
        return []

    def _load_single_crystal(self, cif_text: str, idx: int) -> amd.PeriodicSet:
        """Write CIF text to a temp file, read the first crystal, clean up."""
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".cif", delete=False, encoding="utf-8"
        )
        try:
            tmp.write(cif_text)
            tmp.close()
            reader = amd.CifReader(tmp.name)
            crystals = list(reader)
            if not crystals:
                raise ValueError(f"No crystal structures found in CIF for item[{idx}]")
            return crystals[0]
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
