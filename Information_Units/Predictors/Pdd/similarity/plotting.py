"""Headless figures: dendrogram, heatmap and t-SNE scatter.

Figures are drawn on ``matplotlib.figure.Figure`` objects and saved - the pyplot
state machine is never used, so no window opens, ``plt.show()`` is never called and
the user's matplotlib backend is left untouched.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib
import matplotlib.patheffects as path_effects
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import to_hex
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from scipy.cluster.hierarchy import dendrogram

from ._report import Reporter
from .config import SimilarityConfig

FONT_FALLBACK = "DejaVu Sans"
HEATMAP_CMAP = "magma_r"


def figure_style(config: SimilarityConfig, report: Reporter):
    """``rc_context`` using the configured font, falling back when it is not installed."""
    family = config.font_family
    try:
        font_manager.findfont(family, fallback_to_default=False)
    except ValueError:
        report.warn(f"font {family!r} not found; using {FONT_FALLBACK!r}")
        family = FONT_FALLBACK
    return matplotlib.rc_context({"font.family": [family]})


def save_figure(fig: Figure, stem: Path, config: SimilarityConfig) -> list[str]:
    written = []
    for fmt in config.figure_formats:
        target = stem.with_suffix(f".{fmt}")
        fig.savefig(target, dpi=config.figure_dpi, bbox_inches="tight")
        written.append(target.name)
    return written


def leaf_order(tree: np.ndarray) -> list[int]:
    """Left-to-right (top-to-bottom) leaf order of a linkage matrix."""
    return list(dendrogram(tree, no_plot=True)["leaves"])


def show_tick_labels(n: int, config: SimilarityConfig) -> bool:
    return n <= config.max_tick_labels


def plot_dendrogram(
    tree: np.ndarray,
    labels: Sequence[str],
    config: SimilarityConfig,
    xlabel: str,
) -> Figure:
    """Horizontal dendrogram coloured at ``tau`` (clusters merged at or below tau share a colour)."""
    n = len(labels)
    show_labels = show_tick_labels(n, config)
    height = min(60.0, max(4.0, 0.2 * n if show_labels else 0.04 * n + 4.0))
    fig = Figure(figsize=(7.0, height))
    ax = fig.add_subplot(1, 1, 1)
    dendrogram(
        tree,
        labels=list(labels),
        orientation="left",
        color_threshold=config.tau,
        no_labels=not show_labels,
        leaf_font_size=8,
        ax=ax,
    )
    ax.invert_yaxis()  # first leaf at the top, matching the heatmap rows
    ax.axvline(config.tau, color="grey", linestyle="--", linewidth=1)
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", linestyle="--", alpha=0.5)
    if not show_labels:
        ax.set_yticks([])
    return fig


def _highlight(ax, labels: Sequence[str], targets: Sequence[str], color: str = "blue") -> None:
    index = {name: i for i, name in enumerate(labels)}
    n = len(labels)
    for name in targets:
        if name not in index:
            continue
        t = index[name]
        ax.plot([-0.5, t], [t, t], color=color, lw=1.6, alpha=0.95, zorder=5)  # row: left edge -> diagonal
        ax.plot([t, t], [t, n - 0.5], color=color, lw=1.6, alpha=0.95, zorder=5)  # column: diagonal -> bottom
        ax.text(
            t, t, name, color=color, fontsize=9, ha="left", va="bottom", fontweight="bold", zorder=6,
            path_effects=[path_effects.withStroke(linewidth=2, foreground="white")],
        )


def plot_heatmap(
    matrix: np.ndarray,
    labels: Sequence[str],
    config: SimilarityConfig,
    colorbar_label: str,
    highlight: Sequence[str] = (),
) -> Figure:
    """Lower-triangle distance heatmap with an inset horizontal colourbar.

    ``matrix`` and ``labels`` must already be in dendrogram leaf order.
    """
    n = len(labels)
    show_labels = show_tick_labels(n, config)
    side = min(24.0, max(6.0, 0.14 * n + 3.0))
    fig = Figure(figsize=(side, side))
    ax = fig.add_subplot(1, 1, 1)
    masked = np.ma.array(matrix, mask=np.triu(np.ones((n, n), dtype=bool), k=1))
    cmap = matplotlib.colormaps[HEATMAP_CMAP].with_extremes(bad=(1.0, 1.0, 1.0, 0.0))
    vmax = float(np.max(matrix)) if np.max(matrix) > 0 else 1.0
    image = ax.imshow(masked, cmap=cmap, vmin=0.0, vmax=vmax, origin="upper", interpolation="nearest")
    if show_labels:
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(labels, rotation=90, fontsize=8)
        ax.set_yticklabels(labels, fontsize=8)
    else:
        ax.set_xticks([])
        ax.set_yticks([])
    colorbar = fig.colorbar(image, cax=ax.inset_axes((0.42, 0.84, 0.54, 0.03)), orientation="horizontal")
    colorbar.set_label(colorbar_label)
    _highlight(ax, labels, highlight)
    return fig


def source_color_map(sources: Sequence[str], config: SimilarityConfig) -> dict[str, str]:
    palette = matplotlib.colormaps["tab10"]
    colors = dict(config.source_colors)
    for position, source in enumerate(sorted(set(sources))):
        colors.setdefault(source, to_hex(palette(position % 10)))
    return colors


def plot_tsne(
    coords: np.ndarray,
    labels: Sequence[str],
    sources: Sequence[str],
    config: SimilarityConfig,
    k: int,
) -> Figure:
    colors = source_color_map(sources, config)
    fig = Figure(figsize=(7.0, 6.0))
    ax = fig.add_subplot(1, 1, 1)
    for source in sorted(set(sources)):
        mask = np.array([s == source for s in sources])
        ax.scatter(
            coords[mask, 0], coords[mask, 1], s=70, color=colors[source], edgecolors="black",
            linewidths=0.6, alpha=0.9, zorder=3,
        )
    if len(labels) <= 40:
        for (x, y), name in zip(coords, labels):
            ax.annotate(name, (x, y), fontsize=6, xytext=(3, 3), textcoords="offset points")
    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="w", markerfacecolor=colors[s], markeredgecolor="black",
                   markersize=8, label=f"{s} (N={sum(1 for x in sources if x == s)})")
            for s in sorted(set(sources))
        ],
        fontsize=9,
    )
    ax.set_xlabel("t-SNE dim 1")
    ax.set_ylabel("t-SNE dim 2")
    ax.set_title(f"PDD EMD ({config.metric}, k = {k}), reduced subset")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.tick_params(labelbottom=False, labelleft=False)
    return fig
