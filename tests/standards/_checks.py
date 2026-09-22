"""Shared static-inspection helpers for contribution standards tests."""

import ast
import json
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.parent

with (REPO_ROOT / "devtools" / "metadata.json").open(encoding="utf-8") as metadata_file:
    METADATA = json.load(metadata_file)


IU_KIND_INFO = {
    "Databases": {"type_suffix": "Database", "base_class": "BaseDatabase", "action_method": "retrieve", "action_param": "inputs", "metadata_key": "databases"},
    "Generators": {"type_suffix": "Generator", "base_class": "BaseGenerator", "action_method": "generate", "action_param": "inputs", "metadata_key": "generators"},
    "Predictors": {"type_suffix": "Predictor", "base_class": "BasePredictor", "action_method": "predict", "action_param": "input_data", "metadata_key": "predictors"},
}
FEATURE_ABSTRACT_METHODS = ("info", "extract_inputs", "process_feature", "format_outputs")


def discover_iu_contributions():
    contributions = []
    for kind in IU_KIND_INFO:
        kind_dir = REPO_ROOT / "Information_Units" / kind
        if kind_dir.exists():
            contributions.extend(
                (kind, item.name)
                for item in kind_dir.iterdir()
                if item.is_dir() and not item.name.startswith(("_", "."))
            )
    return sorted(contributions)


def discover_feature_contributions():
    contributions = []
    for category_dir in (REPO_ROOT / "Features").iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("_"):
            continue
        if category_dir.name.lower() not in METADATA.get("features", {}):
            continue
        contributions.extend(
            (category_dir.name, item.name)
            for item in category_dir.iterdir()
            if item.is_dir() and not item.name.startswith("_")
        )
    return sorted(contributions)


def iu_class_name(kind, folder_name):
    return f"{folder_name}{IU_KIND_INFO[kind]['type_suffix']}"


def iu_directory(kind, folder_name):
    return REPO_ROOT / "Information_Units" / kind / folder_name


def feature_class_name(folder_name):
    return f"{folder_name}Feature"


def feature_directory(category, folder_name):
    return REPO_ROOT / "Features" / category / folder_name


def metadata_entries_for_iu(kind, folder_name):
    entries = METADATA.get("information_units", {}).get(IU_KIND_INFO[kind]["metadata_key"], [])
    expected_path = f"Information_Units/{kind}/{folder_name}"
    return [entry for entry in entries if entry.get("folder_path") == expected_path]


def metadata_entries_for_feature(category, folder_name):
    entries = METADATA.get("features", {}).get(category.lower(), [])
    expected_path = f"Features/{category}/{folder_name}"
    return [entry for entry in entries if entry.get("folder_path") == expected_path]


def find_class_node(file_path, class_name):
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def find_class_node_anywhere(search_root, class_name):
    for py_file in search_root.rglob("*.py"):
        try:
            class_node = find_class_node(py_file, class_name)
        except SyntaxError:
            continue
        if class_node is not None:
            return class_node
    return None


def base_class_names(class_node):
    names = []
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def inherits_from(class_node, target_base, search_root, visited=None):
    visited = visited if visited is not None else set()
    if class_node.name in visited:
        return False
    visited.add(class_node.name)

    bases = base_class_names(class_node)
    if target_base in bases:
        return True
    for base in bases:
        base_node = find_class_node_anywhere(search_root, base)
        if base_node is not None and inherits_from(base_node, target_base, search_root, visited):
            return True
    return False


def own_method_node(class_node, method_name):
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
            return node
    return None


def first_parameter_name(function_node):
    parameters = [parameter.arg for parameter in function_node.args.args if parameter.arg != "self"]
    return parameters[0] if parameters else None