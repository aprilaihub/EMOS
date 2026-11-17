# PDD Similarity Tutorial

This page provides a minimal, end-to-end, reproducible example of the PDD predictor's duplicate screening: an **AMD screen** on every structure followed by a **PDD confirmation** of the candidate pairs only.

An executed notebook version of this tutorial is available as [tutorial_pdd_similarity.ipynb](tutorial_pdd_similarity.ipynb).

Before you start:

- Install the requirements from the repository root: `pip install -r requirements.txt` (this tutorial needs `average-minimum-distance`, `pymatgen`, `scikit-learn`, `matplotlib` and `pandas`).
- Run every command and Python snippet from the **repository root**, in the same Python session and in the order shown. Later steps reuse variables from earlier ones.
- Nothing is random except the t-SNE start, which is seeded (`tsne_random_state = 42`), so you should obtain the numbers quoted in the "Expected" notes.

## Demo Example: Find duplicate ZnO structures

Goal: find the duplicate structures among the ZnO CIFs in `tests/fixtures/cif_files` (Materials Project, COD, OQMD and MatterGen), keep one representative per group, and write vectors, a t-SNE embedding, a dendrogram, a heatmap and a provenance file.

The method in short:

1. **AMD (Average Minimum Distance)** is cheap: one vector per structure. A pair is a *candidate* if its AMD distance at `k_amd` is at most `tau`.
2. Structures with no candidate partner are unique and are never touched again. The rest form the *reduced subset*.
3. **PDD (Pointwise Distance Distribution)** is more discriminating but costlier. Its Earth Mover's Distance (EMD) at `k_pdd` is computed **only for candidate pairs**.
4. AMD distance is a lower bound on PDD EMD (same metric, `k_pdd >= k_amd`), so a pair that fails the AMD screen can never pass the PDD test and nothing is lost.

### Step 1: Set up paths and imports

In this step, you put the repository root on `sys.path`, import the pipeline, and choose where the results are written.

```python
import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

sys.path.insert(0, str(Path(".").resolve()))  # repository root

from Information_Units.Predictors.Pdd.PddPredictor import PddPredictor
from Information_Units.Predictors.Pdd.similarity import ConfigError, Reporter, SimilarityConfig, run_similarity_pipeline
from Information_Units.Predictors.Pdd.similarity.descriptors import amd_distance_matrix, compute_descriptors
from Information_Units.Predictors.Pdd.similarity.loading import (
    CartesianConventionError, check_cartesian, load_structures,
)
from Information_Units.Predictors.Pdd.similarity.optional import species_test
from Information_Units.Predictors.Pdd.similarity.screening import (
    EmdCache, reference_groups, same_partition, screen, stage1_amd,
)

CIF_ROOT = Path("tests/fixtures/cif_files")
RESULTS_DIR = Path("results/pdd_similarity_tutorial")
```

### Step 2: Inspect the CIF fixtures

In this step, you count the CIF files in each source folder. The file-name prefix (`mp-`, `cod-`, `oqmd-`, `mg-`) identifies the source of each structure.

```python
SOURCE_FOLDERS = ["mp", "cod", "oqmd", "mg"]
for folder in SOURCE_FOLDERS:
    print(f"{folder:5s}: {len(list((CIF_ROOT / folder).glob('*.cif')))} CIF files")
```

Expected: `mp` 12, `cod` 20, `oqmd` 39, `mg` 51 (122 files). Not every file is ZnO, and one COD file cannot be parsed; the next steps deal with both.

### Step 3: Configure the run

In this step, you describe the run with a `SimilarityConfig`. Every parameter is validated when the object is created.

| Parameter | Meaning |
|---|---|
| `k_amd` | neighbours used for the AMD screen (stage 1) |
| `k_pdd` | neighbours used for the PDD confirmation (stage 2); must be `>= k_amd` |
| `k_max` | neighbours stored per structure; must be `>= k_pdd` |
| `tau` | duplicate threshold in angstrom |
| `metric` | `euclidean`, `cityblock` or `chebyshev`; used for **both** the AMD distances and the EMD ground metric |
| `linkage` | `complete` (every pair in a group is within `tau`), `single`, `average` or `ward` (Euclidean only) |
| `composition_filter` | optional list of reduced formulas to keep |
| `source_prefixes`, `source_priority` | file-name prefix to source label, and the order used to break ties when choosing a representative |

