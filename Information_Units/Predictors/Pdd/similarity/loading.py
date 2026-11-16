"""CIF discovery, parsing and conversion to amd ``PeriodicSet`` objects.

Coordinate convention
---------------------
Periodic sets are built from **Cartesian** coordinates (``structure.cart_coords``) and
the lattice matrix in angstrom.  Passing fractional coordinates together with an
angstrom cell silently produces wrong descriptors, so :func:`check_cartesian` is a
hard failure.  pymatgen's ideal-fraction rounding is disabled
(``frac_tolerance=0``) so coordinates are used exactly as published, which makes
the pipeline agree with ``amd.CifReader``.

Species are ignored by AMD and PDD (positions only): a structure and a
species-swapped copy have distance 0.  Use ``composition_filter`` to compare like
with like.
"""

from __future__ import annotations

import inspect
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from amd import PeriodicSet
from pymatgen.core import Composition, Structure
from pymatgen.io.cif import CifParser
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from ._report import Reporter
from .config import SimilarityConfig

FRAC_TOLERANCE = 0.0


class CartesianConventionError(ValueError):
    """A motif that looks fractional was supplied where Cartesian is required."""


@dataclass
class StructureRecord:
    """One loaded structure, keyed by ``<source>/<path relative to its input folder>``."""

    key: str
    label: str
    source: str
    path: Path
    structure: Structure
    parser_warnings: list[str] = field(default_factory=list)


@dataclass
class LoadResult:
    records: list[StructureRecord]
    discovered: list[dict[str, str]]
    skipped: list[dict[str, str]]
    filtered_out: list[str]
    parse_log: dict[str, list[str]]


# ── coordinates ──────────────────────────────────────────────────────────────
def check_cartesian(motif: np.ndarray, cell: np.ndarray, name: str = "") -> None:
    """Fail if a motif looks like fractional coordinates passed as Cartesian.

    For a cell whose axes are all longer than 1.5 angstrom, a genuine Cartesian motif
    with two or more atoms cannot lie wholly inside ``[0, 1)^3``.  A single-atom
    motif is translation invariant, so it can never be wrong and is not checked.
    """
    motif = np.asarray(motif, dtype=float)
    cell = np.asarray(cell, dtype=float)
    if len(motif) < 2:
        return
    if np.linalg.norm(cell, axis=1).min() > 1.5 and np.all((motif > -1e-6) & (motif < 1.0)):
        raise CartesianConventionError(
            f"{name}: motif lies wholly in [0,1)^3 - fractional coordinates passed as Cartesian?"
        )


def structure_to_periodicset(structure: Structure, name: str = "") -> PeriodicSet:
    """pymatgen ``Structure`` -> amd ``PeriodicSet`` with a Cartesian motif (angstrom)."""
    motif = np.asarray(structure.cart_coords, dtype=float)  # r = f . C
    cell = np.asarray(structure.lattice.matrix, dtype=float)
    check_cartesian(motif, cell, name)
    return PeriodicSet(motif, cell)


def inscribed_radius(structure: Structure) -> float:
    """Radius of the largest sphere inscribed in the cell (half the smallest interplanar spacing)."""
    a, b, c = structure.lattice.matrix
    volume = abs(np.linalg.det(structure.lattice.matrix))
    spacings = [
        volume / np.linalg.norm(np.cross(b, c)),
        volume / np.linalg.norm(np.cross(c, a)),
        volume / np.linalg.norm(np.cross(a, b)),
    ]
    return 0.5 * float(min(spacings))


def k_reliable_for(structure: Structure) -> int:
    """Approximate number of neighbours that fit inside the inscribed sphere.

    Neighbour distances beyond this point depend increasingly on the periodic images
    of a small cell, so large ``k`` is less meaningful for small cells.
    """
    density = structure.num_sites / structure.lattice.volume
    radius = inscribed_radius(structure)
    return max(1, int(np.floor(4.0 / 3.0 * np.pi * radius**3 * density)))


# ── parsing ──────────────────────────────────────────────────────────────────
def parse_cif(path: str | Path) -> tuple[Structure, list[str]]:
    """Parse the first structure of a CIF without ideal-fraction rounding.

    Returns ``(structure, sorted parser warnings)``; raises on failure.
    """
    if "frac_tolerance" not in inspect.signature(CifParser.__init__).parameters:
        raise RuntimeError("Installed pymatgen has no CifParser(frac_tolerance=...) option; please upgrade pymatgen.")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        parser = CifParser(str(path), frac_tolerance=FRAC_TOLERANCE)
        try:
            structures = parser.parse_structures(primitive=False)
        except AttributeError:  # pymatgen < 2024.2
            structures = parser.get_structures(primitive=False)
    messages = [str(w.message) for w in caught] + [str(m) for m in getattr(parser, "warnings", [])]
    if not structures:
        raise ValueError("no structure found in CIF")
    return structures[0], sorted(set(messages))


def assign_source(file_name: str, prefixes: dict[str, str], default: str) -> str:
    for prefix, source in prefixes.items():
        if file_name.startswith(prefix):
            return source
    return default


def discover_cifs(config: SimilarityConfig) -> list[tuple[Path, Path]]:
    """Return ``(input folder, cif path)`` pairs for every configured folder."""
    if not config.input_dirs:
        raise ValueError("No input folders configured (input_dirs is empty).")
    found: list[tuple[Path, Path]] = []
    for folder_text in config.input_dirs:
        folder = Path(folder_text).expanduser()
        if not folder.is_dir():
            raise FileNotFoundError(f"Input folder does not exist: {folder}")
        iterator = folder.rglob(config.glob_pattern) if config.recursive else folder.glob(config.glob_pattern)
        found.extend((folder, path) for path in iterator if path.is_file())
    # Deterministic order independent of folder order: file name first, then full path.
    return sorted(found, key=lambda pair: (pair[1].name, str(pair[1])))


