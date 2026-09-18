"""
Contribution standards compliance tests.

These are fast, offline, structural checks that every Information Unit (IU)
and Feature must satisfy per CONTRIBUTING.md and
docs/tutorials/iu-data-contracts.md. They use static source
inspection (``ast``) rather than importing modules, so they never require
heavy/optional runtime dependencies (pymatgen, torch, etc.) to be installed
and are safe to run on every contribution/PR.

They check:
- Folder conventions (``__init__.py`` + non-empty ``README.md``).
- Naming conventions (class name == FolderName + Type suffix).
- Interface contract (subclasses the right Base class and overrides the
  required primary method with the right first parameter name).
- Registration in ``devtools/metadata.json``.
"""

import ast
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
METADATA_PATH = REPO_ROOT / "devtools" / "metadata.json"

with open(METADATA_PATH, encoding="utf-8") as f:
    METADATA = json.load(f)

IU_KIND_INFO = {
    "Databases": {
        "type_suffix": "Database",
        "base_class": "BaseDatabase",
        "action_method": "retrieve",
        "action_param": "inputs",
        "metadata_key": "databases",
    },
    "Generators": {
        "type_suffix": "Generator",
        "base_class": "BaseGenerator",
        "action_method": "generate",
        "action_param": "inputs",
        "metadata_key": "generators",
    },
    "Predictors": {
        "type_suffix": "Predictor",
        "base_class": "BasePredictor",
        "action_method": "predict",
        "action_param": "input_data",
        "metadata_key": "predictors",
    },
}

FEATURE_ABSTRACT_METHODS = ("info", "extract_inputs", "process_feature", "format_outputs")


def _discover_iu_folders(kind):
    """List IU folders (Databases/Generators/Predictors) that are contributions,
    not the shared Base*/Factory files."""
    kind_dir = REPO_ROOT / "Information_Units" / kind
    if not kind_dir.exists():
        return []
    return sorted(
        item.name for item in kind_dir.iterdir()
        if item.is_dir() and not item.name.startswith("_") and not item.name.startswith(".")
    )


def _discover_features():
    """List (category, folder_name) for every feature under Features/.

    Only categories that are actually registered under ``metadata.json``'s
    ``features`` section count as user-contributed Features. This excludes
    ``Features/IU_Features``, which holds auto-generated IU panel JS files,
    not standalone Feature contributions.
    """
    features_dir = REPO_ROOT / "Features"
    known_categories = set(METADATA.get("features", {}).keys())
    results = []
    for category_dir in features_dir.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("_"):
            continue
        if category_dir.name.lower() not in known_categories:
            continue
        for item in category_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                results.append((category_dir.name, item.name))
    return sorted(results)


def _iu_params():
    params = []
    for kind in IU_KIND_INFO:
        for folder_name in _discover_iu_folders(kind):
            params.append((kind, folder_name))
    return params


def _metadata_entries_for(kind, folder_name):
    """Find matching metadata.json entries by folder_path for an IU."""
    metadata_key = IU_KIND_INFO[kind]["metadata_key"]
    entries = METADATA.get("information_units", {}).get(metadata_key, [])
    expected_path = f"Information_Units/{kind}/{folder_name}"
    return [e for e in entries if e.get("folder_path") == expected_path]


def _metadata_entries_for_feature(category, folder_name):
    entries = METADATA.get("features", {}).get(category.lower(), [])
    expected_path = f"Features/{category}/{folder_name}"
    return [e for e in entries if e.get("folder_path") == expected_path]


def _find_class_node(file_path, class_name):
    """Statically locate a top-level class definition without importing the module."""
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _find_class_node_anywhere(search_root, class_name):
    """Locate a class definition by name anywhere under search_root (for
    resolving intermediate shared base classes, e.g. MattergenGenerator)."""
    for py_file in search_root.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return node
    return None


def _inherits_from(class_node, target_base, search_root, _visited=None):
    """Check whether class_node (transitively) inherits from target_base,
    resolving intermediate base classes defined anywhere under search_root."""
    visited = _visited if _visited is not None else set()
    if class_node.name in visited:
        return False
    visited.add(class_node.name)

    bases = _base_class_names(class_node)
    if target_base in bases:
        return True
    for base in bases:
        base_node = _find_class_node_anywhere(search_root, base)
        if base_node is not None and _inherits_from(base_node, target_base, search_root, visited):
            return True
    return False


def _base_class_names(class_node):
    names = []
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def _own_method_node(class_node, method_name):
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
            return node
    return None


def _first_param_name(func_node):
    positional = [a.arg for a in func_node.args.args if a.arg != "self"]
    return positional[0] if positional else None