```python
cfg = SimilarityConfig(
    input_dirs=[str(CIF_ROOT / folder) for folder in SOURCE_FOLDERS],
    output_dir=str(RESULTS_DIR),
    composition_filter=["ZnO"],
    source_priority=["COD", "MP", "OQMD", "MATTERGEN"],
    k_amd=15,
    k_pdd=30,
    k_max=100,
    tau=0.1,
    metric="euclidean",
    linkage="complete",
    highlight=["mp-2133", "cod-2300112", "oqmd-4908"],  # drawn on the heatmap only if you list names
    figure_dpi=120,
)
```

Invalid configurations are rejected before any structure is read. `cosine` and `correlation` are not norms, so the AMD distance would no longer be a lower bound of the EMD and the screen could drop true duplicates. `k_pdd < k_amd` breaks the same guarantee.

```python
invalid = {
    "k_pdd below k_amd":   dict(k_amd=20, k_pdd=10),
    "cosine metric":       dict(metric="cosine"),
    "correlation metric":  dict(metric="correlation"),
    "ward with cityblock": dict(linkage="ward", metric="cityblock"),
    "k_max below k_pdd":   dict(k_pdd=30, k_max=20),
}
for label, overrides in invalid.items():
    try:
        replace(cfg, **overrides)
        print(f"NOT rejected: {label}")
    except ConfigError as exc:
        problems = "; ".join(line.strip(" -") for line in str(exc).splitlines()[1:])
        print(f"rejected  {label:20s} -> {problems}")
```

Expected: all five configurations are rejected with a message naming the problem.

### Step 4: Load the structures and check the coordinates

In this step, you read the CIFs with pymatgen (`frac_tolerance=0`, first structure of each file), keep only ZnO, and build one periodic set per structure from **Cartesian** coordinates. Each structure is keyed by `<source>/<relative path>`, so a file name that appears in two folders is never overwritten.

```python
report = Reporter(verbose=True)
loaded = load_structures(cfg, report)

print(f"\nloaded {len(loaded.records)} | removed by composition filter: {len(loaded.filtered_out)} | "
      f"skipped: {len(loaded.skipped)}")
for item in loaded.skipped:
    print("  skipped:", item)
print("  filtered out:", loaded.filtered_out)
```

Expected: 119 structures loaded, 2 removed by the composition filter (`COD/cod-1536063.cif`, a partially occupied `Zn10.26O48`, and `COD/cod-4517837.cif`, `Zn5O12`), and 1 skipped file (`COD/cod-3000626.cif`, no structure inside).

A motif that looks like fractional coordinates passed as Cartesian is a hard error, because it silently produces wrong descriptors:

```python
fractional_motif = np.array([[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]])
try:
    check_cartesian(fractional_motif, 4.2 * np.eye(3), "fractional demo")
except CartesianConventionError as exc:
    print("Cartesian guard:", exc)
```

PDD is computed **once** per structure at `k_max`; AMD is derived from it as the weighted mean of its rows.

```python
desc, desc_skipped, _ = compute_descriptors(loaded.records, cfg, report)

weight_error = max(abs(p[:, 0].sum() - 1.0) for p in desc.pdd)
nearest = min(p[:, 1].min() for p in desc.pdd)
print(f"structures with descriptors : {len(desc)}")
print(f"largest |sum(weights) - 1|  : {weight_error:.1e}")
print(f"shortest nearest-neighbour  : {nearest:.3f} A")
print(f"AMD matrix shape            : {desc.amd.shape}  (structures x k_max)")
```

Expected: 119 structures, weight error below $10^{-12}$, shortest nearest-neighbour about 1.513 A, and an AMD matrix of shape `(119, 100)`.

Optionally, cross-check the descriptors against the `amd.CifReader` (agreement within $10^{-5}$ A). This reader is slow, so only 12 files are checked here:

```python
cfg_check = replace(cfg, crosscheck_cifreader=True, k_max=30, k_pdd=30)
_, _, crosscheck_failures = compute_descriptors(loaded.records[:12], cfg_check, Reporter())
print(f"amd.CifReader cross-check failures on 12 files: {len(crosscheck_failures)}")
```

