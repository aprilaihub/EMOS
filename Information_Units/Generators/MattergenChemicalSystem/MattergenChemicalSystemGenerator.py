"""
MattergenChemicalSystemGenerator
================================
Conditional model for generating structures within a specified chemical
system.  Pretrained model: ``chemical_system``.
"""

from __future__ import annotations
from typing import Any, Generator

from Information_Units.Generators.MattergenBaseModel.MattergenGenerator import MattergenGenerator


class MattergenChemicalSystemGenerator(MattergenGenerator):
    """Thin wrapper that locks the pretrained model to *chemical_system*."""

    PRETRAINED_NAME = "chemical_system"
    NUM_BATCHES = 1
    RECORD_TRAJECTORIES = False

    def __init__(self, generator_name: str = "mattergen_chemical_system", logger=None):
        super().__init__(generator_name, logger)

    # ------------------------------------------------------------------
    def info(self) -> str:
        return (
            "MatterGen: Chemical System — conditional model for generating "
            "structures within a specified chemical system "
            f"(pretrained: {self.PRETRAINED_NAME})"
        )

    def generate(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Generate structures using the fixed ``chemical_system`` pretrained model.

        Args:
            inputs (dict[str, Any]): Generation parameters.

        Returns:
            dict[str, Any]: Generation payload:
                {
                    "status": str,
                    "message": str (optional),
                    "source": str,
                    "queries": dict[str, Any],
                    "cif_strings": list[str],
                    "num_structures": int (optional),
                    "structures": list[dict[str, Any]] (optional),
                    "debug_logs": list[str] (optional),
                    "job_id": str (optional)
                }.
        """
        inputs = {**inputs,
                  "pretrained_name": self.PRETRAINED_NAME,
                  "num_batches": inputs.get("num_batches", self.NUM_BATCHES),
                  "record_trajectories": inputs.get("record_trajectories", self.RECORD_TRAJECTORIES)}
        return super().generate(inputs)

    def generate_stream(self, inputs: dict) -> Generator[dict, None, None]:
        inputs = {**inputs,
                  "pretrained_name": self.PRETRAINED_NAME,
                  "num_batches": inputs.get("num_batches", self.NUM_BATCHES),
                  "record_trajectories": inputs.get("record_trajectories", self.RECORD_TRAJECTORIES)}
        yield from super().generate_stream(inputs)
