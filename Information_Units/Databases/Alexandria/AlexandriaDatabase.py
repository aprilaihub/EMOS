import tempfile
from typing import Any
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

    def retrieve(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Retrieve materials from Alexandria (PBEsol) using OPTIMADE API as CIF strings.

        Args:
            inputs (dict[str, Any]): Query parameters with standard property names
                - target_compositions: Material query (e.g., 'Fe', 'Al2O3')
                - batch_size: Max number of results (default: 10)
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
            dict[str, Any]: {"source": "alexandria", "queries": dict, "cif_strings": list[str]}
            
        Examples:
            # Query with band gap filter (PBEsol)
            db.retrieve({
                'target_compositions': 'Al2O3',
                'batch_size': 10,
                'band_gap': [2.0, 5.0]
            })
            
            # Query with multiple filters
            db.retrieve({
                'target_compositions': 'Fe',
                'batch_size': 5,
                'formation_energy_per_atom': [-1.0, 0.0],
                'hull_distance': [0.0, 0.05]
            })
            
            # Compare PBEsol vs SCAN band gaps
            db.retrieve({
                'target_compositions': 'GaAs',
                'batch_size': 3,
                'band_gap': [1.0, 2.0],
                'band_gap_scan': [1.0, 2.0]
            })
        """
        queries = {k: v for k, v in inputs.items() if v is not None and v != ''}
        result = {
            "source": "alexandria",
            "queries": queries,
            "cif_strings": [],
            "entries": [],
        }
        try:
            query = inputs.get('target_compositions', '')
            limit = inputs.get('batch_size', 10)

            properties = {
                k: v for k, v in inputs.items()
                if k not in ['target_compositions', 'batch_size']
            }
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
                return result

            # Convert to pymatgen structures and serialize as CIF strings
            for i, entry in enumerate(structures_data):
                structure = self.api_helper.convert_to_structure(entry)
                if structure:
                    cif_str = structure.to(fmt='cif')
                    if cif_str:
                        result["cif_strings"].append(cif_str)
                        result["entries"].append(self._extract_entry_metadata(entry))
                        if self.logger:
                            self.logger.log(f"Retrieved CIF string {i + 1}")

            return result

        except Exception as e:
            if self.logger:
                self.logger.log(f"Error: {str(e)}")
            return result

    def _extract_entry_metadata(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Extract lightweight metadata and thermodynamic metrics from OPTIMADE entry."""
        attrs = entry.get('attributes', {}) if isinstance(entry, dict) else {}
        return {
            'id': entry.get('id'),
            'chemical_formula_reduced': attrs.get('chemical_formula_reduced'),
            'hull_distance': self._extract_mapped_value(attrs, '_alexandria_hull_distance'),
            'formation_energy_per_atom': self._extract_mapped_value(attrs, '_alexandria_formation_energy_per_atom'),
        }

    def _extract_mapped_value(self, attrs: dict[str, Any], mapped_name: str):
        """Read a value from attributes, supporting dotted paths and literal dotted keys."""
        if mapped_name in attrs:
            return attrs.get(mapped_name)

        cur = attrs
        for part in mapped_name.split('.'):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur.get(part)
        return cur
