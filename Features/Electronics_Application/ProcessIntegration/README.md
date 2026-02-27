# Process Integration

Process integration workflows for electronic device manufacturing

## Overview

This feature provides process integration functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_process_information_units(inputs)`: Integrates with databases, generators, and predictors


## Input Parameters

- **Process Step**: Process step
- **Process Temperature (°C)**: Process temperature
- **Gas Flow Rates**: Gas flow rates
- **In-situ Monitoring**: Enable in-situ monitoring

## Output Parameters

- **Integration Status**: Process integration status
- **Yield Prediction**: Predicted manufacturing yield
- **Recipe Parameters**: Process recipe parameters

## Usage

See the base class documentation for detailed usage instructions.

For integration with information units (Databases, Generators, Predictors), 
the feature automatically processes active units and logs their operations.
