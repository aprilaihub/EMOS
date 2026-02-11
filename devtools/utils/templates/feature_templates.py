"""Template generators for Features"""


def generate_inputs_extraction(inputs):
    """Generate extract_inputs method body from metadata inputs"""
    base_lines = [
        "            'feature_input': input_data.get('featureInput', ''),",
        "            'active_databases': input_data.get('active_databases', []),",
        "            'active_generators': input_data.get('active_generators', []),",
        "            'active_predictors': input_data.get('active_predictors', []),",
        "            'search_criteria': input_data.get('search_criteria', ''),",
        "            'target_properties': input_data.get('target_properties', ''),",
        "            'material_property': input_data.get('material_property', ''),",
    ]
    
    if not inputs:
        return "\n".join(base_lines)
    
    lines = []
    for inp in inputs:
        param_name = inp.get('name', '')
        display_name = inp.get('display_name', param_name)
        default = inp.get('default', '')
        
        # Convert to camelCase from display name
        camel_case = ''.join(word.capitalize() if i > 0 else word.lower() 
                            for i, word in enumerate(display_name.split()))
        
        lines.append(f"            '{param_name}': input_data.get('{camel_case}', '{default}'),")

    lines.extend(base_lines)
    return '\n'.join(lines)


def generate_outputs_formatting(outputs):
    """Generate format_outputs method body from metadata outputs"""
    if not outputs:
        return "            'feature_output': 'placeholder output value',"
    
    lines = []
    for out in outputs:
        output_name = out.get('name', '')
        output_type = out.get('type', 'text')
        lines.append(f"            '{output_name}': 'placeholder {output_type} value',")
    
    return '\n'.join(lines)


def generate_js_inputs_html(inputs, class_name):
    """Generate JavaScript input HTML creation calls"""
    if not inputs:
        return "                ${this.createTextInput(`input_${this.featureId}`, 'Feature Input', 'Enter value')}"
    
    lines = []
    for inp in inputs:
        param_name = inp.get('name', '')
        display_name = inp.get('display_name', param_name)
        input_type = inp.get('type', 'text')
        placeholder = inp.get('placeholder', f'Enter {display_name}')
        
        if input_type == 'text':
            lines.append(f"                ${{this.createTextInput(`{param_name}_${{this.featureId}}`, '{display_name}', '{placeholder}')}}")
        elif input_type == 'number':
            min_val = inp.get('min', '0')
            max_val = inp.get('max', '100')
            step = inp.get('step', '1')
            lines.append(f"                ${{this.createNumberInput(`{param_name}_${{this.featureId}}`, '{display_name}', '{min_val}', '{max_val}', '{step}')}}")
        elif input_type == 'select':
            options = inp.get('options', [])
            options_list = ', '.join([f"{{value: '{o.get('value')}', text: '{o.get('text')}'}}" for o in options])
            lines.append(f"                ${{this.createSelectInput(`{param_name}_${{this.featureId}}`, '{display_name}', [{options_list}])}}")
        elif input_type == 'checkbox':
            lines.append(f"                ${{this.createCheckboxInput(`{param_name}_${{this.featureId}}`, '{display_name}', true)}}")
        elif input_type == 'file':
            accept = inp.get('accept', '*')
            lines.append(f"                ${{this.createFileInput(`{param_name}_${{this.featureId}}`, '{display_name}', '{accept}')}}")
    
    return '\n'.join(lines)


def generate_js_outputs_html(outputs, class_name):
    """Generate JavaScript output display HTML"""
    if not outputs:
        return "                <div class=\"output-item\">\n                    <strong>Output:</strong> <span id=\"output_${this.featureId}\">Pending...</span>\n                </div>"
    
    lines = []
    for out in outputs:
        output_name = out.get('name', '')
        display_name = out.get('display_name', output_name)
        lines.append(f"                <div class=\"output-item\">\n                    <strong>{display_name}:</strong> <span id=\"{output_name}_${{this.featureId}}\">Pending...</span>\n                </div>")
    
    return '\n'.join(lines)


