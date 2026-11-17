"""Unit tests for the PDD similarity pipeline (no CIF fixtures needed)."""

import json

import amd
import numpy as np
import pytest
from amd import PeriodicSet
from pymatgen.core import Lattice, Structure

from Information_Units.Predictors.Pdd.similarity.config import ConfigError, SimilarityConfig
from Information_Units.Predictors.Pdd.similarity.descriptors import (
    Descriptors,
    amd_distance_matrix,
    amd_from_pdd,
    bound_tolerance,
    compute_pdd,
    descriptor_problems,
    emd,
)
from Information_Units.Predictors.Pdd.similarity.loading import (
    CartesianConventionError,
    assign_source,
    check_cartesian,
    k_reliable_for,
    structure_to_periodicset,
)
from Information_Units.Predictors.Pdd.similarity.screening import (
    EmdCache,
    reference_groups,
    same_partition,
    screen,
    stage1_amd,
)

pytestmark = pytest.mark.unit


# ── helpers ──────────────────────────────────────────────────────────────────
def cubic_descriptors(edges, sources=None, names=None, k_max=12, collapse_tol=1e-4):
    """Simple-cubic, one-atom cells: AMD_1 = a, so AMD distances are easy to reason about."""
    pdds, amds = [], []
    for a in edges:
        ps = PeriodicSet(np.zeros((1, 3)), a * np.eye(3))
        pdd = compute_pdd(ps, k_max, collapse_tol)
        pdds.append(pdd)
        amds.append(amd_from_pdd(pdd))
    n = len(edges)
    keys = names or [f"S/{i}.cif" for i in range(n)]
    return Descriptors(
        keys=keys,
        labels=[k.split("/")[-1].replace(".cif", "") for k in keys],
        sources=sources or ["S"] * n,
        pdd=pdds,
        amd=np.vstack(amds),
    )


