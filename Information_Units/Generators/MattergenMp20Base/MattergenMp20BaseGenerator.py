"""
MattergenMp20BaseGenerator
==========================
Unconditional base model trained on the MP-20 dataset for crystal structure
generation.  Pretrained model: ``mp_20_base``.
"""

from __future__ import annotations
from typing import Generator

from Information_Units.Generators.Mattergen.MattergenGenerator import MattergenGenerator


class MattergenMp20BaseGenerator(MattergenGenerator):
    """Thin wrapper that locks the pretrained model to *mp_20_base*."""

    PRETRAINED_NAME = "mp_20_base"
    NUM_BATCHES = 1
    RECORD_TRAJECTORIES = False

    def __init__(self, generator_name: str = "mattergen_mp20_base", logger=None):
        super().__init__(generator_name, logger)

    # ------------------------------------------------------------------
    def info(self) -> str:
        return (
            "MatterGen: MP-20 Base — unconditional base model trained on "
            "the MP-20 dataset for crystal structure generation "
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
