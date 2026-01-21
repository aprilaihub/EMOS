# Property Prediction Feature

## Overview

Predict material properties using machine learning models without expensive calculations. Supports electronic, optical, mechanical, and thermal property predictions.

## Inputs

- `structure` (Structure object): Input material structure
- `predictor` (string): ML model to use ('m3gnet', 'esen', 'synthnn', 'mattersim', 'deepmd')
- `properties` (list): Properties to predict ('bandgap', 'elastic_modulus', 'thermal_conductivity', 'carrier_mobility')
- `include_uncertainty` (bool): Include prediction uncertainty estimates

## Outputs

- `predictions` (dict): Predicted property values
- `uncertainty` (dict): Uncertainty/confidence for each prediction
- `interpretation` (dict): Feature importance and property breakdown
- `success` (bool): Prediction success status
- `model_info` (dict): Information about ML model used