def rock_salt(a=4.2):
    return Structure.from_spacegroup("Fm-3m", Lattice.cubic(a), ["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])


# ── configuration ────────────────────────────────────────────────────────────
class TestConfigValidation:
    def test_defaults_are_valid(self):
        cfg = SimilarityConfig(input_dirs=["x"])
        assert cfg.k_amd <= cfg.k_pdd <= cfg.k_max
        assert cfg.k_tsne_effective == cfg.k_pdd
        assert cfg.metric == "euclidean" and cfg.linkage == "complete"

    def test_k_pdd_below_k_amd_rejected(self):
        with pytest.raises(ConfigError, match="k_pdd"):
            SimilarityConfig(input_dirs=["x"], k_amd=20, k_pdd=10)

    def test_k_max_below_k_pdd_rejected(self):
        with pytest.raises(ConfigError, match="k_max"):
            SimilarityConfig(input_dirs=["x"], k_amd=5, k_pdd=30, k_max=20)

    def test_k_tsne_above_k_max_rejected(self):
        with pytest.raises(ConfigError, match="k_tsne"):
            SimilarityConfig(input_dirs=["x"], k_max=50, k_tsne=60)

    @pytest.mark.parametrize("metric", ["cosine", "correlation"])
    def test_non_norm_metrics_rejected(self, metric):
        with pytest.raises(ConfigError, match="not a norm"):
            SimilarityConfig(input_dirs=["x"], metric=metric)

    def test_unknown_metric_rejected(self):
        with pytest.raises(ConfigError, match="metric"):
            SimilarityConfig(input_dirs=["x"], metric="minkowski")

    @pytest.mark.parametrize("metric", ["cityblock", "chebyshev"])
    def test_ward_requires_euclidean(self, metric):
        with pytest.raises(ConfigError, match="ward"):
            SimilarityConfig(input_dirs=["x"], metric=metric, linkage="ward")

    def test_ward_with_euclidean_allowed(self):
        cfg = SimilarityConfig(input_dirs=["x"], metric="euclidean", linkage="ward")
        assert not cfg.screen_is_exact

    @pytest.mark.parametrize("metric", ["euclidean", "cityblock", "chebyshev"])
    def test_allowed_metrics(self, metric):
        assert SimilarityConfig(input_dirs=["x"], metric=metric).metric == metric

    @pytest.mark.parametrize("tau", [-0.1, float("nan"), float("inf")])
    def test_bad_tau_rejected(self, tau):
        with pytest.raises(ConfigError, match="tau"):
            SimilarityConfig(input_dirs=["x"], tau=tau)

    def test_non_integer_k_rejected(self):
        with pytest.raises(ConfigError):
            SimilarityConfig(input_dirs=["x"], k_amd=2.5)
        with pytest.raises(ConfigError):
            SimilarityConfig(input_dirs=["x"], k_amd=True)

    def test_unknown_key_rejected(self):
        with pytest.raises(ConfigError, match="Unknown"):
            SimilarityConfig.from_dict({"input_dirs": ["x"], "k_amd_typo": 3})

    def test_json_round_trip(self, tmp_path):
        cfg = SimilarityConfig(input_dirs=["a", "b"], k_amd=7, k_pdd=9, tau=0.2, composition_filter=["ZnO"])
        path = tmp_path / "cfg.json"
        path.write_text(json.dumps(cfg.to_dict()), encoding="utf-8")
        assert SimilarityConfig.from_json(path) == cfg

    def test_source_priority_default_follows_prefix_map(self):
        cfg = SimilarityConfig(input_dirs=["x"], source_prefixes={"a-": "A", "b-": "B"}, default_source="Z")
        assert cfg.source_priority_order() == ["A", "B", "Z"]

    def test_assign_source(self):
        prefixes = {"mp-": "MP", "cod-": "COD"}
        assert assign_source("mp-1.cif", prefixes, "other") == "MP"
        assert assign_source("zzz.cif", prefixes, "other") == "other"


# ── coordinates ──────────────────────────────────────────────────────────────
class TestCoordinates:
    def test_fractional_motif_passed_as_cartesian_raises(self):
        fractional = np.array([[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]])
        with pytest.raises(CartesianConventionError):
            check_cartesian(fractional, 4.2 * np.eye(3), "frac")

    def test_cartesian_motif_passes(self):
        check_cartesian(np.array([[0.0, 0.0, 0.0], [2.1, 2.1, 2.1]]), 4.2 * np.eye(3), "cart")

    def test_single_atom_motif_is_never_flagged(self):
        check_cartesian(np.zeros((1, 3)), 4.2 * np.eye(3), "single")

    def test_structure_conversion_uses_cartesian(self):
        structure = rock_salt()
        ps = structure_to_periodicset(structure, "nacl")
        assert np.allclose(ps.motif, structure.cart_coords)
        assert np.allclose(ps.cell, structure.lattice.matrix)

    def test_pdd_weights_sum_to_one_and_checks_pass(self):
        pdd = compute_pdd(structure_to_periodicset(rock_salt()), 20, 1e-4)
        assert abs(pdd[:, 0].sum() - 1.0) < 1e-9
        assert descriptor_problems(pdd, min_nn_dist=0.5) == []

    def test_nearest_neighbour_floor_is_configurable(self):
        pdd = compute_pdd(structure_to_periodicset(rock_salt()), 5, 1e-4)  # nearest neighbour 2.1 A
        assert descriptor_problems(pdd, min_nn_dist=3.0)
        assert descriptor_problems(pdd, min_nn_dist=1.0) == []

    def test_non_finite_pdd_flagged(self):
        pdd = np.array([[1.0, np.nan, 2.0]])
        assert descriptor_problems(pdd, 0.5) == ["PDD contains non-finite values"]

    def test_decreasing_row_flagged(self):
        pdd = np.array([[1.0, 3.0, 2.0]])
        assert any("non-decreasing" in p for p in descriptor_problems(pdd, 0.5))

    def test_amd_is_weighted_mean_of_pdd_rows(self):
        ps = structure_to_periodicset(rock_salt())
        pdd = compute_pdd(ps, 15, 1e-4)
        assert np.allclose(amd_from_pdd(pdd), amd.AMD(ps, 15), atol=1e-3)
        assert np.allclose(amd_from_pdd(pdd, 5), amd_from_pdd(pdd)[:5])

    def test_supercell_invariance(self):
        base = rock_salt()
        supercell = base.copy()
        supercell.make_supercell([2, 2, 2])
        pdd_a = compute_pdd(structure_to_periodicset(base), 30, 1e-4)
        pdd_b = compute_pdd(structure_to_periodicset(supercell), 30, 1e-4)
        assert emd(pdd_a, pdd_b, 30, "euclidean") <= 1e-5

    def test_k_reliable_grows_with_cell(self):
        small = rock_salt()
        large = small.copy()
        large.make_supercell([3, 3, 3])
        assert k_reliable_for(large) > k_reliable_for(small) >= 1


# ── screening ────────────────────────────────────────────────────────────────
class TestScreening:
    def test_bound_tolerance_per_metric(self):
        assert bound_tolerance("euclidean", 16, 1e-4) == pytest.approx(2e-4 * 4)
        assert bound_tolerance("cityblock", 16, 1e-4) == pytest.approx(2e-4 * 16)
        assert bound_tolerance("chebyshev", 16, 1e-4) == pytest.approx(2e-4)

    def test_stage1_components(self):
        d = np.array(
            [
                [0.0, 0.05, 9.0, 9.0, 9.0],
                [0.05, 0.0, 9.0, 9.0, 9.0],
                [9.0, 9.0, 0.0, 0.08, 9.0],
                [9.0, 9.0, 0.08, 0.0, 9.0],
                [9.0, 9.0, 9.0, 9.0, 0.0],
            ]
        )
        s1 = stage1_amd(d, 0.1)
        assert s1.candidate_pairs == [(0, 1), (2, 3)]
        assert s1.n_components == 3
        assert s1.subset.tolist() == [0, 1, 2, 3]  # structure 4 is unique and needs no PDD

    def test_stage1_without_candidates(self):
        s1 = stage1_amd(np.array([[0.0, 5.0], [5.0, 0.0]]), 0.1)
        assert s1.candidate_pairs == [] and len(s1.subset) == 0

    def test_stage1_single_structure(self):
        s1 = stage1_amd(np.zeros((1, 1)), 0.1)
        assert s1.n_components == 1 and len(s1.subset) == 0

    def test_screen_groups_and_pair_savings(self):
        desc = cubic_descriptors([3.0, 3.0, 3.03, 5.0, 7.0, 7.02])
        cfg = SimilarityConfig(input_dirs=["x"], k_amd=3, k_pdd=6, k_max=12, tau=0.1, metric="chebyshev")
        result = screen(desc, cfg)
        assert same_partition(result.group_labels, [1, 1, 1, 2, 3, 3])
        assert result.counts["n_pairs_total"] == 15
        assert result.counts["n_pdd_pairs_evaluated"] == result.counts["n_candidate_pairs"] == 4
        assert result.counts["n_pdd_pairs_saved"] == 11
        assert result.counts["n_subset"] == 5 and result.counts["n_unique_after_stage1"] == 1
        assert result.bound_check["holds"]

    @pytest.mark.parametrize("metric", ["euclidean", "cityblock", "chebyshev"])
    @pytest.mark.parametrize("linkage", ["complete", "single"])
    def test_screen_equals_full_pairwise_pdd(self, metric, linkage):
        rng = np.random.default_rng(3)
        edges = np.concatenate([[3.0, 3.01, 3.02, 3.2, 3.21], rng.uniform(4.0, 9.0, 8)])
        desc = cubic_descriptors(edges, k_max=20)
        cfg = SimilarityConfig(
            input_dirs=["x"], k_amd=4, k_pdd=12, k_max=20, tau=0.1, metric=metric, linkage=linkage
        )
        assert same_partition(screen(desc, cfg).group_labels, reference_groups(desc, cfg))

    def test_representative_ties_break_by_source_priority_then_id(self):
        desc = cubic_descriptors(
            [3.0, 3.0, 3.0],
            sources=["MP", "COD", "COD"],
            names=["MP/a.cif", "COD/z.cif", "COD/b.cif"],
        )
        cfg = SimilarityConfig(
            input_dirs=["x"], k_amd=2, k_pdd=4, k_max=12, tau=0.1, source_priority=["COD", "MP"]
        )
        result = screen(desc, cfg)
        assert len(result.groups) == 1
        assert result.groups[0]["representative_name"] == "COD/b.cif"  # COD beats MP; b < z

    def test_representative_is_medoid(self):
        desc = cubic_descriptors([3.00, 3.04, 3.08], names=["S/a.cif", "S/b.cif", "S/c.cif"])
        cfg = SimilarityConfig(input_dirs=["x"], k_amd=2, k_pdd=4, k_max=12, tau=0.1, metric="chebyshev")
        result = screen(desc, cfg)
        assert result.groups[0]["representative_name"] == "S/b.cif"

    def test_empty_and_single_descriptor_sets(self):
        cfg = SimilarityConfig(input_dirs=["x"], k_amd=2, k_pdd=4, k_max=12)
        one = screen(cubic_descriptors([3.0]), cfg)
        assert one.counts["n_groups"] == 1 and one.counts["n_candidate_pairs"] == 0
        empty = Descriptors([], [], [], [], np.zeros((0, 12)))
        zero = screen(empty, cfg)
        assert zero.counts["n_groups"] == 0

    def test_lower_bound_amd_le_emd_for_all_metrics(self):
        rng = np.random.default_rng(1)
        desc = cubic_descriptors(rng.uniform(3.0, 6.0, 10), k_max=15)
        for metric in ("euclidean", "cityblock", "chebyshev"):
            d_amd = amd_distance_matrix(desc.amd, 5, metric)
            d_emd = EmdCache(desc.pdd, metric).matrix(10, range(len(desc)))
            assert (d_amd - d_emd).max() <= bound_tolerance(metric, 10, 1e-4)

    def test_emd_cache_is_symmetric_and_reused(self):
        desc = cubic_descriptors([3.0, 4.0, 5.0])
        cache = EmdCache(desc.pdd, "euclidean")
        first = cache.get_pairs(5, [(0, 1), (1, 0)])
        assert first[0] == first[1]
        assert len(cache.cached(5)) == 1
        matrix = cache.matrix(5, [0, 1, 2])
        assert np.allclose(matrix, matrix.T) and np.allclose(np.diag(matrix), 0)

    def test_same_partition_ignores_label_values(self):
        assert same_partition([5, 5, 2], [1, 1, 9])
        assert not same_partition([1, 1, 2], [1, 2, 2])
