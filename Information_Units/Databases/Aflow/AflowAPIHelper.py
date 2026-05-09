"""Helper functions for AFLOW AFLUX API interaction and data conversion."""

import re
import time
from urllib.parse import quote

import requests
from pymatgen.core import Composition, Structure
from Information_Units.property_mappings.property_loader import load_source_property_mapping


class AflowAPIHelper:
    """Helper class for AFLOW AFLUX API operations."""

    def __init__(self, base_url: str, logger=None):
        self.base_url = base_url
        self.logger = logger
        self.property_mapping = self._load_property_mapping()
        self.response_fields = self._default_response_fields()

    def _load_property_mapping(self) -> dict:
        """Load AFLOW property mapping from modular property mappings."""
        try:
            mapping = {}
            source_mapping = load_source_property_mapping(source='aflow', source_type='databases')
            for prop_name, aflow_info in source_mapping.items():
                if aflow_info.get('retrievable'):
                    mapping[prop_name] = {
                        'name': aflow_info.get('name'),
                        'retrievable': True,
                        'range_support': aflow_info.get('range_support', False),
                    }
            return mapping
        except Exception as e:
            if self.logger:
                self.logger.log(f"Warning: Could not load AFLOW property mapping: {str(e)}")
            return {}

    def _default_response_fields(self) -> list:
        """Baseline AFLUX fields needed for CIF retrieval and metadata."""
        return [
            'auid',
            'aurl',
            'files',
            'compound',
            'species',
            'spacegroup_relax',
            'Egap',
            'density',
            'natoms',
            'volume_cell',
        ]

    def map_properties(self, standard_properties: dict) -> dict:
        """Map standard EMOS property names to AFLOW property names."""
        mapped = {}
        for standard_name, value in standard_properties.items():
            if standard_name in self.property_mapping:
                prop_info = self.property_mapping[standard_name]
                if prop_info.get('retrievable'):
                    mapped[prop_info['name']] = value
                elif self.logger:
                    self.logger.log(
                        f"Property '{standard_name}' is not retrievable in AFLOW, skipping"
                    )
            elif self.logger:
                self.logger.log(f"Warning: Property '{standard_name}' not in AFLOW mapping, skipping")
        return mapped

    def _validate_filter_properties(self, filters: dict) -> dict:
        """Keep only retrievable mapped AFLOW properties in filters."""
        valid_names = {
            info.get('name')
            for info in self.property_mapping.values()
            if info.get('retrievable') and info.get('name')
        }
        validated = {}
        for prop_name, value in (filters or {}).items():
            if prop_name in valid_names:
                validated[prop_name] = value
            elif self.logger:
                self.logger.log(
                    f"Warning: Property '{prop_name}' not retrievable in AFLOW, skipping from filter"
                )
        return validated

    def is_host_reachable(self) -> bool:
        """Check whether AFLUX host is reachable."""
        try:
            response = requests.get(self.base_url, timeout=5)
            return response.status_code < 500
        except requests.exceptions.RequestException as e:
            if self.logger:
                self.logger.log(f"AFLOW host unreachable: {str(e)}")
            return False

    def build_filter(self, query: str, filters: dict = None) -> str:
        """Build AFLUX summons string fragments for query + filters."""
        fragments = []
        comp_fragment = self._build_composition_filter(query)
        if comp_fragment:
            fragments.append(comp_fragment)

        fragments.extend(self._build_structure_filters(filters or {}))

        return ",".join(fragments) if fragments else ""

    def _build_composition_filter(self, query: str) -> str:
        if not query or str(query).lower() == 'all':
            return ""

        query = str(query).strip()
        try:
            composition = Composition(query)
            elements = [el.symbol for el in composition.elements]
            if elements:
                parts = ",".join([f"'{el}'" for el in elements])
                return f"species({parts})"
        except Exception:
            pass

        return f"species('{query}')"

    def _format_range(self, min_value, max_value) -> str:
        left = "*" if min_value is None else str(min_value)
        right = "*" if max_value is None else str(max_value)
        return f"{left}*,*{right}"

    def _build_structure_filters(self, filters: dict) -> list:
        clauses = []
        for prop_name, value in filters.items():
            if isinstance(value, list) and len(value) == 2:
                clauses.append(f"{prop_name}({self._format_range(value[0], value[1])})")
            elif isinstance(value, str):
                escaped = value.replace("'", "\\'")
                clauses.append(f"{prop_name}('{escaped}')")
            else:
                clauses.append(f"{prop_name}({value})")
        return clauses

    def _build_summons(self, query: str, filters: dict, page: int, page_size: int) -> str:
        query_filter = self.build_filter(query, filters)

        projected = list(self.response_fields)
        for key in filters.keys():
            if key not in projected:
                projected.append(key)

        parts = []
        if query_filter:
            parts.append(query_filter)
        parts.extend(projected)
        parts.append(f"paging({page},{page_size})")
        return ",".join(parts)

    def _normalize_aflux_response(self, payload):
        """Normalize AFLUX payload into a list of entry dicts."""
        if isinstance(payload, list):
            return payload

        if isinstance(payload, dict):
            entries = []
            for key, value in payload.items():
                if isinstance(value, dict) and ' of ' in str(key):
                    entries.append(value)
            return entries

        return []

    def fetch_from_api(self, query: str, limit: int, filters: dict = None) -> list:
        """Fetch entries from AFLUX API with page-based pagination."""
        all_results = []
        filters = self._validate_filter_properties(filters or {})

        if not self.is_host_reachable():
            return all_results

        page = 1
        page_size = max(1, min(200, int(limit) if limit else 10))

        try:
            while len(all_results) < limit:
                remaining = limit - len(all_results)
                current_page_size = min(page_size, remaining)
                summons = self._build_summons(query, filters, page, current_page_size)

                if self.logger:
                    self.logger.log(
                        f"AFLOW AFLUX request (page={page}): {self.base_url}?{summons}"
                    )

                response = requests.get(
                    self.base_url,
                    params=summons,
                    timeout=30,
                )
                response.raise_for_status()

                payload = response.json()
                page_results = self._normalize_aflux_response(payload)

                if not page_results:
                    if self.logger:
                        self.logger.log("No more AFLOW entries available")
                    break

                all_results.extend(page_results)
                page += 1
                time.sleep(1.0)

            if self.logger:
                self.logger.log(f"Total retrieved from AFLOW: {len(all_results)} entries")

            return all_results[:limit]

        except requests.exceptions.RequestException as e:
            if self.logger:
                self.logger.log(f"AFLOW API request failed: {str(e)}")
            return all_results
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error fetching from AFLOW API: {str(e)}")
            return all_results

    def _choose_cif_filename(self, files) -> str:
        """Pick best CIF filename from AFLOW files list."""
        if not isinstance(files, list):
            return ""

        cifs = [name for name in files if isinstance(name, str) and name.lower().endswith('.cif')]
        if not cifs:
            return ""

        preferred = [
            name for name in cifs
            if '_corner' not in name and '_sconv' not in name and '_sprim' not in name
        ]
        candidates = preferred if preferred else cifs
        return sorted(candidates, key=len)[0]

    def _build_file_url(self, aurl: str, filename: str) -> str:
        if not aurl or not filename:
            return ""

        if aurl.startswith('http://') or aurl.startswith('https://'):
            base = aurl.rstrip('/')
        else:
            # AFLUX commonly returns AURL as "host:PATH/TO/ENTRY" (not a TCP port).
            # Convert only the first ':' into a path separator.
            cleaned = aurl.strip('/')
            if ':' in cleaned:
                host, path = cleaned.split(':', 1)
                base = f"http://{host}/{path.lstrip('/')}"
            else:
                base = f"http://{cleaned}"

        # Quote only filename path fragment to preserve directory path in aurl.
        return f"{base}/{quote(filename)}"

    def _structure_from_entry_fields(self, entry: dict):
        """Fallback parser if explicit structural arrays exist in entry payload."""
        lattice_vectors = entry.get('lattice_vectors')
        positions = entry.get('positions_fractional') or entry.get('cartesian_site_positions')
        species = entry.get('species_at_sites')

        if not lattice_vectors or not positions or not species:
            return None

        try:
            coords_are_cartesian = bool(entry.get('cartesian_site_positions')) and not bool(entry.get('positions_fractional'))
            return Structure(
                lattice=lattice_vectors,
                species=species,
                coords=positions,
                coords_are_cartesian=coords_are_cartesian,
            )
        except Exception:
            return None

    def convert_to_structure(self, aflow_entry: dict) -> Structure:
        """Convert AFLOW entry to pymatgen Structure.

        Preferred path is CIF download via `aurl` + `files`.
        """
        try:
            cif_name = self._choose_cif_filename(aflow_entry.get('files', []))
            file_url = self._build_file_url(aflow_entry.get('aurl', ''), cif_name)

            if file_url:
                response = requests.get(file_url, timeout=30)
                response.raise_for_status()
                cif_text = response.text
                if cif_text and 'data_' in cif_text:
                    return Structure.from_str(cif_text, fmt='cif')

            # Fallback path if no CIF available but structural arrays exist.
            fallback = self._structure_from_entry_fields(aflow_entry)
            if fallback is not None:
                return fallback

            if self.logger:
                self.logger.log("Could not construct structure from AFLOW entry")
            return None
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error converting AFLOW entry to structure: {str(e)}")
            return None

    def save_cif_from_structure(self, structure: Structure, entry: dict, index: int, output_dir: str) -> str:
        """Save structure as CIF file in output directory."""
        try:
            formula = entry.get('compound') or getattr(structure.composition, 'reduced_formula', None) or f'structure_{index}'
            formula = str(formula).replace(' ', '_')
            filename = f"{formula}_{index}.cif"
            filepath = os.path.join(output_dir, filename)
            structure.to(filename=filepath, fmt='cif')
            return filepath
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error saving AFLOW CIF: {str(e)}")
            return None
