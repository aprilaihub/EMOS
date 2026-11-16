"""Integration tests for the AMD screen -> PDD confirm pipeline on the CIF fixtures (ZnO set)."""

import json
import sys
from pathlib import Path

import amd
import numpy as np
import pandas as pd
import pytest
from amd import AMD, PeriodicSet
from pymatgen.io.cif import CifParser
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from Information_Units.Predictors.Pdd.similarity import SimilarityConfig, run_similarity_pipeline
from Information_Units.Predictors.Pdd.similarity._report import Reporter
from Information_Units.Predictors.Pdd.similarity.descriptors import (
    amd_distance_matrix,
    bound_tolerance,
    compute_descriptors,
)
from Information_Units.Predictors.Pdd.similarity.loading import load_structures
from Information_Units.Predictors.Pdd.similarity.screening import EmdCache, reference_groups, same_partition, screen

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "cif_files"
SOURCES = ["mp", "cod", "oqmd", "mg"]
SOURCE_PRIORITY = ["COD", "MP", "OQMD", "MATTERGEN"]
K_MAX = 30


def make_config(tmp_path, **overrides):
    params = dict(
        input_dirs=[str(FIXTURES / s) for s in SOURCES],
        output_dir=str(tmp_path),
        composition_filter=["ZnO"],
        k_amd=15,
        k_pdd=30,
        k_max=K_MAX,
        tau=0.1,
        source_priority=SOURCE_PRIORITY,
    )
    params.update(overrides)
    return SimilarityConfig(**params)


@pytest.fixture(scope="module")
def zno(tmp_path_factory):
    cfg = make_config(tmp_path_factory.mktemp("zno"))
    report = Reporter()
    loaded = load_structures(cfg, report)
    desc, skipped, _ = compute_descriptors(loaded.records, cfg, report)
    return {"cfg": cfg, "loaded": loaded, "desc": desc, "skipped": skipped}


# ── verification: coordinates and parser ─────────────────────────────────────
def test_fixture_set_loads(zno):
    assert len(zno["desc"]) >= 100
    assert not zno["skipped"]
    assert all(r.structure.composition.reduced_formula == "ZnO" for r in zno["loaded"].records)


def test_weights_sum_to_one_for_every_structure(zno):
    for key, pdd in zip(zno["desc"].keys, zno["desc"].pdd):
        assert abs(pdd[:, 0].sum() - 1.0) < 1e-9, key
        assert np.isfinite(pdd).all(), key


def test_structures_keyed_by_source_and_relative_path(zno):
    keys = zno["desc"].keys
    assert len(set(keys)) == len(keys)
    assert "MP/mp-2133.cif" in keys and "COD/cod-2300112.cif" in keys


def test_cifreader_agrees_with_pipeline(tmp_path):
    cfg = make_config(tmp_path, crosscheck_cifreader=True, k_max=K_MAX, k_pdd=K_MAX)
    report = Reporter()
    loaded = load_structures(cfg, report)
    desc, _, failures = compute_descriptors(loaded.records, cfg, report)
    assert len(desc) > 100
    assert failures == []


@pytest.mark.parametrize(
    "name, closed_form",
    [
        ("MP/mp-2229.cif", lambda a: a / 2),  # rock salt
        ("MP/mp-1986.cif", lambda a: np.sqrt(3) * a / 4),  # zinc blende
        ("MP/mp-13161.cif", lambda a: np.sqrt(3) * a / 2),  # CsCl type
    ],
)
def test_analytic_amd1(zno, name, closed_form):
    desc, records = zno["desc"], {r.key: r for r in zno["loaded"].records}
    a_conv = SpacegroupAnalyzer(records[name].structure).get_conventional_standard_structure().lattice.a
    assert abs(desc.amd[desc.keys.index(name), 0] - closed_form(a_conv)) <= 1e-4


# ── verification: lower bound and screen equivalence ─────────────────────────
@pytest.mark.parametrize("metric", ["euclidean", "cityblock", "chebyshev"])
def test_amd_is_lower_bound_of_emd_for_all_pairs(zno, metric):
    desc = zno["desc"]
    d_amd = amd_distance_matrix(desc.amd, 15, metric)
    d_emd = EmdCache(desc.pdd, metric).matrix(30, range(len(desc)))
    assert (d_amd - d_emd).max() <= bound_tolerance(metric, 30, 1e-4)


@pytest.mark.parametrize("metric", ["euclidean", "cityblock", "chebyshev"])
@pytest.mark.parametrize("linkage_method", ["complete", "single"])
@pytest.mark.parametrize("tau", [0.03, 0.1, 0.3])
def test_screened_groups_equal_full_pairwise_pdd_groups(zno, metric, linkage_method, tau):
    cfg = make_config(zno["cfg"].output_dir, metric=metric, linkage=linkage_method, tau=tau)
    desc = zno["desc"]
    cache = EmdCache(desc.pdd, metric)
    result = screen(desc, cfg, cache)
    assert same_partition(result.group_labels, reference_groups(desc, cfg, cache))
    assert result.bound_check["holds"]
    assert result.counts["n_pdd_pairs_evaluated"] <= result.counts["n_pairs_total"]


