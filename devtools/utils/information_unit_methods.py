"""Methods for managing Information Units (Databases, Generators, Predictors)"""

import re
from .templates.information_unit_templates import (
    generate_readme,
    generate_init_file,
    generate_python_class
)


class InformationUnitMethods:
    """Methods for creating, updating, and removing information units"""
    
    def create_readme(self, metadata):
        """Generate README.md content"""
        return generate_readme(metadata)
    
    def create_init_file(self):
        """Generate __init__.py content"""
        return generate_init_file()
    
    def create_python_class(self, metadata, unit_type):
        """Generate Python class file content"""
        return generate_python_class(metadata, unit_type)
    
    def create_information_unit_templates(self, change_info):
        """Create template files for new Information Unit"""
        metadata = change_info['metadata']
        unit_type = change_info['unit_type']
        folder_path = self.project_root / change_info['path']
        
        # Create directory
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created directory: {change_info['path']}")
        
        # Create README.md
        readme_path = folder_path / "README.md"
        with open(readme_path, 'w') as f:
            f.write(self.create_readme(metadata))
        print(f"  ✓ Created README.md")
        
        # Create __init__.py
        init_path = folder_path / "__init__.py"
        with open(init_path, 'w') as f:
            f.write(self.create_init_file())
        print(f"  ✓ Created __init__.py")
        
        # Create Python class file
        class_file_path = folder_path / metadata['file_name']
        with open(class_file_path, 'w') as f:
            f.write(self.create_python_class(metadata, unit_type))
        print(f"  ✓ Created {metadata['file_name']}")
        
        return metadata

    def build_information_unit_ui_labels(self, unit_type):
        """Render checkbox label rows for the given unit type using metadata.json"""
        indent = " " * 28
        labels = []
        for item in self.metadata['information_units'][unit_type]:
            value = item['id']
            label = item.get('display_name', item.get('name', value))
            singular = unit_type[:-1]
            labels.append(f"{indent}<label><input type=\"checkbox\" ui-type=\"{singular}\" value=\"{value}\"> {label}</label>")
        return "\n".join(labels)

    def update_information_unit_ui_lists(self):
        """Rewrite index.html checkbox lists from metadata so UI matches backend"""
        index_path = self.project_root / "index.html"
        if not index_path.exists():
            print("  ⚠ index.html not found; skipping UI update")
            return

        content = index_path.read_text()
        replacements = [
            ('databases', 'databasesList'),
            ('generators', 'generatorsList'),
            ('predictors', 'predictorsList'),
        ]

        for unit_type, dom_id in replacements:
            pattern = rf'(<div class="radio-group" id="{dom_id}">\n)(.*?)(\n\s*</div>)'
            new_labels = self.build_information_unit_ui_labels(unit_type)
            content, count = re.subn(pattern, rf"\1{new_labels}\3", content, flags=re.S)
            if count == 0:
                print(f"  ⚠ Could not update {dom_id} in index.html; please verify markup")

        index_path.write_text(content)
        print("  ✓ Updated UI checkboxes in index.html")
    
    def update_information_unit_factory_add(self, metadata, unit_type):
        """Add entry to Factory.py file"""
        folder_map = {
            'databases': ('Databases', 'DatabaseFactory.py'),
            'generators': ('Generators', 'GeneratorFactory.py'),
            'predictors': ('Predictors', 'PredictorFactory.py')
        }

        base_folder, factory_filename = folder_map[unit_type]
        factory_file = self.project_root / "Information_Units" / base_folder / factory_filename
        
        with open(factory_file, 'r') as f:
            content = f.read()
        
        # Prepare import and factory entry
        component_folder = metadata['name']
        class_name = metadata['class_name']
        unit_id = metadata['id']
        
        import_line = f"from Information_Units.{base_folder}.{component_folder}.{class_name} import {class_name}\n"
        factory_entry = f'    "{unit_id}": {class_name},\n'
        
        # Find where to insert import (after last import)
        lines = content.split('\n')
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('from Information_Units'):
                last_import_idx = i
        
        # Insert import
        lines.insert(last_import_idx + 1, import_line.rstrip())
        
        # Find factory dict and insert entry (before closing brace)
        factory_dict_name = f"{unit_type[:-1]}_factory"
        for i, line in enumerate(lines):
            if factory_dict_name in line and '{' in line:
                # Find closing brace
                for j in range(i, len(lines)):
                    if lines[j].strip() == '}':
                        lines.insert(j, factory_entry.rstrip())
                        break
                break
        
        # Write back
        with open(factory_file, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"  ✓ Updated {factory_file.name}")
    
    def update_information_unit_factory_remove(self, change_info):
        """Remove entry from Factory.py file"""
        unit_type = change_info['unit_type']
        component_name = change_info['name']
        
        folder_map = {
            'databases': ('Databases', 'DatabaseFactory.py'),
            'generators': ('Generators', 'GeneratorFactory.py'),
            'predictors': ('Predictors', 'PredictorFactory.py')
        }

        base_folder, factory_filename = folder_map[unit_type]
        factory_file = self.project_root / "Information_Units" / base_folder / factory_filename
        
        with open(factory_file, 'r') as f:
            lines = f.readlines()
        
        # Remove import line and factory entry
        new_lines = []
        skip_next = False
        
        for line in lines:
            # Skip import line containing the folder name
            if f".{component_name}." in line and line.strip().startswith('from'):
                continue
            # Skip factory entry containing the folder name
            if f'{component_name}' in line and ':' in line and line.strip().startswith('"'):
                continue
            new_lines.append(line)
        
        # Write back
        with open(factory_file, 'w') as f:
            f.writelines(new_lines)
        
        print(f"  ✓ Updated {factory_file.name}")
    
    def remove_information_unit_folder(self, change_info):
        """Remove an Information Unit folder"""
        folder_path = self.project_root / change_info['path']
        
        if folder_path.exists():
            import shutil
            shutil.rmtree(folder_path)
            print(f"  ✓ Removed directory: {change_info['path']}")
        else:
            print(f"  ⚠ Directory not found: {change_info['path']}")
