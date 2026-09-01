# MOSFET evaluator

2D Poisson and drift-diffusion solver for MOSFET evaluation from simulation parameters

## Overview

This feature provides mosfet evaluator functionality within the EMOS platform.
The runtime solver is pure Python (`pdd_solver_python`) with no MATLAB dependency.
Its physics model is ported from the educational drift-diffusion MATLAB source by
Chien-Ting Tung (UC Berkeley): http://yrwu-wk.ee.ntu.edu.tw/index.php/teaching-course/

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format


## Input Parameters

- **Channel Length (nm)**: Channel length for simulation
- **Source/Drain Length (nm)**: Source and drain extension length
- **Oxide Thickness (nm)**: Gate oxide thickness
- **Channel Thickness (nm)**: Channel thickness
- **Gate Work Function (eV)**: Gate work function
- **Source/Drain Work Function (eV)**: Source/drain work function
- **Channel Doping (cm^-3)**: Channel doping concentration
- **Source/Drain Doping (cm^-3)**: Source and drain doping concentration
- **Temperature (K)**: Simulation temperature
- **Mesh dx, dy (m)**: Spatial discretization steps
- **Gate Sweep Start (V)**: Start voltage for gate sweep
- **Gate Sweep Stop (V)**: Stop voltage for gate sweep
- **Gate Sweep Points (Nvg)**: Number of gate sweep points
- **Drain Sweep Start/Stop (V)**: Drain sweep range
- **Drain Sweep Points (Nvd)**: Number of drain sweep points
- **Channel and Insulator Material Parameters**: Nc, Nv, permittivity, mobilities, affinity, bandgap, saturation velocity

## Output Parameters

- **Key Metrics**: Id(on), Id(off), Vth (approx), Ion/Ioff ratio
- **Characteristic Curve**: Id/W vs Vd at representative Vgs values
- **Download Results (JSON)**: Exhaustive simulation output for detailed analysis

## Usage

See the base class documentation for detailed usage instructions.

The MOSFET evaluator does not require Information Unit selection.
