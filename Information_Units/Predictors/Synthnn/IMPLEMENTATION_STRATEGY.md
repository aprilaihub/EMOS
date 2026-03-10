# SynthNN Predictor - Implementation Strategy

## Overview
Lightweight wrapper for SynthNN deep learning model predicting synthesizability of inorganic crystalline materials. Based on COD database pattern for consistency.

**Core workflow**: CIF files → Extract compositions → Call SynthNN model → Return standardized properties

---

## Architecture

### File Structure
```
Information_Units/Predictors/Synthnn/
├── SynthnnPredictor.py              # Main orchestrator (predict method)
├── synthnn_model_helper.py          # Model loading, caching, inference
├── composition_helper.py            # CIF parsing, composition extraction
├── __init__.py
└── .models/                         # Cached model weights (git-ignored)
```

### Component Responsibilities

**SynthnnPredictor.py**
- Single `predict()` method that orchestrates the workflow
- Delegates CIF parsing to `composition_helper`
- Delegates model inference to `model_helper`
- Handles errors/warnings, formats output

**synthnn_model_helper.py**
- Loads and caches SynthNN model
- Implements `predict_batch()` for inference
- Lazy-loads model on first use

**composition_helper.py**
- Parses CIF files using pymatgen
- Extracts chemical compositions
- Normalizes composition strings

---

## Input/Output Format

### Input
```python
{filename: filepath, ...}

Example:
{
    'Al2O3.cif': '/path/to/Al2O3.cif',
    'FeO.cif': '/path/to/FeO.cif',
}
```

### Output
```python
{filename: {status, properties, warnings, error}, ...}

Example:
{
    'Al2O3.cif': {
        'status': 'ok',
        'properties': {
            'synthesizable': True,
            'synthesizability_score': 0.92
        },
        'warnings': [],
        'error': None
    },
    'FeO.cif': {
        'status': 'ok',
        'properties': {
            'synthesizable': False,
            'synthesizability_score': 0.31
        },
        'warnings': [],
        'error': None
    },
    'invalid.cif': {
        'status': 'error',
        'properties': {
            'synthesizable': None,
            'synthesizability_score': None
        },
        'warnings': [],
        'error': 'Failed to parse CIF: Invalid syntax'
    }
}
```

**Output Rules**:
- ✅ All input files present in output
- ✅ Critical errors: null property values + `'error'` key
- ✅ `warnings` always present as list
- ✅ JSON-serializable (None → null)

---

## Error Handling

### Critical Errors (null + error key)
- Invalid CIF syntax
- File read errors  
- Unable to extract composition
- Model inference failure

### Non-Critical Warnings (valid values + warnings array)
- Missing CIF metadata
- Default values used
- Structure normalization applied
- Low model confidence (score near threshold)

**Design**: All materials processed independently. One failure doesn't crash batch.

---

## Testing Strategy

### Unit Tests (`tests/unit/test_synthnn_behaviour.py`)
- Mock predictions using pytest fixtures
- Test CIF parsing and composition extraction
- Test error/warning handling
- Test output structure and JSON serialization
- **Run**: `pytest tests/unit/test_synthnn_behaviour.py -v`
- ✅ 38 tests, all passing

**Mocking Approach**:
- Mock `SynthnnModelHelper.__init__` to prevent real model loading
- Mock `predict_batch()` with deterministic scores
- Fixture `mock_model_helper` provides isolated test environment

### Integration Tests (`tests/integration/test_synthnn_sanity.py`)
- Real model tests (actual SynthNN predictions)
- Validate predictions on known materials
- **Run**: `pytest tests/integration/test_synthnn_sanity.py -v`
- **Skip**: `pytest -m "not network"` (to run offline)

---

## Implementation Complete

### Core Functionality ✅
- [x] `composition_helper.py` - CIF parsing with pymatgen
- [x] `synthnn_model_helper.py` - Model loading and inference  
- [x] `SynthnnPredictor.py` - Orchestrator with complete workflow
- [x] Unit tests with mock predictions (at test level)
- [x] Integration tests with real model
- [x] Error/warning handling
- [x] JSON output formatting

---

## Dependencies
- `pymatgen>=2024.6.0` (already in requirements.txt)
- `tensorflow` or `torch` (for real model inference)

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Production code: real model only** | Clean separation - model inference is real, mocking is for tests |
| **Mocking at test level (fixtures)** | Matches pattern in COD/Alexandria tests; fast CI/CD; easy to maintain |
| **Per-material error handling** | Failed materials return null + error; batch continues processing |
| **Filename-based tracking** | Results linked to input files; easy to trace issues |
| **Optional warnings array** | Only present when warnings exist; cleaner output |
| **No new core dependencies** | Reuses existing pymatgen; model comes pre-trained |
| **Lazy model loading** | Efficient memory usage; model only loaded when needed |

---

## References

**Pattern Source**: `Information_Units/Databases/Cod/` and `Information_Units/Databases/Alexandria/`

**Official SynthNN**: [antoniuk1/SynthNN](https://github.com/antoniuk1/SynthNN)
- Input: Chemical composition string (e.g., "Al2O3")
- Output: Synthesizability score 0.0-1.0
