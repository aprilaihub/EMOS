from pathlib import Path
from typing import Any


# Base class for all generators
class BasePredictor:
    def __init__(self, predictor_name='', logger=None):
        self.predictor_name = predictor_name
        self.logger=logger

    def info(self):
        return f'Information about predictor {self.predictor_name}'

    def predict(self, input_data: list[str]) -> dict[str, Any]:
        """
        Predict properties.

        Args:
            input_data (list[str]): Predictor input CIF strings.

        Returns:
            dict[str, Any]: Prediction payload with shape:
                {
                    "source": str,
                    "results": list[{
                        "index": int,
                        "status": str,
                        "properties": dict[str, Any],
                        "warnings": list[str],
                        "error": str | None
                    }]
                }.
        """
        raise NotImplementedError("Subclasses must implement predict()")
