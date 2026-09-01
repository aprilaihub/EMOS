# CIF similarity

Compare uploaded crystal structures using AMD or PDD Earth Mover's Distance

## Overview

This feature provides cif similarity functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format


## Input Parameters

- **CIF Files**: Upload two or more CIF files for similarity comparison
- **Distance Metric**: Select the metric used to calculate the pairwise distance matrix
- **Neighbourhood size k**: Number of nearest neighbours used for the descriptor calculation

## Output Parameters

- **Distance Matrix**: Pairwise distance matrix calculated using the selected metric

## Usage

See the base class documentation for detailed usage instructions.

If this feature needs information units (Databases, Generators, or Predictors),
add a feature-local selector and instantiate only the selected factory entries.
