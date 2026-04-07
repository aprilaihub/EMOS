import tempfile
from typing import Any
from Information_Units.Databases.BaseDatabase import BaseDatabase
from Information_Units.Databases.Materialsproject.MaterialsprojectAPIHelper import MaterialsprojectAPIHelper


class MaterialsprojectDatabase(BaseDatabase):
    """Materials Project database implementation using OPTIMADE API."""

    def __init__(self, database_name='materialsproject', logger=None):
        super().__init__(database_name, logger)
        self.output_dir = tempfile.mkdtemp(prefix="materialsproject_")
        self.base_url = "https://optimade.materialsproject.org/v1/"
        self.api_helper = MaterialsprojectAPIHelper(self.base_url, logger=logger)

    def info(self):
        return (
            "Materials Project (via OPTIMADE): DFT-calculated materials database "
            "(~154K structures, thermodynamic stability with GGA/GGA+U/r2SCAN functionals)"
        )

    def retrieve(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Retrieve materials from Materials Project using OPTIMADE API as CIF strings.

        Args:
            inputs (dict[str, Any]): Query parameters with standard property names
                - query: Material query (e.g., 'Fe', 'Al2O3')
                - limit: Max number of results (default: 10)
                - Additional keys are treated as standard property filters
                
                **Common Properties (queryable)**:
                - id: Unique structure ID
                - type: Entry type
                - last_modified: ISO 8601 timestamp
                - nelements: Number of unique elements [min, max]
                - elements: List of elements
                - chemical_formula_descriptive: Descriptive formula
                - nperiodic_dimensions: Number of periodic dimensions [min, max]
                
                **Thermodynamic Properties (r2SCAN - queryable)**:
                - energy_above_hull_r2scan (eV/atom): Distance from convex hull [min, max]
                - formation_energy_r2scan (eV/atom): Formation energy [min, max]
                - chemical_system: Chemical system identifier (string)

        Returns:
            dict[str, Any]: {"source": "materialsproject", "queries": dict, "cif_strings": list[str]}
            
        Examples:
            # Simple element query
            db.retrieve({
                'query': 'Fe',
                'limit': 5
            })
            
            # Query with energy filter
            db.retrieve({
                'query': 'Fe',
                'limit': 5,
                'energy_above_hull_r2scan': [0.0, 0.05]
            })
            
            # Query with multiple filters
            db.retrieve({
                'query': 'Al2O3',
                'limit': 3,
                'nelements': [2, 3],
                'formation_energy_r2scan': [-2.0, -0.5]
            })
        """
        queries = {k: v for k, v in inputs.items() if v is not None and v != ''}
        result = {
            "source": "materialsproject",
            "queries": queries,
            "cif_strings": [],
        }
        try:
            query = inputs.get('query', '')
            limit = inputs.get('limit', 10)

            # Extract filters: all keys except 'query' and 'limit'
            properties = {k: v for k, v in inputs.items() if k not in ['query', 'limit']}
            filters = self.api_helper.map_properties(properties) if properties else {}

            if self.logger:
                filter_str = f" with filters {filters}" if filters else ""
                self.logger.log(f"Retrieving from Materials Project via OPTIMADE: {query} (limit: {limit}){filter_str}")

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
