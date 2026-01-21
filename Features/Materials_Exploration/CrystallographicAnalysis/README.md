# Crystallographic Analysis Feature

## Overview

Analyze crystal structures including symmetry determination, lattice parameters, phase identification, and structure comparison.

## Inputs

- `structure` (Structure object or file): Input crystal structure (CIF, POSCAR, etc.)
- `tolerance` (float): Symmetry detection tolerance (Angstrom)
- `analysis_type` (string): Type of analysis ('symmetry', 'lattice', 'phase', 'comparison')
- `comparison_structure` (Structure object): Second structure for comparison (if applicable)

## Outputs

- `space_group` (string): Space group symbol and number
- `lattice_parameters` (dict): Lattice constants (a, b, c, alpha, beta, gamma)
- `wyckoff_positions` (list): Atomic Wyckoff positions
- `point_group` (string): Point group symmetry
- `structure_comparison` (dict): Similarity metrics between structures (if comparison)
- `phase_identification` (string): Identified material phase
