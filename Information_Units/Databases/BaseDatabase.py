from pathlib import Path
from typing import Any


# Base class for all databases
class BaseDatabase:
    def __init__(self, database_name='', logger=None):
        self.database_name = database_name
        self.logger=logger

    def info(self):
        return f'Information about database{self.database_name}'

    def retrieve(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Retrieve data from database.

        Args:
            inputs (dict[str, Any]): Parsed retrieval inputs from the frontend.

        Returns:
            dict[str, Any]: Standardized database payload:
                {
                    "source": str,
                    "queries": dict,
                    "cif_strings": list[str]
                }
        """
        raise NotImplementedError("Subclasses must implement retrieve()")
