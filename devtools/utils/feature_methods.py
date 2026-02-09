"""Methods for managing Features"""

import re
from .templates.feature_templates import (
    generate_feature_readme,
    generate_feature_python_class,
    generate_feature_javascript_file,
    generate_inputs_extraction,
    generate_outputs_formatting,
    generate_js_inputs_html,
    generate_js_outputs_html,
    generate_js_outputs_placeholder,
    generate_js_updateOutputs
)


class FeatureMethods:
    """Methods for creating, updating, and removing features"""
    
    def _generate_inputs_extraction(self, inputs):
        """Generate extract_inputs method body from metadata inputs"""
        return generate_inputs_extraction(inputs)
    
    def _generate_outputs_formatting(self, outputs):
        """Generate format_outputs method body from metadata outputs"""
        return generate_outputs_formatting(outputs)
    
    def _generate_js_inputs_html(self, inputs, class_name):
        """Generate JavaScript input HTML creation calls"""
        return generate_js_inputs_html(inputs, class_name)
    
    def _generate_js_outputs_html(self, outputs, class_name):
        """Generate JavaScript output display HTML"""
        return generate_js_outputs_html(outputs, class_name)
    
    def _generate_js_outputs_placeholder(self, outputs):
        """Generate placeholder return values for JavaScript processFeature()"""
        return generate_js_outputs_placeholder(outputs)
    
    def _generate_js_updateOutputs(self, outputs):
        """Generate updateOutputs method for JavaScript feature class"""
        return generate_js_updateOutputs(outputs)
    
    def create_feature_readme(self, metadata):
        """Generate README.md content for features"""
        return generate_feature_readme(metadata)
    
    def create_feature_python_class(self, metadata, category):
        """Generate Python feature class file content following BaseFeature pattern"""
        inputs = metadata.get('inputs', [])
        outputs = metadata.get('outputs', [])
        
        inputs_extraction = self._generate_inputs_extraction(inputs)
        outputs_formatting = self._generate_outputs_formatting(outputs)
        
        return generate_feature_python_class(metadata, category, inputs_extraction, outputs_formatting)
    
    def create_feature_javascript_file(self, metadata, category):
        """Generate JavaScript feature class file content following BaseFeature pattern"""
        class_name = metadata['class_name'].replace('Feature', '')
        inputs = metadata.get('inputs', [])
        outputs = metadata.get('outputs', [])
        
        inputs_html = self._generate_js_inputs_html(inputs, class_name)
        outputs_html = self._generate_js_outputs_html(outputs, class_name)
        outputs_placeholder = self._generate_js_outputs_placeholder(outputs)
        updateOutputs_method = self._generate_js_updateOutputs(outputs)
        
        return generate_feature_javascript_file(
            metadata, category, inputs_html, outputs_html, 
            outputs_placeholder, updateOutputs_method
        )
    
    def create_feature_templates(self, change_info):
        """Create template files for new Feature"""
        metadata = change_info['metadata']
        category = change_info['category']
        folder_path = self.project_root / change_info['path']
        
        # Create directory
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created directory: {change_info['path']}")
        
        # Create README.md
        readme_path = folder_path / "README.md"
        with open(readme_path, 'w') as f:
            f.write(self.create_feature_readme(metadata))
        print(f"  ✓ Created README.md")
        
        # Create __init__.py
        init_path = folder_path / "__init__.py"
        with open(init_path, 'w') as f:
            f.write(self.create_init_file())
        print(f"  ✓ Created __init__.py")
        
        # Create Python class file
        python_file_path = folder_path / metadata['file_name']
        with open(python_file_path, 'w') as f:
            f.write(self.create_feature_python_class(metadata, category))
        print(f"  ✓ Created {metadata['file_name']}")
        
        # Create JavaScript file
        js_file_path = folder_path / metadata['js_file']
        with open(js_file_path, 'w') as f:
            f.write(self.create_feature_javascript_file(metadata, category))
        print(f"  ✓ Created {metadata['js_file']}")
        
        return metadata
    
    def update_feature_factory_add(self, metadata, category):
        """Add entry to Feature FeatureFactory.py file"""
        factory_file = self.project_root / "Features" / "FeatureFactory.py"
        
        if not factory_file.exists():
            print(f"  ⚠ Factory file not found: {factory_file}")
            return
        
        with open(factory_file, 'r') as f:
            content = f.read()
        
        # Prepare import and factory entry
        component_folder = metadata['name']
        class_name = metadata['class_name']
        feature_id = str(metadata['id'])

        module_path = metadata['folder_path'].replace('/', '.')
        import_line = f"from {module_path}.{class_name} import {class_name}\n"
        factory_entry = f'    "{feature_id}": {class_name},\n'
        
        # Find where to insert import (after last import)
        lines = content.split('\n')
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('from Features'):
                last_import_idx = i
        
        # Insert import
        lines.insert(last_import_idx + 1, import_line.rstrip())
        
        # Find factory dict and insert entry (before closing brace)
        for i, line in enumerate(lines):
            if 'feature_factory' in line and '{' in line:
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
    
    def update_feature_factory_remove(self, change_info):
        """Remove entry from Feature FeatureFactory.py file"""
        component_name = change_info['name']
        class_name = f"{component_name}Feature"
        factory_file = self.project_root / "Features" / "FeatureFactory.py"
        
        if not factory_file.exists():
            print(f"  ⚠ Factory file not found: {factory_file}")
            return
        
        with open(factory_file, 'r') as f:
            lines = f.readlines()
        
        # Remove import line and factory entry
        new_lines = []
        for line in lines:
            # Skip import line containing the class name
            if line.strip().startswith('from') and f"{class_name} import {class_name}" in line:
                continue
            # Skip factory entry containing the class name
            if f": {class_name}," in line and line.strip().startswith('"'):
                continue
            new_lines.append(line)
        
        # Write back
        with open(factory_file, 'w') as f:
            f.writelines(new_lines)
        
        print(f"  ✓ Updated {factory_file.name}")
    
    def remove_feature_folder(self, change_info):
        """Remove a Feature folder"""
        folder_path = self.project_root / change_info['path']
        
        if folder_path.exists():
            import shutil
            shutil.rmtree(folder_path)
            print(f"  ✓ Removed directory: {change_info['path']}")
        else:
            print(f"  ⚠ Directory not found: {change_info['path']}")
    
    def update_feature_factory_ids(self):
        """Rebuild feature_factory dictionary IDs from metadata.json to match current state"""
        factory_file = self.project_root / "Features" / "FeatureFactory.py"
        
        if not factory_file.exists():
            print("  ⚠ FeatureFactory.py not found; skipping factory ID update")
            return
        
        with open(factory_file, 'r') as f:
            content = f.read()
        
        # Build new factory dictionary from metadata
        factory_entries = []
        indent = "    "
        
        # Collect all features first
        all_features = []
        for category in ['materials_exploration', 'electronics_application']:
            features = self.metadata.get('features', {}).get(category, [])
            all_features.extend(features)
        
        # Iterate with enumeration to handle last entry
        for i, feature in enumerate(all_features):
            feature_id = str(feature.get('id'))
            class_name = feature.get('class_name')
            comma = '' if i == len(all_features) - 1 else ','
            factory_entries.append(f'{indent}"{feature_id}": {class_name}{comma}')
        
        new_factory_dict = "\n".join(factory_entries)
        
        # Replace the feature_factory dictionary
        pattern = r'(feature_factory = \{)(.*?)(\n\})'
        replacement = rf'\1\n{new_factory_dict}\n\3'
        content = re.sub(pattern, replacement, content, flags=re.S)
        
        factory_file.write_text(content)
        print("  ✓ Updated feature_factory IDs in FeatureFactory.py")
