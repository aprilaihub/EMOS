# Database Extractor

Extract and analyze specific material properties and data from integrated databases

## Overview

This feature provides database extractor functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_process_information_units(inputs)`: Integrates with databases, generators, and predictors


## Input Parameters

- **Database Source**: Database source for extraction
- **Extraction Type**: Type of data to extract
- **Filter Criteria**: Filter criteria for extraction
- **Maximum Entries**: Maximum number of entries to extract
- **Configuration File**: Optional configuration file
- **Include Metadata**: Include metadata in extraction

## Output Parameters

- **Records Extracted**: Number of records extracted
- **Data Size**: Total size of extracted data
- **File Format**: Format of extracted data
- **Processing Time**: Time taken for extraction
- **Download Package**: Download extracted data package

## Usage

See the base class documentation for detailed usage instructions.

For integration with information units (Databases, Generators, Predictors), 
the feature automatically processes active units and logs their operations.
