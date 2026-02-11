"""Comparison and validation methods for metadata vs filesystem"""


class ComparisonMethods:
    """Methods for comparing metadata with filesystem and validating changes"""
    
    def get_metadata_folders(self):
        """Extract all folder paths from metadata (information units and features)"""
        folders = {
            'information_units': {
                'databases': [],
                'generators': [],
                'predictors': []
            },
            'features': {}
        }
        
        # Information Units
        for db in self.metadata['information_units']['databases']:
            folders['information_units']['databases'].append({
                'path': db['folder_path'],
                'metadata': db
            })
            
        for gen in self.metadata['information_units']['generators']:
            folders['information_units']['generators'].append({
                'path': gen['folder_path'],
                'metadata': gen
            })
            
        for pred in self.metadata['information_units']['predictors']:
            folders['information_units']['predictors'].append({
                'path': pred['folder_path'],
                'metadata': pred
            })
        
        # Features
        feature_folders = self.get_feature_metadata_folders()
        folders['features'] = feature_folders
            
        return folders
    
    def get_actual_folders(self):
        """Scan filesystem for actual Information Unit and Feature folders"""
        folders = {
            'information_units': {
                'databases': [],
                'generators': [],
                'predictors': []
            },
            'features': {}
        }
        
        # Information Units
        base_paths = {
            'databases': self.project_root / "Information_Units" / "Databases",
            'generators': self.project_root / "Information_Units" / "Generators",
            'predictors': self.project_root / "Information_Units" / "Predictors"
        }
        
        for unit_type, base_path in base_paths.items():
            if base_path.exists():
                for item in base_path.iterdir():
                    if item.is_dir() and not item.name.startswith('_'):
                        rel_path = str(item.relative_to(self.project_root))
                        folders['information_units'][unit_type].append(rel_path)
        
        # Features
        feature_folders = self.get_feature_actual_folders()
        folders['features'] = feature_folders
        
        return folders
    
    def compare_folders(self, metadata_folders, actual_folders):
        """Compare metadata vs actual folders and identify changes for both information units and features"""
        additions = []
        removals = []
        
        # Information Units comparison
        for unit_type in ['databases', 'generators', 'predictors']:
            meta_paths = set([f['path'] for f in metadata_folders['information_units'][unit_type]])
            actual_paths = set(actual_folders['information_units'][unit_type])
            
            # Find additions (in metadata but not in filesystem)
            for folder_info in metadata_folders['information_units'][unit_type]:
                if folder_info['path'] not in actual_paths:
                    additions.append({
                        'type': 'information_unit',
                        'unit_type': unit_type,
                        'path': folder_info['path'],
                        'metadata': folder_info['metadata']
                    })
            
            # Find removals (in filesystem but not in metadata)
            for path in actual_paths:
                if path not in meta_paths:
                    folder_name = path.split('/')[-1]
                    removals.append({
                        'type': 'information_unit',
                        'unit_type': unit_type,
                        'path': path,
                        'name': folder_name
                    })
        
        # Features comparison
        feature_additions, feature_removals = self.compare_feature_folders(
            metadata_folders['features'], 
            actual_folders['features']
        )
        additions.extend(feature_additions)
        removals.extend(feature_removals)
        
        return additions, removals
    
    def validate_changes(self, additions, removals):
        """Validate that changes meet contribution requirements"""
        total_changes = len(additions) + len(removals)
        
        if total_changes == 0:
            return 'no_change', None
        
        if total_changes > 1:
            return 'multiple_changes', {
                'additions': additions,
                'removals': removals
            }
        
        # Single change - return its type
        if len(additions) == 1:
            return 'addition', additions[0]
        else:
            return 'removal', removals[0]
    
    def get_feature_metadata_folders(self):
        """Extract all feature paths from metadata"""
        folders = {
            'materials_exploration': [],
            'electronics_application': []
        }
        
        features = self.metadata.get('features', {})
        
        for category, feature_list in features.items():
            if category == 'materials_exploration':
                category_key = 'materials_exploration'
            elif category == 'electronics_application':
                category_key = 'electronics_application'
            else:
                continue
            
            # feature_list is now an array of feature objects
            for feature_meta in feature_list:
                path = feature_meta.get('folder_path')
                if path:
                    folders[category_key].append({
                        'path': path,
                        'metadata': {
                            'display_name': feature_meta.get('display_name'),
                            'description': feature_meta.get('description'),
                            'name': feature_meta.get('name'),
                            'id': feature_meta.get('id'),
                            'class_name': feature_meta.get('class_name'),
                            'file_name': feature_meta.get('file_name'),
                            'js_file': feature_meta.get('js_file_name'),
                            'category': category_key,
                            'folder_path': path,
                            'inputs': feature_meta.get('inputs', []),
                            'outputs': feature_meta.get('outputs', [])
                        }
                    })
        
        return folders
    
    def get_feature_actual_folders(self):
        """Scan filesystem for actual feature folders"""
        folders = {
            'materials_exploration': [],
            'electronics_application': []
        }
        
        base_paths = {
            'materials_exploration': self.project_root / "Features" / "Materials_Exploration",
            'electronics_application': self.project_root / "Features" / "Electronics_Application"
        }
        
        for category, base_path in base_paths.items():
            if base_path.exists():
                for item in base_path.iterdir():
                    if item.is_dir() and not item.name.startswith('_'):
                        rel_path = str(item.relative_to(self.project_root))
                        folders[category].append(rel_path)
        
        return folders
    
    def compare_feature_folders(self, metadata_folders, actual_folders):
        """Compare metadata vs actual feature folders and identify changes"""
        additions = []
        removals = []
        
        for category in ['materials_exploration', 'electronics_application']:
            meta_paths = set([f['path'] for f in metadata_folders[category]])
            actual_paths = set(actual_folders[category])
            
            # Find additions (in metadata but not in filesystem)
            for folder_info in metadata_folders[category]:
                if folder_info['path'] not in actual_paths:
                    additions.append({
                        'type': 'feature',
                        'category': category,
                        'path': folder_info['path'],
                        'metadata': folder_info['metadata']
                    })
            
            # Find removals (in filesystem but not in metadata)
            for path in actual_paths:
                if path not in meta_paths:
                    folder_name = path.split('/')[-1]
                    removals.append({
                        'type': 'feature',
                        'category': category,
                        'path': path,
                        'name': folder_name
                    })
        
        return additions, removals