# ---------------------------------------------------------------------------
# Information Unit (Database/Generator/Predictor) compliance
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize("kind,folder_name", _iu_params())
class TestInformationUnitContributionStandards:
    def test_folder_has_readme_and_init(self, kind, folder_name):
        iu_dir = REPO_ROOT / "Information_Units" / kind / folder_name
        readme = iu_dir / "README.md"
        assert readme.exists(), f"{kind}/{folder_name} is missing a README.md"
        assert readme.stat().st_size > 0, f"{kind}/{folder_name}/README.md is empty"
        assert (iu_dir / "__init__.py").exists(), \
            f"{kind}/{folder_name} is missing __init__.py"

    def test_class_follows_naming_convention(self, kind, folder_name):
        info = IU_KIND_INFO[kind]
        expected_class_name = f"{folder_name}{info['type_suffix']}"
        expected_file = REPO_ROOT / "Information_Units" / kind / folder_name / f"{expected_class_name}.py"
        assert expected_file.exists(), (
            f"Expected {expected_class_name}.py in Information_Units/{kind}/{folder_name} "
            f"(class name must be {{FolderName}}{info['type_suffix']})"
        )

    def test_registered_in_metadata(self, kind, folder_name):
        entries = _metadata_entries_for(kind, folder_name)
        assert len(entries) == 1, (
            f"Information_Units/{kind}/{folder_name} must have exactly one entry in "
            f"devtools/metadata.json (found {len(entries)})"
        )
        info = IU_KIND_INFO[kind]
        expected_class_name = f"{folder_name}{info['type_suffix']}"
        assert entries[0]["class_name"] == expected_class_name

    def test_implements_required_interface(self, kind, folder_name):
        info = IU_KIND_INFO[kind]
        class_name = f"{folder_name}{info['type_suffix']}"
        file_path = REPO_ROOT / "Information_Units" / kind / folder_name / f"{class_name}.py"
        if not file_path.exists():
            pytest.skip(f"{class_name}.py not found; covered by naming convention test")

        class_node = _find_class_node(file_path, class_name)
        assert class_node is not None, f"Could not find class {class_name} in {file_path}"

        search_root = REPO_ROOT / "Information_Units" / kind
        assert _inherits_from(class_node, info["base_class"], search_root), (
            f"{class_name} must subclass {info['base_class']} (directly or via an "
            f"intermediate base) per iu-data-contracts.md"
        )

        action_method = info["action_method"]
        method_node = _own_method_node(class_node, action_method)
        assert method_node is not None, \
            f"{class_name} must override {action_method}() per iu-data-contracts.md"

        first_param = _first_param_name(method_node)
        assert first_param == info["action_param"], (
            f"{class_name}.{action_method}() first parameter must be named "
            f"'{info['action_param']}' per iu-data-contracts.md, got '{first_param}'"
        )


# ---------------------------------------------------------------------------
# Feature compliance
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize("category,folder_name", _discover_features())
class TestFeatureContributionStandards:
    def test_folder_has_readme_and_init(self, category, folder_name):
        feature_dir = REPO_ROOT / "Features" / category / folder_name
        readme = feature_dir / "README.md"
        assert readme.exists(), f"Features/{category}/{folder_name} is missing a README.md"
        assert readme.stat().st_size > 0, f"Features/{category}/{folder_name}/README.md is empty"
        assert (feature_dir / "__init__.py").exists(), \
            f"Features/{category}/{folder_name} is missing __init__.py"

    def test_class_follows_naming_convention(self, category, folder_name):
        expected_class_name = f"{folder_name}Feature"
        expected_file = REPO_ROOT / "Features" / category / folder_name / f"{expected_class_name}.py"
        assert expected_file.exists(), (
            f"Expected {expected_class_name}.py in Features/{category}/{folder_name} "
            f"(class name must be {{FolderName}}Feature)"
        )

    def test_registered_in_metadata(self, category, folder_name):
        entries = _metadata_entries_for_feature(category, folder_name)
        assert len(entries) == 1, (
            f"Features/{category}/{folder_name} must have exactly one entry in "
            f"devtools/metadata.json (found {len(entries)})"
        )
        expected_class_name = f"{folder_name}Feature"
        assert entries[0]["class_name"] == expected_class_name

    def test_implements_base_feature_interface(self, category, folder_name):
        class_name = f"{folder_name}Feature"
        file_path = REPO_ROOT / "Features" / category / folder_name / f"{class_name}.py"
        if not file_path.exists():
            pytest.skip(f"{class_name}.py not found; covered by naming convention test")

        class_node = _find_class_node(file_path, class_name)
        assert class_node is not None, f"Could not find class {class_name} in {file_path}"

        assert "BaseFeature" in _base_class_names(class_node), \
            f"{class_name} must subclass BaseFeature"

        for method in FEATURE_ABSTRACT_METHODS:
            assert _own_method_node(class_node, method) is not None, \
                f"{class_name} must override the abstract '{method}' method"