def generate_js_outputs_placeholder(outputs):
    """Generate placeholder return values for JavaScript processFeature()"""
    if not outputs:
        return "            'output': 'placeholder value',"
    
    lines = []
    for out in outputs:
        output_name = out.get('name', '')
        display_name = out.get('display_name', output_name)
        lines.append(f"            {output_name}: '{display_name} - placeholder',")
    
    return '\n'.join(lines)


def generate_js_updateOutputs(outputs):
    """Generate updateOutputs method for JavaScript feature class"""
    if not outputs:
        return ""  # Use default BaseFeature implementation
    
    lines = []
    lines.append("    updateOutputs(results = null) {")
    lines.append("        const finalResults = results || this.results;")
    lines.append("        ")
    lines.append("        if (finalResults.error) {")
    
    # Use first output field for error display
    first_output = outputs[0].get('name', 'output')
    lines.append(f"            document.getElementById(`{first_output}_${{this.featureId}}`).textContent = `Error: ${{finalResults.error}}`;")
    lines.append("            return;")
    lines.append("        }")
    lines.append("        ")
    
    # Generate update for each output field
    for out in outputs:
        output_name = out.get('name', '')
        lines.append(f"        if (finalResults.{output_name}) {{")
        lines.append(f"            document.getElementById(`{output_name}_${{this.featureId}}`).textContent = finalResults.{output_name};")
        lines.append("        }")
    
    lines.append("    }")
    
    return '\n'.join(lines)


def _build_inputs_section(inputs):
    """Build inputs documentation section"""
    if not inputs:
        return ""
    
    section = "\n## Input Parameters\n\n"
    for inp in inputs:
        section += f"- **{inp.get('display_name', inp.get('name'))}**: {inp.get('description', 'Parameter description')}\n"
    return section


def _build_outputs_section(outputs):
    """Build outputs documentation section"""
    if not outputs:
        return ""
    
    section = "\n## Output Parameters\n\n"
    for out in outputs:
        section += f"- **{out.get('display_name', out.get('name'))}**: {out.get('description', 'Output description')}\n"
    return section


def generate_feature_readme(metadata):
    """Generate README.md content for features"""
    inputs_section = _build_inputs_section(metadata.get('inputs', []))
    outputs_section = _build_outputs_section(metadata.get('outputs', []))
    
    template = """# {display_name}

{description}

## Overview

This feature provides {display_name_lower} functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_process_information_units(inputs)`: Integrates with databases, generators, and predictors

{inputs_section}{outputs_section}
## Usage

See the base class documentation for detailed usage instructions.

For integration with information units (Databases, Generators, Predictors), 
the feature automatically processes active units and logs their operations.
"""
    
    return template.format(
        display_name=metadata['display_name'],
        description=metadata['description'],
        display_name_lower=metadata['display_name'].lower(),
        inputs_section=inputs_section,
        outputs_section=outputs_section
    )


