import tempfile
from typing import Any
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

    def retrieve(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Retrieve materials from COD using OPTIMADE API as CIF strings.

        Args:
            inputs (dict[str, Any]): Query parameters with standard property names
                - target_compositions: Material query (e.g., 'Fe', 'Al2O3')
                - batch_size: Max number of results (default: 10)
                - Additional keys are treated as standard property filters
                  
                Example:
                  db.retrieve({
                      'target_compositions': 'Fe',
                      'batch_size': 5,
                      'natoms': [1, 10],
                      'volume': [20, 100],
                      'spacegroup_number': 225
                  })

        Returns:
            dict[str, Any]: {"source": "cod", "queries": dict, "cif_strings": list[str]}
        """
        queries = {k: v for k, v in inputs.items() if v is not None and v != ''}
        result = {
            "source": "cod",
            "queries": queries,
            "cif_strings": [],
        }
        try:
            query = inputs.get('target_compositions', '')
            # Default limit of 10 is the page size limit provided by the COD OPTIMADE API
            limit = inputs.get('batch_size', 10)

            # Extract filters: all keys except 'target_compositions' and 'batch_size'
            properties = {
                k: v for k, v in inputs.items()
                if k not in ['target_compositions', 'batch_size']
            }
            filters = self.api_helper.map_properties(properties) if properties else {}

            if self.logger:
                filter_str = f" with filters {filters}" if filters else ""
                self.logger.log(f"Retrieving from COD via OPTIMADE: {query} (limit: {limit}){filter_str}")

            # Fetch data from OPTIMADE API
            structures_data = self.api_helper.fetch_from_api(query, limit, filters)

            if not structures_data:
                if self.logger:
                    self.logger.log("No structures found")
                return result

            # Convert to pymatgen structures and serialize as CIF strings
            for i, entry in enumerate(structures_data):
                structure = self.api_helper.convert_to_structure(entry)
                if structure:
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