def test_screen_saves_pdd_pairs(zno):
    result = screen(zno["desc"], zno["cfg"])
    counts = result.counts
    assert counts["n_pdd_pairs_saved"] > 0
    assert counts["n_pdd_pairs_saved"] + counts["n_pdd_pairs_evaluated"] == counts["n_pairs_total"]
    assert counts["n_subset"] + counts["n_unique_after_stage1"] == counts["n_structures"]


def test_complete_linkage_guarantees_pairwise_tau(zno):
    result = screen(zno["desc"], zno["cfg"])
    assert max(g["max_intra_A"] for g in result.groups) <= zno["cfg"].tau + 1e-12


# ── verification: regression against an independent v7-style computation ─────
@pytest.fixture(scope="module")
def regression_run(tmp_path_factory):
    cfg = make_config(tmp_path_factory.mktemp("reg"), k_amd=5, k_pdd=15, linkage="ward", metric="euclidean")
    return run_similarity_pipeline(cfg)


def test_regression_against_v7_style_computation(regression_run):
    res = regression_run
    paths = {f["name"]: Path(f["path"]) for f in res.run_info["input_files"]}
    # independent path: CifParser -> Cartesian PeriodicSet -> AMD (no PDD, no pipeline code),
    # ordered by file name as in v7
    ordered_keys = sorted(res.descriptors.keys, key=lambda key: (paths[key].name, key))
    vectors = []
    for key in ordered_keys:
        structure = CifParser(str(paths[key]), frac_tolerance=0).parse_structures(primitive=False)[0]
        ps = PeriodicSet(np.asarray(structure.cart_coords), np.asarray(structure.lattice.matrix))
        vectors.append(np.asarray(AMD(ps, 100), dtype=float))
    labels = [paths[key].stem for key in ordered_keys]

    table = pd.read_csv(res.run_dir / "amd_descriptors.csv").set_index("name")
    assert np.allclose(table.loc[ordered_keys].to_numpy(), np.vstack(vectors)[:, :5], atol=1e-3)  # amd_descriptors.csv

    cdm = amd.AMD_pdist(np.vstack(vectors)[:, :5], metric="euclidean")
    tree = linkage(cdm, method="ward", optimal_ordering=True)
    leaves = dendrogram(tree, no_plot=True)["leaves"]
    expected_order = [labels[i] for i in leaves]
    assert res.amd_leaf_order == expected_order  # dendrogram leaf order

    matrix = pd.read_csv(res.run_dir / "amd_distance_matrix_k005.csv", index_col=0)
    expected = squareform(cdm)[np.ix_(leaves, leaves)]
    assert np.allclose(matrix.to_numpy(), expected, atol=1e-3)  # AMD distance matrix


# ── verification: outputs ────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def full_run(tmp_path_factory):
    cfg = make_config(
        tmp_path_factory.mktemp("full"),
        plot_pdd_subset=True,
        highlight=["mp-2133", "cod-2300112", "not-a-structure"],
        crosscheck_cifreader=True,
        validate_structure_matcher=False,
        species_test=True,
    )
    return run_similarity_pipeline(cfg)


def test_run_directory_contains_all_output_types(full_run):
    expected = {
        "amd_descriptors.csv", "pdd_store.pkl", "pdd_store.csv", "cif_metadata.csv",  # vectors
        "tsne_coords.csv", "tsne.png",  # t-SNE
        "amd_dendrogram.png", "amd_heatmap.png", "amd_distance_matrix_k015.csv",  # dendrogram + heatmap
        "pdd_dendrogram.png", "pdd_heatmap.png",  # optional PDD plots (flag on)
        "run_info.json", "parse_warnings.json", "duplicate_groups.csv", "group_members.csv", "candidate_pairs.csv",
    }
    present = {p.name for p in full_run.run_dir.iterdir()}
    assert expected <= present
    assert all((full_run.run_dir / name).stat().st_size > 0 for name in expected)


def test_vectors_and_scope(full_run):
    desc, counts = full_run.descriptors, full_run.screen.counts
    amd_table = pd.read_csv(full_run.run_dir / "amd_descriptors.csv")
    assert list(amd_table.columns) == ["name"] + [f"AMD_{i}" for i in range(1, 16)]
    assert len(amd_table) == len(desc)  # AMD vectors for the full set
    pdd_long = pd.read_csv(full_run.run_dir / "pdd_store.csv")
    assert pdd_long["name"].nunique() == counts["n_subset"]  # PDD only for the reduced subset
    tsne = pd.read_csv(full_run.run_dir / "tsne_coords.csv")
    assert len(tsne) == counts["n_subset"]
    metadata = pd.read_csv(full_run.run_dir / "cif_metadata.csv")
    assert len(metadata) == len(desc) and "k_reliable" in metadata.columns


