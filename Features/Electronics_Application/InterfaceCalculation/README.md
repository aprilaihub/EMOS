# Interface Calculation

Calculate and analyze interfaces between different materials in electronic applications

## Overview

This feature provides interface calculation functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_process_information_units(inputs)`: Integrates with databases, generators, and predictors


## Input Parameters

- **Material 1**: First material in interface
- **Material 2**: Second material in interface
- **Interface Type**: Type of interface
- **Calculation Method**: Calculation method
- **Supercell Size (atoms)**: Supercell size
- **Include Strain Effects**: Include strain effects
- **Calculate Band Offset**: Calculate band offset

## Output Parameters

- **Interface Energy**: Interface energy
- **Band Offset**: Band offset value
- **Lattice Mismatch**: Lattice mismatch percentage
- **Interface States**: Density of interface states
- **Charge Transfer**: Charge transfer at interface

## Usage

See the base class documentation for detailed usage instructions.

For integration with information units (Databases, Generators, Predictors), 
the feature automatically processes active units and logs their operations.
