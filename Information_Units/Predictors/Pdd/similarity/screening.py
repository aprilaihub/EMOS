"""Staged duplicate screening: AMD on the full set, PDD only where needed.

Stage 1 (AMD, all structures)
    Pairwise AMD distance at ``k_amd``.  A pair is a *candidate* if its distance is
    ``<= tau``.  Connected components of the candidate graph partition the set;
    structures in singleton components are unique and need no PDD.  The *reduced
    subset* is every structure in a component of size >= 2.

Stage 2 (PDD, candidate pairs only)
    PDD EMD at ``k_pdd`` (same metric) for the candidate pairs.  The final distance
    matrix equals the AMD distance where it exceeds ``tau`` and the PDD EMD
    otherwise.  This is valid because AMD is a lower bound on EMD.  Groups are cut
    from a hierarchical clustering of each component at ``tau``.

Guarantee
    ``complete`` linkage: every pair in a group is within ``tau``.  ``single``:
    groups are chains of pairs within ``tau``.  For these two the screened groups are
    identical to full pairwise PDD grouping (they depend only on which pairs are
    ``<= tau``).  ``average`` and ``ward`` depend on the actual values, so the
    screened result is an approximation and has no pairwise guarantee.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial.distance import squareform

from .config import SimilarityConfig
from .descriptors import Descriptors, amd_distance_matrix, bound_tolerance, emd

_PARALLEL_MIN_PAIRS = 200  # below this a process pool costs more than it saves

# worker-process globals (set by _init_worker)
_W_PDDS: list[np.ndarray] | None = None
_W_METRIC: str | None = None


def _init_worker(pdds: list[np.ndarray], metric: str) -> None:
    global _W_PDDS, _W_METRIC
    _W_PDDS, _W_METRIC = pdds, metric


def _emd_task(task: tuple[int, int, int]) -> float:
    i, j, k = task
    return emd(_W_PDDS[i], _W_PDDS[j], k, _W_METRIC)  # type: ignore[index]


class EmdCache:
    """Pairwise PDD EMD, computed on demand and cached per ``k``.

    ``n_jobs > 1`` evaluates large batches in a process pool.  On Windows the
    calling script must be import-safe (``if __name__ == "__main__":``).
    """

    def __init__(self, pdds: list[np.ndarray], metric: str, n_jobs: int = 1) -> None:
        self._pdds = pdds
        self.metric = metric
        self.n_jobs = n_jobs
        self._store: dict[int, dict[tuple[int, int], float]] = {}

    def get_pairs(self, k: int, pairs: Iterable[tuple[int, int]]) -> list[float]:
        store = self._store.setdefault(k, {})
        normalised = [(min(i, j), max(i, j)) for i, j in pairs]
        missing = list(dict.fromkeys(p for p in normalised if p not in store))
        if missing:
            if self.n_jobs > 1 and len(missing) >= _PARALLEL_MIN_PAIRS:
                tasks = [(i, j, k) for i, j in missing]
                chunk = max(1, len(tasks) // (self.n_jobs * 8))
                with ProcessPoolExecutor(
                    max_workers=self.n_jobs, initializer=_init_worker, initargs=(self._pdds, self.metric)
                ) as pool:
                    values = list(pool.map(_emd_task, tasks, chunksize=chunk))
            else:
                values = [emd(self._pdds[i], self._pdds[j], k, self.metric) for i, j in missing]
            store.update(zip(missing, values))
        return [store[p] for p in normalised]

    def matrix(self, k: int, indices: Iterable[int]) -> np.ndarray:
        """Symmetric EMD matrix over ``indices`` (every pair is evaluated)."""
        idx = [int(i) for i in indices]
        m = len(idx)
        result = np.zeros((m, m))
        pairs = [(idx[a], idx[b]) for a in range(m) for b in range(a + 1, m)]
        values = self.get_pairs(k, pairs)
        position = 0
        for a in range(m):
            for b in range(a + 1, m):
                result[a, b] = result[b, a] = values[position]
                position += 1
        return result

    def cached(self, k: int) -> dict[tuple[int, int], float]:
        return self._store.get(k, {})


# ── stage 1 ──────────────────────────────────────────────────────────────────
@dataclass
class Stage1Result:
    d_amd: np.ndarray
    candidate_pairs: list[tuple[int, int]]
    component_labels: np.ndarray
    n_components: int
    subset: np.ndarray  # indices of structures in components of size >= 2


def stage1_amd(d_amd: np.ndarray, tau: float) -> Stage1Result:
    n = len(d_amd)
    rows, cols = np.triu_indices(n, 1)
    mask = d_amd[rows, cols] <= tau
    cand_i, cand_j = rows[mask], cols[mask]
    graph = coo_matrix((np.ones(len(cand_i)), (cand_i, cand_j)), shape=(n, n))
    n_components, labels = connected_components(graph, directed=False)
    sizes = np.bincount(labels, minlength=n_components) if n else np.zeros(0, dtype=int)
    subset = np.flatnonzero(sizes[labels] >= 2) if n else np.zeros(0, dtype=int)
    candidates = [(int(i), int(j)) for i, j in zip(cand_i, cand_j)]
    return Stage1Result(d_amd, candidates, labels, int(n_components), subset)


# ── full screen ──────────────────────────────────────────────────────────────
@dataclass
class ScreenResult:
    stage1: Stage1Result
    d_final: np.ndarray
    group_labels: np.ndarray  # 1..G per structure
    groups: list[dict[str, Any]]
    members: list[dict[str, Any]]
    candidate_table: list[dict[str, Any]]
    counts: dict[str, Any]
    bound_check: dict[str, Any]
    exact: bool = field(default=True)

    @property
    def subset(self) -> np.ndarray:
        return self.stage1.subset


def screen(desc: Descriptors, config: SimilarityConfig, cache: EmdCache | None = None) -> ScreenResult:
    """Run stage 1 (AMD) and stage 2 (PDD on candidate pairs) and group at ``tau``."""
    n = len(desc)
    cache = cache or EmdCache(desc.pdd, config.metric, config.n_jobs)
    d_amd = amd_distance_matrix(desc.amd, config.k_amd, config.metric)
    s1 = stage1_amd(d_amd, config.tau)

    # stage 2: PDD EMD for candidate pairs only
    emd_values = cache.get_pairs(config.k_pdd, s1.candidate_pairs)
    d_final = d_amd.copy()
    for (i, j), value in zip(s1.candidate_pairs, emd_values):
        d_final[i, j] = d_final[j, i] = value

    # group each multi-structure component at tau
    provisional = np.arange(n)  # singletons keep their own id
    next_id = n
    for component in np.unique(s1.component_labels[s1.subset]):
        idx = np.flatnonzero(s1.component_labels == component)
        sub = d_final[np.ix_(idx, idx)]
        tree = linkage(squareform(sub, checks=False), method=config.linkage)
        cut = fcluster(tree, config.tau, criterion="distance")
        provisional[idx] = next_id + cut
        next_id += int(cut.max()) + 1
    group_labels = _canonical_labels(provisional)

    groups, members = _group_tables(desc, config, d_final, group_labels)

    # bound check AMD(k_amd) <= EMD(k_pdd) over every evaluated pair
    violations = [float(d_amd[i, j] - v) for (i, j), v in zip(s1.candidate_pairs, emd_values)]
    max_violation = max(0.0, *violations) if violations else 0.0  # 0 = AMD <= EMD for every pair
    tolerance = bound_tolerance(config.metric, config.k_pdd, config.collapse_tol)
    bound = {
        "pairs_checked": len(violations),
        "max_violation_A": max_violation,
        "tolerance_A": tolerance,
        "holds": bool(max_violation <= tolerance),
    }

    n_pairs = n * (n - 1) // 2
    n_candidates = len(s1.candidate_pairs)
    sizes = np.bincount(s1.component_labels, minlength=s1.n_components) if n else np.zeros(0, dtype=int)
    counts = {
        "n_structures": n,
        "n_pairs_total": n_pairs,
        "n_candidate_pairs": n_candidates,
        "n_components": s1.n_components,
        "n_components_multi": int((sizes >= 2).sum()),
        "n_unique_after_stage1": int((sizes == 1).sum()),
        "n_subset": int(len(s1.subset)),
        "n_pdd_pairs_evaluated": n_candidates,
        "n_pdd_pairs_saved": n_pairs - n_candidates,
        "n_groups": int(group_labels.max()) if n else 0,
        "n_duplicate_groups": sum(1 for g in groups if g["n_members"] > 1),
        "n_removed_as_duplicates": n - (int(group_labels.max()) if n else 0),
    }
    candidate_table = [
        {
            "a": desc.keys[i],
            "b": desc.keys[j],
            "amd_A": float(d_amd[i, j]),
            "pdd_emd_A": float(v),
            "confirmed": bool(v <= config.tau),
        }
        for (i, j), v in zip(s1.candidate_pairs, emd_values)
    ]
    return ScreenResult(
        stage1=s1,
        d_final=d_final,
        group_labels=group_labels,
        groups=groups,
        members=members,
        candidate_table=candidate_table,
        counts=counts,
        bound_check=bound,
        exact=config.screen_is_exact,
    )


def _canonical_labels(labels: np.ndarray) -> np.ndarray:
    """Relabel to 1..G in order of first appearance."""
    mapping: dict[int, int] = {}
    out = np.empty(len(labels), dtype=int)
    for position, value in enumerate(labels):
        out[position] = mapping.setdefault(int(value), len(mapping) + 1)
    return out


def _group_tables(
    desc: Descriptors, config: SimilarityConfig, d_final: np.ndarray, group_labels: np.ndarray
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    priority = {source: rank for rank, source in enumerate(config.source_priority_order())}
    fallback_rank = len(priority)
    groups: list[dict[str, Any]] = []
    members: list[dict[str, Any]] = []
    for group in range(1, int(group_labels.max()) + 1 if len(group_labels) else 1):
        idx = np.flatnonzero(group_labels == group)
        if not len(idx):
            continue
        sums = d_final[np.ix_(idx, idx)].sum(axis=1)  # medoid: smallest summed distance to the rest
        order = sorted(
            range(len(idx)),
            key=lambda t: (
                round(float(sums[t]), 12),
                priority.get(desc.sources[idx[t]], fallback_rank),
                desc.keys[idx[t]],
            ),
        )
        rep = int(idx[order[0]])
        groups.append(
            {
                "group": group,
                "representative": desc.labels[rep],
                "representative_name": desc.keys[rep],
                "n_members": int(len(idx)),
                "members": "; ".join(desc.labels[i] for i in idx),
                "sources": "; ".join(sorted({desc.sources[i] for i in idx})),
                "max_intra_A": float(d_final[np.ix_(idx, idx)].max()) if len(idx) > 1 else 0.0,
            }
        )
        for i in idx:
            members.append(
                {
                    "group": group,
                    "name": desc.keys[i],
                    "label": desc.labels[i],
                    "source": desc.sources[i],
                    "is_representative": int(i) == rep,
                    "distance_to_representative_A": float(d_final[i, rep]),
                }
            )
    return groups, members


# ── reference (verification only) ────────────────────────────────────────────
def reference_groups(desc: Descriptors, config: SimilarityConfig, cache: EmdCache | None = None) -> np.ndarray:
    """Groups from full pairwise PDD EMD at ``k_pdd`` (O(N^2) EMD; for verification only)."""
    n = len(desc)
    if n < 2:
        return np.arange(1, n + 1)
    cache = cache or EmdCache(desc.pdd, config.metric, config.n_jobs)
    matrix = cache.matrix(config.k_pdd, range(n))
    tree = linkage(squareform(matrix, checks=False), method=config.linkage)
    return _canonical_labels(fcluster(tree, config.tau, criterion="distance"))


def same_partition(labels_a: Sequence[int], labels_b: Sequence[int]) -> bool:
    """True if two labelings describe the same grouping (label values may differ)."""
    return bool(np.array_equal(_canonical_labels(np.asarray(labels_a)), _canonical_labels(np.asarray(labels_b))))
