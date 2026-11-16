"""PDD / AMD descriptors, per-structure checks and distance helpers.

The PDD is computed **once** per structure at ``k_max``.  The AMD is derived from it
as the weighted mean of the PDD rows, and AMD at ``k`` is simply the first ``k``
entries - it is never recomputed for each ``k``.

For any norm, ``|| AMD_a(k) - AMD_b(k) || <= EMD(PDD_a, PDD_b; k)``, and EMD
is non-decreasing in ``k``.  Hence an AMD distance above ``tau`` at ``k_amd``
guarantees an EMD above ``tau`` at any ``k_pdd >= k_amd`` (up to the row-merging
tolerance ``collapse_tol``).
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import amd
import numpy as np
from amd import AMD, PDD
from scipy.spatial.distance import squareform

from ._report import Reporter
from .config import SimilarityConfig
from .loading import CartesianConventionError, StructureRecord, structure_to_periodicset

TOL_WEIGHTS = 1e-9  # |sum(weights) - 1|
TOL_MONOTONE = 1e-9  # angstrom, allowed decrease along a PDD row (float noise)


@dataclass
class Descriptors:
    """PDD (``k_max``) and AMD for every structure that passed the checks."""

    keys: list[str]
    labels: list[str]
    sources: list[str]
    pdd: list[np.ndarray]  # each (rows, k_max + 1); column 0 = row weights
    amd: np.ndarray  # (n, k_max)

    def __len__(self) -> int:
        return len(self.keys)


# ── PDD / AMD / EMD primitives ───────────────────────────────────────────────
def compute_pdd(periodic_set: amd.PeriodicSet, k: int, collapse_tol: float) -> np.ndarray:
    """PDD of a periodic set. Column 0 = row weights; columns 1..k = distances (angstrom)."""
    return np.asarray(PDD(periodic_set, k, collapse=True, collapse_tol=collapse_tol), dtype=float)


def amd_from_pdd(pdd: np.ndarray, k: int | None = None) -> np.ndarray:
    """AMD as the weighted mean of PDD rows (optionally the first ``k`` entries only)."""
    distances = pdd[:, 1:] if k is None else pdd[:, 1 : k + 1]
    return np.average(distances, weights=pdd[:, 0], axis=0)


def emd(pdd_a: np.ndarray, pdd_b: np.ndarray, k: int, metric: str) -> float:
    """EMD between PDDs truncated to the first ``k`` neighbours, with the given ground metric."""
    return float(
        amd.EMD(
            np.ascontiguousarray(pdd_a[:, : k + 1]),
            np.ascontiguousarray(pdd_b[:, : k + 1]),
            metric=metric,
        )
    )


def amd_distance_matrix(amd_matrix: np.ndarray, k: int, metric: str) -> np.ndarray:
    """Square matrix of AMD distances using the first ``k`` AMD values."""
    n = len(amd_matrix)
    if n < 2:
        return np.zeros((n, n))
    return squareform(amd.AMD_pdist(np.ascontiguousarray(amd_matrix[:, :k]), metric=metric))


def bound_tolerance(metric: str, k: int, collapse_tol: float) -> float:
    """Allowed violation of ``AMD <= EMD`` caused by PDD row merging (``collapse_tol``)."""
    factor = {"euclidean": math.sqrt(k), "cityblock": float(k), "chebyshev": 1.0}[metric]
    return 2.0 * collapse_tol * factor


# ── per-structure checks ─────────────────────────────────────────────────────
def descriptor_problems(pdd: np.ndarray, min_nn_dist: float) -> list[str]:
    """Return the failed sanity checks for one PDD (empty list = all passed)."""
    if not np.isfinite(pdd).all():
        return ["PDD contains non-finite values"]
    problems: list[str] = []
    weight_error = abs(float(pdd[:, 0].sum()) - 1.0)
    if weight_error > TOL_WEIGHTS:
        problems.append(f"row weights sum to 1 {weight_error:+.2e} off (tolerance {TOL_WEIGHTS:g})")
    if (np.diff(pdd[:, 1:], axis=1) < -TOL_MONOTONE).any():
        problems.append("PDD rows are not non-decreasing in k")
    nearest = float(pdd[:, 1].min())
    if nearest < min_nn_dist:
        problems.append(f"nearest-neighbour distance {nearest:.3f} A is below min_nn_dist = {min_nn_dist:g} A")
    return problems


def cifreader_pdd(path: Path, k: int, collapse_tol: float) -> tuple[np.ndarray | None, str]:
    """PDD from the package's own CIF reader: an independent cross-check of the pipeline."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            periodic_set = next(iter(amd.CifReader(str(path), show_warnings=False)), None)
    except Exception as exc:
        return None, f"CifReader failed: {type(exc).__name__}: {exc}"
    if periodic_set is None:
        return None, "CifReader yielded no structure"
    return compute_pdd(periodic_set, k, collapse_tol), ""


