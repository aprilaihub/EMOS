# MOSFET evaluator

Evaluate MOSFET performance from uploaded CIF files and simulation parameters

## Overview

This feature provides mosfet evaluator functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format
- `_process_information_units(inputs)`: Integrates with databases, generators, and predictors


## Input Parameters

- **CIF Files**: Browse and upload one or more CIF files for MOSFET evaluation
- **Device Type**: MOSFET device polarity
- **Channel Length (nm)**: Channel length for simulation
- **Channel Width (nm)**: Channel width for simulation
- **Oxide Thickness (nm)**: Gate oxide thickness
- **Supply Voltage VDD (V)**: Supply voltage
- **Gate Work Function (eV)**: Gate work function
- **Source/Drain Doping (cm^-3)**: Source and drain doping concentration
- **Temperature (K)**: Simulation temperature
- **Drain Voltage VD (V)**: Drain voltage
- **Gate Sweep Start (V)**: Start voltage for gate sweep
- **Gate Sweep Stop (V)**: Stop voltage for gate sweep
- **Gate Sweep Step (V)**: Step size for gate sweep
- **Validate Band Gap from CIF**: Validate band gap using uploaded CIF files
- **Validate Electron Mobility from CIF**: Validate electron mobility using uploaded CIF files
- **Validate Hole Mobility from CIF**: Validate hole mobility using uploaded CIF files
- **Validate Dielectric Constant from CIF**: Validate dielectric constant using uploaded CIF files

## Output Parameters

- **Download Results (JSON)**: Download JSON file containing MOSFET simulation performance for each uploaded CIF file

## Usage

See the base class documentation for detailed usage instructions.

For integration with information units (Databases, Generators, Predictors), 
the feature automatically processes active units and logs their operations.
