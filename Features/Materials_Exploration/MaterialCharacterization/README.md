# Material Characterization Feature

## Overview

Comprehensively characterize material properties through integrated analysis of electronic, optical, mechanical, and thermal properties.

## Inputs

- `structure` (Structure object): Input material structure
- `property_types` (list): Properties to characterize ('electronic', 'optical', 'mechanical', 'thermal')
- `calculation_level` (string): Computation depth ('fast', 'standard', 'accurate')

## Outputs

- `electronic_properties` (dict): Bandgap, effective mass, carrier mobility, conductivity
- `optical_properties` (dict): Refractive index, absorption coefficient, dielectric constant
- `mechanical_properties` (dict): Elastic moduli, hardness, bulk modulus, shear modulus
- `thermal_properties` (dict): Thermal conductivity, heat capacity, thermal expansion
- `summary_report` (dict): Consolidated property summary
