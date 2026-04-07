import tempfile
from typing import Any

from Information_Units.Databases.Aflow.AflowAPIHelper import AflowAPIHelper
from Information_Units.Databases.BaseDatabase import BaseDatabase


class AflowDatabase(BaseDatabase):
    """AFLOW database implementation using AFLUX API."""

    def __init__(self, database_name='aflow', logger=None):
        super().__init__(database_name, logger)
        self.output_dir = tempfile.mkdtemp(prefix="aflow_")
        self.base_url = "https://aflow.org/API/aflux/"
        self.api_helper = AflowAPIHelper(self.base_url, logger=logger)

    def info(self):
        return (
            "AFLOW: Automatic-FLOW computational materials database "
            "with electronic, mechanical, and thermal properties"
        )

    def retrieve(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Retrieve materials from AFLOW via AFLUX as CIF strings.

        Args:
            inputs (dict[str, Any]): Query parameters, including optional
                ``target_compositions``, ``batch_size``, and property filters.

        Returns:
            dict[str, Any]: {"source": "aflow", "queries": dict, "cif_strings": list[str]}.
        """
        queries = {k: v for k, v in inputs.items() if v is not None and v != ''}
        result = {
            "source": "aflow",
            "queries": queries,
            "cif_strings": [],
        }
        try:
            query = inputs.get('target_compositions', '')
            limit = int(inputs.get('batch_size', 10))
            if limit <= 0:
                return result

            properties = {
                k: v for k, v in inputs.items()
                if k not in ['target_compositions', 'batch_size']
            }
            filters = self.api_helper.map_properties(properties) if properties else {}

            if self.logger:
                filter_str = f" with filters {filters}" if filters else ""
                self.logger.log(
                    f"Retrieving from AFLOW via AFLUX: {query} (limit: {limit}){filter_str}"
                )

            entries = self.api_helper.fetch_from_api(query, limit, filters)

            if not entries:
                if self.logger:
                    self.logger.log("No structures found in AFLOW")
                return result

            for i, entry in enumerate(entries):
                structure = self.api_helper.convert_to_structure(entry)
                if not structure:
                    continue

                cif_str = structure.to(fmt='cif')
                if cif_str:
                    result["cif_strings"].append(cif_str)
                    if self.logger:
                        self.logger.log(f"Retrieved CIF string {i + 1}")

            return result

        except Exception as e:
            if self.logger:
                self.logger.log(f"Error: {str(e)}")
            return result
