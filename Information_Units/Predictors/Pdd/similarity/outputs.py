"""CSV / pickle / JSON writers and run provenance."""

from __future__ import annotations

import datetime
import json
import pickle
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from .config import SimilarityConfig
from .descriptors import Descriptors

PACKAGES = ("average-minimum-distance", "pymatgen", "numpy", "scipy", "pandas", "matplotlib", "scikit-learn")


def package_versions() -> dict[str, str]:
    out = {}
    for dist in PACKAGES:
        try:
            out[dist] = version(dist)
        except PackageNotFoundError:
            out[dist] = "unknown"
    return out


def make_run_dir(base: str | Path) -> Path:
    """Create ``<base>/run_<YYYYmmdd_HHMMSS>`` (suffix added if it already exists)."""
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = Path(base)
    run_dir = base / f"run_{stamp}"
    counter = 2
    while run_dir.exists():
        run_dir = base / f"run_{stamp}_{counter}"
        counter += 1
    run_dir.mkdir(parents=True)
    return run_dir


def write_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=_json_default)


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"not JSON serialisable: {type(value).__name__}")


def write_amd_descriptors(path: Path, desc: Descriptors, k_amd: int) -> None:
    frame = pd.DataFrame(desc.amd[:, :k_amd], columns=[f"AMD_{i + 1}" for i in range(k_amd)])
    frame.insert(0, "name", desc.keys)
    frame.to_csv(path, index=False)


def write_pdd_store(pkl_path: Path, csv_path: Path, desc: Descriptors, subset: Iterable[int], k_max: int) -> None:
    """PDD of the reduced subset: a pickle of ``{name: array}`` and a long-form CSV."""
    store = {desc.keys[int(i)]: desc.pdd[int(i)] for i in subset}
    with open(pkl_path, "wb") as fh:
        pickle.dump(store, fh)
    rows = []
    for name, matrix in store.items():
        for row_index, row in enumerate(matrix):
            record = {"name": name, "row": row_index, "weight": float(row[0])}
            record.update({f"d{i + 1}": float(row[i + 1]) for i in range(matrix.shape[1] - 1)})
            rows.append(record)
    columns = ["name", "row", "weight", *[f"d{i + 1}" for i in range(k_max)]]
    pd.DataFrame(rows, columns=columns if not rows else None).to_csv(csv_path, index=False)


def write_matrix(path: Path, matrix: np.ndarray, labels: Sequence[str]) -> None:
    pd.DataFrame(matrix, index=list(labels), columns=list(labels)).to_csv(path)


def build_run_info(
    config: SimilarityConfig,
    run_dir: Path,
    timestamp: str,
    discovered: list[dict[str, str]],
    counts: dict[str, Any],
    bound_check: dict[str, Any],
    skipped: list[dict[str, str]],
    filtered_out: list[str],
    crosscheck_failures: list[dict[str, Any]],
    warnings_: list[str],
    outputs: list[str],
    extras: dict[str, Any],
) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "run_dir": str(run_dir),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": package_versions(),
        "parameters": config.to_dict(),
        "resolved": {
            "k_tsne": config.k_tsne_effective,
            "source_priority": config.source_priority_order(),
            "screen_is_exact": config.screen_is_exact,
        },
        "method": {
            "cif_parser": "pymatgen CifParser(frac_tolerance=0).parse_structures(primitive=False), first structure",
            "coordinate_handling": "Cartesian motif (structure.cart_coords) + lattice.matrix; positions only, species ignored",
            "pdd": "amd.PDD(k_max, collapse=True, collapse_tol=collapse_tol), computed once per structure",
            "amd": "weighted mean of PDD rows; AMD(k) = first k entries",
            "metric_use": "one metric for AMD distances and the EMD ground metric",
            "guarantee": {
                "complete": "every pair in a group is within tau",
                "single": "groups are chains of pairs within tau",
                "average": "no pairwise guarantee; screen is an approximation of full pairwise grouping",
                "ward": "no pairwise guarantee; screen is an approximation of full pairwise grouping",
            }[config.linkage],
        },
        "input_files": discovered,
        "filtered_out_by_composition": filtered_out,
        "skipped": skipped,
        "crosscheck_failures": crosscheck_failures,
        "stage_counts": counts,
        "bound_check": bound_check,
        "warnings": warnings_,
        "outputs": outputs,
        **extras,
    }
