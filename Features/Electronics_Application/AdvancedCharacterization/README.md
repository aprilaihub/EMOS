# Advanced Characterization

Advanced characterization techniques for electronic materials evaluation

## Overview

This feature provides advanced characterization functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_process_information_units(inputs)`: Integrates with databases, generators, and predictors


## Input Parameters

- **Characterization Technique**: Characterization technique to use
- **Scan Range**: Measurement scan range parameter
- **Reference Data**: Reference data file for comparison
- **Automatic Analysis**: Enable automatic data analysis

## Output Parameters

- **Characterization Status**: Status of characterization measurement
- **Material Quality**: Assessment of material quality
- **Analysis Report**: Detailed analysis report

## Usage

See the base class documentation for detailed usage instructions.

For integration with information units (Databases, Generators, Predictors), 
the feature automatically processes active units and logs their operations.
