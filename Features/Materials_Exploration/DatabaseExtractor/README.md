# Database Extractor Feature

## Overview

Extract and filter material data from multiple databases with aggregation and export capabilities in various formats.

## Inputs

- `databases` (list): Database sources ('materials_project', 'jarvis', 'oqmd', etc.)
- `composition` (string): Chemical composition filter
- `property_filters` (dict): Property ranges (e.g., {'bandgap_min': 1.0, 'bandgap_max': 3.0})
- `export_format` (string): Output format ('csv', 'json', 'cif', 'xlsx')
- `max_results` (int): Maximum number of results to return

## Outputs

- `data` (DataFrame/dict): Extracted and filtered material data
- `export_file` (string): Path to exported file
- `material_count` (int): Number of materials extracted
- `properties_available` (list): Properties included in export
- `summary_statistics` (dict): Basic statistics on extracted data
