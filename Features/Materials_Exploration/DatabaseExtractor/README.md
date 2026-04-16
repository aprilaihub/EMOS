# Database Extractor

Extract and analyze specific material properties and data from integrated databases

## Overview

This feature retrieves batched data from selected databases using canonical
property keys defined in `Information_Units/property_mappings/common_properties.json`.

It supports two retrieval modes:

- `strict`: query only databases that can retrieve all selected properties
- `lenient`: query all selected databases and ignore non-queryable properties

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_run_database_extraction(inputs)`: Executes strict/lenient extraction per selected database


## Input Parameters

- **selectedProperties / selected_properties**: Property keys to query
- **batchSize / batch_size**: Number of records to retrieve per database
- **retrievalMode / retrieval_mode**: `strict` or `lenient`
- **queryValues / query_values**: Optional property filters (`dict` or JSON string)
- **targetCompositions / target_compositions**: Optional composition query
- **active_databases**: Selected database IU entries (`[{"value": "materialsproject", ...}]`)

## Output Parameters

- **recordsExtracted**: Total number of extracted CIF records
- **databaseCount**: Number of databases queried
- **skippedDatabaseCount**: Number of databases skipped (strict mode or unavailable)
- **downloadPackage**: JSON payload availability message
- **extraction**: Full structured extraction payload with per-database details:
	- `properties_requested`, `properties_used`, `properties_skipped`
	- source field mapping (`source_fields_used`)
	- database payload and record count

## Usage

### Example Request

```json
{
	"selectedProperties": ["band_gap", "formation_energy_r2scan"],
	"batchSize": 50,
	"retrievalMode": "lenient",
	"queryValues": {
		"band_gap": [1.0, 3.0]
	},
	"active_databases": [
		{"value": "materialsproject", "name": "Materials Project"},
		{"value": "aflow", "name": "AFLOW"}
	]
}
```

### Notes

- The extractor uses `property_loader.py` to resolve per-database property mappings.
- Warning and skip reasons are emitted through processing logs.