Expected: `0` failures.

### Step 5: Stage 1 - AMD screen on the full set

In this step, you compute all pairwise AMD distances at `k_amd`, mark pairs within `tau` as candidates, and take the connected components of the candidate graph. Structures in singleton components are unique and need no PDD.

```python
d_amd = amd_distance_matrix(desc.amd, cfg.k_amd, cfg.metric)
stage1 = stage1_amd(d_amd, cfg.tau)

n = len(desc)
print(f"structures                     : {n}")
print(f"all pairs                      : {n * (n - 1) // 2}")
print(f"candidate pairs (AMD <= tau)   : {len(stage1.candidate_pairs)}")
print(f"unique after stage 1           : {n - len(stage1.subset)}")
print(f"reduced subset (components >=2): {len(stage1.subset)}")
```

Expected: 663 candidate pairs out of 7021, 25 structures unique after stage 1, and a reduced subset of 94 structures.

### Step 6: Stage 2 - PDD confirmation on candidate pairs only

In this step, you compute the EMD at `k_pdd` for the candidate pairs only. The final distance is the AMD distance where the pair is not a candidate and the PDD EMD where it is. Groups come from a linkage cut at `tau`; each group's representative is its medoid, with ties broken by source priority and then ID.

The wurtzite and zinc blende polymorphs of ZnO (`mp-2133`, `mp-1986`) have almost the same first 15 neighbour distances, so they pass the AMD screen, but PDD at `k_pdd = 30` tells them apart.

```python
cache = EmdCache(desc.pdd, cfg.metric, cfg.n_jobs)
screened = screen(desc, cfg, cache)

print(json.dumps(screened.counts, indent=2))
print("bound check (AMD <= EMD):", screened.bound_check)

pair = next(row for row in screened.candidate_table
            if {row["a"], row["b"]} == {"MP/mp-2133.cif", "MP/mp-1986.cif"})
print("wurtzite vs zinc blende:", pair)
confirmed = sum(row["confirmed"] for row in screened.candidate_table)
print(f"candidates confirmed by PDD: {confirmed} | rejected by PDD: {len(screened.candidate_table) - confirmed}")
```

Expected: 71 groups (20 with more than one member), 6358 of 7021 PDD pairs saved, 198 candidates confirmed and 465 rejected, and `'holds': True` in the bound check. The wurtzite / zinc blende pair has AMD distance 0.044 A (a candidate) but PDD EMD 1.229 A (rejected).

### Step 7: Verify the screen against full pairwise PDD grouping

In this step, you check that skipping the PDD calculation for non-candidate pairs changes nothing. With `complete` (or `single`) linkage the groups only depend on which pairs are within `tau`, so the screened groups must be identical to the groups obtained from the EMD of **all** pairs. This evaluates every pair, so it is for verification only. Run it for each allowed metric.

```python
for metric in ("euclidean", "cityblock", "chebyshev"):
    cfg_m = replace(cfg, metric=metric)
    cache_m = EmdCache(desc.pdd, metric)
    screened_m = screen(desc, cfg_m, cache_m)
    identical = same_partition(screened_m.group_labels, reference_groups(desc, cfg_m, cache_m))
    print(f"{metric:10s} identical groups: {identical} | groups: {screened_m.counts['n_groups']:3d} | "
          f"PDD pairs evaluated: {screened_m.counts['n_pdd_pairs_evaluated']:4d} of {screened_m.counts['n_pairs_total']}")
    assert identical and screened_m.bound_check["holds"]
```

Expected: `identical groups: True` for all three metrics (71, 100 and 50 groups; 663, 152 and 1221 PDD pairs evaluated).

### Step 8: Run the full pipeline

In this step, you run everything in one call. The pipeline writes a timestamped `run_<YYYYmmdd_HHMMSS>` folder containing the vectors, the t-SNE embedding, the dendrogram and heatmap, the group tables and `run_info.json`. Figures are only saved, never shown.

```python
result = run_similarity_pipeline(cfg, verbose=True)
RUN_DIR = result.run_dir
for name in sorted(p.name for p in RUN_DIR.iterdir()):
    print(f"  {name}")
```

