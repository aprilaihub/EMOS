"""Optional extras, off by default.

* :func:`structure_matcher_validation`  pairwise comparison with pymatgen's
  species-aware ``StructureMatcher`` (O(N^2) fits - slow for large sets).
* :func:`species_test`  demonstrates that AMD / PDD ignore species.
* :func:`sensitivity_sweep`  number of candidate pairs / groups over a grid of
  ``k_amd`` and ``tau`` (and metrics), reusing a shared EMD cache.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Sequence

import numpy as np
import pandas as pd
from pymatgen.core import Structure
from scipy.sparse.csgraph import connected_components

from ._report import Reporter
from .config import ConfigError, SimilarityConfig
from .descriptors import Descriptors, compute_pdd, emd
from .loading import StructureRecord, structure_to_periodicset
from .screening import EmdCache, screen


# ── StructureMatcher validation ──────────────────────────────────────────────
def structure_matcher_validation(
    records: Sequence[StructureRecord],
    group_labels: Sequence[int] | np.ndarray,
    report: Reporter,
) -> dict[str, Any]:
    """Compare pipeline groups with ``StructureMatcher`` at two strictness levels.

    ``type`` uses pymatgen defaults (scale = True: same structure type);
    ``geom`` is strict and unscaled (about tau-scale geometric agreement).
    """
    from pymatgen.analysis.structure_matcher import StructureMatcher

    matchers = {
        "type": StructureMatcher(),
        "geom": StructureMatcher(ltol=0.01, stol=0.02, angle_tol=0.5, scale=False),
    }
    labels = np.asarray(group_labels)
    n = len(records)
    rows, cols = np.triu_indices(n, 1)
    same = labels[:, None] == labels[None, :]
    result: dict[str, Any] = {}
    for name, matcher in matchers.items():
        match = np.eye(n, dtype=bool)
        for i, j in zip(rows.tolist(), cols.tolist()):
            try:
                match[i, j] = match[j, i] = bool(matcher.fit(records[i].structure, records[j].structure))
            except Exception as exc:
                report.warn(f"StructureMatcher[{name}] failed for {records[i].key} / {records[j].key}: {exc}")
        tp = int((same & match)[rows, cols].sum())
        fp = int((same & ~match)[rows, cols].sum())
        fn = int((~same & match)[rows, cols].sum())
        n_ref_groups = connected_components(match, directed=False)[0]
        result[name] = {
            "matching_pairs": int(match[rows, cols].sum()),
            "reference_groups": int(n_ref_groups),
            "false_merges": fp,
            "missed_duplicates": fn,
            "precision": tp / (tp + fp) if tp + fp else 1.0,
            "recall": tp / (tp + fn) if tp + fn else 1.0,
        }
    return result


# ── species test ─────────────────────────────────────────────────────────────
def species_test(record: StructureRecord, k: int, metric: str, collapse_tol: float) -> dict[str, Any]:
    """Relabel every site with one element and compare descriptors.

    Positions are unchanged, so the PDD EMD is 0 although the chemistry differs.
    This is why a composition filter (or grouping by composition) is the safeguard.
    """
    structure = record.structure
    present = {str(el) for el in structure.composition.elements}
    replacement = "Zn" if "Zn" not in present or len(present) > 1 else "O"
    relabelled = Structure(structure.lattice, [replacement] * len(structure), structure.frac_coords)
    pdd_a = compute_pdd(structure_to_periodicset(structure), k, collapse_tol)
    pdd_b = compute_pdd(structure_to_periodicset(relabelled), k, collapse_tol)
    return {
        "structure": record.key,
        "original_composition": structure.composition.reduced_formula,
        "relabelled_composition": relabelled.composition.reduced_formula,
        "pdd_emd_A": emd(pdd_a, pdd_b, k, metric),
        "note": "positions identical, species differ: AMD and PDD cannot tell them apart",
    }


# ── sensitivity sweep ────────────────────────────────────────────────────────
def sensitivity_sweep(desc: Descriptors, config: SimilarityConfig) -> pd.DataFrame:
    """Groups and PDD workload over ``sweep_ks`` x ``sweep_taus`` x metrics."""
    metrics = config.sweep_metrics or [config.metric]
    rows: list[dict[str, Any]] = []
    for metric in metrics:
        cache = EmdCache(desc.pdd, metric, config.n_jobs)  # shared across the grid: EMD is evaluated once per pair
        for k_amd in config.sweep_ks:
            for tau in config.sweep_taus:
                try:
                    cell = replace(
                        config,
                        metric=metric,
                        k_amd=k_amd,
                        k_pdd=max(config.k_pdd, k_amd),
                        k_tsne=None,
                        tau=tau,
                    )
                except ConfigError:
                    continue  # e.g. ward with a non-Euclidean metric
                result = screen(desc, cell, cache)
                rows.append(
                    {
                        "metric": metric,
                        "k_amd": k_amd,
                        "k_pdd": cell.k_pdd,
                        "tau_A": tau,
                        "n_candidate_pairs": result.counts["n_candidate_pairs"],
                        "n_subset": result.counts["n_subset"],
                        "n_groups": result.counts["n_groups"],
                        "bound_holds": result.bound_check["holds"],
                    }
                )
    return pd.DataFrame(rows)
