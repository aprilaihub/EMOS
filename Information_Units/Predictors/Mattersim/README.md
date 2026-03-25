# MatterSim Predictor

MatterSim (Microsoft's Machine Learning Interatomic Potential for inorganic crystals) predictor information unit for batch processing of crystal structures.

## Overview

The MattersimPredictor uses Microsoft's MLIP to predict properties of inorganic crystal structures. It processes a single CIF file and returns comprehensive results.

**Supports:**
- Energy prediction
- Force calculation  
- Stress tensor computation
- Structure relaxation (atomic positions and/or cell parameters)
- Relaxed structure output (CIF format)

## Key Methods

- `info()`: Returns description and capabilities
- `predict(inputs)`: Processes a single CIF file and returns results

## Installation

### Docker Quick Checks

Before running MatterSim tests or predictions, verify the service is running:

```bash
docker compose up -d mattersim
docker compose ps mattersim
docker compose logs mattersim --tail 20
```

### Requirements

Install the following packages in your WSL conda environment:

```bash
# Create conda environment (recommended)
conda create -n emos-mattersim python=3.10 -y
conda activate emos-mattersim

# Install MatterSim with dependencies
conda install -c conda-forge mattersim pymatgen ase -y

# Verify installation
python -c "from mattersim.forcefield import MatterSimCalculator; print('✅ MatterSim ready')"
```

## API Documentation

### Input Parameters

The `predict()` method accepts a dictionary with CIF file path and optional calculation parameters:

```python
{
    'cif_file': '/path/to/structure.cif',     # REQUIRED
    'compute_energy': True,                    # Optional: default True
    'compute_forces': False,                   # Optional: default False
    'compute_stress': False,                   # Optional: default False
    'relax': False,                            # Optional: default False
    'relax_atoms': True,                       # Optional: default True
    'relax_cell': False,                       # Optional: default False
    'output_dir': '/path/to/output'            # Optional: save relaxed CIF
}
```

### Output

Returns a dictionary with calculation results:

```python
{
    'status': 'ok' or 'error',
    'properties': {
        'energy': float,                    # Total energy (eV)
        'forces': List[List[float]],        # Atomic forces (eV/Å)
        'stress': List[float],              # Stress tensor (GPa)
        'relaxed_energy': float,            # Energy after relaxation (if relax=True)
        'relaxed_structure': List,          # Atomic positions after relaxation
        'relaxed_cell': List,               # Cell after relaxation
        'relaxed_cif': str,                 # Path to relaxed CIF file (if output_dir provided)
        'num_atoms': int,                   # Number of atoms
        'cell': List,                       # Cell parameters
        'positions': List,                  # Atomic positions
        'atomic_numbers': List,             # Atomic numbers
    },
    'warnings': List[str],                  # Non-critical issues
    'error': str or None                    # Error message if status='error'
}
```

## Usage Examples

### Basic Energy Calculation

```python
from Information_Units.Predictors.Mattersim.MattersimPredictor import MattersimPredictor

# Initialize predictor
predictor = MattersimPredictor('mattersim')

# Predict energy
results = predictor.predict({
    'cif_file': '/path/to/Al2O3.cif',
    'compute_energy': True
})

print(f"Status: {results['status']}")
print(f"Energy: {results['properties']['energy']} eV")
```

### Structure with Forces and Stress

```python
results = predictor.predict({
    'cif_file': '/path/to/structure.cif',
    'compute_energy': True,
    'compute_forces': True,
    'compute_stress': True
})

if results['status'] == 'ok':
    print(f"Energy: {results['properties']['energy']:.6f} eV")
    print(f"Forces calculated: {len(results['properties']['forces'])} atoms")
    print(f"Stress: {results['properties']['stress']}")
```

### Structure Relaxation with CIF Output

```python
results = predictor.predict({
    'cif_file': '/path/to/structure.cif',
    'relax': True,
    'relax_atoms': True,
    'relax_cell': False,
    'compute_energy': True,
    'output_dir': '/path/to/output'  # Save relaxed structure
})

if results['status'] == 'ok':
    print(f"Initial energy: {results['properties']['energy']:.6f} eV")
    print(f"Relaxed energy: {results['properties']['relaxed_energy']:.6f} eV")
    print(f"Relaxed CIF saved to: {results['properties']['relaxed_cif']}")
```

### Full Calculation with All Properties

```python
results = predictor.predict({
    'cif_file': '/path/to/structure.cif',
    'compute_energy': True,
    'compute_forces': True,
    'compute_stress': True,
    'relax': True,
    'relax_atoms': True,
    'relax_cell': True,
    'output_dir': '/path/to/output'
})

if results['status'] == 'ok':
    props = results['properties']
    print(f"Initial energy: {props['energy']:.6f} eV")
    print(f"Relaxed energy: {props['relaxed_energy']:.6f} eV")
    print(f"Relaxed CIF: {props['relaxed_cif']}")
    print(f"Atoms: {props['num_atoms']}")
    print(f"Warnings: {results['warnings']}")
else:
    print(f"Error: {results['error']}")
```

## Features

### Supported Calculations

| Feature | Status | Notes |
|---------|--------|-------|
| Energy | ✅ | Fast, accurate energy prediction |
| Forces | ✅ | Per-atom force predictions |
| Stress | ✅ | Stress tensor calculation |
| Structure Relaxation | ✅ | BFGS-based optimization |
| Atomic Position Relaxation | ✅ | Default relaxation mode |
| Cell Parameter Relaxation | ✅ | Optional cell optimization |
| Relaxed CIF Output | ✅ | Save optimized structures |
| Single File Processing | ✅ | Process one CIF file per call |

### Supported File Formats

- **CIF** (.cif) - Crystallographic Information File (primary format)
- **Output**: CIF format for relaxed structures

## Error Handling

The predictor includes comprehensive error handling:

- Validates file existence
- Handles invalid CIF format
- Gracefully handles calculation failures
- Provides detailed error messages
- Processes files independently (one failure doesn't affect others)
- Non-critical warnings are collected in warnings array

## Performance Characteristics

- **Load CIF**: ~50-100ms
- **Energy calc**: ~100-200ms  
- **Force calc**: ~150-250ms
- **Stress calc**: ~200-300ms
- **Relaxation**: 1-10s (depends on system size)

## Related Documentation

- [BasePredictor.py](../BasePredictor.py) - Base class
- [MatterSim GitHub](https://github.com/microsoft/mattersim)
- [PyMatGen](https://pymatgen.org/)
- [ASE](https://wiki.fysik.dtu.dk/ase/)

## Troubleshooting

### Import Errors

If you get import errors:

```bash
conda install -c conda-forge mattersim pymatgen ase --force-reinstall
```

### CIF File Not Found

Ensure absolute path to CIF file:

```python
from pathlib import Path
cif_path = str(Path('/home/user/structures/material.cif').resolve())
```

### Relaxation Issues

Try without cell relaxation:

```python
results = predictor.predict({
    'structure.cif': cif_path,
    'relax': True,
    'relax_atoms': True,
    'relax_cell': False  # Disable cell relaxation
})
```

## Development Notes

- Uses PyMatGen for structure loading (with ASE fallback)
- Leverages ASE for structure relaxation (BFGS optimizer)
- Graceful degradation if optional dependencies missing
- Single file processing (call predict() for each file separately)
- All operations logged for debugging