def generate_feature_python_class(metadata, category, inputs_extraction, outputs_formatting):
    """Generate Python feature class file content from template"""
    template = """from Features.BaseFeature import BaseFeature
from Information_Units.Generators.GeneratorFactory import generator_factory
from Information_Units.Databases.DatabaseFactory import database_factory
from Information_Units.Predictors.PredictorFactory import predictor_factory


class {class_name}(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("{feature_name}", logger)
    
    def info(self):
        return "{feature_name}: {description}"
    
    def extract_inputs(self, input_data):
        return {{
{inputs_extraction}
        }}
    
    def process_feature(self, inputs):
        if self.logger:
            self.logger.log('Initializing {feature_name}...', 'info')
        
        # Process information units (databases, generators, predictors)
        self._process_information_units(inputs)
        
        if self.logger:
            self.logger.log('{feature_name} processing completed', 'info')
        
        return {{
            'status': 'completed',
            'message': '{feature_name} feature executed successfully'
        }}
    
    def format_outputs(self, results):
        return {{
{outputs_formatting}
        }}
    
    def _process_information_units(self, inputs):
        \"\"\"Process active databases, generators, and predictors with proper logging\"\"\"
        # Process databases
        active_databases = inputs.get('active_databases', [])
        if not active_databases:
            if self.logger:
                self.logger.log('No active databases found.', 'warning')
        else:
            if self.logger:
                database_names = ', '.join(db["name"] for db in active_databases)
                self.logger.log(f'Active databases ({{len(active_databases)}}): {{database_names}}', 'info')
            
            for dtbs in active_databases:
                db_key = dtbs['value']
                if db_key in database_factory:
                    db_instance = database_factory[db_key](db_key, self.logger)
                    if self.logger:
                        self.logger.log(db_instance.info(), 'info')
                    retrieve_inputs = {{'search_criteria': inputs.get('search_criteria', '')}}
                    try:
                        db_instance.retrieve(retrieve_inputs)
                    except Exception as e:
                        if self.logger:
                            self.logger.log(f'Database {{db_key}} retrieve() error: {{str(e)}}', 'warning')
        
        # Process generators
        active_generators = inputs.get('active_generators', [])
        if not active_generators:
            if self.logger:
                self.logger.log('No active generators found.', 'warning')
        else:
            if self.logger:
                generator_names = ', '.join(gen["name"] for gen in active_generators)
                self.logger.log(f'Active generators ({{len(active_generators)}}): {{generator_names}}', 'info')
            
            for gnrtr in active_generators:
                gen_key = gnrtr['value']
                if gen_key in generator_factory:
                    gen_instance = generator_factory[gen_key](gen_key, self.logger)
                    if self.logger:
                        self.logger.log(gen_instance.info(), 'info')
                    generate_inputs = {{'target_properties': inputs.get('target_properties', '')}}
                    try:
                        gen_instance.generate(generate_inputs)
                    except Exception as e:
                        if self.logger:
                            self.logger.log(f'Generator {{gen_key}} generate() error: {{str(e)}}', 'warning')
        
        # Process predictors
        active_predictors = inputs.get('active_predictors', [])
        if not active_predictors:
            if self.logger:
                self.logger.log('No active predictors found.', 'warning')
        else:
            if self.logger:
                predictor_names = ', '.join(pred["name"] for pred in active_predictors)
                self.logger.log(f'Active predictors ({{len(active_predictors)}}): {{predictor_names}}', 'info')
            
            for prdctr in active_predictors:
                pred_key = prdctr['value']
                if pred_key in predictor_factory:
                    pred_instance = predictor_factory[pred_key](pred_key, self.logger)
                    if self.logger:
                        self.logger.log(pred_instance.info(), 'info')
                    predict_inputs = {{'material_property': inputs.get('material_property', '')}}
                    try:
                        pred_instance.predict(predict_inputs)
                    except Exception as e:
                        if self.logger:
                            self.logger.log(f'Predictor {{pred_key}} predict() error: {{str(e)}}', 'warning')
"""
    
    return template.format(
        class_name=metadata['class_name'],
        feature_name=metadata['display_name'],
        description=metadata['description'],
        inputs_extraction=inputs_extraction,
        outputs_formatting=outputs_formatting
    )


def generate_feature_javascript_file(metadata, category, inputs_html, outputs_html, outputs_placeholder, updateOutputs_method):
    """Generate JavaScript feature class file content from template"""
    class_name = metadata['class_name'].replace('Feature', '')
    feature_name = metadata['display_name']
    description = metadata['description']
    
    # Build the class with optional updateOutputs method
    updateOutputs_section = f"\n\n{updateOutputs_method}" if updateOutputs_method else ""
    
    template = """// {feature_name} Feature
class {class_name}Feature extends BaseFeature {{
    constructor(featureId) {{
        super(featureId, '{feature_name}', '{description}');
    }}

    createInputsHTML() {{
        return `
            <p>Configure input parameters for {feature_name}</p>
            <div class="input-controls">
{inputs_html}
            </div>
        `;
    }}

    createOutputsHTML() {{
        return `
            <p>{feature_name} results and outputs</p>
            <div class="output-display" id="outputDisplay_${{this.featureId}}">
{outputs_html}
            </div>
        `;
    }}

    async processFeature() {{
        // Placeholder processing logic for {feature_name}
        return {{
{outputs_placeholder}
        }};
    }}{updateOutputs_section}
}}

window.{class_name}Feature = {class_name}Feature;
"""
    
    return template.format(
        class_name=class_name,
        feature_name=feature_name,
        description=description,
        inputs_html=inputs_html,
        outputs_html=outputs_html,
        outputs_placeholder=outputs_placeholder,
        updateOutputs_section=updateOutputs_section
    )
