# PDD Predictor

Computes Pointwise Distance Distribution (PDD) descriptors for crystal structures using the [average-minimum-distance](https://github.com/dwiddo/average-minimum-distance) package.

## Overview

**PDD** is a geometric descriptor predictor: given one or more CIF structures, it computes a PDD matrix (and derived AMD vector) per structure, plus an Earth-Mover's-Distance comparison matrix when multiple structures are supplied.

- **Input**: `list[str]` of CIF text strings (EMOS standard contract)
- **Output**: `dict` with `source` and `results` keys, each result carrying `pdd_vector` and `pdd_matrix`
- **Parameters**: `k` — neighbourhood size for descriptor calculation (default 100)

## Usage

```python
from Information_Units.Predictors.Pdd.PddPredictor import PddPredictor

predictor = PddPredictor(predictor_name="pdd", k=100)
output = predictor.predict([cif_string_1, cif_string_2])

for result in output["results"]:
    if result["status"] == "ok":
        print(result["properties"]["pdd_vector"])
```

## Output Format

Follows the standard predictor contract (see [docs/tutorials/iu-data-contracts.md](../../../docs/tutorials/iu-data-contracts.md)):

```python
{
    "source": "pdd",
    "results": [
        {
            "index": 0,
            "status": "ok",
            "properties": {"pdd_vector": [...], "pdd_matrix": [[...]]},
            "warnings": [],
            "error": None,
            "cif_input": "..."
        }
    ]
}
```
