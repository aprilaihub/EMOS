# Band Structure Feature

## Overview

Calculate and analyze electronic band structures of materials, including density of states and band gap analysis for semiconductor and device design.

## Inputs

- `structure` (Structure object): Input material structure
- `calculation_type` (string): Band structure type ('standard', 'hseg', 'uniform', 'hybrid')
- `num_k_points` (int): Number of k-points along path
- `dos_smearing` (float): DOS broadening parameter (eV)
- `fermi_level` (float): Fermi level reference (optional)

## Outputs

- `band_structure` (dict): K-points, eigenvalues, and band data
- `density_of_states` (dict): DOS energies and values
- `bandgap` (dict): Bandgap value, type (direct/indirect), and locations
- `effective_mass` (dict): Electron and hole effective masses
- `band_edges` (dict): Valence and conduction band edge positions
- `k_points` (array): K-point coordinates and path
