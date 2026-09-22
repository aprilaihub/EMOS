# CIF similarity

**Type:** Feature  
**ID:** `3`  
**Implementation:** `Features/Materials_Exploration/CifSimilarity/CifSimilarityFeature.py`

Compares uploaded crystal structures using supported distance metrics.

## Inputs

- `cif_strings: list[str]`
- `labels: list[str]` (optional)
- `distanceMetric: str`: `amd` or `pdd_emd`
- `k: int` (default: `100`, range: `1` to `500`)

## Outputs

- `status: str` and `message: str`
- `labels: list[str]`
- `distance_matrix: list[list[float]]`
- `k: int`, `distance_metric: str`, and `failed: list[str]`
