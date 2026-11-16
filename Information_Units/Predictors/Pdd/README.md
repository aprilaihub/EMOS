# PDD Predictor

Computes Pointwise Distance Distribution (PDD) descriptors for crystal structures using the [average-minimum-distance](https://github.com/dwiddo/average-minimum-distance) package, and screens folders of CIFs for duplicates with a two-stage **AMD screen -> PDD confirm** pipeline.

## Overview

**PDD** is a geometric descriptor predictor: given one or more CIF structures, it computes a PDD matrix and the derived AMD vector per structure.

- **Input**: `list[str]` of CIF text strings (EMOS standard contract)
- **Output**: `dict` with `source` and `results` keys, each result carrying `pdd_vector` and `pdd_matrix`
- **Parameters**: `k` — neighbourhood size for descriptor calculation (default 100)

PDD layout: `(rows, k + 1)`. Column 0 holds the row weights (they sum to 1); columns 1..k hold the sorted neighbour distances. `pdd_vector` is the AMD: the weighted mean of the distance columns, shape `(k,)`.

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

## Duplicate screening (`similarity/`)

`PddPredictor.screen(config)` (or the CLI) finds duplicate structures in one or more CIF folders.

1. **Descriptors** — PDD once per structure at `k_max`; AMD is the weighted mean of PDD rows (AMD at `k` = first `k` entries).
2. **Stage 1, AMD on every structure** — pairs with AMD distance `<= tau` at `k_amd` are candidates. Connected components of the candidate graph are formed; singletons are unique and need no PDD. Structures in components of size `>= 2` form the *reduced subset*.
3. **Stage 2, PDD on candidate pairs only** — EMD at `k_pdd` with the same metric. The final distance is the AMD distance where it exceeds `tau` and the PDD EMD otherwise (valid because AMD is a lower bound on EMD). Each component is clustered and cut at `tau`; the representative of each group is its medoid (ties: source priority, then ID).

```python
from Information_Units.Predictors.Pdd.similarity import SimilarityConfig, run_similarity_pipeline

config = SimilarityConfig(
    input_dirs=["tests/fixtures/cif_files/mp", "tests/fixtures/cif_files/cod"],
    composition_filter=["ZnO"],   # optional
    k_amd=15, k_pdd=30, k_max=100, tau=0.1,
    metric="euclidean", linkage="complete",
)
result = run_similarity_pipeline(config, verbose=True)
```

```bash
python -m Information_Units.Predictors.Pdd.similarity --config my_config.json
python -m Information_Units.Predictors.Pdd.similarity --input-dir cifs/mp --tau 0.05 --k-amd 10 --k-pdd 20
```

### Parameters (validated)

| Parameter | Default | Rule |
|---|---|---|
| `k_amd` | 15 | neighbours for the AMD screen |
| `k_pdd` | 30 | `>= k_amd`, otherwise the lower-bound guarantee fails |
| `k_max` | 100 | `>= k_pdd` |
| `k_tsne` | `k_pdd` | `<= k_max` |
| `tau` | 0.1 Å | `>= 0` |
| `metric` | `euclidean` | `euclidean`, `cityblock` or `chebyshev`; used for both the AMD distances and the EMD ground metric. `cosine` and `correlation` are rejected (not norms, so AMD ≤ EMD does not hold) |
| `linkage` | `complete` | `complete`, `single`, `average`, `ward` (`ward` only with `euclidean`) |
| `input_dirs`, `source_prefixes`, `source_priority` | | input folders; file-name prefix → source label; representative tie-break order |
| `composition_filter` | `None` | reduced formulas to keep, e.g. `["ZnO"]` |
| `disordered` | `warn` | `warn` or `skip` structures with partial occupancy |
| `min_nn_dist` | 0.5 Å | structures with a shorter nearest-neighbour distance are skipped |
| `plot_pdd_subset`, `highlight`, `font_family`, `max_tick_labels` | | figure options (figures are saved, never shown) |

### Guarantee

With `complete` linkage every pair in a group is within `tau`; `single` gives chains of pairs within `tau`. For these two linkages the screened groups are identical to grouping with full pairwise PDD (verified in `tests/integration/test_pdd_similarity_pipeline.py` for all three metrics). `average` and `ward` depend on distance values, so the screen is then an approximation and a warning is recorded.

### Limitations

- AMD and PDD use **positions only**. A structure and a species-swapped copy have distance 0. Use `composition_filter` (or compare within a composition).
- Partially occupied sites are used at their listed positions (`disordered="skip"` drops them).
- `k_reliable` (neighbours inside the inscribed sphere) is recorded in `cif_metadata.csv`; a warning is issued when `k_amd`, `k_pdd` or `k_tsne` exceeds it for periodic models (P1 cells with at least `model_min_sites` sites).
- Pairwise EMD uses a plain loop by default; set `n_jobs > 1` to use a process pool (on Windows the calling script must be import-safe).

### Outputs (timestamped `run_<YYYYmmdd_HHMMSS>/` directory)

`amd_descriptors.csv` (`AMD_1..AMD_k_amd`, all structures), `pdd_store.pkl` / `pdd_store.csv` (reduced subset), `cif_metadata.csv`, `candidate_pairs.csv`, `duplicate_groups.csv`, `group_members.csv`, `amd_distance_matrix_k###.csv` (dendrogram leaf order), `amd_dendrogram.png`, `amd_heatmap.png`, `tsne_coords.csv`, `tsne.png`, `parse_warnings.json`, `run_info.json` (parameters, package versions, input files, stage counts, bound check, warnings). Optional: `pdd_dendrogram.png` / `pdd_heatmap.png` (`plot_pdd_subset`), `sensitivity_sweep.csv`.

Step-by-step walkthrough: [docs/tutorials/tutorial_pdd_similarity.ipynb](../../../docs/tutorials/tutorial_pdd_similarity.ipynb).
