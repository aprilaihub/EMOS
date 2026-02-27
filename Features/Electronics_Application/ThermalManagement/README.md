# Thermal Management

Thermal management analysis for electronic device performance optimization

## Overview

This feature provides thermal management functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_process_information_units(inputs)`: Integrates with databases, generators, and predictors


## Input Parameters

- **Thermal Property**: Thermal property to analyze
- **Operating Power (W)**: Operating power
- **Ambient Temperature (°C)**: Ambient temperature
- **Include Convection**: Include convection effects

## Output Parameters

- **Optimization Status**: Thermal optimization status
- **Maximum Temperature**: Maximum temperature reached
- **Cooling Solution**: Recommended cooling solution

## Usage

See the base class documentation for detailed usage instructions.

For integration with information units (Databases, Generators, Predictors), 
the feature automatically processes active units and logs their operations.