Expected output files:

```text
amd_dendrogram.png        amd_descriptors.csv       amd_distance_matrix_k015.csv
amd_heatmap.png           candidate_pairs.csv       cif_metadata.csv
duplicate_groups.csv      group_members.csv         parse_warnings.json
pdd_emd_matrix_k030.csv   pdd_store.csv             pdd_store.pkl
run_info.json             tsne.png                  tsne_coords.csv
```

| File | Content |
|---|---|
| `amd_descriptors.csv` | one AMD vector per structure (all structures) |
| `pdd_store.pkl`, `pdd_store.csv` | PDD vectors of the reduced subset (candidate structures only) |
| `candidate_pairs.csv` | every candidate pair with its AMD distance, PDD EMD and decision |
| `duplicate_groups.csv`, `group_members.csv` | the groups and their members, with the chosen representative |
| `amd_distance_matrix_k015.csv`, `pdd_emd_matrix_k030.csv` | distance matrices in dendrogram leaf order |
| `amd_dendrogram.png`, `amd_heatmap.png` | AMD figures on the full set |
| `tsne.png`, `tsne_coords.csv` | t-SNE of the PDD EMD on the reduced subset |
| `cif_metadata.csv`, `parse_warnings.json` | per-structure metadata and parser warnings |
| `run_info.json` | parameters, versions, counts, warnings |

### Step 9: Inspect the duplicate groups

In this step, you read the group table. Each row is one group of structures that are the same within `tau`; `representative` is the structure to keep.

```python
groups = pd.read_csv(RUN_DIR / "duplicate_groups.csv")
print(f"{len(groups)} groups, {int((groups['n_members'] > 1).sum())} of them with more than one member")
print(groups.sort_values("n_members", ascending=False).head(5)[
    ["group", "representative", "n_members", "sources", "max_intra_A"]].to_string(index=False))

members = pd.read_csv(RUN_DIR / "group_members.csv")
biggest = groups.sort_values("n_members", ascending=False).iloc[0]["group"]
print(members[members["group"] == biggest][
    ["label", "source", "is_representative", "distance_to_representative_A"]].to_string(index=False))
assert (groups["max_intra_A"] <= cfg.tau).all()
```

Expected: 71 groups, 20 of them with more than one member. With `complete` linkage, `max_intra_A` is never larger than `tau`: every pair inside a group is within the threshold.

### Step 10: View the figures

In this step, you open the saved figures from `RUN_DIR`.

- `amd_dendrogram.png` (AMD, whole set): branches are coloured at `tau`, so clusters that merge below the dashed line are duplicates by the AMD screen.
- `amd_heatmap.png` (AMD, whole set): lower triangle in the same leaf order as the dendrogram. The structures in `highlight` are marked.
- `tsne.png` (PDD EMD, reduced subset only): structures closer together have more similar PDDs.

Tick labels are hidden automatically when there are more than `max_tick_labels` structures.

```python
for figure in ("amd_dendrogram.png", "amd_heatmap.png", "tsne.png"):
    path = RUN_DIR / figure
    print(f"{figure}: {path.stat().st_size // 1024} KB -> {path}")
```

### Step 11: Check the descriptors against closed-form values

In this step, you compare the first AMD value (the nearest-neighbour distance) of three cubic ZnO structures with its closed form in terms of the conventional cubic lattice parameter $a$: rock salt $a/2$, zinc blende $\sqrt{3}a/4$ and CsCl type $\sqrt{3}a/2$.

```python
closed_forms = {
    "MP/mp-2229.cif":  ("rock salt, a/2",             lambda a: a / 2),
    "MP/mp-1986.cif":  ("zinc blende, sqrt(3)a/4",    lambda a: np.sqrt(3) * a / 4),
    "MP/mp-13161.cif": ("CsCl type, sqrt(3)a/2",      lambda a: np.sqrt(3) * a / 2),
}
by_key = {record.key: record for record in loaded.records}
rows = []
for key, (label, formula) in closed_forms.items():
    a_conv = SpacegroupAnalyzer(by_key[key].structure).get_conventional_standard_structure().lattice.a
    amd_1 = float(desc.amd[desc.keys.index(key), 0])
    rows.append({"structure": key, "type": label, "a_conv_A": a_conv, "AMD_1_A": amd_1,
                 "closed_form_A": formula(a_conv), "abs_diff_A": abs(amd_1 - formula(a_conv))})
check = pd.DataFrame(rows)
print(check.to_string(index=False))
assert check["abs_diff_A"].max() <= 1e-4
```