def test_run_info_records_provenance(full_run):
    info = json.loads((full_run.run_dir / "run_info.json").read_text(encoding="utf-8"))
    for package in ("average-minimum-distance", "pymatgen", "numpy"):
        assert info["packages"][package] != "unknown"
    assert info["parameters"]["k_amd"] == 15 and info["parameters"]["metric"] == "euclidean"
    assert len(info["input_files"]) >= 100 and info["stage_counts"]["n_candidate_pairs"] > 0
    assert info["bound_check"]["holds"]
    assert info["species_test"]["pdd_emd_A"] < 1e-9  # PDD cannot see species
    assert any("highlight target 'not-a-structure'" in w for w in info["warnings"])


def test_figures_are_headless(full_run):
    if "matplotlib.pyplot" in sys.modules:
        import matplotlib.pyplot as plt

        assert plt.get_fignums() == []


def test_dendrogram_and_heatmap_share_leaf_order(full_run):
    matrix = pd.read_csv(full_run.run_dir / "amd_distance_matrix_k015.csv", index_col=0)
    assert list(matrix.index) == full_run.amd_leaf_order == list(matrix.columns)


# ── verification: edge cases ─────────────────────────────────────────────────
def _copy_cif(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def test_no_candidate_pairs_gives_empty_subset_and_no_tsne(tmp_path):
    folder = tmp_path / "in"
    for name in ("mp-2229", "mp-1986", "mp-13161"):  # rock salt, zinc blende, CsCl: clearly different
        _copy_cif(FIXTURES / "mp" / f"{name}.cif", folder / f"{name}.cif")
    cfg = SimilarityConfig(input_dirs=[str(folder)], output_dir=str(tmp_path / "out"), k_amd=5, k_pdd=10, k_max=10,
                           tau=0.01)
    result = run_similarity_pipeline(cfg)
    assert result.screen.counts["n_candidate_pairs"] == 0
    assert result.screen.counts["n_subset"] == 0 and result.screen.counts["n_groups"] == 3
    assert result.tsne is None and not (result.run_dir / "tsne_coords.csv").exists()
    assert any("no candidate pairs" in w for w in result.run_info["warnings"])
    assert (result.run_dir / "amd_heatmap.png").exists()
    assert pd.read_csv(result.run_dir / "pdd_store.csv").empty


def test_subset_below_four_skips_tsne(tmp_path):
    folder = tmp_path / "in"
    _copy_cif(FIXTURES / "mp" / "mp-2229.cif", folder / "mp-2229.cif")
    _copy_cif(FIXTURES / "mp" / "mp-2229.cif", folder / "copy-of-mp-2229.cif")
    _copy_cif(FIXTURES / "mp" / "mp-1986.cif", folder / "mp-1986.cif")
    cfg = SimilarityConfig(input_dirs=[str(folder)], output_dir=str(tmp_path / "out"), k_amd=5, k_pdd=10, k_max=10,
                           tau=0.05)
    result = run_similarity_pipeline(cfg)
    assert result.screen.counts["n_subset"] == 2 and result.screen.counts["n_groups"] == 2
    assert result.tsne is None
    assert any("t-SNE skipped" in w for w in result.run_info["warnings"])
    assert result.screen.groups[0]["representative"] == "mp-2229"  # MP source beats 'other'; ties by id


def test_single_structure_runs_cleanly(tmp_path):
    folder = tmp_path / "in"
    _copy_cif(FIXTURES / "mp" / "mp-2229.cif", folder / "mp-2229.cif")
    cfg = SimilarityConfig(input_dirs=[str(folder)], output_dir=str(tmp_path / "out"), k_amd=5, k_pdd=10, k_max=10)
    result = run_similarity_pipeline(cfg)
    assert result.screen.counts["n_groups"] == 1 and result.screen.counts["n_pairs_total"] == 0
    assert (result.run_dir / "run_info.json").exists() and result.tsne is None


def test_same_file_name_in_two_folders_is_not_overwritten(tmp_path):
    for folder in ("a", "b"):
        _copy_cif(FIXTURES / "mp" / "mp-2229.cif", tmp_path / folder / "mp-2229.cif")
    cfg = SimilarityConfig(input_dirs=[str(tmp_path / "a"), str(tmp_path / "b")], output_dir=str(tmp_path / "out"),
                           k_amd=5, k_pdd=10, k_max=10)
    loaded = load_structures(cfg, Reporter())
    assert len(loaded.records) == 2
    assert len({r.key for r in loaded.records}) == 2 and len({r.label for r in loaded.records}) == 2


def test_empty_after_composition_filter_runs_cleanly(tmp_path):
    cfg = make_config(tmp_path, composition_filter=["SiO2"])
    result = run_similarity_pipeline(cfg)
    assert result.screen.counts["n_structures"] == 0
    assert (result.run_dir / "run_info.json").exists()


def test_missing_input_folder_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_similarity_pipeline(SimilarityConfig(input_dirs=[str(tmp_path / "nope")], output_dir=str(tmp_path)))
