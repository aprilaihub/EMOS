# Tensor Analysis

Comprehensive analysis tools for understanding material structure-property relationships

## Overview

This feature provides tensor analysis functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_process_information_units(inputs)`: Integrates with databases, generators, and predictors


## Input Parameters

- **Sample ID**: Sample identifier
- **Characterization Type**: Type of characterization
- **Resolution (nm)**: Resolution for analysis
- **Sample Data File**: Sample data file for analysis

## Output Parameters

- **Analysis Status**: Analysis completion status
- **Structure-Property Correlation**: Structure-property correlation value
- **Visualization Data**: Visualization data availability

## Usage

See the base class documentation for detailed usage instructions.

For integration with information units (Databases, Generators, Predictors), 
the feature automatically processes active units and logs their operations.