Expected: all three differences are below $10^{-4}$ A.

### Step 12: Species are ignored

In this step, you see the main limitation. AMD and PDD describe **positions only**. If every atom of a structure is relabelled with the same element, nothing in the descriptor changes, so the two structures have distance 0 although their chemistry differs. Use the composition filter (as in this tutorial), or compare within one composition.

```python
print(json.dumps(species_test(by_key["MP/mp-2133.cif"], cfg.k_pdd, cfg.metric, cfg.collapse_tol), indent=2))
```

Expected: `"relabelled_composition": "Zn"` and `"pdd_emd_A": 0.0`.

### Step 13: Read the run provenance

In this step, you read `run_info.json`, which records everything needed to reproduce the run: the parameters, package versions, the input file list, the counts at each stage and every warning.

```python
info = json.loads((RUN_DIR / "run_info.json").read_text(encoding="utf-8"))
print("packages     :", info["packages"])
print("guarantee    :", info["method"]["guarantee"])
print("stage counts :", json.dumps(info["stage_counts"]))
print("bound check  :", info["bound_check"])
print("input files  :", len(info["input_files"]))
print("warnings     :", info["warnings"])
```

Expected: the guarantee reads "every pair in a group is within tau", 122 input files, and one warning for `COD/cod-3000626.cif`.

### Step 14: Run it from the predictor or the command line

In this step, you run the same pipeline through the EMOS predictor, which accepts a plain dictionary. The call below screens only the 12 Materials Project structures.

```python
summary = PddPredictor().screen({
    "input_dirs": [str(CIF_ROOT / "mp")],
    "output_dir": str(RESULTS_DIR),
    "k_amd": 15, "k_pdd": 30, "k_max": 50, "tau": 0.1,
    "figure_dpi": 120,
})
print(json.dumps(summary["stage_counts"], indent=2))
```

Expected: 12 structures, 66 pairs, 5 candidate pairs, 12 groups and no duplicate groups.

The command line does the same and accepts a JSON file (`--config`) with any configuration field; command-line options override the file:

```bash
python -m Information_Units.Predictors.Pdd.similarity --input-dir tests/fixtures/cif_files/mp --output-dir results/pdd_similarity_tutorial --tau 0.1 --k-amd 15 --k-pdd 30 --quiet
```

### Step 15: Run the tests

Run the PDD tests before submitting a change:

```bash
pytest -q tests/unit/test_pdd_similarity.py tests/integration/test_pdd_similarity_pipeline.py tests/integration/test_pdd_predictor.py
pytest -q tests/standards tests/iu_contracts -k "Pdd or pdd"
```

The tests cover configuration validation, the Cartesian guard, the lower bound, screen equivalence for all three metrics, the closed-form values above, a regression against an independent AMD computation, and the edge cases (no candidate pairs, fewer than 4 structures, a single structure). The integration tests take about a minute.

## Tuning notes

- Lower `tau` finds only closer matches; every group stays within `tau` with `complete` linkage.
- A larger `k_pdd` separates polymorphs that share their nearest neighbours (as the wurtzite / zinc blende pair does) at the price of more EMD work; a larger `k_amd` shrinks the candidate set.
- Keep `k_pdd` well below the number of atoms that fit in your smallest periodic model cell; `cif_metadata.csv` lists `k_reliable` for each structure and the run records a warning when it is exceeded.
- `single` linkage groups chains of near-duplicates; `average` and `ward` have no pairwise guarantee, and the screened result is then an approximation (a warning is recorded).

## Remove the tutorial results (cleanup)

When you are done, delete the results folder:

```python
shutil.rmtree(RESULTS_DIR, ignore_errors=True)
```

The tutorial adds no files to the repository other than the results folder, so nothing else needs to be removed.
