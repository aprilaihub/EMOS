#!/usr/bin/env python3
"""
Generate a heatmap of property coverage across all EMOS Information Units.
Output: property_heatmap.png

Usage:
    python3 plot_property_heatmap.py
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────

MAPPINGS_ROOT = Path(__file__).parent.parent
COMMON_FILE   = MAPPINGS_ROOT / "common_properties.json"
SOURCES_ROOT  = MAPPINGS_ROOT / "sources"
OUTPUT_FILE   = Path(__file__).parent / "property_heatmap.png"

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

CAT_GROUP = {
    "structural":           "Structural",
    "structural_scan":      "Structural",
    "chemical_composition": "Composition",
    "composition":          "Composition",
    "electronic":           "Electronic",
    "electronic_scan":      "Electronic",
    "energetic":            "Energetic",
    "energetic_scan":       "Energetic",
    "thermodynamic":        "Energetic",
    "mechanical":           "Mechanical",
    "magnetic":             "Magnetic",
    "transport":            "Transport",
    "thermal":              "Thermal",
    "dielectric":           "Dielectric/Piezo",
    "piezoelectric":        "Dielectric/Piezo",
    "solar":                "Solar/Optical",
    "predictor":            "Simulation Output",
    "unknown":              "Magnetic",
}

COLUMNS = [
    "Structural", "Composition", "Electronic", "Energetic",
    "Mechanical", "Magnetic", "Transport", "Thermal",
    "Dielectric/Piezo", "Solar/Optical", "Simulation Output",
]

# Display labels and section separators
IU_DISPLAY = {
    # databases
    "aflow":                          "AFLOW",
    "alexandria":                     "Alexandria",
    "cod":                            "COD",
    "jarvisdft":                      "JARVIS-DFT",
    "materialsproject":               "Materials Project",
    "mathub3d":                       "MatHub-3d",
    # generators
    "mattergen_base_model":           "MatterGen · Base",
    "mattergen_mp_20_base":           "MatterGen · MP-20 Base",
    "mattergen_space_group":          "MatterGen · Space Group",
    "mattergen_chemical_system":      "MatterGen · Chem. System",
    "mattergen_dft_band_gap":         "MatterGen · Band Gap",
    "mattergen_bulk_modulus":         "MatterGen · Bulk Modulus",
    "mattergen_magnetic_density":     "MatterGen · Mag. Density",
    "mattergen_chemical_system_stability": "MatterGen · Chem.+Stability",
    "mattergen_magnetic_density_hhi": "MatterGen · Mag.+HHI",
    # predictors
    "gbfs":     "GBFS (3D)",
    "gbfs2d":   "GBFS-2D",
    "mattersim":"MatterSim",
    "synthnn":  "SynthNN",
}

# Ordered row groups
ROW_ORDER = {
    "databases":  ["aflow", "alexandria", "cod", "jarvisdft", "materialsproject", "mathub3d"],
    "generators": ["mattergen_base_model", "mattergen_mp_20_base", "mattergen_space_group",
                   "mattergen_chemical_system", "mattergen_dft_band_gap", "mattergen_bulk_modulus",
                   "mattergen_magnetic_density", "mattergen_chemical_system_stability",
                   "mattergen_magnetic_density_hhi"],
    "predictors": ["gbfs", "gbfs2d", "mattersim", "synthnn"],
}

SECTION_COLORS = {
    "databases":  "#1f77b4",   # blue
    "generators": "#2ca02c",   # green
    "predictors": "#d62728",   # red
}

FONT_SCALE = 1.5

# ──────────────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────────────

def load_sources():
    with COMMON_FILE.open() as f:
        common_props = json.load(f)["properties"]

    sources = {}
    for type_dir in SOURCES_ROOT.iterdir():
        if not type_dir.is_dir():
            continue
        for json_file in type_dir.glob("*.json"):
            with json_file.open() as f:
                data = json.load(f)
            counts = {}
            for prop_name, prop_info in data.get("properties", {}).items():
                cat = prop_info.get("category") or common_props.get(prop_name, {}).get("category", "unknown")
                grp = CAT_GROUP.get(cat)
                if grp:
                    counts[grp] = counts.get(grp, 0) + 1
            sources[(type_dir.name, json_file.stem)] = counts
    return sources


# ──────────────────────────────────────────────────────────────────────────────
# Build matrix
# ──────────────────────────────────────────────────────────────────────────────

def build_matrix(sources):
    rows, labels, section_boundaries, section_labels = [], [], [], []
    current_row = 0

    for section, names in ROW_ORDER.items():
        section_boundaries.append((current_row, section))
        for name in names:
            counts = sources.get((section, name), {})
            rows.append([counts.get(col, 0) for col in COLUMNS])
            labels.append(IU_DISPLAY.get(name, name))
            current_row += 1

    return np.array(rows, dtype=float), labels, section_boundaries


# ──────────────────────────────────────────────────────────────────────────────
# Plot
# ──────────────────────────────────────────────────────────────────────────────

def plot(matrix, row_labels, section_boundaries):
    # Transpose: property groups become rows, IUs become columns
    matrix = matrix.T                        # shape: (n_props, n_ius)
    n_rows, n_cols = matrix.shape            # n_rows=11 props, n_cols=19 IUs

    fig, ax = plt.subplots(figsize=(16, 8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Discrete colormap with steps of 5, fixed range 0–25
    step = 5
    bounds = list(range(0, 26, step))        # [0, 5, 10, 15, 20, 25]
    # Shift lower bound to 1 so zero values fall below the range (shown as gray)
    color_bounds = [1] + bounds[1:]           # [1, 5, 10, 15, 20, 25]
    n_colors = len(color_bounds) - 1

    base_cmap = mcolors.LinearSegmentedColormap.from_list(
        "emos", ["#90e0ef", "#00b4d8", "#0e4d4d", "#0d1117"], N=n_colors
    )
    base_cmap.set_under("#444444")            # gray for zero
    norm = mcolors.BoundaryNorm(color_bounds, ncolors=n_colors, clip=False)

    im = ax.imshow(matrix, aspect="equal", cmap=base_cmap, norm=norm,
                   interpolation="nearest")

    # ── Annotate cells with raw counts ───────────────────────────────────────
    for r in range(n_rows):
        for c in range(n_cols):
            val = int(matrix[r, c])
            if val > 0:
                brightness = val / 25
                text_color = "white" if brightness > 0.5 else "#111111"
                ax.text(c, r, str(val), ha="center", va="center",
                        fontsize=7.5 * FONT_SCALE, color=text_color, fontweight="bold")

    # ── Axes ─────────────────────────────────────────────────────────────────
    # X-axis: IU names (columns) at the bottom
    ax.set_xticks(range(n_cols))
    ax.xaxis.tick_bottom()
    ax.xaxis.set_label_position("bottom")
    ax.set_xticklabels(row_labels, rotation=90, ha="center", fontsize=8.5 * FONT_SCALE, color="black")

    # Y-axis: property groups (rows)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(COLUMNS, fontsize=9 * FONT_SCALE, color="black")
    ax.tick_params(colors="black", length=0)

    for spine in ax.spines.values():
        spine.set_visible(False)

    # ── Section dividers + top colour bars (grouping IU columns) ─────────────
    from matplotlib.transforms import blended_transform_factory
    # x in data coords, y in axes fraction
    bar_tf = blended_transform_factory(ax.transData, ax.transAxes)

    section_label_map = {
        "databases":  "Databases",
        "generators": "Generators",
        "predictors": "Predictors",
    }
    boundaries = [col for col, _ in section_boundaries] + [n_cols]

    for i, (start_col, section) in enumerate(section_boundaries):
        end_col = boundaries[i + 1]
        color = SECTION_COLORS[section]

        # Vertical divider left of section (skip first)
        if start_col > 0:
            ax.axvline(start_col - 0.5, color="#777777", linewidth=1.2, zorder=3)

        # Coloured bar above the heatmap with a clear label for the IU section.
        bar = plt.Rectangle((start_col - 0.5, 1.01),
                     end_col - start_col, 0.08,
                             color=color, transform=bar_tf,
                             clip_on=False, zorder=4)
        ax.add_patch(bar)

        # Section label centred on bar
        mid = (start_col + end_col - 1) / 2
        ax.text(mid, 1.05, section_label_map[section],
                ha="center", va="center",
            fontsize=10 * FONT_SCALE, fontweight="bold", color="white",
            transform=bar_tf, clip_on=False, zorder=5)

    # ── Grid lines ────────────────────────────────────────────────────────────
    for c in range(n_cols + 1):
        ax.axvline(c - 0.5, color="#d6d6d6", linewidth=0.6, zorder=2)
    for r in range(n_rows + 1):
        ax.axhline(r - 0.5, color="#d6d6d6", linewidth=0.4, zorder=2)

    # ── Colorbar ─────────────────────────────────────────────────────────────
    cbar = fig.colorbar(im, ax=ax, fraction=0.015, pad=0.02,
                        ticks=color_bounds, spacing="uniform", extend="min")
    cbar.set_label("Number of properties", color="black", fontsize=8 * FONT_SCALE)
    cbar.ax.set_yticklabels([str(b) for b in color_bounds], color="black", fontsize=7 * FONT_SCALE)
    cbar.ax.yaxis.set_tick_params(color="black")
    cbar.outline.set_edgecolor("#666666")

    # ── Title ─────────────────────────────────────────────────────────────────
    ax.set_title("EMOS Property Coverage — All Information Units",
                 color="black", fontsize=13 * FONT_SCALE, fontweight="bold", pad=62)

    plt.tight_layout()
    plt.savefig(OUTPUT_FILE, dpi=160, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    print(f"✓ Saved to {OUTPUT_FILE}")


# ──────────────────────────────────────────────────────────────────────────────

def main():
    sources = load_sources()
    matrix, row_labels, section_boundaries = build_matrix(sources)
    plot(matrix, row_labels, section_boundaries)


if __name__ == "__main__":
    main()
