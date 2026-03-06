# SynthNN Predictor - Phase 1 Mock Implementation

## Overview

**SynthNN** is a lightweight wrapper for predicting synthesizability of inorganic crystalline materials from their chemical composition. It takes CIF (Crystallographic Information File) files as input, extracts the chemical composition, and returns a synthesizability score (0-1).

**Phase 1 Status**: ✅ Complete with mock predictions  
**Phase 2/3 Status**: 🔜 Real model integration (future work)

### Key Features

- ✅ Real CIF parsing via [pymatgen](https://pymatgen.org/)
- ✅ Deterministic mock scoring for testing (Phase 1)
- ✅ Complete error and warning handling
- ✅ Batch processing of multiple materials
- ✅ JSON-compatible output format
- ✅ Comprehensive unit test coverage

---

## Installation

### Requirements

Uses existing dependencies from `requirements.txt`:
- `pymatgen>=2024.6.0` - For CIF parsing and structure manipulation

No additional packages required for Phase 1.

---

## Usage

### Basic Example

```python
from Information_Units.Predictors.Synthnn import SynthnnPredictor

# Initialize predictor (uses mock by default in Phase 1)
predictor = SynthnnPredictor(predictor_name='synthnn', use_mock=True)

# Prepare input: {filename: filepath}
input_data = {
    'Al2O3.cif': '/path/to/Al2O3.cif',
    'FeO.cif': '/path/to/FeO.cif',
    'invalid.cif': '/path/to/corrupted.cif'
}

# Run prediction
results = predictor.predict(input_data)

# Output structure:
# {
#     'Al2O3.cif': {
#         'synthesizable': True,
#         'synthesizability_score': 0.92,
#         'warnings': [...]  # optional
#     },
#     'FeO.cif': {
#         'synthesizable': False,
#         'synthesizability_score': 0.31
#     },
#     'invalid.cif': {
#         'synthesizable': None,
#         'synthesizability_score': None,
#         'error': 'Failed to parse CIF: Invalid syntax'
#     }
# }
```

### Input Format

Provide a dictionary mapping filenames to their file paths:

```python
input_data = {
    'material1.cif': '/absolute/path/to/material1.cif',
    'material2.cif': '/absolute/path/to/material2.cif',
    # ... more files
}

results = predictor.predict(input_data)
```

### Output Format

Returns a dictionary with filename keys containing prediction results:

#### Successful Prediction (with warning example)
```python
{
    'Al2O3.cif': {
        'synthesizable': True,
        'synthesizability_score': 0.92,
        'warnings': [
            'CIF missing symmetry information',
            'Using default tolerance for site occupancy'
        ]
    }
}
```

#### Successful Prediction (no warnings)
```python
{
    'SiO2.cif': {
        'synthesizable': True,
        'synthesizability_score': 0.95
    }
}
```

#### Failed Prediction
```python
{
    'invalid.cif': {
        'synthesizable': None,
        'synthesizability_score': None,
        'error': 'Failed to parse CIF: Invalid syntax at line 5'
    }
}
```

#### Mixed Batch
```python
{
    'Al2O3.cif': {
        'synthesizable': True,
        'synthesizability_score': 0.92
    },
    'FeO.cif': {
        'synthesizable': False,
        'synthesizability_score': 0.31
    },
    'corrupted.cif': {
        'synthesizable': None,
        'synthesizability_score': None,
        'error': 'Failed to read file: ...'
    }
}
```

### Output Fields

| Field | Type | Always Present | Description |
|-------|------|---|---|
| `synthesizable` | bool/null | Yes | True if score ≥ 0.70, False if < 0.70, null if prediction failed |
| `synthesizability_score` | float/null | Yes | Likelihood of successful synthesis (0-1), or null if failed |
| `warnings` | list | Only if warnings exist | Non-critical issues (e.g., missing metadata, low confidence) |
| `error` | str | Only if critical failure | Error message explaining why prediction failed |

---

## API Methods

### `SynthnnPredictor(predictor_name='synthnn', logger=None, use_mock=True)`

Initialize the predictor.

**Parameters:**
- `predictor_name` (str): Name identifier for this predictor instance
- `logger` (optional): Logger instance for capturing warnings/errors
- `use_mock` (bool): If True (default), use deterministic mock scores (Phase 1)

**Example:**
```python
predictor = SynthnnPredictor(predictor_name='my_synthnn', use_mock=True)
```

### `predict(input_data: dict) -> dict`

Predict synthesizability from CIF files.

**Parameters:**
- `input_data` (dict): Mapping of filenames to file paths

**Returns:**
- dict: Prediction results for each input file

**Error Handling:**
- Empty input returns empty dict: `{}`
- File read errors are captured and returned with error message
- CIF parsing errors are handled gracefully
- One failure doesn't crash batch processing

**Example:**
```python
results = predictor.predict({
    'Al2O3.cif': '/path/to/Al2O3.cif',
    'FeO.cif': '/path/to/FeO.cif'
})

# Check results
for filename, prediction in results.items():
    if prediction['synthesizable'] is not None:
        score = prediction['synthesizability_score']
        status = "synthesizable" if prediction['synthesizable'] else "not synthesizable"
        print(f"{filename}: {status} (score: {score})")
    else:
        print(f"{filename}: Failed - {prediction['error']}")
```

### `info() -> str`

Get description of predictor capabilities.

**Returns:**
- str: Human-readable description

**Example:**
```python
print(predictor.info())
# Output: SynthNN: Predicts synthesizability of inorganic crystalline materials ...
```

---

## Phase 1: Mock Prediction Scoring

### Scoring Rules

The Phase 1 mock implementation uses deterministic rules based on composition:

| Category | Examples | Score Range |
|----------|----------|---|
| Common structural oxides | Al2O3, SiO2, TiO2, Fe2O3 | 0.85-0.95 |
| Rock salt structure | NaCl | 0.93 |
| CommonBasic oxides | ZnO, MgO, CaO | 0.87-0.91 |
| Organic/complex | Contains C, N, H | 0.50-0.65 |
| Unknown inorganic | Other compositions | 0.73 |

### Synthesizability Threshold

- **Synthesizable**: score ≥ 0.70
- **Not synthesizable**: score < 0.70

Example:
- Al2O3 (score 0.92) → synthesizable
- FeO (score 0.31) → not synthesizable

---

## Testing

### Run All Tests

```bash
# From workspace root
pytest tests/unit/test_synthnn_behaviour.py -v
```

### Run Specific Test Class

```bash
pytest tests/unit/test_synthnn_behaviour.py::TestSynthnnPredictor -v
```

### Run Specific Test

```bash
pytest tests/unit/test_synthnn_behaviour.py::TestSynthnnPredictor::test_predict_full_workflow -v
```

### Test Coverage

- **composition_helper**: CIF parsing, formula normalization, error handling
- **synthnn_model_helper**: Mock predictions, empty batches, error resilience
- **SynthnnPredictor**: Full workflow, error handling, output structure, warnings

---

## Architecture

### Components

1. **SynthnnPredictor.py** - Main orchestrator
   - Handles file I/O
   - Coordinates composition extraction and prediction
   - Formats results and manages errors

2. **composition_helper.py** - CIF ↔ Composition utilities
   - Parses CIF files using pymatgen
   - Normalizes chemical formulas
   - Validates composition strings

3. **synthnn_model_helper.py** - Model wrapper
   - Encapsulates model loading (Phase 2/3)
   - Provides batch inference interface
   - Returns mock scores (Phase 1) or real predictions (Phase 2/3)

### Data Flow

```
Input (filenames → paths)
    ↓
Read CIF files
    ↓
Extract compositions with composition_helper
    ↓
Normalize formulas
    ↓
Batch predict with model_helper
    ↓
Format results + error handling
    ↓
Output (filenames → predictions)
```

---

## Phase 2/3: Real Model Integration (Future)

### Planned Changes

Phase 2/3 will integrate the real SynthNN model from [antoniuk1/SynthNN](https://github.com/antoniuk1/SynthNN):

- Replace `_predict_mock()` with `_predict_real()` in `synthnn_model_helper.py`
- Download and cache pretrained model weights
- Add composition encoding for model input (if needed)
- Add optional `torch` dependency
- Create integration tests with real model

### Architecture Remains Unchanged

- Same input/output interface
- Unit tests from Phase 1 still pass (with real scores)
- Performance improvements only (mock → real)
- No changes to SynthnnPredictor logic

### Toggle Between Phases

```python
# Phase 1 (current): Mock predictions
predictor = SynthnnPredictor(use_mock=True)

# Phase 2/3 (future): Real predictions
predictor = SynthnnPredictor(use_mock=False)
```

---

## Error Handling

### Critical Errors (∅ predictions)

| Error | Cause | Response |
|-------|-------|----------|
| File not found | Invalid filepath | Null score + error message |
| Invalid CIF | Malformed structure file | Null score + error message |
| Parse failure | Corrupted CIF data | Null score + error message |
| Model error | Prediction failure | Null score + error message |

### Non-Critical Warnings (✓ predictions)

| Warning | Cause | Response |
|---------|-------|----------|
| Low confidence | Score near threshold | Valid score + warning message |
| Missing metadata | Incomplete CIF | Valid score + warning message |

---

## Troubleshooting

### "File not found" error

**Cause**: Filepath doesn't exist  
**Solution**: Verify file path is absolute and correct

```python
from pathlib import Path
filepath = '/path/to/file.cif'
if not Path(filepath).exists():
    print(f"File not found: {filepath}")
```

### "Failed to parse CIF" error

**Cause**: CIF file has invalid syntax  
**Solution**: Validate CIF file with pymatgen directly

```python
from pymatgen.core.structure import Structure
try:
    struct = Structure.from_file('/path/to/file.cif')
    print(f"Valid CIF: {struct.composition}")
except Exception as e:
    print(f"Invalid CIF: {e}")
```

### Empty results dictionary

**Cause**: Empty input provided  
**Solution**: Provide at least one filename→filepath mapping

```python
input_data = {'file.cif': '/path/to/file.cif'}
results = predictor.predict(input_data)
```

---

## References

- **SynthNN Paper**: Antoniuk et al., npj Computational Materials (2023)
  - "Predicting the synthesizability of crystalline inorganic materials from the data of known material compositions"
  
- **Official Repository**: [antoniuk1/SynthNN](https://github.com/antoniuk1/SynthNN)

- **pymatgen Documentation**: [pymatgen.org](https://pymatgen.org/)

---

## Implementation Status

### Phase 1: ✅ Complete
- [x] composition_helper.py (CIF parsing)
- [x] synthnn_model_helper.py (mock predictions)
- [x] SynthnnPredictor.py (orchestration)
- [x] Unit tests
- [x] Documentation

### Phase 2/3: 🔜 Future
- [ ] Real model loading
- [ ] Composition encoding (if needed)
- [ ] Integration tests
- [ ] Performance optimization

---

## License

Part of EMOS (Exploration of Materials using Open Science)  
See root [README.md](../../../../README.md) for project license information.
