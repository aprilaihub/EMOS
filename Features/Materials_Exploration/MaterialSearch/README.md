# Material Search Feature

## Overview

Search through material databases using various criteria including composition, structure type, and property ranges to discover materials with desired properties.

## Inputs

- `composition` (string): Chemical composition (e.g., 'FeO2')
- `max_energy` (float): Maximum formation energy threshold
- `crystal_system` (string): Crystal structure type (e.g., 'cubic', 'hexagonal')
- `property_min` / `property_max` (dict): Property value ranges

## Outputs

- `materials` (list): Found materials with their metadata
- `structure_files` (list): CIF or structure files for matching materials
- `properties` (dict): Computed/retrieved properties for each material
- `count` (int): Total number of materials found
