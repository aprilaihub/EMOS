"""Helper functions for MatHub-3d database: data loading, filtering, and CIF cross-referencing."""

import os
import json
import zipfile
from pymatgen.core import Structure, Composition


class Mathub3dHelper:
    """Helper class for MatHub-3d local dataset operations and CIF cross-referencing."""

    def __init__(self, logger=None):
        self.logger = logger
        self._data = None
        self._zip_path = os.path.join(os.path.dirname(__file__), 'MatHub-3d.zip')
        self.property_mapping = self._load_property_mapping()

    def _load_property_mapping(self) -> dict:
        """Load mathub3d property mapping from property_mappings.json."""
        try:
            mapping_file = os.path.join(
                os.path.dirname(__file__), '..', '..', 'property_mappings.json'
            )
            with open(mapping_file, 'r') as f:
                data = json.load(f)

            mapping = {}
            for prop_name, prop_details in data.get('properties', {}).items():
                mathub3d_info = prop_details.get('mathub3d', {})
                if mathub3d_info.get('retrievable'):
                    mapping[prop_name] = {
                        'name': mathub3d_info.get('name'),
                        'retrievable': True,
                        'range_support': mathub3d_info.get('range_support', False),
                    }
            return mapping
        except Exception as e:
            if self.logger:
                self.logger.log(f"Warning: Could not load MatHub-3d property mapping: {str(e)}")
            return {}

    def load_data(self) -> list:
        """Lazy-load MatHub-3d.json from the zip archive. Cached after first call."""
        if self._data is None:
            with zipfile.ZipFile(self._zip_path, 'r') as zf:
                with zf.open('MatHub-3d.json') as f:
                    self._data = json.load(f)
            if self.logger:
                self.logger.log(f"Loaded {len(self._data)} entries from MatHub-3d.json")
        return self._data

    def parse_elements(self, query: str) -> list:
        """Parse a formula or element string into a list of element symbols."""
        if not query or query.lower() == 'all':
            return []
        try:
            composition = Composition(query)
            return [el.symbol for el in composition.elements]
        except Exception:
            return [query]

    def map_properties(self, standard_properties: dict) -> dict:
        """Map standard property names to MatHub-3d JSON field names."""
        mapped = {}
        for standard_name, value in standard_properties.items():
            if standard_name in self.property_mapping:
                prop_info = self.property_mapping[standard_name]
                if prop_info.get('retrievable'):
                    mapped[prop_info['name']] = value
            else:
                if self.logger:
                    self.logger.log(f"Warning: Property '{standard_name}' not in mapping, skipping")
        return mapped

    def filter_by_formula(self, data: list, query: str) -> list:
        """Filter entries where all queried elements are present in entry's elements list."""
        elements = self.parse_elements(query)
        if not elements:
            return data
        return [
            entry for entry in data
            if all(el in (entry.get('elements') or []) for el in elements)
        ]

    def filter_by_properties(self, data: list, filters: dict) -> list:
        """Apply property filters (range, exact, boolean) to data entries."""
        if not filters:
            return data

        results = data
        for field_name, value in filters.items():
            filtered = []
            for entry in results:
                entry_val = entry.get(field_name)
                if entry_val is None:
                    continue
                if isinstance(value, list) and len(value) == 2:
                    if value[0] <= entry_val <= value[1]:
                        filtered.append(entry)
                elif isinstance(value, bool):
                    if entry_val == value:
                        filtered.append(entry)
                else:
                    if entry_val == value:
                        filtered.append(entry)
            results = filtered
        return results

    def get_lattice(self, entry: dict) -> dict:
        """Extract lattice parameters, preferring relaxed (after_*) over initial (before_*)."""
        lattice = {}
        for param in ['a', 'b', 'c', 'alpha', 'beta', 'gamma']:
            relaxed = entry.get(f'after_{param}')
            initial = entry.get(f'before_{param}')
            lattice[param] = relaxed if relaxed is not None else initial
        return lattice

    def find_cif_match(self, entry, cod_db, mp_db, output_dir, tolerance=0.05):
        """
        Query COD + MP by formula, compare lattice params, return best CIF string or None.

        Preference: Materials Project first (DFT lattice closer to MatHub-3d), then COD.
        """
        formula = entry.get('formula', '')
        if not formula:
            return None

        target_lattice = self.get_lattice(entry)
        target_a = target_lattice.get('a')
        target_b = target_lattice.get('b')
        target_c = target_lattice.get('c')
        if not all([target_a, target_b, target_c]):
            return None

        # Collect CIF candidates from both databases
        all_candidates = []
        for source_name, db in [('materialsproject', mp_db), ('cod', cod_db)]:
            try:
                payload = db.retrieve({'target_compositions': formula, 'batch_size': 10})
                cif_strings = payload.get('cif_strings', []) if isinstance(payload, dict) else []
                if cif_strings:
                    for cif_str in cif_strings:
                        all_candidates.append((source_name, cif_str))
            except Exception as e:
                if self.logger:
                    self.logger.log(f"Warning: {source_name} lookup failed for {formula}: {str(e)}")

        if not all_candidates:
            return None

        # Find best lattice match
        best_cif = None
        best_deviation = float('inf')

        for source, cif_str in all_candidates:
            try:
                structure = Structure.from_str(cif_str, fmt='cif')
                lat = structure.lattice
                dev_a = abs(lat.a - target_a) / target_a
                dev_b = abs(lat.b - target_b) / target_b
                dev_c = abs(lat.c - target_c) / target_c
                max_dev = max(dev_a, dev_b, dev_c)

                if max_dev < tolerance and max_dev < best_deviation:
                    best_deviation = max_dev
                    best_cif = cif_str
            except Exception:
                continue

        if best_cif:
            return best_cif

        # Fallback: prefer MP, then COD (no lattice match within tolerance)
        mp_first = next((c for s, c in all_candidates if s == 'materialsproject'), None)
        return mp_first or all_candidates[0][1]
