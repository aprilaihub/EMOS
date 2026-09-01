"""Methods for managing Information Units (Databases, Generators, Predictors)"""

import re
from html import escape
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

    def build_information_unit_ui_rows(self, unit_type):
        """Render IU option rows (name + IU panel button) from metadata.json."""
        indent_row = " " * 28
        indent_label = " " * 32
        indent_button = " " * 32
        indent_attr = " " * 36

        rows = []
        singular = unit_type[:-1]

        for item in self.metadata['information_units'][unit_type]:
            value = item['id']
            label = item.get('display_name', item.get('name', value))
            description = item.get('description', '')

            # Escape metadata text because it is injected into HTML attributes.
            value_esc = escape(str(value), quote=True)
            label_esc = escape(str(label), quote=True)
            desc_esc = escape(str(description), quote=True)

            rows.append(
                f"{indent_row}<div class=\"iu-option-row\">\n"
                f"{indent_label}<span class=\"iu-option-name\">{label_esc}</span>\n"
                f"{indent_button}<button\n"
                f"{indent_attr}class=\"iu-feature-btn\"\n"
                f"{indent_attr}data-iu-feature=\"{value_esc}\"\n"
                f"{indent_attr}data-iu-type=\"{singular}\"\n"
                f"{indent_attr}data-iu-name=\"{label_esc}\"\n"
                f"{indent_attr}data-iu-desc=\"{desc_esc}\"\n"
                f"{indent_attr}title=\"Open IU panel\"\n"
                f"{indent_attr}aria-label=\"Open IU panel\"\n"
                f"{indent_button}>\u25b6</button>\n"
                f"{indent_row}</div>"
            )

        return "\n".join(rows)

    def _replace_div_inner(self, content, open_tag, new_inner):
        """Replace inner HTML of a div identified by an exact opening tag string."""
        start = content.find(open_tag)
        if start == -1:
            return content, 0

        inner_start = start + len(open_tag)
        token_pattern = re.compile(r'<div\b[^>]*>|</div>')
        depth = 1

        for token in token_pattern.finditer(content, inner_start):
            token_text = token.group(0)
            if token_text.startswith('<div'):
                depth += 1
            else:
                depth -= 1

            if depth == 0:
                inner_end = token.start()
                return content[:inner_start] + "\n" + new_inner + "\n" + content[inner_end:], 1

        return content, 0

    def _build_information_unit_column(self, unit_type, heading, dom_id):
        """Render one IU column (Databases/Generators/Predictors)."""
        indent_col = " " * 24
        indent_h3 = " " * 28
        indent_group = " " * 28
        indent_group_close = " " * 28

        rows = self.build_information_unit_ui_rows(unit_type)
        return (
            f"{indent_col}<div class=\"info-column\">\n"
            f"{indent_h3}<h3>{heading}</h3>\n"
            f"{indent_group}<div class=\"radio-group\" id=\"{dom_id}\">\n"
            f"{rows}\n"
            f"{indent_group_close}</div>\n"
            f"{indent_col}</div>"
        )

    def build_information_units_block(self):
        """Render complete info-units block from metadata to keep index.html stable."""
        columns = [
            self._build_information_unit_column('databases', 'Databases', 'databasesList'),
            self._build_information_unit_column('generators', 'Generators', 'generatorsList'),
            self._build_information_unit_column('predictors', 'Predictors', 'predictorsList'),
        ]
        return "\n".join(columns)

    def build_information_units_section(self):
        """Render the full Information Units <section> block."""
        info_units_block = self.build_information_units_block()
        return (
            "                <section class=\"control-section\">\n"
            "                    <h2>Information Units</h2>\n"
            "                    <div class=\"info-units\">\n"
            f"{info_units_block}\n"
            "                    </div>\n"
            "                </section>\n"
        )

    def update_information_unit_ui_lists(self):
        """Rewrite index.html IU lists from metadata so UI matches backend."""
        index_path = self.project_root / "index.html"
        if not index_path.exists():
            print("  ⚠ index.html not found; skipping UI update")
            return

        content = index_path.read_text()
        section_pattern = r'(<!-- Information Units Section -->\s*)(.*?)(\s*<!-- Features Section -->)'
        new_section = self.build_information_units_section()
        content, count = re.subn(section_pattern, rf'\1{new_section}\3', content, flags=re.S)
        if count == 0:
            print("  ⚠ Could not update Information Units section in index.html; please verify markup")

        index_path.write_text(content)
        print("  ✓ Updated Information Unit lists in index.html")
    
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
