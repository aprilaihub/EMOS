import tempfile
from Information_Units.Databases.BaseDatabase import BaseDatabase
from Information_Units.Databases.Jarvisdft.JarvisdftAPIHelper import JarvisdftAPIHelper


class JarvisdftDatabase(BaseDatabase):
    """JARVIS-DFT database implementation using OPTIMADE API."""

    def __init__(self, database_name='jarvisdft', logger=None):
        super().__init__(database_name, logger)
        self.output_dir = tempfile.mkdtemp(prefix="jarvisdft_")
        self.base_url = "https://jarvis.nist.gov/optimade/jarvisdft/v1/"
        self.api_helper = JarvisdftAPIHelper(self.base_url, logger=logger)

    def info(self):
        return (
            "JARVIS-DFT: NIST computational materials database with "
            "electronic, optical, thermoelectric, and solar cell properties"
        )

    def retrieve(self, inputs: dict) -> list:
        """
        Retrieve materials from JARVIS-DFT using OPTIMADE API and save as CIF files.

        Args:
            inputs (dict): Query parameters with standard property names
                - query: Material query (e.g., 'Si', 'Fe2O3')
                - limit: Max number of results (default: 10)
                - Additional keys are treated as standard property filters

                **Properties**:
                - band_gap (eV): Electronic band gap (OPT-PBE) [min, max]
                - mbj_bandgap (eV): MBJ band gap [min, max]
                - hse_gap (eV): HSE06 band gap [min, max]
                - formation_energy_per_atom (eV/atom): Formation energy [min, max]
                - space_group: Space group number [min, max]
                - hull_distance (eV/atom): Distance from convex hull [min, max]
                - energy (eV): Total energy [min, max]
                - magnetization (μB): Total magnetization [min, max]
                - density (g/cm³): Density [min, max]
                - bulk_modulus (GPa): Bulk modulus (Kv) [min, max]
                - shear_modulus (GPa): Shear modulus (Gv) [min, max]
                - spillage: Spin-orbit spillage [min, max]
                - slme (%): Spectroscopic limited maximum efficiency [min, max]
                - poisson_ratio: Poisson's ratio [min, max]
                - exfoliation_energy (meV/atom): Exfoliation energy [min, max]
                - epsx: Static dielectric constant (x) [min, max]
                - mepsx: Electronic dielectric constant (x) [min, max]
                - n_seebeck (μV/K): n-type Seebeck coefficient [min, max]
                - p_seebeck (μV/K): p-type Seebeck coefficient [min, max]
                - n_powerfact (μW/(cm·K²)): n-type power factor [min, max]
                - p_powerfact (μW/(cm·K²)): p-type power factor [min, max]
                - Tc_supercon (K): Superconducting Tc [min, max]
                - dfpt_piezo_max_dij (C/N): Max piezoelectric strain coeff [min, max]
                - avg_elec_mass (mₑ): Average electron mass [min, max]
                - avg_hole_mass (mₑ): Average hole mass [min, max]

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
                    f"Retrieving from JARVIS-DFT via OPTIMADE: "
                    f"{query} (limit: {limit}){filter_str}"
                )

            structures_data = self.api_helper.fetch_from_api(query, limit, filters)

            if not structures_data:
                if self.logger:
                    self.logger.log("No structures found in JARVIS-DFT")
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
