import tempfile
from Information_Units.Databases.BaseDatabase import BaseDatabase
from Information_Units.Databases.Cod.CodAPIHelper import CodAPIHelper


class CodDatabase(BaseDatabase):
    """COD database implementation using OPTIMADE API"""

    def __init__(self, database_name='cod', logger=None):
        super().__init__(database_name, logger)
        self.output_dir = tempfile.mkdtemp(prefix="cod_")
        self.base_url = "https://www.crystallography.net/cod/optimade/v1/"
        self.api_helper = CodAPIHelper(self.base_url, logger=logger)

    def info(self):
        return "COD: Crystallography Open Database (via OPTIMADE)"

    def retrieve(self, inputs: dict) -> list:
        """
        Retrieve materials from COD using OPTIMADE API and save as CIF files.

        Args:
            inputs (dict): Query parameters
                - query: Material query (e.g., 'Fe', 'Al2O3')
                - limit: Max number of results (default: 10)

        Returns:
            list: Paths to saved CIF files
        """
        try:
            query = inputs.get('query', '')
            limit = inputs.get('limit', 10)

            if self.logger:
                self.logger.log(f"Retrieving from COD via OPTIMADE: {query} (limit: {limit})")

            # Fetch data from OPTIMADE API
            structures_data = self.api_helper.fetch_from_api(query, limit)

            if not structures_data:
                if self.logger:
                    self.logger.log("No structures found")
                return []

            # Convert to pymatgen structures and save as CIF
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
