"""Methods for updating UI files (index.html, script.js)"""

import re


class UIUpdateMethods:
    """Methods for updating UI components based on metadata"""
    
    def update_feature_ui_buttons(self):
        """Update feature buttons in index.html based on metadata.json"""
        index_path = self.project_root / "index.html"
        if not index_path.exists():
            print("  ⚠ index.html not found; skipping UI button update")
            return
        
        content = index_path.read_text()
        
        # Build buttons for Materials Exploration
        materials_buttons = self._build_feature_buttons('materials_exploration')
        
        # Build buttons for Electronics Application
        electronics_buttons = self._build_feature_buttons('electronics_application')
        
        # Replace Materials Exploration buttons
        materials_pattern = r'(<!-- Materials Exploration Subsection -->.*?<div class="feature-grid">)(.*?)(</div>\s*</div>\s*</div>)'
        content = re.sub(materials_pattern, rf'\1{materials_buttons}\3', content, flags=re.S)
        
        # Replace Electronics Application buttons
        electronics_pattern = r'(<!-- Electronics Application Subsection -->.*?<div class="feature-grid">)(.*?)(</div>\s*</div>\s*</div>)'
        content = re.sub(electronics_pattern, rf'\1{electronics_buttons}\3', content, flags=re.S)
        
        index_path.write_text(content)
        print("  ✓ Updated feature buttons in index.html")
    
    def _build_feature_buttons(self, category):
        """Build HTML for feature buttons from metadata"""
        features = self.metadata.get('features', {}).get(category, [])
        buttons = []
        indent = "\n" + " " * 32
        
        for feature in features:
            feature_id = feature.get('id')
            name = feature.get('display_name', feature.get('name'))
            desc = feature.get('description', '')
            
            button = f'<button class="feature-btn" data-feature="{feature_id}" data-feature-name="{name}" data-feature-desc="{desc}">{name}</button>'
            buttons.append(button)
        
        return indent + indent.join(buttons) + "\n" + " " * 28
    
    def update_feature_ui_scripts(self):
        """Update feature mappings in script.js based on metadata.json"""
        script_path = self.project_root / "script.js"
        if not script_path.exists():
            print("  ⚠ script.js not found; skipping UI script update")
            return
        
        content = script_path.read_text()
        
        # Build featureClasses mapping
        feature_classes_mapping = self._build_feature_classes_mapping()
        
        # Build featureFiles mapping
        feature_files_mapping = self._build_feature_files_mapping()
        
        # Replace featureClasses
        classes_pattern = r'(const featureClasses = \{)(.*?)(\};)'
        content = re.sub(classes_pattern, rf'\1{feature_classes_mapping}\3', content, flags=re.S)
        
        # Replace featureFiles
        files_pattern = r'(const featureFiles = \{)(.*?)(\};)'
        content = re.sub(files_pattern, rf'\1{feature_files_mapping}\3', content, flags=re.S)
        
        script_path.write_text(content)
        print("  ✓ Updated feature mappings in script.js")
    
    def _build_feature_classes_mapping(self):
        """Build JavaScript featureClasses object from metadata"""
        lines = []
        indent = "\n    "
        
        # Combine both categories
        for category in ['materials_exploration', 'electronics_application']:
            features = self.metadata.get('features', {}).get(category, [])
            for feature in features:
                feature_id = feature.get('id')
                class_name = feature.get('class_name')
                lines.append(f"{indent}{feature_id}: '{class_name}',")
        
        return ''.join(lines) + "\n"
    
    def _build_feature_files_mapping(self):
        """Build JavaScript featureFiles object from metadata"""
        lines = []
        indent = "\n    "
        
        # Combine both categories
        for category in ['materials_exploration', 'electronics_application']:
            features = self.metadata.get('features', {}).get(category, [])
            for feature in features:
                feature_id = feature.get('id')
                folder_path = feature.get('folder_path')
                js_file = feature.get('js_file_name')
                
                # Convert to relative path for frontend
                file_path = f"./{folder_path}/{js_file}"
                lines.append(f"{indent}{feature_id}: '{file_path}',")
        
        return ''.join(lines) + "\n"
    
    def update_all_feature_ui(self):
        """Update all UI components for features (buttons and scripts)"""
        print("\n  Updating UI components...")
        self.update_feature_ui_buttons()
        self.update_feature_ui_scripts()
        print("  ✓ All UI components updated")
