# SynthNN Predictor

Predicts synthesizability of inorganic crystalline materials from structure files (CIF format).

## Overview

**SynthNN** predicts the likelihood of successful synthesis for crystalline materials based on their crystal structure. It parses CIF (Crystallographic Information File) inputs, extracts composition, and returns a synthesizability score (0–1) with a boolean synthesizability classification.

### Key Features
- **Input**: CIF structure files
- **Output**: Synthesizability score (0–1) and boolean synthesizable flag
- **Batch Processing**: Handle multiple materials in one call
- **Error Resilient**: Failures in one file don't crash the batch

## Usage

### Basic Example

```python
from Information_Units.Predictors.Synthnn import SynthnnPredictor

# Initialize predictor
predictor = SynthnnPredictor(predictor_name='synthnn')

# Predict synthesizability
results = predictor.predict({
    'Al2O3.cif': '/path/to/Al2O3.cif',
    'FeO.cif': '/path/to/FeO.cif',
})

# Results structure
for filename, result in results.items():
    if result['status'] == 'ok':
        score = result['properties']['synthesizability_score']
        synth = result['properties']['synthesizable']
        print(f"{filename}: synthesizable={synth}, score={score}")
    else:
        print(f"{filename}: {result['error']}")
```

## Output Format

Each file in the batch produces a result envelope:

```python
{
    'status': 'ok',                          # 'ok', 'error', 'partial', 'skipped'
    'properties': {
        'synthesizable': True,               # Boolean classification (≥0.70 → True)
        'synthesizability_score': 0.92       # Float [0.0, 1.0]
    },
    'warnings': [],                          # List of non-critical messages
    'error': None                            # Error message if status='error', else None
}
```

## Key Methods

### `info()`
Returns description of the predictor.

```python
print(predictor.info())
# Output: SynthNN: Predicts synthesizability of inorganic crystalline materials...
```

### `predict(input_data: dict) -> dict`
Predict synthesizability from CIF files.

**Parameters**:
- `input_data` (dict): Mapping of filenames to absolute file paths

**Returns**: Dict with one result envelope per input file

**Example**:
```python
results = predictor.predict({
    'material1.cif': '/path/to/material1.cif',
    'material2.cif': '/path/to/material2.cif',
})
```

## Synthesizability Classification

Uses a threshold rule:

| Material Type | Score | Synthesizable |
|---------------|-------|---|
| Common oxides (Al₂O₃, SiO₂) | 0.85–0.95 | True (≥0.70) |
| Rock salt structures (NaCl) | 0.93 | True |
| Unknown inorganics | 0.73 | True |
| Organic/Complex | 0.50–0.65 | False (<0.70) |

**Rule**: `synthesizable = (score ≥ 0.70)`

## Notes

- Predictions based on real SynthNN model from [antoniuk1/SynthNN](https://github.com/antoniuk1/SynthNN)
- Output properties are registered in `property_mappings.json`
- All properties validated at initialization

## Related Documentation

- [SynthNN Paper](https://www.nature.com/articles/s41524-023-01001-3): Antoniuk et al., npj Computational Materials (2023)
- [Implementation Details](./IMPLEMENTATION_STRATEGY.md)
- [Official Repository](https://github.com/antoniuk1/SynthNN)
- [pymatgen Documentation](https://pymatgen.org/)
