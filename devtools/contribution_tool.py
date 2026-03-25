#!/usr/bin/env python3
"""
EMOS Contribution Tool

Manages additions and removals of Information Units based on metadata.json.
Supports multiple changes in a single run.
"""

import json
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
        
        total_changes = len(additions) + len(removals)

        if total_changes == 0:
            print("✓ No differences found!")
            print("  Metadata and filesystem are in sync.")
            print("\nSyncing UI checkboxes from metadata...")
            self.update_information_unit_ui_lists()
            return

        # ── Summarise all pending changes ─────────────────────────────
        print(f"Found {total_changes} change(s):\n")
        if additions:
            print(f"  Additions ({len(additions)}):")
            for add in additions:
                label = add.get('metadata', {}).get('display_name', add['path'])
                print(f"    + {label}  ({add['path']})")
        if removals:
            print(f"\n  Removals ({len(removals)}):")
            for rem in removals:
                print(f"    - {rem.get('name', rem['path'])}  ({rem['path']})")

        confirm = input(f"\nProceed with all {total_changes} change(s)? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("\n✗ Cancelled.")
            return

        # ── Process additions ─────────────────────────────────────────
        for i, change_info in enumerate(additions, 1):
            print(f"\n{'─'*50}")
            print(f"  Addition {i}/{len(additions)}")
            print(f"{'─'*50}")

            if change_info['type'] == 'information_unit':
                self._handle_iu_addition(change_info)
            elif change_info['type'] == 'feature':
                self._handle_feature_addition(change_info)

        # ── Process removals ──────────────────────────────────────────
        for i, change_info in enumerate(removals, 1):
            print(f"\n{'─'*50}")
            print(f"  Removal {i}/{len(removals)}")
            print(f"{'─'*50}")

            if change_info['type'] == 'information_unit':
                self._handle_iu_removal(change_info)
            elif change_info['type'] == 'feature':
                self._handle_feature_removal(change_info)

        # ── Final UI sync (once, after all changes) ───────────────────
        print("\n" + "="*60)
        print("Syncing UI checkboxes from metadata...")
        self.update_information_unit_ui_lists()
        print(f"\n✓ All {total_changes} change(s) completed successfully!")

    # ── Single-change handlers ────────────────────────────────────────

    def _handle_iu_addition(self, change_info):
        """Create templates and update factory for one Information Unit addition."""
        unit_type = change_info['unit_type']
        meta = change_info['metadata']
        print(f"\n📦 ADDITION detected (Information Unit):\n")
        print(f"  Type: {unit_type.capitalize()[:-1]}")
        print(f"  Path: {change_info['path']}")
        print(f"  Name: {meta['display_name']}")
        print(f"  Description: {meta['description']}")

        print("\nThis will create:")
        print(f"  - {change_info['path']}/README.md")
        print(f"  - {change_info['path']}/__init__.py")
        print(f"  - {change_info['path']}/{meta['file_name']}")
        print(f"  - Update {unit_type.capitalize()[:-1]}Factory.py")

        print("\n🔨 Creating templates...\n")
        metadata = self.create_information_unit_templates(change_info)
        self.update_information_unit_factory_add(metadata, unit_type)
        print("\n✓ Addition completed successfully!")

    def _handle_feature_addition(self, change_info):
        """Create templates and update factory for one Feature addition."""
        category = change_info['category']
        meta = change_info['metadata']
        cat_display = 'Materials Exploration' if category == 'materials_exploration' else 'Electronics Application'
        print(f"\n📦 ADDITION detected (Feature):\n")
        print(f"  Category: {cat_display}")
        print(f"  Path: {change_info['path']}")
        print(f"  Name: {meta['display_name']}")
        print(f"  Description: {meta['description']}")

        print("\nThis will create:")
        print(f"  - {change_info['path']}/README.md")
        print(f"  - {change_info['path']}/__init__.py")
        print(f"  - {change_info['path']}/{meta['file_name']}")
        print(f"  - {change_info['path']}/{meta['js_file']}")
        print(f"  - Update FeatureFactory.py")

        print("\n🔨 Creating templates...\n")
        metadata = self.create_feature_templates(change_info)
        self.update_feature_factory_add(metadata, category)
        self.update_feature_factory_ids()
        self.update_all_feature_ui()
        print("\n✓ Addition completed successfully!")

    def _handle_iu_removal(self, change_info):
        """Remove folder and update factory for one Information Unit removal."""
        unit_type = change_info['unit_type']
        print(f"\n🗑️  REMOVAL detected (Information Unit):\n")
        print(f"  Type: {unit_type.capitalize()[:-1]}")
        print(f"  Path: {change_info['path']}")
        print(f"  Name: {change_info['name']}")

        print("\nThis will:")
        print(f"  - Delete {change_info['path']}/")
        print(f"  - Update {unit_type.capitalize()[:-1]}Factory.py")

        print("\n🔨 Removing...\n")
        self.remove_information_unit_folder(change_info)
        self.update_information_unit_factory_remove(change_info)
        print("\n✓ Removal completed successfully!")

    def _handle_feature_removal(self, change_info):
        """Remove folder and update factory for one Feature removal."""
        category = change_info['category']
        cat_display = 'Materials Exploration' if category == 'materials_exploration' else 'Electronics Application'
        print(f"\n🗑️  REMOVAL detected (Feature):\n")
        print(f"  Category: {cat_display}")
        print(f"  Path: {change_info['path']}")
        print(f"  Name: {change_info['name']}")

        print("\nThis will:")
        print(f"  - Delete {change_info['path']}/")
        print(f"  - Update FeatureFactory.py")

        print("\n🔨 Removing...\n")
        self.remove_feature_folder(change_info)
        self.update_feature_factory_remove(change_info)
        self.update_feature_factory_ids()
        self.update_all_feature_ui()
        print("\n✓ Removal completed successfully!")


if __name__ == "__main__":
    # Get project root (parent of metadata directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    tool = ContributionTool(project_root)
    tool.run()
