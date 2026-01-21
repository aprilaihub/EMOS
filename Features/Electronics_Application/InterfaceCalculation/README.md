# Interface Calculation Feature

## Overview

Calculate electronic properties and stability of material interfaces, including band alignment, interface energy, and charge transfer for multilayer devices.

## Inputs

- `material_1` (Structure object): First material at interface
- `material_2` (Structure object): Second material at interface
- `interface_plane` (tuple): Miller indices for interface plane (e.g., (100))
- `num_layers_1` (int): Number of layers of material 1
- `num_layers_2` (int): Number of layers of material 2
- `distance` (float): Initial interlayer distance (Angstrom)

## Outputs

- `interface_structure` (Structure object): Optimized interface structure
- `interface_energy` (float): Interface formation energy (J/m²)
- `band_alignment` (dict): Band offset and alignment diagram
- `band_offset_VB` (float): Valence band offset (eV)
- `band_offset_CB` (float): Conduction band offset (eV)
- `charge_transfer` (dict): Charge transfer at interface
- `interface_dipole` (float): Interface dipole moment
- `stability_score` (float): Interface stability assessment
