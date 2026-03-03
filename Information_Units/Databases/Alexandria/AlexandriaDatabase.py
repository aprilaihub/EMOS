import tempfile
from Information_Units.Databases.BaseDatabase import BaseDatabase
from Information_Units.Databases.Alexandria.AlexandriaAPIHelper import AlexandriaAPIHelper


class AlexandriaDatabase(BaseDatabase):
    """Alexandria database implementation using OPTIMADE API (PBEsol)."""

    def __init__(self, database_name='alexandria', logger=None):
        super().__init__(database_name, logger)
        self.output_dir = tempfile.mkdtemp(prefix="alexandria_")
        self.base_url = "https://alexandria.icams.rub.de/pbesol/v1/"
        self.api_helper = AlexandriaAPIHelper(self.base_url, logger=logger)

    def info(self):
        return (
            "Alexandria (PBEsol): DFT-calculated materials database "
            "(415K structures, optimized for band gap accuracy)"
        )

    def retrieve(self, inputs: dict) -> list:
        """
        Retrieve materials from Alexandria (PBEsol) using OPTIMADE API and save as CIF files.

        Args:
            inputs (dict): Query parameters with standard property names
                - query: Material query (e.g., 'Fe', 'Al2O3')
                - limit: Max number of results (default: 10)
                - Additional keys are treated as standard property filters

        Returns:
            list: Paths to saved CIF files
        """
        try:
            query = inputs.get('query', '')
            limit = inputs.get('limit', 10)

            properties = {k: v for k, v in inputs.items() if k not in ['query', 'limit']}
            filters = self.api_helper.map_properties(properties) if properties else {}

            if self.logger:
                filter_str = f" with filters {filters}" if filters else ""
                self.logger.log(
                    f"Retrieving from Alexandria (PBEsol) via OPTIMADE: "
                    f"{query} (limit: {limit}){filter_str}"
                )

            structures_data = self.api_helper.fetch_from_api(query, limit, filters)

            if not structures_data:
                if self.logger:
                    self.logger.log("No structures found in Alexandria")
                return []

            cif_paths = []
            for i, entry in enumerate(structures_data):
                structure = self.api_helper.convert_to_structure(entry)
                if structure:
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