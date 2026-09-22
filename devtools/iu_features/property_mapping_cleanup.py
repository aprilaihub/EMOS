"""Helpers for cleaning up IU source property mappings during feature removal."""

from __future__ import annotations

import sys
from pathlib import Path

DEVTOOLS_DIR = Path(__file__).resolve().parents[1]
if str(DEVTOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(DEVTOOLS_DIR))

from utils.property_mappings_methods import PropertyMappingsMethods


class _PropertyMappingCleaner(PropertyMappingsMethods):
    def __init__(self, project_root: Path):
        self.project_root = project_root


def cleanup_removed_iu_property_mappings(project_root: Path, iu_id: str, iu_type: str) -> None:
    """Remove IU mapping file and exclusive common properties for one IU.

    Args:
        project_root: EMOS repository root path
        iu_id: IU source id (e.g., 'aflow')
        iu_type: IU source type folder ('databases', 'generators', 'predictors')
    """
    cleaner = _PropertyMappingCleaner(project_root)
    cleaner.cleanup_property_mappings_for_removed_unit(source_name=iu_id, source_type=iu_type)

