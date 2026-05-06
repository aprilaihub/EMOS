"""Helper functions for JARVIS-DFT database API interaction and data conversion."""

import re
import time
import requests
from pymatgen.core import Structure, Lattice, Composition
from Information_Units.property_mappings.property_loader import load_source_property_mapping


class JarvisdftAPIHelper:
    """Helper class for JARVIS-DFT OPTIMADE API operations."""

    def __init__(self, base_url: str, logger=None):
        """
        Initialize JARVIS-DFT API helper.

        Args:
            base_url: Base URL for JARVIS-DFT OPTIMADE API
            logger: Optional logger instance
        """
        self.base_url = base_url
        self.logger = logger
        self.property_mapping = self._load_property_mapping()
        self.response_fields = self._build_response_fields()

    def _load_property_mapping(self) -> dict:
        """
        Load property mapping from modular source mapping files.

        Returns:
            dict: Mapping with structure {prop_name: {name: jarvis_name, ...}} for retrievable properties
        """
        try:
            mapping = {}
            source_mapping = load_source_property_mapping(source='jarvisdft', source_type='databases')
            for prop_name, jarvisdft_info in source_mapping.items():
                if jarvisdft_info.get('retrievable'):
                    mapping[prop_name] = {
                        'name': jarvisdft_info.get('name'),
                        'retrievable': True,
                        'range_support': jarvisdft_info.get('range_support', False),
                    }

            return mapping
        except Exception as e:
            if self.logger:
                self.logger.log(f"Warning: Could not load JARVIS-DFT property mapping: {str(e)}")
            return {}

    def _build_response_fields(self) -> str:
        """
        Build response_fields string dynamically from JARVIS-DFT /info/structures.
        Ensures only safe, supported fields are requested.

        Returns:
            str: Comma-separated response_fields string
        """
        baseline_fields = [
            'id',
            'elements',
            'nelements',
            'lattice_vectors',
            'species_at_sites',
            'cartesian_site_positions',
            'chemical_formula_reduced',
            'last_modified',
            'nsites',
        ]
        optional_fields = [
            'species',
            'nperiodic_dimensions',
            'structure_features',
            '_jarvis_source',
            '_jarvis_reference',
        ]

        try:
            response = requests.get(
                f"{self.base_url}info/structures",
                headers={"Accept": "application/json"},
                timeout=30,
                allow_redirects=True,
            )
            response.raise_for_status()
            payload = response.json()

            data = payload.get('data', {})
            supported_fields = set()

            properties = data.get('properties')
            if isinstance(properties, dict):
                supported_fields.update(properties.keys())

            attributes = data.get('attributes', {}) if isinstance(data, dict) else {}
            attribute_properties = attributes.get('properties')
            if isinstance(attribute_properties, dict):
                supported_fields.update(attribute_properties.keys())

            output_fields = data.get('output_fields_by_format', {})
            if isinstance(output_fields, dict):
                supported_fields.update(output_fields.get('json', []) or [])

            attr_output_fields = attributes.get('output_fields_by_format', {})
            if isinstance(attr_output_fields, dict):
                supported_fields.update(attr_output_fields.get('json', []) or [])

            if not supported_fields:
                if self.logger:
                    self.logger.log("/info/structures returned no parsable supported fields; using baseline response_fields")
                return ",".join(baseline_fields)

            response_fields = [field for field in baseline_fields if field in supported_fields]
            response_fields.extend([field for field in optional_fields if field in supported_fields])

            if not response_fields:
                response_fields = baseline_fields

            if self.logger:
                self.logger.log(f"Using JARVIS-DFT response_fields: {','.join(response_fields)}")

            return ",".join(response_fields)
        except Exception as e:
            if self.logger:
                self.logger.log(f"Warning: Could not resolve JARVIS-DFT response fields dynamically: {str(e)}")
                self.logger.log("Using baseline JARVIS-DFT response_fields")
            return ",".join(baseline_fields)

    def map_properties(self, standard_properties: dict) -> dict:
        """
        Map standard property names to JARVIS-DFT property names.
        Only maps properties that are marked as retrievable.

        Args:
            standard_properties: Dict with standard property names as keys

        Returns:
            dict: Dict with JARVIS-DFT property names as keys (non-retrievable properties excluded)
        """
        mapped = {}
        for standard_name, value in standard_properties.items():
            if standard_name in self.property_mapping:
                prop_info = self.property_mapping[standard_name]
                if prop_info.get('retrievable'):
                    mapped[prop_info['name']] = value
                else:
                    if self.logger:
                        self.logger.log(
                            f"Property '{standard_name}' is not retrievable in JARVIS-DFT OPTIMADE, skipping"
                        )
            else:
                if self.logger:
                    self.logger.log(f"Warning: Property '{standard_name}' not in mapping, skipping")
        return mapped

    def _validate_filter_properties(self, filters: dict) -> dict:
        """
        Validate that requested filter properties are retrievable in JARVIS-DFT.
        Skip non-retrievable properties to avoid errors from OPTIMADE API.

        Args:
            filters: Dict with mapped JARVIS-DFT property names

        Returns:
            dict: Validated filters with only retrievable properties
        """
        validated = {}
        for prop_name, value in filters.items():
            is_retrievable = False

            # Check if property is marked retrievable in mapping
            for std_name, prop_info in self.property_mapping.items():
                if prop_info.get('name') == prop_name and prop_info.get('retrievable'):
                    is_retrievable = True
                    break

            if is_retrievable:
                validated[prop_name] = value
            else:
                if self.logger:
                    self.logger.log(f"Warning: Property '{prop_name}' not retrievable in JARVIS-DFT, skipping from filter")

        return validated

    def fetch_from_api(self, query: str, limit: int, filters: dict = None) -> list:
        """
        Fetch structures from JARVIS-DFT OPTIMADE API with page-number pagination.

        JARVIS-DFT uses page-number based pagination (page=1, page=2, ...)
        with a server-enforced hard cap of 20 entries per page.

        Args:
            query: Element or formula to search for
            limit: Maximum number of results to fetch
            filters: Optional dict with structure property filters

        Returns:
            list: Raw structure data from OPTIMADE API
        """
        all_results = []
        page_number = 1
        page_limit = 20  # JARVIS server hard cap: always returns max 20 per page
        filters = filters or {}

        try:
            if not self.is_host_reachable():
                return []

            # Validate filters before building OPTIMADE query
            filters = self._validate_filter_properties(filters)

            while len(all_results) < limit:
                optimade_filter = self.build_filter(query, filters)

                params = {
                    'page_limit': page_limit,
                    'page': page_number,
                }
                if optimade_filter:
                    params['filter'] = optimade_filter

                if self.logger:
                    self.logger.log(
                        f"JARVIS-DFT API request (page={page_number}): "
                        f"{self.base_url}structures with params {params}"
                    )

                response = requests.get(
                    f"{self.base_url}structures",
                    params=params,
                    headers={"Accept": "application/json"},
                    timeout=30,
                    allow_redirects=True,
                )
                response.raise_for_status()

                data = response.json()
                page_results = data.get('data', [])

                if page_results:
                    if self.logger:
                        self.logger.log(f"Retrieved {len(page_results)} structures (page: {page_number})")
                    all_results.extend(page_results)
                    page_number += 1
                    time.sleep(1.0)
                else:
                    if self.logger:
                        self.logger.log("No more structures available")
                    break

                # Also stop if server indicates no more data
                next_link = data.get('links', {}).get('next')
                if next_link is None:
                    break

            if self.logger:
                self.logger.log(f"Total retrieved from JARVIS-DFT: {len(all_results)} structures")

            return all_results[:limit]

        except requests.exceptions.RequestException as e:
            if self.logger:
                self.logger.log(f"JARVIS-DFT API request failed: {str(e)}")
            return all_results
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error fetching from JARVIS-DFT API: {str(e)}")
            return all_results

    def is_host_reachable(self) -> bool:
        """
        Check whether the JARVIS-DFT OPTIMADE host is reachable.

        Returns:
            bool: True if reachable, False otherwise
        """
        try:
            requests.get(
                self.base_url,
                headers={"Accept": "application/json"},
                timeout=5,
                allow_redirects=True,
            )
            return True
        except requests.exceptions.RequestException as e:
            if self.logger:
                self.logger.log(f"JARVIS-DFT host unreachable: {str(e)}")
            return False

    def build_filter(self, query: str, filters: dict = None) -> str:
        """
        Build OPTIMADE filter combining composition and structure filters.

        Args:
            query: Element or formula to search for
            filters: Optional dict with structure property filters

        Returns:
            str: OPTIMADE filter string or None if no filter needed
        """
        filters = filters or {}
        filter_parts = []

        comp_filter = self._build_composition_filter(query)
        if comp_filter:
            filter_parts.append(comp_filter)

        struct_filters = self._build_structure_filters(filters)
        if struct_filters:
            filter_parts.extend(struct_filters)

        if filter_parts:
            return " AND ".join(filter_parts)
        return None

    def _build_composition_filter(self, query: str) -> str:
        """
        Build OPTIMADE filter for element or formula queries.

        Args:
            query: Element or formula to search for

        Returns:
            str: OPTIMADE filter string or None if no filter needed
        """
        if not query or query.lower() == 'all':
            return None

        try:
            composition = Composition(query)
            elements = [el.symbol for el in composition.elements]
            if elements:
                if len(elements) == 1:
                    return f'elements HAS ALL "{elements[0]}"'
                # JARVIS requires comma-separated list syntax for HAS ALL
                element_list = ','.join([f'"{el}"' for el in elements])
                return f'elements HAS ALL {element_list}'
        except Exception:
            pass

        return f'elements HAS ALL "{query}"'

    def _build_structure_filters(self, filters: dict) -> list:
        """
        Build OPTIMADE filters for structure properties.
        Only builds filters for properties marked as retrievable in the mapping.

        Args:
            filters: Dict with filter keys and values (typically after mapping)

        Returns:
            list: List of OPTIMADE filter strings
        """
        filter_parts = []

        for prop_name, value in filters.items():
            is_retrievable = False
            for _, prop_info in self.property_mapping.items():
                if prop_info['name'] == prop_name and prop_info.get('retrievable'):
                    is_retrievable = True
                    break

            if not is_retrievable:
                if self.logger:
                    self.logger.log(f"Property '{prop_name}' is not retrievable, skipping from filter")
                continue

            if isinstance(value, list) and len(value) == 2:
                filter_parts.append(f"{prop_name} >= {value[0]} AND {prop_name} <= {value[1]}")
            elif isinstance(value, str):
                filter_parts.append(f'{prop_name} = "{value}"')
            else:
                filter_parts.append(f"{prop_name} = {value}")

        return filter_parts

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

            lattice_vectors = attrs.get('lattice_vectors')
            if not lattice_vectors:
                if self.logger:
                    self.logger.log("No lattice_vectors in entry")
                return None
            if len(lattice_vectors) != 3 or any(len(v) != 3 for v in lattice_vectors):
                if self.logger:
                    self.logger.log("Invalid lattice_vectors shape")
                return None

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
                        continue

                    site_species.append(occupancies if len(occupancies) > 1 else list(occupancies.keys())[0])
                    site_positions.append(pos)
                    continue

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

            lattice = Lattice(lattice_vectors)
            structure = Structure(
                lattice=lattice,
                species=site_species,
                coords=site_positions,
                coords_are_cartesian=coords_are_cartesian,
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
            attrs = entry.get('attributes', {})
            formula = attrs.get('chemical_formula_reduced') or f'structure_{index}'
            formula = formula.replace(' ', '_')

            filename = f"{formula}_{index}.cif"
            filepath = os.path.join(output_dir, filename)
            structure.to(filename=filepath, fmt='cif')

            return filepath

        except Exception as e:
            if self.logger:
                self.logger.log(f"Error saving CIF: {str(e)}")
            return None
