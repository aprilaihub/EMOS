# Thermal Management Feature

## Overview

Analyze thermal transport properties and heat dissipation pathways, identify thermal bottlenecks, and optimize thermal management strategies for electronic devices.

## Inputs

- `device_structure` (Structure object): Device to analyze
- `power_dissipation` (float): Total power dissipation (W)
- `ambient_temperature` (float): Environment temperature (K or °C)
- `boundary_conditions` (dict): Heat sink type and properties
- `optimization_goal` (string): Primary target ('minimize_peak_temp', 'minimize_gradient', 'maximize_efficiency')
- `thermal_interface` (dict): Interface materials and properties

## Outputs

- `thermal_conductivity` (dict): Thermal conductivity values by material
- `temperature_profile` (array): Temperature distribution in device
- `peak_temperature` (float): Maximum operating temperature
- `thermal_bottlenecks` (list): Components limiting heat dissipation
- `heat_flux_map` (array): Heat flow distribution
- `optimization_suggestions` (list): Recommended design improvements
- `thermal_resistance_analysis` (dict): Thermal resistance breakdown
