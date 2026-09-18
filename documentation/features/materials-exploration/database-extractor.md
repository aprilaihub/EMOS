# Database Extractor

**Type:** Feature  
**ID:** `1`  
**Implementation:** `Features/Materials_Exploration/DatabaseExtractor/DatabaseExtractorFeature.py`

Extracts and analyzes material data from selected databases.

## Inputs

- `selected_properties: list[str]`
- `batch_size: int` (default: `100`)
- `retrieval_mode: str`: `strict` or `lenient`
- `query_values: dict`
- `target_compositions: str`
- `active_databases: list[str | dict]`

## Outputs

- `status: str` and `message: str`
- `recordsExtracted: int`, `dataSize: str`, `fileFormat: "json"`, and `processingTime: str`
- `downloadPackage: str`, `databaseCount: int`, `skippedDatabaseCount: int`, and `extraction: dict`
