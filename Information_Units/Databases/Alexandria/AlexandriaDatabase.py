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
                
                **Properties (PBEsol - default functional)**:
                - band_gap (eV): Electronic band gap [min, max]
                - band_gap_direct (eV): Direct electronic band gap [min, max]
                - formation_energy_per_atom (eV/atom): Formation energy [min, max]
                - space_group: Space group number [min, max]
                - hull_distance (eV/atom): Distance from convex hull [min, max]
                - magnetization (μB/unit_cell): Total magnetization [min, max]
                - energy (eV): Total energy [min, max]
                - energy_corrected (eV): Total energy with corrections [min, max]
                - phase_separation_energy (eV/atom): Phase stability [min, max]
                - decomposition: Decomposition products (string)
                - xc_functional: Functional used (string)
                - dos_ef (states/eV/cell): DOS at Fermi level [min, max]
                - charges: Atomic charges [min, max]
                - forces (eV/Å): Forces on atoms [min, max]
                - stress_tensor (kbar): Stress tensor components [min, max]
                - magnetic_moments (μB): Local magnetic moments [min, max]
                
                **Properties (SCAN variant - alternative functional)**:
                - band_gap_scan (eV): Band gap (SCAN) [min, max]
                - band_gap_direct_scan (eV): Direct band gap (SCAN) [min, max]
                - formation_energy_per_atom_scan (eV/atom): Formation energy (SCAN) [min, max]
                - hull_distance_scan (eV/atom): Hull distance (SCAN) [min, max]
                - magnetization_scan (μB/unit_cell): Magnetization (SCAN) [min, max]
                - energy_scan (eV): Total energy (SCAN) [min, max]
                - energy_corrected_scan (eV): Total energy corrected (SCAN) [min, max]
                - phase_separation_energy_scan (eV/atom): Phase stability (SCAN) [min, max]
                - decomposition_scan: Decomposition (SCAN) (string)
                - dos_ef_scan (states/eV/cell): DOS at Fermi level (SCAN) [min, max]
                - charges_scan: Atomic charges (SCAN) [min, max]
                - forces_scan (eV/Å): Forces on atoms (SCAN) [min, max]
                - stress_tensor_scan (kbar): Stress tensor (SCAN) [min, max]
                - magnetic_moments_scan (μB): Local magnetic moments (SCAN) [min, max]

        Returns:
            list: Paths to saved CIF files
            
        Examples:
            # Query with band gap filter (PBEsol)
            db.retrieve({
                'query': 'Al2O3',
                'limit': 10,
                'band_gap': [2.0, 5.0]
            })
            
            # Query with multiple filters
            db.retrieve({
                'query': 'Fe',
                'limit': 5,
                'formation_energy_per_atom': [-1.0, 0.0],
                'hull_distance': [0.0, 0.05]
            })
            
            # Compare PBEsol vs SCAN band gaps
            db.retrieve({
                'query': 'GaAs',
                'limit': 3,
                'band_gap': [1.0, 2.0],
                'band_gap_scan': [1.0, 2.0]
            })
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