"""Validated configuration for the AMD screen -> PDD confirm similarity pipeline.

Every parameter that changes a result is validated here, so an invalid
combination is rejected before any structure is read.

Why the metric list is restricted
---------------------------------
The AMD screen is lossless only if ``AMD distance <= PDD EMD``.  That bound
holds when the same *norm* is used for the AMD distance and for the EMD ground
metric.  ``euclidean``, ``cityblock`` and ``chebyshev`` are norms; ``cosine`` and
``correlation`` are not, so the screen could silently drop true duplicates.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field, fields
from numbers import Integral, Real
from pathlib import Path
from typing import Any

ALLOWED_METRICS = ("euclidean", "cityblock", "chebyshev")
REJECTED_METRICS = ("cosine", "correlation")
ALLOWED_LINKAGES = ("complete", "single", "average", "ward")
# Only these linkages depend solely on which pairs are <= tau, which is what makes
# the AMD screen exactly equivalent to full pairwise PDD grouping.
EXACT_SCREEN_LINKAGES = ("complete", "single")
ALLOWED_DISORDER_POLICIES = ("warn", "skip")
ALLOWED_FIGURE_FORMATS = ("png", "pdf", "svg")

DEFAULT_SOURCE_PREFIXES = {
    "mp-": "MP",
    "cod-": "COD",
    "oqmd-": "OQMD",
    "mg-": "MATTERGEN",
}


class ConfigError(ValueError):
    """Raised when a pipeline configuration is invalid."""


def _is_int(value: Any) -> bool:
    return isinstance(value, Integral) and not isinstance(value, bool)


def _is_real(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


@dataclass
class SimilarityConfig:
    """Parameters for :func:`run_similarity_pipeline`.

    Neighbour indices
        ``k_amd``   neighbours used for the AMD screen (stage 1).
        ``k_pdd``   neighbours used for PDD confirmation (stage 2); ``>= k_amd``.
        ``k_max``   neighbours stored per structure; ``>= k_pdd``.
        ``k_tsne``  neighbours for the t-SNE EMD matrix (default: ``k_pdd``).

    ``tau`` is the duplicate threshold in angstrom.  ``metric`` is used both for the
    AMD distances and as the EMD ground metric.

    ``model_min_sites``: a P1 cell with at least this many sites is treated as a
    *periodic model* (e.g. a generated structure); ``k_reliable`` warnings apply to these.
    """

    # ── inputs ────────────────────────────────────────────────────────────────
    input_dirs: list[str] = field(default_factory=list)
    output_dir: str = "results"
    glob_pattern: str = "*.cif"
    recursive: bool = False
    source_prefixes: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_SOURCE_PREFIXES))
    default_source: str = "other"
    source_priority: list[str] = field(default_factory=list)
    composition_filter: list[str] | None = None
    disordered: str = "warn"

    # ── screening ─────────────────────────────────────────────────────────────
    k_amd: int = 15
    k_pdd: int = 30
    k_max: int = 100
    tau: float = 0.1
    metric: str = "euclidean"
    linkage: str = "complete"
    collapse_tol: float = 1e-4
    min_nn_dist: float = 0.5
    n_jobs: int = 1
    model_min_sites: int = 40

    # ── embedding ─────────────────────────────────────────────────────────────
    k_tsne: int | None = None
    tsne_random_state: int = 42
    tsne_min_structures: int = 4

    # ── checks ────────────────────────────────────────────────────────────────
    crosscheck_cifreader: bool = False
    crosscheck_tol: float = 1e-5

    # ── figures ───────────────────────────────────────────────────────────────
    plot_pdd_subset: bool = False
    highlight: list[str] = field(default_factory=list)
    font_family: str = "Arial"
    figure_dpi: int = 200
    figure_formats: list[str] = field(default_factory=lambda: ["png"])
    max_tick_labels: int = 60
    source_colors: dict[str, str] = field(default_factory=dict)

    # ── optional extras (off by default) ──────────────────────────────────────
    validate_structure_matcher: bool = False
    species_test: bool = False
    sensitivity_sweep: bool = False
    sweep_taus: list[float] = field(default_factory=lambda: [0.01, 0.03, 0.1, 0.3])
    sweep_ks: list[int] = field(default_factory=lambda: [5, 15, 30])
    sweep_metrics: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    # ── validation ────────────────────────────────────────────────────────────
    def validate(self) -> None:
        errors: list[str] = []

        if isinstance(self.input_dirs, (str, Path)):
            self.input_dirs = [str(self.input_dirs)]
        self.input_dirs = [str(p) for p in self.input_dirs]
        if isinstance(self.composition_filter, str):
            self.composition_filter = [self.composition_filter]
        if self.composition_filter is not None:
            self.composition_filter = [str(f) for f in self.composition_filter]
            if not self.composition_filter:
                self.composition_filter = None

        for name in ("k_amd", "k_pdd", "k_max"):
            value = getattr(self, name)
            if not _is_int(value) or value < 1:
                errors.append(f"{name} must be an integer >= 1 (got {value!r})")
        if not errors:
            if self.k_pdd < self.k_amd:
                errors.append(
                    f"k_pdd ({self.k_pdd}) must be >= k_amd ({self.k_amd}); otherwise "
                    "AMD <= EMD no longer holds and the screen could drop true duplicates"
                )
            if self.k_max < self.k_pdd:
                errors.append(f"k_max ({self.k_max}) must be >= k_pdd ({self.k_pdd})")
        if self.k_tsne is not None:
            if not _is_int(self.k_tsne) or self.k_tsne < 1:
                errors.append(f"k_tsne must be an integer >= 1 or null (got {self.k_tsne!r})")
            elif _is_int(self.k_max) and self.k_tsne > self.k_max:
                errors.append(f"k_tsne ({self.k_tsne}) must be <= k_max ({self.k_max})")

        if not _is_real(self.tau) or not math.isfinite(self.tau) or self.tau < 0:
            errors.append(f"tau must be a finite number >= 0 (got {self.tau!r})")
        for name in ("collapse_tol", "min_nn_dist", "crosscheck_tol"):
            value = getattr(self, name)
            if not _is_real(value) or not math.isfinite(value) or value < 0:
                errors.append(f"{name} must be a finite number >= 0 (got {value!r})")

        if self.metric in REJECTED_METRICS:
            errors.append(
                f"metric {self.metric!r} is not a norm, so AMD <= EMD does not hold and the "
                f"screen is not lossless; use one of {ALLOWED_METRICS}"
            )
        elif self.metric not in ALLOWED_METRICS:
            errors.append(f"metric must be one of {ALLOWED_METRICS} (got {self.metric!r})")

        if self.linkage not in ALLOWED_LINKAGES:
            errors.append(f"linkage must be one of {ALLOWED_LINKAGES} (got {self.linkage!r})")
        elif self.linkage == "ward" and self.metric != "euclidean":
            errors.append("linkage 'ward' requires metric 'euclidean'")

        if self.disordered not in ALLOWED_DISORDER_POLICIES:
            errors.append(f"disordered must be one of {ALLOWED_DISORDER_POLICIES} (got {self.disordered!r})")
        if not _is_int(self.n_jobs) or self.n_jobs < 1:
            errors.append(f"n_jobs must be an integer >= 1 (got {self.n_jobs!r})")
        if not _is_int(self.model_min_sites) or self.model_min_sites < 1:
            errors.append(f"model_min_sites must be an integer >= 1 (got {self.model_min_sites!r})")
        if not _is_int(self.tsne_min_structures) or self.tsne_min_structures < 2:
            errors.append("tsne_min_structures must be an integer >= 2")
        if not _is_int(self.figure_dpi) or self.figure_dpi < 1:
            errors.append("figure_dpi must be a positive integer")
        if not _is_int(self.max_tick_labels) or self.max_tick_labels < 0:
            errors.append("max_tick_labels must be an integer >= 0")
        bad_formats = [f for f in self.figure_formats if f not in ALLOWED_FIGURE_FORMATS]
        if bad_formats or not self.figure_formats:
            errors.append(f"figure_formats must be a non-empty subset of {ALLOWED_FIGURE_FORMATS}")
        if not isinstance(self.source_prefixes, dict):
            errors.append("source_prefixes must be a mapping of file-name prefix to source label")

        if self.sensitivity_sweep:
            if any(not _is_real(t) or t < 0 for t in self.sweep_taus) or not self.sweep_taus:
                errors.append("sweep_taus must be a non-empty list of numbers >= 0")
            if any(not _is_int(k) or k < 1 or k > self.k_max for k in self.sweep_ks) or not self.sweep_ks:
                errors.append("sweep_ks must be a non-empty list of integers in [1, k_max]")
            bad = [m for m in self.sweep_metrics if m not in ALLOWED_METRICS]
            if bad:
                errors.append(f"sweep_metrics must be a subset of {ALLOWED_METRICS} (got {bad})")

        if errors:
            raise ConfigError("Invalid configuration:\n  - " + "\n  - ".join(errors))

    # ── derived values ────────────────────────────────────────────────────────
    @property
    def k_tsne_effective(self) -> int:
        return self.k_tsne if self.k_tsne is not None else self.k_pdd

    @property
    def screen_is_exact(self) -> bool:
        """True when screened groups are guaranteed identical to full pairwise PDD groups."""
        return self.linkage in EXACT_SCREEN_LINKAGES

    def source_priority_order(self) -> list[str]:
        """Source labels from highest to lowest priority when choosing representatives."""
        if self.source_priority:
            return list(self.source_priority)
        return list(dict.fromkeys([*self.source_prefixes.values(), self.default_source]))

    # ── serialisation ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimilarityConfig":
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ConfigError(f"Unknown configuration keys: {unknown}")
        return cls(**data)

    @classmethod
    def from_json(cls, path: str | Path) -> "SimilarityConfig":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))
