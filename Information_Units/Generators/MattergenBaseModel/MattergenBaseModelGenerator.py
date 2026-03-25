"""
MattergenBaseModelGenerator
===========================
Unconditional diffusion model for general inorganic crystal structure
generation.  Pretrained model: ``mattergen_base``.
"""

from __future__ import annotations
from typing import Generator

from Information_Units.Generators.MattergenBaseModel.MattergenGenerator import MattergenGenerator


class MattergenBaseModelGenerator(MattergenGenerator):
    """Thin wrapper that locks the pretrained model to *mattergen_base*."""

    PRETRAINED_NAME = "mattergen_base"
    NUM_BATCHES = 1
    RECORD_TRAJECTORIES = False

    def __init__(self, generator_name: str = "mattergen_base_model", logger=None):
        super().__init__(generator_name, logger)

    # ------------------------------------------------------------------
    def info(self) -> str:
        return (
            "MatterGen: Base Model — unconditional diffusion model for "
            "general inorganic crystal structure generation "
            f"(pretrained: {self.PRETRAINED_NAME})"
        )

    def generate(self, inputs: dict) -> dict:
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