# ── descriptor stage ─────────────────────────────────────────────────────────
def compute_descriptors(
    records: Sequence[StructureRecord],
    config: SimilarityConfig,
    report: Reporter,
) -> tuple[Descriptors, list[dict[str, str]], list[dict[str, float | str]]]:
    """Compute PDD (once, at ``k_max``) and derive AMD for every record.

    Returns ``(descriptors, skipped, crosscheck_failures)``.  A structure failing a
    sanity check is skipped and reported.  A :class:`CartesianConventionError` is a
    hard failure and propagates.
    """
    keys, labels, sources, pdds, amds = [], [], [], [], []
    skipped: list[dict[str, str]] = []
    crosscheck_failures: list[dict[str, float | str]] = []

    for record in records:
        try:
            periodic_set = structure_to_periodicset(record.structure, record.key)
            pdd = compute_pdd(periodic_set, config.k_max, config.collapse_tol)
            amd_reference = np.asarray(AMD(periodic_set, config.k_max), dtype=float)
        except CartesianConventionError:
            raise
        except Exception as exc:
            skipped.append({"name": record.key, "reason": f"descriptor failed: {type(exc).__name__}: {exc}"})
            report.warn(f"{record.key}: descriptor calculation failed ({exc})")
            continue

        problems = descriptor_problems(pdd, config.min_nn_dist)
        if problems:
            skipped.append({"name": record.key, "reason": "; ".join(problems)})
            report.warn(f"{record.key}: skipped - {'; '.join(problems)}")
            continue

        amd_vector = amd_from_pdd(pdd)
        if not np.allclose(amd_reference, amd_vector, atol=10 * config.collapse_tol):
            raise RuntimeError(
                f"{record.key}: AMD differs from the weighted mean of PDD rows "
                f"(max deviation {np.abs(amd_reference - amd_vector).max():.2e} A)"
            )

        if config.crosscheck_cifreader:
            reference, note = cifreader_pdd(record.path, config.k_max, config.collapse_tol)
            if reference is None:
                report.warn(f"{record.key}: CifReader cross-check not possible ({note})")
            else:
                distance = emd(pdd, reference, config.k_max, config.metric)
                if distance > config.crosscheck_tol:
                    crosscheck_failures.append({"name": record.key, "emd_A": distance})
                    report.warn(
                        f"{record.key}: EMD to amd.CifReader = {distance:.2e} A exceeds {config.crosscheck_tol:g} A"
                    )

        keys.append(record.key)
        labels.append(record.label)
        sources.append(record.source)
        pdds.append(pdd)
        amds.append(amd_vector)

    amd_matrix = np.vstack(amds) if amds else np.zeros((0, config.k_max))
    report.info(f"Descriptors computed for {len(keys)} / {len(records)} structures (PDD once, k_max = {config.k_max}).")
    return Descriptors(keys, labels, sources, pdds, amd_matrix), skipped, crosscheck_failures
