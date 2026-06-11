#!/usr/bin/env python3
"""
Generate a detailed property coverage table for all EMOS Information Units.
Output: PROPERTY_COVERAGE_TABLE.md

Usage:
    python3 generate_property_coverage.py
"""

import json
from datetime import datetime
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

MAPPINGS_ROOT = Path(__file__).parent.parent          # property_mappings/
COMMON_FILE = MAPPINGS_ROOT / "common_properties.json"
SOURCES_ROOT = MAPPINGS_ROOT / "sources"
OUTPUT_FILE = Path(__file__).parent / "PROPERTY_COVERAGE_TABLE.md"

# Map raw categories → display column groups
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
    "dielectric":           "Dielectric / Piezo",
    "piezoelectric":        "Dielectric / Piezo",
    "solar":                "Solar / Optical",
    "predictor":            "Simulation Output",
    "unknown":              "Magnetic",   # mag_density, hhi_score
}

# Ordered column groups used in tables
DB_COLUMNS = [
    "Structural", "Composition", "Electronic", "Energetic",
    "Mechanical", "Magnetic", "Transport", "Thermal",
    "Dielectric / Piezo", "Solar / Optical",
]
GEN_COLUMNS = [
    "Structural", "Composition", "Electronic", "Energetic",
    "Mechanical", "Magnetic",
]
PRED_COLUMNS = [
    "Structural", "Electronic", "Energetic", "Simulation Output",
]

# Human-readable display names for IUs
IU_DISPLAY = {
    "aflow":                          "AFLOW",
    "alexandria":                     "Alexandria (PBEsol + SCAN)",
    "cod":                            "COD",
    "jarvisdft":                      "JARVIS-DFT",
    "materialsproject":               "Materials Project",
    "mathub3d":                       "MatHub-3d",
    "mattergen_base_model":           "MatterGen — Base Model",
    "mattergen_bulk_modulus":         "MatterGen — Bulk Modulus",
    "mattergen_chemical_system":      "MatterGen — Chemical System",
    "mattergen_chemical_system_stability": "MatterGen — Chem. System + Stability",
    "mattergen_dft_band_gap":         "MatterGen — DFT Band Gap",
    "mattergen_magnetic_density":     "MatterGen — Magnetic Density",
    "mattergen_magnetic_density_hhi": "MatterGen — Magnetic Density + HHI",
    "mattergen_mp_20_base":           "MatterGen — MP-20 Base",
    "mattergen_space_group":          "MatterGen — Space Group",
    "gbfs":                           "GBFS (3D)",
    "gbfs2d":                         "GBFS-2D",
    "mattersim":                      "MatterSim",
    "synthnn":                        "SynthNN",
}

# Short specialisation notes per IU
IU_NOTES = {
    "aflow":            "Broadest structural library; mechanical tensors (AEL), thermal (AGL: Debye, thermal conductivity, heat capacity), full symmetry analysis",
    "alexandria":       "Dual-functional: every property computed with **PBEsol** *and* **SCAN**; ideal for band-gap and stability benchmarking",
    "cod":              "Experimental crystallography only — structural geometry and composition; no computed properties",
    "jarvisdft":        "Unique coverage: thermoelectric transport (Seebeck, power factor), dielectric, piezoelectric, and solar cell efficiency (SLME); multi-level band gaps (OPT, MBJ, HSE)",
    "materialsproject": "Thermodynamic stability via **r2SCAN**; formation energy and hull distance; standard starting point for stability screening",
    "mathub3d":         "Thermoelectric focus: transport + electronic + magnetic in a compact 74 K entry dataset",
    "mattergen_base_model":           "Unconditional generation — no property constraint",
    "mattergen_mp_20_base":           "Unconditional generation trained on MP-20 dataset",
    "mattergen_space_group":          "Condition on target space group symmetry",
    "mattergen_chemical_system":      "Condition on target chemical system (element set)",
    "mattergen_dft_band_gap":         "Condition on target direct DFT band gap",
    "mattergen_bulk_modulus":         "Condition on target bulk modulus",
    "mattergen_magnetic_density":     "Condition on target magnetic density",
    "mattergen_chemical_system_stability": "Condition on chemical system **and** thermodynamic stability (hull distance)",
    "mattergen_magnetic_density_hhi": "Condition on magnetic density **and** earth-abundance (HHI score)",
    "gbfs":    "LightGBM model for 3D bulk materials: band gap, dielectric constant, carrier mobilities (e⁻/h⁺), formation energy, metal/insulator class",
    "gbfs2d":  "Same as GBFS but specialised for 2D layered materials; includes stability prediction",
    "mattersim": "Universal ML force-field: energies, forces, stresses on any structure + full structure relaxation pipeline (relaxed CIF, energy, forces, stress)",
    "synthnn": "Synthesizability scoring — probability that a given structure can be experimentally synthesised",
}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def load_common_props():
    with COMMON_FILE.open() as f:
        data = json.load(f)
    return data["properties"]


