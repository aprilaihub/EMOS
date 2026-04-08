"""Methods for managing property mappings as Information Units are added/removed."""

import json
from pathlib import Path


class PropertyMappingsMethods:
    """Methods for handling property mapping files and common properties cleanup."""
    
    def _get_property_mappings_root(self) -> Path:
        """Get the root path for property mappings."""
        return self.project_root / "Information_Units" / "property_mappings"
    
    def _get_common_properties_path(self) -> Path:
        """Get the path to common_properties.json."""
        return self._get_property_mappings_root() / "common_properties.json"
    
    def _get_source_mapping_path(self, source_name: str, source_type: str) -> Path:
        """Get the path to a source mapping file.
        
        Args:
            source_name: Name of the source (e.g., 'aflow')
            source_type: Type of the source (e.g., 'databases', 'generators', 'predictors')
        
        Returns:
            Path to the source mapping file
        """
        return (
            self._get_property_mappings_root()
            / "sources"
            / source_type
            / f"{source_name}.json"
        )
    
    def _read_json(self, path: Path) -> dict:
        """Read a JSON file safely."""
        if not path.exists():
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  ⚠ Error reading {path}: {e}")
            return {}
    
    def _write_json(self, path: Path, data: dict) -> None:
        """Write a JSON file safely."""
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"  ⚠ Error writing {path}: {e}")
    
    def _get_all_source_properties(self) -> dict[str, set[str]]:
        """Get all properties used by each source.
        
        Returns:
            Dictionary mapping source_name -> set of property names it uses
        """
        sources_root = self._get_property_mappings_root() / "sources"
        if not sources_root.exists():
            return {}
        
        source_properties: dict[str, set[str]] = {}
        
        # Iterate through all source types (databases, generators, predictors)
        for source_type_dir in sources_root.iterdir():
            if not source_type_dir.is_dir():
                continue
            
            # Iterate through all source files
            for mapping_file in source_type_dir.glob("*.json"):
                source_name = mapping_file.stem
                mapping_data = self._read_json(mapping_file)
                properties = mapping_data.get("properties", {})
                source_properties[source_name] = set(properties.keys())
        
        return source_properties
    
    def _get_exclusive_properties(self, source_name: str, source_type: str) -> set[str]:
        """Find properties that are ONLY used by this source.
        
        Args:
            source_name: Name of the source being removed
            source_type: Type of the source being removed
        
        Returns:
            Set of property names that are exclusive to this source
        """
        all_source_props = self._get_all_source_properties()
        removed_source_props = all_source_props.get(source_name, set())
        
        # Find properties used by OTHER sources
        other_sources_props: set[str] = set()
        for other_source, props in all_source_props.items():
            if other_source != source_name:
                other_sources_props.update(props)
        
        # Exclusive properties are those in removed source but NOT in others
        exclusive = removed_source_props - other_sources_props
        
        return exclusive
    
    def _remove_properties_from_common(self, property_names: set[str]) -> None:
        """Remove specified properties from common_properties.json.
        
        Args:
            property_names: Set of property names to remove
        """
        if not property_names:
            return
        
        common_path = self._get_common_properties_path()
        common_data = self._read_json(common_path)
        properties = common_data.get("properties", {})
        
        removed_count = 0
        for prop_name in property_names:
            if prop_name in properties:
                del properties[prop_name]
                removed_count += 1
                print(f"    - Removed property: {prop_name}")
        
        if removed_count > 0:
            self._write_json(common_path, common_data)
            print(f"  ✓ Removed {removed_count} exclusive property/properties from common_properties.json")
    
    def _remove_source_mapping_file(self, source_name: str, source_type: str) -> None:
        """Delete the mapping file for a source.
        
        Args:
            source_name: Name of the source
            source_type: Type of the source
        """
        mapping_path = self._get_source_mapping_path(source_name, source_type)
        
        if mapping_path.exists():
            try:
                mapping_path.unlink()
                print(f"  ✓ Deleted mapping file: {mapping_path.relative_to(self.project_root)}")
            except OSError as e:
                print(f"  ⚠ Error deleting {mapping_path}: {e}")
        else:
            print(f"  ⚠ Mapping file not found: {mapping_path}")
    
    def cleanup_property_mappings_for_removed_unit(
        self,
        source_name: str,
        source_type: str
    ) -> None:
        """Clean up property mappings when an Information Unit is removed.
        
        This method:
        1. Identifies exclusive properties (only used by this source)
        2. Removes the source's mapping file
        3. Removes exclusive properties from common_properties.json
        
        Args:
            source_name: Name of the source being removed (e.g., 'aflow')
            source_type: Type of the source being removed (e.g., 'databases')
        """
        print(f"\n  Cleaning up property mappings for {source_name}...")
        
        # Check if mapping file exists
        mapping_path = self._get_source_mapping_path(source_name, source_type)
        if not mapping_path.exists():
            print(f"  ⚠ No mapping file found for {source_name}; skipping cleanup")
            return
        
        # Find exclusive properties
        exclusive_props = self._get_exclusive_properties(source_name, source_type)
        
        if exclusive_props:
            print(f"  Found {len(exclusive_props)} property/properties exclusive to this source:")
            for prop in sorted(exclusive_props):
                print(f"    • {prop}")
        else:
            print(f"  No exclusive properties found (all are used by other sources)")
        
        # Remove the mapping file
        self._remove_source_mapping_file(source_name, source_type)
        
        # Remove exclusive properties from common_properties.json
        self._remove_properties_from_common(exclusive_props)
