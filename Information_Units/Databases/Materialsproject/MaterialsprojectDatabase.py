import tempfile
from typing import Any, Optional
from Information_Units.Databases.BaseDatabase import BaseDatabase
from Information_Units.Databases.Materialsproject.MaterialsprojectAPIHelper import MaterialsprojectAPIHelper
try:
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer as _SGA
except ImportError:
    _SGA = None


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
                - target_compositions: Material query (e.g., 'Fe', 'Al2O3')
                - batch_size: Max number of results (default: 10)
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
                'target_compositions': 'Fe',
                'batch_size': 5
            })
            
            # Query with energy filter
            db.retrieve({
                'target_compositions': 'Fe',
                'batch_size': 5,
                'energy_above_hull_r2scan': [0.0, 0.05]
            })
            
            # Query with multiple filters
            db.retrieve({
                'target_compositions': 'Al2O3',
                'batch_size': 3,
                'nelements': [2, 3],
                'formation_energy_r2scan': [-2.0, -0.5]
            })
        """
        queries = {k: v for k, v in inputs.items() if v is not None and v != ''}
        result = {
            "source": "materialsproject",
            "queries": queries,
            "cif_strings": [],
            "entries": [],
        }
        try:
            query = inputs.get('target_compositions', '')
            limit = inputs.get('batch_size', 10)

            # Extract filters: all keys except 'target_compositions' and 'batch_size'
            properties = {
                k: v for k, v in inputs.items()
                if k not in ['target_compositions', 'batch_size']
            }
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
                        result["entries"].append(self._extract_entry_metadata(entry, structure))
                        if self.logger:
                            self.logger.log(f"Retrieved CIF string {i + 1}")

            return result

        except Exception as e:
            if self.logger:
                self.logger.log(f"Error: {str(e)}")
            return result

    def _extract_entry_metadata(self, entry: dict[str, Any], structure=None) -> dict[str, Any]:
        """Extract lightweight metadata and thermodynamic metrics from OPTIMADE entry."""
        attrs = entry.get('attributes', {}) if isinstance(entry, dict) else {}
        predicted_stable = self._extract_mp_stability_metric(attrs, 'is_stable')
        if predicted_stable is None:
            predicted_stable = self._extract_mp_stability_metric(attrs, 'predicted_stable')
        if predicted_stable is None:
            # Alternate flat keys (defensive fallback).
            for alt_name in ('predicted_stable', '_mp_stability.predicted_stable'):
                predicted_stable = self._extract_mapped_value(attrs, alt_name)
                if predicted_stable is not None:
                    break

        energy_above_hull = self._extract_mp_stability_metric(attrs, 'energy_above_hull')
        if energy_above_hull is None:
            for alt_name in ('energy_above_hull_r2scan', '_mp_stability.energy_above_hull'):
                energy_above_hull = self._extract_mapped_value(attrs, alt_name)
                if energy_above_hull is not None:
                    break

        formation_energy = self._extract_mp_stability_metric(attrs, 'formation_energy_per_atom')
        if formation_energy is None:
            for alt_name in ('formation_energy_r2scan', '_mp_stability.formation_energy_per_atom'):
                formation_energy = self._extract_mapped_value(attrs, alt_name)
                if formation_energy is not None:
                    break

        space_group_number: Optional[int] = None
        if structure is not None and _SGA is not None:
            try:
                space_group_number = _SGA(structure, symprec=0.1).get_space_group_number()
            except Exception:
                pass

        return {
            'id': entry.get('id'),
            'chemical_formula_reduced': attrs.get('chemical_formula_reduced'),
            'space_group_number': space_group_number,
            'predicted_stable_r2scan': predicted_stable,
            'energy_above_hull_r2scan': energy_above_hull,
            'formation_energy_r2scan': formation_energy,
        }

    def _extract_mapped_value(self, attrs: dict[str, Any], mapped_name: str):
        """Read a value from attributes, supporting dotted paths and literal dotted keys."""
        if mapped_name in attrs:
            return attrs.get(mapped_name)

        cur: Any = attrs
        for part in mapped_name.split('.'):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur.get(part)
        return cur

    def _extract_mp_stability_metric(self, attrs: dict[str, Any], metric_key: str):
        """Extract MP stability metric from known branch variants in priority order."""
        stability_obj = attrs.get('_mp_stability')
        if not isinstance(stability_obj, dict):
            return None

        # Prefer the newest branch first, then fall back.
        branch_priority = [
            'r2scan',
            'gga_gga+u_r2scan',
            'gga_gga+u',
            'gga+u_r2scan',
            'gga+u',
        ]

        for branch in branch_priority:
            branch_obj = stability_obj.get(branch)
            if isinstance(branch_obj, dict) and metric_key in branch_obj:
                return branch_obj.get(metric_key)

        # Unknown branch names: scan all branch dicts.
        for branch_obj in stability_obj.values():
            if isinstance(branch_obj, dict) and metric_key in branch_obj:
                return branch_obj.get(metric_key)

        return None
