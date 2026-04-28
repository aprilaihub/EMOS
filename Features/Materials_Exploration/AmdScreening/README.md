# AMD screening

Screen uploaded CIF structures for AMD-based candidate selection

## Overview

This feature provides amd screening functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_process_information_units(inputs)`: Integrates with databases, generators, and predictors


## Input Parameters

- **CIF Files**: Browse and upload one or more CIF files for AMD screening

## Output Parameters

- **Download Results (JSON)**: Download JSON file containing AMD screening results

## Usage

See the base class documentation for detailed usage instructions.

For integration with information units (Databases, Generators, Predictors), 
the feature automatically processes active units and logs their operations.