def load_all_sources(common_props):
    """Return {(source_type, source_name): {prop_name: enriched_info}}"""
    sources = {}
    for type_dir in sorted(SOURCES_ROOT.iterdir()):
        if not type_dir.is_dir():
            continue
        source_type = type_dir.name
        for json_file in sorted(type_dir.glob("*.json")):
            source_name = json_file.stem
            with json_file.open() as f:
                data = json.load(f)
            props = {}
            for prop_name, prop_info in data.get("properties", {}).items():
                # Enrich with common-property metadata where missing
                common = common_props.get(prop_name, {})
                enriched = {
                    "category": prop_info.get("category") or common.get("category", "unknown"),
                    "description": common.get("description", prop_info.get("description", "")),
                    "unit": common.get("unit", prop_info.get("unit", "")),
                    **prop_info,
                }
                props[prop_name] = enriched
            sources[(source_type, source_name)] = props
    return sources


def group_counts(props):
    counts = {}
    for prop_info in props.values():
        grp = CAT_GROUP.get(prop_info["category"])
        if grp:
            counts[grp] = counts.get(grp, 0) + 1
    return counts


def props_by_group(props):
    grouped = {}
    for prop_name, prop_info in props.items():
        grp = CAT_GROUP.get(prop_info["category"])
        if grp:
            grouped.setdefault(grp, []).append((prop_name, prop_info))
    return grouped


def check(val):
    """Return val as string or em-dash if zero/missing."""
    return str(val) if val else "—"


def display(source_name):
    return IU_DISPLAY.get(source_name, source_name)


def note(source_name):
    return IU_NOTES.get(source_name, "")


# ──────────────────────────────────────────────────────────────────────────────
# Section builders
# ──────────────────────────────────────────────────────────────────────────────

def build_header():
    return f"""\
# EMOS Property Coverage Table

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This document maps every EMOS Information Unit (IU) to the property groups it supports,
and lists each individual property with its unit and description.

> **How to read:**
> - **Databases** — properties that can be *queried and filtered* when retrieving materials
> - **Generators** — properties accepted as *conditioning targets* when generating novel structures
> - **Predictors** — properties *predicted from* an input crystal structure
> - Numbers in summary tables = count of distinct properties in that group

---
"""


def build_database_section(sources, common_props):
    db_sources = {sn: props for (st, sn), props in sources.items() if st == "databases"}

    lines = ["## 1. Databases\n"]

    # ── Summary count table ──────────────────────────────────────────────────
    header_cols = " | ".join(DB_COLUMNS)
    sep_cols = " | ".join([":---:"] * len(DB_COLUMNS))
    lines.append(f"| Information Unit | {header_cols} | **Total** |")
    lines.append(f"|---|{sep_cols}|:---:|")

    totals_row = {c: 0 for c in DB_COLUMNS}
    for sn, props in db_sources.items():
        counts = group_counts(props)
        row_vals = [check(counts.get(c, 0)) for c in DB_COLUMNS]
        total = sum(counts.get(c, 0) for c in DB_COLUMNS)
        for c in DB_COLUMNS:
            totals_row[c] += counts.get(c, 0)
        lines.append(f"| **{display(sn)}** | {' | '.join(row_vals)} | **{total}** |")

    # Totals row
    totals_vals = [str(totals_row[c]) for c in DB_COLUMNS]
    grand_total = sum(totals_row.values())
    lines.append(f"| **TOTAL** | {' | '.join(totals_vals)} | **{grand_total}** |")
    lines.append("")

    # ── Per-database detail ───────────────────────────────────────────────────
    lines.append("### Database Specialisations\n")
    lines.append("| Database | Specialisation |")
    lines.append("|---|---|")
    for sn in db_sources:
        lines.append(f"| **{display(sn)}** | {note(sn)} |")
    lines.append("")

    # ── Full property listings ────────────────────────────────────────────────
    lines.append("### Full Property Listings\n")
    for sn, props in db_sources.items():
        lines.append(f"#### {display(sn)}\n")
        grouped = props_by_group(props)
        for grp in DB_COLUMNS:
            group_props = grouped.get(grp, [])
            if not group_props:
                continue
            lines.append(f"**{grp}** ({len(group_props)} properties)\n")
            lines.append("| Property | Unit | Description |")
            lines.append("|---|---|---|")
            for prop_name, info in sorted(group_props, key=lambda x: x[0]):
                unit = info.get("unit", "").strip()
                desc = info.get("description", "").strip().rstrip(".")
                lines.append(f"| `{prop_name}` | {unit or '—'} | {desc} |")
            lines.append("")
        lines.append("---\n")

    return "\n".join(lines)


