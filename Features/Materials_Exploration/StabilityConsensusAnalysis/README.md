# Stability Consensus Analysis

Analyze and aggregate stability consensus from uploaded CIF structures

## Overview

This feature provides stability consensus analysis functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_process_information_units(inputs)`: Integrates with databases, generators, and predictors


## Input Parameters

- **CIF Files**: Browse and upload one or more CIF files for stability consensus analysis

## Output Parameters

- **Download Results (JSON)**: Download JSON file containing stability consensus analysis results

## Usage

See the base class documentation for detailed usage instructions.

For integration with information units (Databases, Generators, Predictors), 
the feature automatically processes active units and logs their operations.