def load_structures(config: SimilarityConfig, report: Reporter) -> LoadResult:
    """Load, filter and key every CIF configured in ``config``."""
    wanted: set[str] | None = None
    if config.composition_filter:
        wanted = {Composition(f).reduced_formula for f in config.composition_filter}

    records: list[StructureRecord] = []
    discovered: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    filtered_out: list[str] = []
    parse_log: dict[str, list[str]] = {}
    seen_keys: set[str] = set()

    for folder, path in discover_cifs(config):
        source = assign_source(path.name, config.source_prefixes, config.default_source)
        key = f"{source}/{path.relative_to(folder).as_posix()}"
        if key in seen_keys:
            original, counter = key, 2
            key = f"{original}@{folder.name}"
            while key in seen_keys:
                key, counter = f"{original}@{folder.name}#{counter}", counter + 1
            report.warn(f"duplicate relative path {original!r}; second file keyed as {key!r}")
        seen_keys.add(key)
        discovered.append({"name": key, "path": str(path)})

        try:
            structure, messages = parse_cif(path)
        except Exception as exc:  # unreadable CIF: record and continue
            parse_log[key] = [f"LOAD FAILED: {type(exc).__name__}: {exc}"]
            skipped.append({"name": key, "reason": f"parse failed: {type(exc).__name__}: {exc}"})
            report.warn(f"{key}: could not be parsed ({exc})")
            continue
        parse_log[key] = messages

        if wanted is not None and structure.composition.reduced_formula not in wanted:
            filtered_out.append(key)
            continue
        if not structure.is_ordered:
            if config.disordered == "skip":
                skipped.append({"name": key, "reason": "disordered (partial occupancy)"})
                report.warn(f"{key}: partial occupancy; skipped (disordered='skip')")
                continue
            report.warn(f"{key}: partial occupancy; positions are used as given and species are ignored")

        records.append(
            StructureRecord(
                key=key,
                label=path.stem,
                source=source,
                path=path,
                structure=structure,
                parser_warnings=messages,
            )
        )

    # Display label: file stem, or the full key when stems collide.
    stems = [r.label for r in records]
    for record in records:
        if stems.count(record.label) > 1:
            record.label = record.key

    n_warned = sum(1 for messages in parse_log.values() if messages)
    report.info(
        f"Discovered {len(discovered)} CIF files: {len(records)} loaded, {len(skipped)} skipped, "
        f"{len(filtered_out)} removed by the composition filter; parser warnings for {n_warned} files."
    )
    return LoadResult(records, discovered, skipped, filtered_out, parse_log)


# ── metadata ─────────────────────────────────────────────────────────────────
def build_metadata(records: list[StructureRecord], config: SimilarityConfig, report: Reporter) -> pd.DataFrame:
    """One row per structure: composition, symmetry, cell and k_reliable."""
    rows: list[dict[str, Any]] = []
    for record in records:
        structure = record.structure
        composition, lattice = structure.composition, structure.lattice
        try:
            analyzer = SpacegroupAnalyzer(structure)
            sg_symbol = analyzer.get_space_group_symbol()
            sg_number = analyzer.get_space_group_number()
            crystal_system = analyzer.get_crystal_system()
            n_sym_ops = len(analyzer.get_symmetry_operations())
        except Exception as exc:
            report.warn(f"{record.key}: symmetry analysis failed ({exc})")
            sg_symbol, sg_number, crystal_system, n_sym_ops = "?", -1, "?", 0

        element_fractions = {
            str(el): float(composition.get_atomic_fraction(el))
            for el in sorted(composition.elements, key=lambda e: e.Z)
        }
        rows.append(
            {
                "name": record.key,
                "label": record.label,
                "source": record.source,
                "formula": composition.formula,
                "reduced_formula": composition.reduced_formula,
                "space_group_symbol": sg_symbol,
                "space_group_number": sg_number,
                "n_sites": structure.num_sites,
                "Z_formula_units": int(round(composition.get_reduced_composition_and_factor()[1])),
                "density_g_cm3": round(structure.density, 4),
                "volume_A3": round(lattice.volume, 4),
                "volume_per_atom_A3": round(lattice.volume / structure.num_sites, 4),
                "a_A": round(lattice.a, 4),
                "b_A": round(lattice.b, 4),
                "c_A": round(lattice.c, 4),
                "alpha_deg": round(lattice.alpha, 4),
                "beta_deg": round(lattice.beta, 4),
                "gamma_deg": round(lattice.gamma, 4),
                "crystal_system": crystal_system,
                "n_sym_ops": n_sym_ops,
                "is_ordered": structure.is_ordered,
                "is_periodic_model": bool(sg_number == 1 and structure.num_sites >= config.model_min_sites),
                "r_inscribed_A": round(inscribed_radius(structure), 4),
                "k_reliable": k_reliable_for(structure),
                **element_fractions,
            }
        )
    frame = pd.DataFrame(rows)
    element_columns = [c for c in frame.columns if c not in _FIXED_METADATA_COLUMNS]
    if element_columns:
        frame[element_columns] = frame[element_columns].fillna(0.0)
    return frame


_FIXED_METADATA_COLUMNS = {
    "name", "label", "source", "formula", "reduced_formula", "space_group_symbol",
    "space_group_number", "n_sites", "Z_formula_units", "density_g_cm3", "volume_A3",
    "volume_per_atom_A3", "a_A", "b_A", "c_A", "alpha_deg", "beta_deg", "gamma_deg",
    "crystal_system", "n_sym_ops", "is_ordered", "is_periodic_model", "r_inscribed_A", "k_reliable",
}
