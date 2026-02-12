"""Helper functions for COD database API interaction and data conversion."""

import os
import re
import tempfile
import requests
from pymatgen.core import Structure, Lattice, Composition


class CodAPIHelper:
    """Helper class for COD OPTIMADE API operations."""

    def __init__(self, base_url: str, logger=None):
        """
        Initialize COD API helper.

        Args:
            base_url: Base URL for COD OPTIMADE API
            logger: Optional logger instance
        """
        self.base_url = base_url
        self.logger = logger

    def fetch_from_api(self, query: str, limit: int) -> list:
        """
        Fetch structures from COD OPTIMADE API.

        Args:
            query: Element or formula to search for
            limit: Maximum number of results

        Returns:
            list: Raw structure data from OPTIMADE API
        """
        try:
            # Build OPTIMADE filter query
            optimade_filter = self.build_filter(query)

            # Make API request
            params = {
                'page_limit': limit,
                'response_fields': (
                    'lattice_vectors,'
                    'cartesian_site_positions,'
                    'fractional_site_positions,'
                    'species_at_sites,'
                    'species,'
                    'chemical_formula_reduced'
                )
            }
            if optimade_filter:
                params['filter'] = optimade_filter

            if self.logger:
                self.logger.log(f"API Request: {self.base_url}structures with params {params}")

            response = requests.get(
                f"{self.base_url}structures",
                params=params,
                headers={"Accept": "application/json"},
                timeout=30
            )
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            if 'data' in data:
                if self.logger:
                    self.logger.log(f"Retrieved {len(data['data'])} structures from API")
                return data['data']
            else:
                if self.logger:
                    self.logger.log("No 'data' field in API response")
                return []

        except requests.exceptions.RequestException as e:
            if self.logger:
                self.logger.log(f"API request failed: {str(e)}")
            return []
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error fetching from API: {str(e)}")
            return []

    def build_filter(self, query: str) -> str:
        """
        Build OPTIMADE filter for element or formula queries.

        Args:
            query: Element or formula to search for

        Returns:
            str: OPTIMADE filter string or None if no filter needed
        """
        if not query or query.lower() == 'all':
            return None

        # Try parsing as a chemical formula first
        try:
            composition = Composition(query)
            elements = [el.symbol for el in composition.elements]
            if elements:
                if len(elements) == 1:
                    return f'elements HAS "{elements[0]}"'
                return " AND ".join([f'elements HAS "{el}"' for el in elements])
        except Exception:
            pass

        # Fallback: treat the query as a raw element symbol
        return f'elements HAS "{query}"'

    def convert_to_structure(self, optimade_entry: dict) -> Structure:
        """
        Convert OPTIMADE structure entry to pymatgen Structure.

        Args:
            optimade_entry: Single structure entry from OPTIMADE API

        Returns:
            Structure: pymatgen Structure object or None if conversion fails
        """
        try:
            attrs = optimade_entry.get('attributes', {})

            # Get lattice vectors
            lattice_vectors = attrs.get('lattice_vectors')
            if not lattice_vectors:
                if self.logger:
                    self.logger.log("No lattice_vectors in entry")
                return None
            if len(lattice_vectors) != 3 or any(len(v) != 3 for v in lattice_vectors):
                if self.logger:
                    self.logger.log("Invalid lattice_vectors shape")
                return None

            # Get species and positions
            species_at_sites = attrs.get('species_at_sites')
            species_list = attrs.get('species') or []
            positions = attrs.get('cartesian_site_positions')
            coords_are_cartesian = True
            if not positions:
                positions = attrs.get('fractional_site_positions')
                coords_are_cartesian = False

            if not species_at_sites or not positions:
                if self.logger:
                    self.logger.log("Missing species or positions")
                return None

            if len(species_at_sites) != len(positions):
                if self.logger:
                    self.logger.log(
                        f"Species/positions length mismatch: {len(species_at_sites)} vs {len(positions)}"
                    )
                return None

            if any(len(p) != 3 for p in positions):
                if self.logger:
                    self.logger.log("Invalid positions shape")
                return None

            # Map OPTIMADE species_at_sites -> pymatgen-compatible species
            species_map = {}
            for entry in species_list:
                name = entry.get("name")
                if name:
                    species_map[name] = entry

            site_species = []
            site_positions = []
            for site_label, pos in zip(species_at_sites, positions):
                entry = species_map.get(site_label)
                if entry:
                    chem_symbols = entry.get("chemical_symbols") or []
                    concentrations = entry.get("concentration") or []
                    if concentrations and len(concentrations) != len(chem_symbols):
                        if self.logger:
                            self.logger.log("Species concentration length mismatch")
                        return None

                    occupancies = {}
                    for symbol, conc in zip(chem_symbols, concentrations or [1.0] * len(chem_symbols)):
                        symbol_str = str(symbol).strip().lower()
                        if symbol_str in {"x", "vacancy", "vac", "none"}:
                            continue
                        occupancies[str(symbol)] = conc

                    if not occupancies:
                        # Skip pure vacancy sites
                        continue

                    site_species.append(occupancies if len(occupancies) > 1 else list(occupancies.keys())[0])
                    site_positions.append(pos)
                    continue

                # Fallback: treat site label as an element symbol or skip vacancies
                label_str = str(site_label).strip().lower()
                if label_str in {"vacancy", "vac", "x", "none"}:
                    continue
                match = re.match(r"[A-Z][a-z]?", str(site_label))
                if not match:
                    if self.logger:
                        self.logger.log(f"Unrecognized species label: {site_label}")
                    return None
                site_species.append(match.group(0))
                site_positions.append(pos)

            if not site_species:
                if self.logger:
                    self.logger.log("No valid sites after species mapping")
                return None

            # Create pymatgen Structure
            lattice = Lattice(lattice_vectors)
            structure = Structure(
                lattice=lattice,
                species=site_species,
                coords=site_positions,
                coords_are_cartesian=coords_are_cartesian
            )

            return structure

        except Exception as e:
            if self.logger:
                self.logger.log(f"Error converting structure: {str(e)}")
            return None

    def save_cif_from_structure(self, structure: Structure, entry: dict, index: int, output_dir: str) -> str:
        """
        Save pymatgen Structure as CIF file.

        Args:
            structure: pymatgen Structure object
            entry: Original OPTIMADE entry (for metadata)
            index: Index for filename
            output_dir: Directory to save CIF file

        Returns:
            str: Path to saved CIF file or None if failed
        """
        try:
            # Get formula for filename
            attrs = entry.get('attributes', {})
            formula = attrs.get('chemical_formula_reduced', f'structure_{index}')
            formula = formula.replace(' ', '_')

            # Save CIF
            filename = f"{formula}_{index}.cif"
            filepath = os.path.join(output_dir, filename)
            structure.to(filename=filepath, fmt='cif')

            return filepath

        except Exception as e:
            if self.logger:
                self.logger.log(f"Error saving CIF: {str(e)}")
            return None