def build_generator_section(sources):
    gen_sources = {sn: props for (st, sn), props in sources.items() if st == "generators"}

    lines = ["## 2. Generators (MatterGen Models)\n"]
    lines.append(
        "Generators produce novel crystal structures *conditioned on* the listed properties. "
        "A ✓ marks that the model accepts the property group as a conditioning target.\n"
    )

    # ── Summary table ────────────────────────────────────────────────────────
    header_cols = " | ".join(GEN_COLUMNS)
    sep_cols = " | ".join([":---:"] * len(GEN_COLUMNS))
    lines.append(f"| Model | {header_cols} | **Conditioning Props** |")
    lines.append(f"|---|{sep_cols}|:---:|")

    for sn, props in gen_sources.items():
        counts = group_counts(props)
        row_vals = ["✓" if counts.get(c, 0) else "—" for c in GEN_COLUMNS]
        total = sum(1 for c in GEN_COLUMNS if counts.get(c, 0))
        lines.append(f"| **{display(sn)}** | {' | '.join(row_vals)} | **{total}** |")
    lines.append("")

    # ── Notes ────────────────────────────────────────────────────────────────
    lines.append("### Model Notes\n")
    lines.append("| Model | Description |")
    lines.append("|---|---|")
    for sn in gen_sources:
        lines.append(f"| **{display(sn)}** | {note(sn)} |")
    lines.append("")

    # ── Full property listings ────────────────────────────────────────────────
    lines.append("### Full Conditioning Property Listings\n")
    for sn, props in gen_sources.items():
        if not props:
            continue
        lines.append(f"#### {display(sn)}\n")
        lines.append("| Property | Unit | Description |")
        lines.append("|---|---|---|")
        for prop_name, info in sorted(props.items()):
            unit = info.get("unit", "").strip()
            desc = info.get("description", "").strip().rstrip(".")
            lines.append(f"| `{prop_name}` | {unit or '—'} | {desc} |")
        lines.append("")
    lines.append("---\n")

    return "\n".join(lines)


def build_predictor_section(sources):
    pred_sources = {sn: props for (st, sn), props in sources.items() if st == "predictors"}

    lines = ["## 3. Predictors\n"]
    lines.append(
        "Predictors take a crystal structure as input and return the listed properties.\n"
    )

    # ── Summary table ────────────────────────────────────────────────────────
    header_cols = " | ".join(PRED_COLUMNS)
    sep_cols = " | ".join([":---:"] * len(PRED_COLUMNS))
    lines.append(f"| Predictor | {header_cols} | **Total** |")
    lines.append(f"|---|{sep_cols}|:---:|")

    for sn, props in pred_sources.items():
        counts = group_counts(props)
        row_vals = [check(counts.get(c, 0)) for c in PRED_COLUMNS]
        total = sum(counts.get(c, 0) for c in PRED_COLUMNS)
        lines.append(f"| **{display(sn)}** | {' | '.join(row_vals)} | **{total}** |")
    lines.append("")

    # ── Notes ────────────────────────────────────────────────────────────────
    lines.append("### Predictor Notes\n")
    lines.append("| Predictor | Specialisation |")
    lines.append("|---|---|")
    for sn in pred_sources:
        lines.append(f"| **{display(sn)}** | {note(sn)} |")
    lines.append("")

    # ── Full property listings ────────────────────────────────────────────────
    lines.append("### Full Predicted Property Listings\n")
    for sn, props in pred_sources.items():
        grouped = props_by_group(props)
        lines.append(f"#### {display(sn)}\n")
        lines.append("| Property | Unit | Description |")
        lines.append("|---|---|---|")
        for prop_name, info in sorted(props.items()):
            unit = info.get("unit", "").strip()
            desc = info.get("description", "").strip().rstrip(".")
            lines.append(f"| `{prop_name}` | {unit or '—'} | {desc} |")
        lines.append("")
    lines.append("---\n")

    return "\n".join(lines)


