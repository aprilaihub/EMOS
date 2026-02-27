# Property Prediction

Electronic property prediction and optimization for semiconductor applications

## Overview

This feature provides property prediction functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_process_information_units(inputs)`: Integrates with databases, generators, and predictors


## Input Parameters

- **Material System**: Material system for prediction
- **Property to Predict**: Property to predict
- **Temperature (K)**: Temperature for prediction
- **Include Defects**: Include defect effects

## Output Parameters

- **Prediction Status**: Status of prediction
- **Band Gap**: Predicted band gap
- **Carrier Mobility**: Predicted carrier mobility

## Usage

See the base class documentation for detailed usage instructions.

For integration with information units (Databases, Generators, Predictors), 
the feature automatically processes active units and logs their operations.
