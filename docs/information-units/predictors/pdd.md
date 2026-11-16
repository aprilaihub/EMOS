# PDD

**Type:** Predictor  
**ID:** `pdd`  
**Implementation:** `Information_Units/Predictors/Pdd/PddPredictor.py`

Computes pointwise distance distribution descriptors for crystal structures.

## Inputs

- `input_data: list[str]` containing CIF strings
- `k: int` (default: `100`)

## Outputs

- `source: "pdd"`
- `results: list[dict]`
- Each result includes `index`, `cif_input`, `status`, `warnings`, `error`, `pdd_vector`, and `pdd_matrix`
- `pdd_vector` is the AMD (weighted mean of the PDD distance columns), shape `(k,)`
- `pdd_matrix` has shape `(rows, k + 1)`; column 0 holds the row weights

## Duplicate screening

`PddPredictor.screen(config)` runs a two-stage screen over folders of CIFs: AMD distances on every structure find candidate pairs within `tau`, and PDD Earth Mover's Distance confirms only those pairs. It writes vectors, a t-SNE embedding, a dendrogram, a heatmap and `run_info.json` to a timestamped run directory. See the [PDD README](../../../Information_Units/Predictors/Pdd/README.md) for parameters and guarantees, and the [PDD similarity tutorial](../../tutorials/tutorial_pdd_similarity.md) (also as an [executed notebook](../../tutorials/tutorial_pdd_similarity.ipynb)) for a reproducible walkthrough.
