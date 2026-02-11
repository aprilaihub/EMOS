#!/usr/bin/env python3
"""
EMOS Contribution Tool

Manages additions and removals of Information Units based on metadata.json.
Ensures one change at a time for clean contributions.
"""

import json
import sys
from pathlib import Path

from make_metadata import generate_metadata_from_core
from utils.comparison_methods import ComparisonMethods
from utils.information_unit_methods import InformationUnitMethods
from utils.feature_methods import FeatureMethods
from utils.ui_update_methods import UIUpdateMethods


class ContributionTool(
    ComparisonMethods,
    InformationUnitMethods,
    FeatureMethods,
    UIUpdateMethods
):
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.metadata_path = self.project_root / "devtools" / "metadata.json"
        self.metadata = None
        
    def load_metadata(self):
        """Load metadata.json"""
        with open(self.metadata_path, 'r') as f:
            self.metadata = json.load(f)
    
    def run(self):
        """Main execution flow"""
        print("\n" + "="*60)
        print("EMOS Contribution Tool")
        print("="*60 + "\n")
        
        # Regenerate metadata from ui_data.json
        print("Syncing metadata from ui_data.json...")
        generate_metadata_from_core()
        print("✓ Metadata updated\n")
        
        # Load metadata
        print("Loading metadata.json...")
        self.load_metadata()
        
        # Get folders from metadata and filesystem
        metadata_folders = self.get_metadata_folders()
        actual_folders = self.get_actual_folders()
        
        # Compare
        additions, removals = self.compare_folders(metadata_folders, actual_folders)
        
        # Validate
        change_type, change_info = self.validate_changes(additions, removals)
        
        # Handle different scenarios
        if change_type == 'no_change':
            print("✓ No differences found!")
            print("  Metadata and filesystem are in sync.")
            print("\nSyncing UI checkboxes from metadata...")
            self.update_information_unit_ui_lists()
            print("\nPress Enter to exit...")
            input()
            return
        
        if change_type == 'multiple_changes':
            print("✗ ERROR: Multiple changes detected!\n")
            print("Only ONE addition or removal is allowed at a time.\n")
            
            if change_info['additions']:
                print("Additions found:")
                for add in change_info['additions']:
                    print(f"  + {add['path']}")
            
            if change_info['removals']:
                print("\nRemovals found:")
                for rem in change_info['removals']:
                    print(f"  - {rem['path']}")
            
            print("\n⚠ Please update metadata.json to include only one change.")
            sys.exit(1)
        
        # Handle single valid change
        if change_type == 'addition':
            # Information Unit Addition
            if change_info['type'] == 'information_unit':
                unit_type = change_info['unit_type']
                print("📦 ADDITION detected (Information Unit):\n")
                print(f"  Type: {unit_type.capitalize()[:-1]}")
                print(f"  Path: {change_info['path']}")
                print(f"  Name: {change_info['metadata']['display_name']}")
                print(f"  Description: {change_info['metadata']['description']}")
                
                print("\nThis will create:")
                print(f"  - {change_info['path']}/README.md")
                print(f"  - {change_info['path']}/__init__.py")
                print(f"  - {change_info['path']}/{change_info['metadata']['file_name']}")
                print(f"  - Update {unit_type.capitalize()[:-1]}Factory.py")
                
                confirm = input("\nProceed with addition? (yes/no): ").strip().lower()
                
                if confirm in ['yes', 'y']:
                    print("\n🔨 Creating templates...\n")
                    metadata = self.create_information_unit_templates(change_info)
                    self.update_information_unit_factory_add(metadata, unit_type)
                    self.update_information_unit_ui_lists()
                    print("\n✓ Addition completed successfully!")
                else:
                    print("\n✗ Addition cancelled.")
            
            # Feature Addition
            elif change_info['type'] == 'feature':
                category = change_info['category']
                category_display = 'Materials Exploration' if category == 'materials_exploration' else 'Electronics Application'
                
                print("📦 ADDITION detected (Feature):\n")
                print(f"  Category: {category_display}")
                print(f"  Path: {change_info['path']}")
                print(f"  Name: {change_info['metadata']['display_name']}")
                print(f"  Description: {change_info['metadata']['description']}")
                
                print("\nThis will create:")
                print(f"  - {change_info['path']}/README.md")
                print(f"  - {change_info['path']}/__init__.py")
                print(f"  - {change_info['path']}/{change_info['metadata']['file_name']}")
                print(f"  - {change_info['path']}/{change_info['metadata']['js_file']}")
                print(f"  - Update FeatureFactory.py")
                
                confirm = input("\nProceed with addition? (yes/no): ").strip().lower()
                
                if confirm in ['yes', 'y']:
                    print("\n🔨 Creating templates...\n")
                    metadata = self.create_feature_templates(change_info)
                    self.update_feature_factory_add(metadata, category)
                    self.update_feature_factory_ids()
                    self.update_all_feature_ui()
                    print("\n✓ Addition completed successfully!")
                else:
                    print("\n✗ Addition cancelled.")
        
        elif change_type == 'removal':
            # Information Unit Removal
            if change_info['type'] == 'information_unit':
                unit_type = change_info['unit_type']
                print("🗑️  REMOVAL detected (Information Unit):\n")
                print(f"  Type: {unit_type.capitalize()[:-1]}")
                print(f"  Path: {change_info['path']}")
                print(f"  Name: {change_info['name']}")
                
                print("\nThis will:")
                print(f"  - Delete {change_info['path']}/")
                print(f"  - Update {unit_type.capitalize()[:-1]}Factory.py")
                
                confirm = input("\n⚠ Proceed with removal? (yes/no): ").strip().lower()
                
                if confirm in ['yes', 'y']:
                    print("\n🔨 Removing...\n")
                    self.remove_information_unit_folder(change_info)
                    self.update_information_unit_factory_remove(change_info)
                    self.update_information_unit_ui_lists()
                    print("\n✓ Removal completed successfully!")
                else:
                    print("\n✗ Removal cancelled.")
            
            # Feature Removal
            elif change_info['type'] == 'feature':
                category = change_info['category']
                category_display = 'Materials Exploration' if category == 'materials_exploration' else 'Electronics Application'
                
                print("🗑️  REMOVAL detected (Feature):\n")
                print(f"  Category: {category_display}")
                print(f"  Path: {change_info['path']}")
                print(f"  Name: {change_info['name']}")
                
                print("\nThis will:")
                print(f"  - Delete {change_info['path']}/")
                print(f"  - Update FeatureFactory.py")
                
                confirm = input("\n⚠ Proceed with removal? (yes/no): ").strip().lower()
                
                if confirm in ['yes', 'y']:
                    print("\n🔨 Removing...\n")
                    self.remove_feature_folder(change_info)
                    self.update_feature_factory_remove(change_info)
                    self.update_feature_factory_ids()
                    self.update_all_feature_ui()
                    print("\n✓ Removal completed successfully!")
                else:
                    print("\n✗ Removal cancelled.")


if __name__ == "__main__":
    # Get project root (parent of metadata directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    tool = ContributionTool(project_root)
    tool.run()
