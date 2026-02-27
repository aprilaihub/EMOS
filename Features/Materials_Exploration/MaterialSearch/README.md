# Material Search

Search and explore materials from comprehensive databases using various criteria

## Overview

This feature provides material search functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_process_information_units(inputs)`: Integrates with databases, generators, and predictors


## Input Parameters

- **Material Name/Formula**: Material name or chemical formula for search
- **Property Type**: Type of material property to search by
- **Minimum Value**: Minimum property value for filtering
- **Maximum Value**: Maximum property value for filtering
- **Include Composite Materials**: Include composite materials in search results

## Output Parameters

- **Materials Found**: Number of materials found matching search criteria
- **Top Match**: Best matching material from search results
- **Property Range**: Range of property values in search results
- **Download**: Download link for complete search results

## Usage

See the base class documentation for detailed usage instructions.

For integration with information units (Databases, Generators, Predictors), 
the feature automatically processes active units and logs their operations.
