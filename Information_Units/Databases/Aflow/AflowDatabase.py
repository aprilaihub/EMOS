import tempfile

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

    def retrieve(self, inputs: dict) -> list:
        """Retrieve materials from AFLOW via AFLUX and save as CIF files."""
        try:
            query = inputs.get('query', '')
            limit = int(inputs.get('limit', 10))
            if limit <= 0:
                return []

            properties = {k: v for k, v in inputs.items() if k not in ['query', 'limit']}
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
                return []

            cif_paths = []
            for i, entry in enumerate(entries):
                structure = self.api_helper.convert_to_structure(entry)
                if not structure:
                    continue

                cif_path = self.api_helper.save_cif_from_structure(
                    structure, entry, i, self.output_dir
                )
                if cif_path:
                    cif_paths.append(cif_path)
                    if self.logger:
                        self.logger.log(f"Saved: {cif_path}")

            return cif_paths

        except Exception as e:
            if self.logger:
                self.logger.log(f"Error: {str(e)}")
            return []
