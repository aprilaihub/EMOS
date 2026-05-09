from pathlib import Path
from typing import Any


# Base class for all generators
class BaseGenerator:
    def __init__(self, generator_name='', logger=None):
        self.generator_name = generator_name
        self.logger=logger

    def info(self):
        return f'Information about generator {self.generator_name}'

    def generate(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Generate materials based on parsed inputs.

        Args:
            inputs (dict[str, Any]): Parsed generator inputs from the frontend.

        Returns:
            dict[str, Any]: Generation payload with shape:
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
        raise NotImplementedError("Subclasses must implement generate()")
