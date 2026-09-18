# Stability Consensus Analysis

**Type:** Feature  
**ID:** `2`  
**Implementation:** `Features/Materials_Exploration/StabilityConsensusAnalysis/StabilityConsensusAnalysisFeature.py`

Analyzes stability information from uploaded CIF structures and selected services.

## Inputs

- `cif_file: str` or `cif_files: list[str | dict]`
- `active_databases: list[dict]`
- `active_predictors: list[dict]`

## Outputs

- `composition: str | None`
- `sources: dict`, `summary: dict`, and `results_per_cif: list[dict]`
- `batch_summary: dict`
- `downloadResultsJson: str`
