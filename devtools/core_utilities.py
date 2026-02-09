"""
EMOS Core Utilities
Converts core_metadata.json to full metadata.json

Display names are the source of truth - everything else is derived automatically.
"""
import re
import json

def display_name_to_folder_name(display_name):
    """Convert display name to PascalCase folder name"""
    # Remove special chars, PascalCase
    name = re.sub(r'[^\w\s]', '', display_name)
    words = [word.capitalize() for word in name.split()]
    return ''.join(words)

def display_name_to_id(display_name):
    """Convert display name to snake_case ID"""
    # Convert to snake_case
    name = re.sub(r'[^\w\s]', '_', display_name.lower())
    name = re.sub(r'[\s_]+', '_', name)
    return name.strip('_')

def display_name_to_class_name(display_name, component_type):
    """Convert display name to ClassName"""
    folder_name = display_name_to_folder_name(display_name)
    type_suffix = component_type.capitalize()
    return f"{folder_name}{type_suffix}"

def display_name_to_file_name(display_name, component_type, file_type="py"):
    """Convert display name to file name"""
    class_name = display_name_to_class_name(display_name, component_type)
    return f"{class_name}.{file_type}"

def generate_information_unit_metadata(display_name, unit_type, description):
    """Generate complete metadata for an information unit"""
    return {
        "id": display_name_to_id(display_name),
        "name": display_name_to_folder_name(display_name), 
        "display_name": display_name,
        "description": description,
        "folder_path": f"Information_Units/{unit_type.title()}s/{display_name_to_folder_name(display_name)}",
        "class_name": display_name_to_class_name(display_name, unit_type),
        "file_name": display_name_to_file_name(display_name, unit_type)
    }

def generate_feature_metadata(display_name, category, description, core_meta=None):
    """Generate complete metadata for a feature"""
    category_map = {
        "materials_exploration": "Materials_Exploration",
        "electronics_application": "Electronics_Application"
    }
    
    # Generate numeric ID from order in category
    feature_id = 1
    if core_meta and "features" in core_meta:
        category_features = list(core_meta["features"][category].keys())
        try:
            feature_id = category_features.index(display_name) + 1
            if category == "electronics_application":
                materials_count = len(core_meta["features"].get("materials_exploration", []))
                feature_id += materials_count
        except ValueError:
            pass
    
    folder_name = display_name_to_folder_name(display_name)
    
    return {
        "id": feature_id,
        "name": display_name,
        "display_name": display_name,
        "description": description,
        "folder_path": f"Features/{category_map[category]}/{folder_name}",
        "class_name": display_name_to_class_name(display_name, "feature"), 
        "file_name": display_name_to_file_name(display_name, "feature"),
        "js_file_name": f"{folder_name}.js"
    }

def generate_metadata_from_core(core_metadata_path="core_metadata.json", output_path="metadata.json"):
    """
    Main function: Convert core_metadata.json to full metadata.json
    
    Args:
        core_metadata_path: Path to the core metadata file
        output_path: Path where the full metadata will be saved
    
    Returns:
        dict: The expanded metadata dictionary
    """
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    core_metadata_path = os.path.join(script_dir, core_metadata_path)
    output_path = os.path.join(script_dir, output_path)
    
    with open(core_metadata_path, 'r') as f:
        core = json.load(f)
    
    # Create full metadata structure
    metadata = {
        "version": "1.0.0",
        "last_updated": "2024-11-07", 
        "description": "Auto-generated from core metadata using display-name derivation",
        "information_units": {
            "databases": [],
            "generators": [], 
            "predictors": []
        },
        "features": {
            "materials_exploration": [],
            "electronics_application": []
        },
        "ui_input_types": {
            "text": {"description": "Single line text input", "html_element": "input", "attributes": ["type='text'", "placeholder", "required"]},
            "number": {"description": "Numeric input with min/max/step", "html_element": "input", "attributes": ["type='number'", "min", "max", "step", "required"]},
            "select": {"description": "Dropdown selection with options", "html_element": "select", "attributes": ["required"], "children": "option"},
            "checkbox": {"description": "Boolean checkbox input", "html_element": "input", "attributes": ["type='checkbox'", "checked"]},
            "file": {"description": "File upload input", "html_element": "input", "attributes": ["type='file'", "accept", "multiple"]},
            "textarea": {"description": "Multi-line text input", "html_element": "textarea", "attributes": ["rows", "cols", "placeholder", "required"]},
            "range": {"description": "Slider input for numeric range", "html_element": "input", "attributes": ["type='range'", "min", "max", "step", "value"]}
        },
        "ui_output_types": {
            "text": {"description": "Simple text display", "html_element": "span", "attributes": []},
            "number": {"description": "Numeric value display", "html_element": "span", "attributes": []},
            "table": {"description": "Tabular data display", "html_element": "table", "attributes": ["border", "cellpadding", "cellspacing"]},
            "link": {"description": "Clickable download/external link", "html_element": "a", "attributes": ["href", "target", "download"]},
            "file": {"description": "File download link or viewer", "html_element": "a", "attributes": ["href", "download"]},
            "image": {"description": "Image display", "html_element": "img", "attributes": ["src", "alt", "width", "height"]}
        },
        "code_templates": {
            "information_units": {
                "database": {"base_class": "BaseDatabase", "methods": ["__init__", "info", "retrieve"], "imports": ["from Information_Units.Databases.BaseDatabase import BaseDatabase"]},
                "generator": {"base_class": "BaseGenerator", "methods": ["__init__", "info", "generate"], "imports": ["from Information_Units.Generators.BaseGenerator import BaseGenerator"]},
                "predictor": {"base_class": "BasePredictor", "methods": ["__init__", "info", "predict"], "imports": ["from Information_Units.Predictors.BasePredictor import BasePredictor"]}
            },
            "features": {
                "base_class": "BaseFeature", 
                "methods": ["__init__", "info", "extract_inputs", "process_feature", "format_outputs", "_process_information_units"],
                "imports": ["from Features.BaseFeature import BaseFeature", "from Information_Units.Generators.GeneratorFactory import generator_factory", "from Information_Units.Databases.DatabaseFactory import database_factory", "from Information_Units.Predictors.PredictorFactory import predictor_factory"]
            }
        }
    }
    
    # Generate information units from display names
    for unit_type in ["databases", "generators", "predictors"]:
        for display_name, description in core["information_units"][unit_type].items():
            unit_metadata = generate_information_unit_metadata(display_name, unit_type[:-1], description)
            metadata["information_units"][unit_type].append(unit_metadata)
    
    # Generate features from display names
    for category in ["materials_exploration", "electronics_application"]:
        for display_name, description in core["features"][category].items():
            feature_metadata = generate_feature_metadata(display_name, category, description, core)
            # Add input/output definitions if they exist
            if display_name in core.get("feature_inputs_outputs", {}):
                feature_metadata["inputs"] = core["feature_inputs_outputs"][display_name]["inputs"]
                feature_metadata["outputs"] = core["feature_inputs_outputs"][display_name]["outputs"]
            metadata["features"][category].append(feature_metadata)
    
    # Save the generated metadata
    with open(output_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Generated {output_path} from {core_metadata_path}")
    print(f"   - {len(metadata['information_units']['databases'])} databases")
    print(f"   - {len(metadata['information_units']['generators'])} generators") 
    print(f"   - {len(metadata['information_units']['predictors'])} predictors")
    print(f"   - {len(metadata['features']['materials_exploration'])} materials features")
    print(f"   - {len(metadata['features']['electronics_application'])} electronics features")
    
    return metadata

# Main execution
if __name__ == "__main__":
    generate_metadata_from_core()