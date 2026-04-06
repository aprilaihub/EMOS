import tempfile
from Information_Units.Databases.BaseDatabase import BaseDatabase
from Information_Units.Databases.Mathub3d.Mathub3dHelper import Mathub3dHelper
from Information_Units.Databases.Cod.CodDatabase import CodDatabase
from Information_Units.Databases.Materialsproject.MaterialsprojectDatabase import MaterialsprojectDatabase


class Mathub3dDatabase(BaseDatabase):
    """MatHub-3d database: local JSON filtering + CIF cross-referencing via COD/MP."""

    def __init__(self, database_name='mathub3d', logger=None):
        super().__init__(database_name, logger)
        self.output_dir = tempfile.mkdtemp(prefix="mathub3d_")
        self.helper = Mathub3dHelper(logger=logger)
        self.cod_db = CodDatabase(logger=logger)
        self.mp_db = MaterialsprojectDatabase(logger=logger)

    def info(self):
        return (
            "MatHub-3d: first-principles materials repository "
            "(74K structures, thermoelectric transport properties). "
            "CIF files retrieved via COD/Materials Project cross-referencing."
        )

    def retrieve(self, inputs: dict) -> dict:
        """
        Filter MatHub-3d dataset and retrieve CIF files via COD/MP cross-referencing.

        Args:
            inputs (dict): Query parameters with standard property names
                - query: Material query (e.g., 'Fe', 'Al2O3')
                - limit: Max number of CIF results (default: 10)
                - Additional keys are treated as standard property filters:
                  band_gap, energy_per_atom, bulk_modulus, density, volume,
                  space_group, magnetization, is_magnetic, nelements, etc.

        Returns:
            dict: {"source": "mathub3d", "queries": dict, "cif_strings": list[str]}
        """
        queries = {k: v for k, v in inputs.items() if v is not None and v != ''}
        result = {
            "source": "mathub3d",
            "queries": queries,
            "cif_strings": [],
        }
        try:
            query = inputs.get('query', '')
            limit = inputs.get('limit', 10)

            properties = {k: v for k, v in inputs.items() if k not in ['query', 'limit']}
            filters = self.helper.map_properties(properties) if properties else {}

            if self.logger:
                filter_str = f" with filters {filters}" if filters else ""
                self.logger.log(
                    f"Retrieving from MatHub-3d: {query} (limit: {limit}){filter_str}"
                )

            data = self.helper.load_data()
            results = self.helper.filter_by_formula(data, query)
            results = self.helper.filter_by_properties(results, filters)

            if self.logger:
                self.logger.log(f"MatHub-3d filtered: {len(results)} candidates")

            if not results:
                return result

            # Cross-reference with COD/MP to get CIF files
            cif_strings = []
            for entry in results:
                if len(cif_strings) >= limit:
                    break
                cif_str = self.helper.find_cif_match(
                    entry, self.cod_db, self.mp_db, self.output_dir
                )
                if cif_str:
                    cif_strings.append(cif_str)
                    if self.logger:
                        self.logger.log(f"CIF match for formula: {entry.get('formula')}")

            if self.logger:
                self.logger.log(f"Total CIF strings retrieved: {len(cif_strings)}")

            result["cif_strings"] = cif_strings
            return result

        except Exception as e:
            if self.logger:
                self.logger.log(f"Error: {str(e)}")
            return result