def build_overview_section(sources):
    """Cross-IU overview table and coverage gap analysis."""
    all_groups = [
        "Structural", "Composition", "Electronic", "Energetic",
        "Mechanical", "Magnetic", "Transport", "Thermal",
        "Dielectric / Piezo", "Solar / Optical", "Simulation Output",
    ]

    # Collect which IUs cover each group, split by type
    db_by_group = {g: [] for g in all_groups}
    gen_by_group = {g: [] for g in all_groups}
    pred_by_group = {g: [] for g in all_groups}

    for (st, sn), props in sources.items():
        counts = group_counts(props)
        for g in all_groups:
            if counts.get(g, 0):
                if st == "databases":
                    db_by_group[g].append(display(sn))
                elif st == "generators":
                    gen_by_group[g].append(display(sn))
                elif st == "predictors":
                    pred_by_group[g].append(display(sn))

    lines = ["## 4. Combined Overview\n"]
    lines.append("| Property Group | Databases | Generators | Predictors |")
    lines.append("|---|---|---|---|")
    for g in all_groups:
        dbs = ", ".join(db_by_group[g]) or "—"
        gens = ", ".join(gen_by_group[g]) or "—"
        preds = ", ".join(pred_by_group[g]) or "—"
        lines.append(f"| **{g}** | {dbs} | {gens} | {preds} |")
    lines.append("")

    # ── Coverage gap analysis ─────────────────────────────────────────────────
    lines.append("## 5. Coverage Gaps\n")
    lines.append(
        "The following property groups are present in some IUs but absent from others, "
        "representing potential areas for future extension.\n"
    )
    lines.append("| Property Group | Gap |")
    lines.append("|---|---|")

    gap_notes = {
        "Thermal":           "Only **AFLOW** provides thermal properties (Debye temperature, thermal conductivity, heat capacity, vibrational entropy). No generator or predictor support.",
        "Dielectric / Piezo": "Exclusive to **JARVIS-DFT**. No ML predictor or generator for dielectric or piezoelectric properties.",
        "Solar / Optical":   "Only **JARVIS-DFT** exposes SLME (Spectroscopic Limited Maximum Efficiency). No generator or predictor.",
        "Magnetic":          "Only **MatHub-3d** (database) and MatterGen magnetic models (generators). No ML predictor available.",
        "Transport":         "Only **JARVIS-DFT** and **MatHub-3d**. No ML predictor for Seebeck coefficient or carrier mobility across databases.",
        "Composition":       "All databases offer composition filtering; only **MatterGen** generators condition on it. No predictor returns composition.",
        "Simulation Output": "Exclusive to **MatterSim** (relaxation pipeline) and **SynthNN** (synthesizability). Not covered by any database.",
    }
    for g, msg in gap_notes.items():
        lines.append(f"| **{g}** | {msg} |")
    lines.append("")

    lines.append("---\n")
    lines.append("*Generated from `Information_Units/property_mappings/` — EMOS repository*\n")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("Loading property mappings...")
    common_props = load_common_props()
    sources = load_all_sources(common_props)
    print(f"  Loaded {len(sources)} source files")

    print("Building markdown sections...")
    sections = [
        build_header(),
        build_database_section(sources, common_props),
        build_generator_section(sources),
        build_predictor_section(sources),
        build_overview_section(sources),
    ]

    md = "\n".join(sections)

    OUTPUT_FILE.write_text(md, encoding="utf-8")
    print(f"\n✓ Written to {OUTPUT_FILE}")
    print(f"  {len(md.splitlines())} lines, {len(md):,} characters")


if __name__ == "__main__":
    main()
