# Advanced Characterization Feature

## Overview

Perform comprehensive multi-technique characterization of materials and devices, combining electronic structure, transport, optical, and defect analysis.

## Inputs

- `structure` (Structure object): Material/device to characterize
- `analysis_methods` (list): Analysis types ('electronic', 'transport', 'optical', 'xrd', 'defects')
- `calculation_level` (string): Computation depth ('fast', 'standard', 'comprehensive')
- `include_defects` (bool): Include point/line defect analysis
- `temperature` (float): Analysis temperature (K)

## Outputs

- `electronic_structure` (dict): Band structure, DOS, effective masses
- `transport_properties` (dict): Mobility, conductivity, Seebeck coefficient
- `optical_properties` (dict): Absorption, refractive index, dielectric function
- `xrd_data` (dict): X-ray diffraction patterns and indexing
- `defect_analysis` (dict): Formation energies, defect levels, concentrations
- `comprehensive_report` (dict): Integrated characterization summary
- `property_uncertainties` (dict): Confidence in calculated properties
