"""AMD Screening Feature.

Computes the AMD (Average Minimum Distance) pairwise similarity matrix for
two or more uploaded CIF structures, then generates a combined dendrogram +
lower-triangle heatmap figure following the paper's visualisation style.

Output:
- AMD distance matrix (n × n) as JSON
- Base-64 encoded PNG of the heatmap/dendrogram figure
"""

from __future__ import annotations

import base64
import io
import json
import os
import tempfile
import threading
from typing import Any

import amd
import numpy as np

from Features.BaseFeature import BaseFeature


# ── Matplotlib / Seaborn are optional; import lazily so server startup never ─
# ── fails if they are not yet installed. ─────────────────────────────────────
def _import_plot_libs():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from scipy.cluster.hierarchy import dendrogram, linkage
    return plt, sns, dendrogram, linkage


class AmdScreeningFeature(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("AMD screening", logger)
        self._cancelled = False
        self._cancel_lock = threading.Lock()

    # ── BaseFeature contract ──────────────────────────────────────────────────

    def info(self):
        return (
            "AMD Screening: Compute pairwise AMD similarity matrix for uploaded "
            "CIF structures and visualise as a heatmap + Ward-linkage dendrogram."
        )

    def extract_inputs(self, input_data: dict) -> dict:
        return {
            "cif_strings": input_data.get("cif_strings", []),
            "labels": input_data.get("labels", []),          # optional display names
            "k": int(input_data.get("k", 100) or 100),
            "active_databases": input_data.get("active_databases", []),
            "active_generators": input_data.get("active_generators", []),
            "active_predictors": input_data.get("active_predictors", []),
        }

    def process_feature(self, inputs: dict) -> dict:
        with self._cancel_lock:
            self._cancelled = False

        if self.logger:
            self.logger.log("Initialising AMD screening\u2026", "info")

        cif_strings: list[str] = inputs.get("cif_strings", [])
        labels: list[str] = inputs.get("labels", [])
        k: int = int(inputs.get("k", 100))

        if len(cif_strings) < 2:
            msg = f"AMD screening requires at least 2 CIF files. Got {len(cif_strings)}."
            if self.logger:
                self.logger.log(msg, "warning")
            return {"status": "error", "message": msg}

        # ── Step 1: load crystals ─────────────────────────────────────────────
        if self.logger:
            self.logger.log(
                f"Loading {len(cif_strings)} CIF structures (k={k})\u2026", "info"
            )

        periodic_sets: list[tuple[str, Any]] = []
        tmp_paths: list[str] = []
        failed: list[str] = []

        try:
            for idx, cif_text in enumerate(cif_strings):
                if self._is_cancelled():
                    return {"status": "cancelled", "message": "Processing was cancelled."}

                label = labels[idx] if idx < len(labels) else f"S{idx + 1}"
                try:
                    tmp = tempfile.NamedTemporaryFile(
                        mode="w", suffix=".cif", delete=False, encoding="utf-8"
                    )
                    tmp.write(cif_text)
                    tmp.close()
                    tmp_paths.append(tmp.name)

                    crystals = list(amd.CifReader(tmp.name))
                    if not crystals:
                        raise ValueError("No crystal structures found in CIF.")
                    periodic_sets.append((label, crystals[0]))
                    if self.logger:
                        self.logger.log(
                            f"  Loaded structure {idx + 1}/{len(cif_strings)}: {label}", "info"
                        )

                except Exception as exc:
                    failed.append(f"{label}: {exc}")
                    if self.logger:
                        self.logger.log(f"  Failed to load {label}: {exc}", "error")
        finally:
            for p in tmp_paths:
                try:
                    os.unlink(p)
                except OSError:
                    pass

        if len(periodic_sets) < 2:
            msg = (
                f"AMD screening requires at least 2 valid structures. "
                f"Only {len(periodic_sets)} loaded successfully."
            )
            if self.logger:
                self.logger.log(msg, "error")
            return {"status": "error", "message": msg, "failed": failed}

        # ── Step 2: compute AMD vectors and pairwise distance matrix ──────────
        if self.logger:
            self.logger.log(
                f"Computing AMD vectors (k={k}) for {len(periodic_sets)} structures\u2026",
                "info",
            )

        vl: list[str] = []
        amd_vectors: list[Any] = []

        for label, ps in periodic_sets:
            if self._is_cancelled():
                return {"status": "cancelled", "message": "Processing was cancelled."}
            try:
                amd_vec = amd.AMD(ps, k)
                amd_vectors.append(amd_vec)
                vl.append(label)
                if self.logger:
                    self.logger.log(f"  AMD vector computed for: {label}", "info")
            except Exception as exc:
                failed.append(f"{label}: {exc}")
                if self.logger:
                    self.logger.log(f"  AMD vector failed for {label}: {exc}", "error")

        n = len(amd_vectors)
        if n < 2:
            return {
                "status": "error",
                "message": "Not enough AMD vectors computed.",
                "failed": failed,
            }

        if self.logger:
            self.logger.log(f"Building {n}\u00d7{n} AMD distance matrix\u2026", "info")

        mat = np.zeros((n, n))
        total_pairs = n * (n - 1) // 2
        done = 0
        for i in range(n):
            for j in range(i + 1, n):
                if self._is_cancelled():
                    return {"status": "cancelled", "message": "Processing was cancelled."}
                dist = float(
                    amd.AMD_cdist([amd_vectors[i]], [amd_vectors[j]], metric="chebyshev")[0, 0]
                )
                mat[i, j] = dist
                mat[j, i] = dist
                done += 1
                if self.logger:
                    self.logger.log(
                        f"  Pair ({i + 1},{j + 1}) dist = {dist:.6f}  [{done}/{total_pairs}]",
                        "info",
                    )

        # ── Step 3: generate heatmap + dendrogram figure ──────────────────────
        if self.logger:
            self.logger.log("Generating heatmap and dendrogram figure\u2026", "info")

        plot_b64 = self._make_figure(mat, vl, k)

        if self.logger:
            self.logger.log("AMD screening complete.", "success")

        return {
            "status": "completed",
            "message": f"AMD screening complete. {n} structures, {total_pairs} pairs.",
            "labels": vl,
            "amd_matrix": mat.tolist(),
            "plot_base64": plot_b64,
            "k": k,
            "failed": failed,
        }

    def process_feature_stream(self, inputs: dict):
        """Yield SSE events while running AMD screening."""
        with self._cancel_lock:
            self._cancelled = False

        n_cif = len(inputs.get("cif_strings", []))
        yield f"event: log\ndata: {json.dumps({'message': 'Initialising AMD screening\u2026', 'level': 'info'})}\n\n"

        if n_cif < 2:
            msg = f"AMD screening requires at least 2 CIF files. Got {n_cif}."
            yield f"event: log\ndata: {json.dumps({'message': msg, 'level': 'warning'})}\n\n"
            yield f"event: result\ndata: {json.dumps({'status': 'error', 'message': msg})}\n\n"
            return

        yield (
            f"event: progress\ndata: "
            f"{json.dumps({'progress': 0.05, 'message': f'Loading {n_cif} structures\u2026'})}\n\n"
        )
        result = self.process_feature(inputs)
        yield f"event: progress\ndata: {json.dumps({'progress': 1.0, 'message': 'Done.'})}\n\n"
        yield f"event: result\ndata: {json.dumps(result)}\n\n"

    def format_outputs(self, results: dict) -> dict:
        return {
            "status": results.get("status", "unknown"),
            "message": results.get("message", ""),
            "labels": results.get("labels"),
            "amd_matrix": results.get("amd_matrix"),
            "plot_base64": results.get("plot_base64"),
            "k": results.get("k"),
            "failed": results.get("failed", []),
        }

    def cancel(self) -> dict:
        with self._cancel_lock:
            self._cancelled = True
        if self.logger:
            self.logger.log(
                "Cancel requested \u2014 AMD screening will stop after current operation.",
                "warning",
            )
        return {"status": "ok", "message": "Cancel signal sent to AMD screening."}

    # ── Private helpers ───────────────────────────────────────────────────────

    def _is_cancelled(self) -> bool:
        with self._cancel_lock:
            return self._cancelled

    def _make_figure(self, mat: np.ndarray, labels: list[str], k: int) -> str:
        """Build the dendrogram + lower-triangle heatmap; return base-64 PNG."""
        try:
            plt, sns, dendrogram, linkage = _import_plot_libs()
        except ImportError as exc:
            if self.logger:
                self.logger.log(
                    f"matplotlib/seaborn not installed \u2014 plot skipped. ({exc})", "warning"
                )
            return ""

        n = len(labels)
        HEATMAP_CMAP = "YlOrRd"

        FS = {
            "cif_label": max(5, min(9, 110 // max(n, 1))),
            "axis_label": 9,
            "tick": 8,
            "annot": max(5, min(7, 80 // max(n, 1))),
            "cbar_label": 8,
        }
        LW = {"dendrogram": 1.0, "grid_line": 0.5, "grid_alpha": 0.4, "tick": 0.8}

        from scipy.spatial.distance import squareform
        from scipy.cluster.hierarchy import leaves_list

        condensed = squareform(mat, checks=False)
        Z = linkage(condensed, method="ward")
        order = leaves_list(Z)
        mat_r = mat[np.ix_(order, order)]
        vl_r = [labels[i] for i in order]

        fig_w = max(8.0, n * 0.55 + 4.0)
        fig_h = max(5.0, n * 0.45 + 2.0)
        fig, (ax_dend, ax_heat) = plt.subplots(
            1, 2,
            figsize=(fig_w, fig_h),
            gridspec_kw={"width_ratios": [1, 2]},
        )

        # ── (c) AMD dendrogram ────────────────────────────────────────────────
        max_d = float(Z[:, 2].max()) if len(Z) else 1.0
        dendrogram(
            Z, labels=labels, ax=ax_dend,
            leaf_rotation=0, leaf_font_size=FS["cif_label"],
            color_threshold=0.65 * max_d,
            orientation="left",
        )
        for line in ax_dend.get_lines():
            line.set_linewidth(LW["dendrogram"])
        ax_dend.invert_yaxis()
        ax_dend.set_xlabel(
            f"Ward Linkage (Average Minimum Distance [a.u.], k={k})",
            fontsize=FS["axis_label"],
        )
        ax_dend.grid(axis="x", linewidth=LW["grid_line"], alpha=LW["grid_alpha"], linestyle="--")
        ax_dend.tick_params(axis="y", labelsize=FS["cif_label"], width=LW["tick"])
        ax_dend.tick_params(axis="x", labelsize=FS["tick"], width=LW["tick"])

        # ── (d) AMD cross-correlation heatmap (lower triangle, square cells) ──
        mask_tri = np.triu(np.ones_like(mat_r, dtype=bool), k=1)
        vmax = float(mat_r.max()) or 1.0
        sns.heatmap(
            mat_r, mask=mask_tri, square=True, ax=ax_heat,
            xticklabels=vl_r, yticklabels=vl_r,
            cmap=HEATMAP_CMAP, vmin=0, vmax=vmax,
            annot=(n <= 20), fmt=".3f",
            annot_kws={"size": FS["annot"]} if n <= 20 else {},
            linewidths=0.1,
            cbar=False,
        )
        ax_heat.tick_params(axis="x", rotation=90, labelsize=FS["cif_label"], width=LW["tick"])
        ax_heat.tick_params(axis="y", left=True, labelleft=False, width=LW["tick"])

        # Inset colorbar in blank upper-right triangle
        from matplotlib.cm import ScalarMappable as _SM
        from matplotlib.colors import Normalize as _Norm
        _norm = _Norm(vmin=0, vmax=vmax)
        _sm = _SM(cmap=HEATMAP_CMAP, norm=_norm)
        _sm.set_array([])
        _cax = ax_heat.inset_axes([0.42, 0.84, 0.54, 0.04])
        _cb = fig.colorbar(_sm, cax=_cax, orientation="horizontal")
        _cb.set_label(f"Average Minimum Distance [a.u.] (k={k})", fontsize=FS["cbar_label"])
        _cb.ax.tick_params(labelsize=FS["tick"], width=LW["tick"])

        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")
