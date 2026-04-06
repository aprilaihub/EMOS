from pathlib import Path


# Base class for all generators
class BasePredictor:
    def __init__(self, predictor_name='', logger=None):
        self.predictor_name = predictor_name
        self.logger=logger

    def info(self):
        return f'Information about predictor {self.predictor_name}'

    def predict(self, input_data) -> dict:
        """
        Predict properties.
        Args:
            input_data: Predictor input payload (typically list[str] CIF strings)
        Returns:
            Standardized prediction payload (to be implemented by subclasses)
        """
        raise NotImplementedError("Subclasses must implement predict()")
