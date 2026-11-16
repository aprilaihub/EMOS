"""End-to-end AMD screen -> PDD confirm pipeline.

    load CIFs -> descriptors (PDD once) -> stage 1 AMD (all) -> stage 2 PDD (candidates)
              -> groups / representatives -> vectors, t-SNE, dendrogram, heatmap, run_info.json
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform

from . import outputs, plotting
from ._report import Reporter
from .config import SimilarityConfig
from .descriptors import Descriptors, amd_distance_matrix, compute_descriptors
from .embedding import embed_tsne
from .loading import LoadResult, StructureRecord, build_metadata, load_structures
from .screening import EmdCache, ScreenResult, screen


@dataclass
class PipelineResult:
    """Everything produced by one run (all arrays are also written to ``run_dir``)."""

    run_dir: Path
    config: SimilarityConfig
    descriptors: Descriptors
    screen: ScreenResult
    run_info: dict[str, Any]
    files: list[str] = field(default_factory=list)
    tsne: pd.DataFrame | None = None
    amd_leaf_order: list[str] = field(default_factory=list)

    @property
    def representatives(self) -> list[str]:
        return [g["representative"] for g in self.screen.groups]

    def summary(self) -> dict[str, Any]:
        """JSON-safe digest used by the predictor / CLI."""
        return {
            "run_dir": str(self.run_dir),
            "stage_counts": self.screen.counts,
            "bound_check": self.screen.bound_check,
            "representatives": self.representatives,
            "warnings": self.run_info["warnings"],
            "outputs": self.files,
        }


def run_similarity_pipeline(config: SimilarityConfig, verbose: bool = False) -> PipelineResult:
    """Run the full pipeline and write every output into a timestamped run directory."""
    report = Reporter(verbose)
    started = datetime.datetime.now()
    timestamp = started.strftime("%Y%m%d_%H%M%S")
    run_dir = outputs.make_run_dir(config.output_dir)
    files: list[str] = []
    report.info(f"Run directory: {run_dir}")
    if not config.screen_is_exact:
        report.warn(
            f"linkage {config.linkage!r} depends on distance values, so screened groups may differ from full "
            "pairwise PDD grouping; use 'complete' or 'single' for an exact screen"
        )

    # ── load ──────────────────────────────────────────────────────────────────
    loaded: LoadResult = load_structures(config, report)
    outputs.write_json(run_dir / "parse_warnings.json", loaded.parse_log)
    files.append("parse_warnings.json")

    # ── descriptors ───────────────────────────────────────────────────────────
    desc, desc_skipped, crosscheck_failures = compute_descriptors(loaded.records, config, report)
    skipped = loaded.skipped + desc_skipped
    kept = {key for key in desc.keys}
    records: list[StructureRecord] = [r for r in loaded.records if r.key in kept]

    metadata = build_metadata(records, config, report)
    metadata.to_csv(run_dir / "cif_metadata.csv", index=False)
    files.append("cif_metadata.csv")
    outputs.write_amd_descriptors(run_dir / "amd_descriptors.csv", desc, config.k_amd)
    files.append("amd_descriptors.csv")
    _warn_k_reliable(metadata, config, report)

    # ── staged screening ──────────────────────────────────────────────────────
    cache = EmdCache(desc.pdd, config.metric, config.n_jobs)
    result = screen(desc, config, cache)
    counts = result.counts
    report.info(
        f"Stage 1 (AMD, k={config.k_amd}, tau={config.tau} A): {counts['n_candidate_pairs']} candidate pairs of "
        f"{counts['n_pairs_total']}; {counts['n_unique_after_stage1']} structures unique, "
        f"{counts['n_subset']} in the reduced subset."
    )
    report.info(
        f"Stage 2 (PDD EMD, k={config.k_pdd}): {counts['n_pdd_pairs_evaluated']} pairs evaluated, "
        f"{counts['n_pdd_pairs_saved']} saved; {counts['n_groups']} groups from {counts['n_structures']} structures."
    )
    if not result.bound_check["holds"]:
        report.warn(
            f"AMD <= EMD bound violated by {result.bound_check['max_violation_A']:.2e} A "
            f"(tolerance {result.bound_check['tolerance_A']:.2e} A)"
        )
    if counts["n_candidate_pairs"] == 0 and counts["n_structures"] > 0:
        report.warn("no candidate pairs: every structure is unique at this tau, so the PDD stage and t-SNE are skipped")

    pd.DataFrame(result.candidate_table, columns=["a", "b", "amd_A", "pdd_emd_A", "confirmed"]).to_csv(
        run_dir / "candidate_pairs.csv", index=False
    )
    pd.DataFrame(result.groups).to_csv(run_dir / "duplicate_groups.csv", index=False)
    pd.DataFrame(result.members).to_csv(run_dir / "group_members.csv", index=False)
    files += ["candidate_pairs.csv", "duplicate_groups.csv", "group_members.csv"]

    subset = result.subset
    outputs.write_pdd_store(run_dir / "pdd_store.pkl", run_dir / "pdd_store.csv", desc, subset, config.k_max)
    files += ["pdd_store.pkl", "pdd_store.csv"]
    _warn_subset_k_reliable(metadata, subset, config, report)

    # ── figures and embedding ─────────────────────────────────────────────────
    amd_leaf_names: list[str] = []
    with plotting.figure_style(config, report):
        amd_leaf_names = _amd_dendrogram_and_heatmap(desc, config, run_dir, files, report)
        tsne_frame = _tsne(desc, config, cache, subset, result, run_dir, files, report)
        if config.plot_pdd_subset:
            _pdd_subset_plots(desc, config, cache, subset, run_dir, files, report)

    # ── optional extras ───────────────────────────────────────────────────────
    extras: dict[str, Any] = {}
    if config.validate_structure_matcher and len(records) > 1:
        from .optional import structure_matcher_validation

        extras["structure_matcher_validation"] = structure_matcher_validation(records, result.group_labels, report)
    if config.species_test and records:
        from .optional import species_test

        extras["species_test"] = species_test(records[0], config.k_pdd, config.metric, config.collapse_tol)
    if config.sensitivity_sweep and len(desc) > 1:
        from .optional import sensitivity_sweep

        sweep = sensitivity_sweep(desc, config)
        sweep.to_csv(run_dir / "sensitivity_sweep.csv", index=False)
        files.append("sensitivity_sweep.csv")

    counts_out = dict(counts)
    counts_out.update(
        {
            "n_files_discovered": len(loaded.discovered),
            "n_filtered_out_by_composition": len(loaded.filtered_out),
            "n_skipped": len(skipped),
            "n_loaded": len(loaded.records),
        }
    )
    files.append("run_info.json")
    run_info = outputs.build_run_info(
        config,
        run_dir,
        timestamp,
        loaded.discovered,
        counts_out,
        result.bound_check,
        skipped,
        loaded.filtered_out,
        crosscheck_failures,
        report.warnings,
        files,
        {"duration_s": round((datetime.datetime.now() - started).total_seconds(), 2), **extras},
    )
    outputs.write_json(run_dir / "run_info.json", run_info)
    report.info(f"Done. {len(files)} output files written to {run_dir}")

    return PipelineResult(
        run_dir=run_dir,
        config=config,
        descriptors=desc,
        screen=result,
        run_info=run_info,
        files=files,
        tsne=tsne_frame,
        amd_leaf_order=amd_leaf_names,
    )


# ── helpers ──────────────────────────────────────────────────────────────────
def _warn_k_reliable(metadata: pd.DataFrame, config: SimilarityConfig, report: Reporter) -> None:
    """Warn when k_amd exceeds k_reliable for periodic models (small P1 cells with periodic-image artefacts)."""
    if metadata.empty:
        return
    models = metadata[metadata["is_periodic_model"]]
    n_low = int((models["k_reliable"] < config.k_amd).sum())
    if n_low:
        report.warn(
            f"{n_low} of {len(models)} periodic models have k_reliable < k_amd = {config.k_amd} "
            f"(smallest {int(models['k_reliable'].min())}); neighbour distances beyond the inscribed sphere "
            "depend on periodic images of the model cell"
        )


def _warn_subset_k_reliable(
    metadata: pd.DataFrame, subset: np.ndarray, config: SimilarityConfig, report: Reporter
) -> None:
    if metadata.empty or not len(subset):
        return
    models = metadata.iloc[subset]
    models = models[models["is_periodic_model"]]
    for name, k in (("k_pdd", config.k_pdd), ("k_tsne", config.k_tsne_effective)):
        n_low = int((models["k_reliable"] < k).sum())
        if n_low:
            report.warn(
                f"{n_low} of {len(models)} periodic models in the subset have k_reliable < {name} = {k} "
                f"(smallest {int(models['k_reliable'].min())})"
            )


def _ordered_matrix(matrix: np.ndarray, config: SimilarityConfig) -> tuple[np.ndarray, list[int]]:
    """Linkage tree of a distance matrix and its dendrogram leaf order."""
    tree = linkage(squareform(matrix, checks=False), method=config.linkage, optimal_ordering=True)
    return tree, plotting.leaf_order(tree)


def _amd_dendrogram_and_heatmap(
    desc: Descriptors, config: SimilarityConfig, run_dir: Path, files: list[str], report: Reporter
) -> list[str]:
    n = len(desc)
    if n < 2:
        report.warn(f"{n} structure(s) after filtering: AMD dendrogram and heatmap skipped")
        return list(desc.labels)
    d_amd = amd_distance_matrix(desc.amd, config.k_amd, config.metric)
    tree, order = _ordered_matrix(d_amd, config)
    labels = [desc.labels[i] for i in order]
    ordered = d_amd[np.ix_(order, order)]
    outputs.write_matrix(run_dir / f"amd_distance_matrix_k{config.k_amd:03d}.csv", ordered, labels)
    files.append(f"amd_distance_matrix_k{config.k_amd:03d}.csv")

    metric_name = config.metric.capitalize()
    fig = plotting.plot_dendrogram(
        tree, desc.labels, config,
        f"{config.linkage.capitalize()} linkage (AMD, {metric_name}, k={config.k_amd}) [A]",
    )
    files += plotting.save_figure(fig, run_dir / "amd_dendrogram", config)
    highlight = _resolve_highlight(desc, config, report)
    fig = plotting.plot_heatmap(
        ordered, labels, config, f"AMD distance, {metric_name} [A] (k={config.k_amd})", highlight
    )
    files += plotting.save_figure(fig, run_dir / "amd_heatmap", config)
    return labels


def _resolve_highlight(desc: Descriptors, config: SimilarityConfig, report: Reporter) -> list[str]:
    """Highlights are drawn only if the user supplied names; match on label or key."""
    resolved = []
    for name in config.highlight:
        if name in desc.labels:
            resolved.append(name)
        elif name in desc.keys:
            resolved.append(desc.labels[desc.keys.index(name)])
        else:
            report.warn(f"highlight target {name!r} is not in the dataset")
    return resolved


def _tsne(
    desc: Descriptors,
    config: SimilarityConfig,
    cache: EmdCache,
    subset: np.ndarray,
    result: ScreenResult,
    run_dir: Path,
    files: list[str],
    report: Reporter,
) -> pd.DataFrame | None:
    n_sub = len(subset)
    if n_sub < config.tsne_min_structures:
        report.warn(
            f"reduced subset has {n_sub} structure(s) (< {config.tsne_min_structures}): t-SNE skipped"
        )
        return None
    k = config.k_tsne_effective
    matrix = cache.matrix(k, subset)
    labels = [desc.labels[i] for i in subset]
    outputs.write_matrix(run_dir / f"pdd_emd_matrix_k{k:03d}.csv", matrix, labels)
    files.append(f"pdd_emd_matrix_k{k:03d}.csv")
    embedding = embed_tsne(matrix, config.tsne_random_state)
    frame = pd.DataFrame(
        {
            "name": [desc.keys[i] for i in subset],
            "label": labels,
            "source": [desc.sources[i] for i in subset],
            "group": result.group_labels[subset],
            "tsne_1": embedding.coords[:, 0],
            "tsne_2": embedding.coords[:, 1],
        }
    )
    frame.to_csv(run_dir / "tsne_coords.csv", index=False)
    files.append("tsne_coords.csv")
    report.info(
        f"t-SNE on PDD EMD at k={k}: {n_sub} structures, perplexity {embedding.perplexity:.1f}, "
        f"KL divergence {embedding.kl_divergence:.4f}"
    )
    fig = plotting.plot_tsne(embedding.coords, labels, [desc.sources[i] for i in subset], config, k)
    files += plotting.save_figure(fig, run_dir / "tsne", config)
    return frame


def _pdd_subset_plots(
    desc: Descriptors,
    config: SimilarityConfig,
    cache: EmdCache,
    subset: np.ndarray,
    run_dir: Path,
    files: list[str],
    report: Reporter,
) -> None:
    if len(subset) < 2:
        report.warn("PDD subset plots skipped: fewer than 2 structures in the reduced subset")
        return
    matrix = cache.matrix(config.k_pdd, subset)
    tree, order = _ordered_matrix(matrix, config)
    names = [desc.labels[i] for i in subset]
    labels = [names[i] for i in order]
    ordered = matrix[np.ix_(order, order)]
    outputs.write_matrix(run_dir / f"pdd_subset_emd_matrix_k{config.k_pdd:03d}.csv", ordered, labels)
    files.append(f"pdd_subset_emd_matrix_k{config.k_pdd:03d}.csv")
    metric_name = config.metric.capitalize()
    fig = plotting.plot_dendrogram(
        tree, names, config, f"{config.linkage.capitalize()} linkage (PDD EMD, {metric_name}, k={config.k_pdd}) [A]"
    )
    files += plotting.save_figure(fig, run_dir / "pdd_dendrogram", config)
    fig = plotting.plot_heatmap(ordered, labels, config, f"PDD EMD, {metric_name} [A] (k={config.k_pdd})")
    files += plotting.save_figure(fig, run_dir / "pdd_heatmap", config)
