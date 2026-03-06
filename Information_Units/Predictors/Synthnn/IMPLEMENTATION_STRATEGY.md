# SynthNN Predictor - Implementation Strategy

## Overview
Lightweight wrapper for SynthNN deep learning model predicting synthesizability of inorganic crystalline materials. Pattern-based on COD database implementation for consistency.

**Key Goal**: Take CIF files → Extract compositions → Call SynthNN model → Return standardized predictions.

---

## Development Approach: Phased Implementation

### **Phase 1: Mock-First Development (Current Focus)**
Build complete, production-ready predictor with **mock predictions** only:
- ✅ Full `predict()` workflow functional
- ✅ Real CIF parsing via pymatgen
- ✅ Deterministic mock scores for testing
- ✅ Complete error/warning handling
- ✅ Comprehensive unit tests
- ✅ Standardized JSON output format

**Benefits**:
- Fast iteration (no model download/loading)
- Testable immediately (no external dependencies)
- Validates architecture before model integration
- Unit tests remain useful long-term (faster CI/CD)

**Deliverable**: Fully functional predictor that returns mock scores but handles all real-world scenarios (invalid CIFs, file I/O, batch processing, errors, warnings).

---

### **Phase 2/3: Real Model Integration (Future Work)**
Replace mock predictions with actual SynthNN model:
- Explore official [antoniuk1/SynthNN](https://github.com/antoniuk1/SynthNN) repo
- Implement `_predict_real()` method (single function change)
- Download/cache pretrained weights
- Add integration tests with real model

**Key Point**: Architecture from Phase 1 remains unchanged. Simply toggle `use_mock=False` to enable real predictions.

---

## File Structure

```
Information_Units/Predictors/Synthnn/
├── SynthnnPredictor.py              # Minimal orchestrator (predict method only)
├── synthnn_model_helper.py          # Model loading, caching, inference logic
├── composition_helper.py             # CIF parsing, composition extraction/normalization
├── README.md                         # User-facing documentation
├── IMPLEMENTATION_STRATEGY.md        # This file
├── __init__.py
└── .models/                         # (Git-ignored) cached model weights
    └── synthnn_model.pt             # Pre-trained weights (lazy-loaded)
```

---

## Phase 1: Mock Implementation Strategy

### What Gets Built
1. **Real CIF parsing**: `composition_helper.py` uses actual pymatgen to parse CIF files
2. **Mock predictions**: `synthnn_model_helper.py` returns deterministic scores based on composition
3. **Full orchestration**: `SynthnnPredictor.py` handles complete workflow including errors/warnings
4. **Production-ready output**: JSON-formatted results with proper error handling

### Mock Scoring Rules
Simple, deterministic scoring based on composition patterns:

```python
def _predict_mock(self, compositions: List[str]) -> Dict[str, float]:
    """Phase 1 mock scoring."""
    common_synthesizable = {
        'Al2O3': 0.92,   # Alumina (very common)
        'Fe2O3': 0.88,   # Iron oxide
        'SiO2': 0.95,    # Silica
        'TiO2': 0.90,    # Titania
        'ZnO': 0.87,     # Zinc oxide
    }
    
    results = {}
    for comp in compositions:
        if comp in common_synthesizable:
            results[comp] = common_synthesizable[comp]
        elif contains_organic_elements(comp):  # C, N, H
            results[comp] = 0.55  # Lower score for organic/complex
        else:
            results[comp] = 0.75  # Default moderate score
    
    return results
```

### Why This Works
- ✅ **Complete workflow testing**: Validates entire pipeline without model
- ✅ **Deterministic tests**: Same input always produces same output
- ✅ **Fast execution**: No model loading, no GPU, runs in milliseconds
- ✅ **Realistic scenarios**: Tests real CIF parsing, file I/O, error handling
- ✅ **Easy transition**: Phase 2/3 only changes `_predict_real()` implementation

---

## Core Implementation Components

### 1. SynthnnPredictor.py (Minimal Orchestrator)
**Responsibility**: Single entry point, delegates all logic.

**Phase 1 Note**: Uses mock predictions by default (`use_mock=True` in model helper).

```python
class SynthnnPredictor(BasePredictor):
    def __init__(self, predictor_name, logger=None):
        super().__init__(predictor_name, logger)
        self.model_helper = SynthnnModelHelper(logger=logger, use_mock=True)  # Phase 1 default
        self.composition_helper = CompositionHelper()
    
    def predict(self, input_data: dict) -> dict:
        """
        Args:
            input_data: {
                'Al2O3.cif': '/path/to/Al2O3.cif',
                'FeO.cif': '/path/to/FeO.cif',
                ...
            }
        
        Returns:
            {
                'Al2O3.cif': {
                    'synthesizable': True,
                    'synthesizability_score': 0.92,
                    'warnings': ['CIF missing symmetry information']
                },
                'FeO.cif': {
                    'synthesizable': False,
                    'synthesizability_score': 0.31
                },
                'invalid.cif': {
                    'synthesizable': null,
                    'synthesizability_score': null,
                    'error': 'Failed to parse CIF: Invalid syntax at line 5'
                }
            }
            
            Note: 'warnings' key only included if warnings exist (optional)
        """
        # 1. Read CIF files and extract compositions (delegate to composition_helper)
        # 2. Predict scores for each composition (delegate to synthnn_model_helper)
        # 3. Format results as {filename: {property: value OR null, ...}}
        # 4. Failed materials get null values + 'error' key with message
        # 5. Non-critical issues add optional 'warnings' array (e.g., missing metadata)
        # 6. Log all operations via self.logger (detailed errors/warnings)
```

**Key Design Points**:
- Keep method minimal (~30-40 lines)
- Input: filename → filepath mapping (direct, no wrapper key)
- Output: filename → properties dict (extensible for other predictors)
- All errors logged internally (not raised) — process all materials even if some fail
- Failed materials included in output with null values + 'error' message
- Dual error tracking: concise message in output + detailed message in logs

---

### 2. composition_helper.py (CIF ↔ Composition)
**Responsibility**: Parse CIF files and extract/normalize chemical formulas.

```python
class CompositionHelper:
    """Utilities for CIF parsing and composition extraction."""
    
    @staticmethod
    def extract_from_cif(cif_content: str) -> tuple:
        """
        Parse CIF string using pymatgen.
        
        Returns:
            (formula_string, success: bool)
            Examples:
            - "Al2O3" (reduced formula)
            - "Fe2O3"
            
        Gracefully handles:
            - Invalid CIF syntax → return (None, False) with error logged
            - Multi-site occupancies → uses reduced formula
            - Fractional coordinates → normalized
        """
        try:
            from pymatgen.core.structure import Structure
            struct = Structure.from_str(cif_content, fmt='cif')
            return (str(struct.composition.reduced_formula), True)
        except Exception as e:
            return (None, False)  # Let caller handle error
    
    @staticmethod
    def normalize_composition(formula: str) -> str:
        """
        Normalize composition for model input.
        
        Handles:
            - Whitespace removal
            - Stoichiometry standardization
            - Element ordering (alphabetical)
        
        Returns:
            Normalized formula string suitable for SynthNN model
        """
```

---

### 3. synthnn_model_helper.py (Model Management)
**Responsibility**: Load, cache, and run inference on SynthNN model.

```python
class SynthnnModelHelper:
    """Wrapper for SynthNN model with caching and mock capability."""
    
    MODEL_CACHE_DIR = Path(__file__).parent / '.models'
    MODEL_FILE = 'synthnn_model.pt'
    
    def __init__(self, logger=None, use_mock=True):
        """
        Args:
            logger: Optional logger for warnings
            use_mock: If True, return deterministic mock scores (default for Phase 1)
        """
        self.logger = logger
        self.use_mock = use_mock
        self.model = None
        if not use_mock:
            self._load_model()  # Only load if not using mock (Phase 2/3)
    
    def _load_model(self):
        """
        Load SynthNN model (Phase 2/3 implementation).
        
        Phase 1: Not implemented (use_mock=True by default)
        Phase 2/3: Load model from cache or download from official source
        """
        pass  # Placeholder for Phase 2/3
    
    def predict_batch(self, compositions: List[str]) -> Dict[str, float]:
        """
        Batch prediction for multiple compositions.
        
        Args:
            compositions: ['Al2O3', 'FeO', ...]
        
        Returns:
            {'Al2O3': 0.92, 'FeO': 0.31, ...}
            
        Phase 1: Returns deterministic mock scores
        Phase 2/3: Returns actual SynthNN model predictions
        """
        if self.use_mock:
            return self._predict_mock(compositions)
        else:
            return self._predict_real(compositions)
    
    def _predict_mock(self, compositions: List[str]) -> Dict[str, float]:
        """
        Return deterministic mock scores for testing (Phase 1).
        
        Mock scoring rules:
        - Common oxides (Al2O3, Fe2O3, SiO2): 0.85-0.95
        - Common compounds: 0.70-0.85
        - Unknown/rare compositions: 0.40-0.60
        
        Returns float scores (0-1) indicating synthesizability likelihood.
        """
        # Phase 1 implementation goes here
        common_high = ['Al2O3', 'Fe2O3', 'SiO2', 'TiO2', 'ZnO']
        results = {}
        
        for comp in compositions:
            if comp in common_high:
                results[comp] = 0.90  # High synthesizability
            elif any(elem in comp for elem in ['C', 'N', 'H']):
                results[comp] = 0.55  # Organic/complex - medium
            else:
                results[comp] = 0.75  # Default - moderately high
        
        return results
    
    def _predict_real(self, compositions: List[str]) -> Dict[str, float]:
        """
        Call actual SynthNN model (Phase 2/3 implementation).
        
        Phase 1: Returns None (triggers error handling in caller)
        Phase 2/3: Integration point for official SynthNN repo
        
        Three potential approaches:
        1. Direct model call (if SynthNN provides Python API)
        2. Subprocess wrapper (if SynthNN provides CLI tool)
        3. Import as module (if SynthNN is pip-installable)
        """
        # Phase 1: Not implemented
        if self.logger:
            self.logger.log("Real model not implemented (Phase 2/3)", 'warn')
        return {comp: None for comp in compositions}  # Triggers error handling
```

---

## Input/Output Specification

### Unified Predictor Interface

All predictors follow this consistent pattern for maximum extensibility and usability:

**Input**: `{filename: filepath, ...}`
```python
{
    'Al2O3.cif': '/path/to/Al2O3.cif',
    'FeO.cif': '/path/to/FeO.cif',
    'SiO2.cif': '/path/to/SiO2.cif'
}
```

**Output**: `{filename: {property: value, ...}, ...}`
```python
{
    'Al2O3.cif': {
        'synthesizable': True,
        'synthesizability_score': 0.92,
        'warnings': [
            'CIF missing symmetry information',
            'Using default tolerance for site occupancy'
        ]
    },
    'FeO.cif': {
        'synthesizable': False,
        'synthesizability_score': 0.31
        # No warnings key - only included when warnings exist
    },
    'SiO2.cif': {
        'synthesizable': True,
        'synthesizability_score': 0.87
    },
    'invalid.cif': {
        'synthesizable': null,
        'synthesizability_score': null,
        'error': 'Failed to parse CIF: Invalid syntax at line 5'
    },
    'corrupted.cif': {
        'synthesizable': null,
        'synthesizability_score': null,
        'error': 'Unable to extract composition: Ambiguous element symbols'
    }
}
```

**Output Field Details**:
- **Required properties**: All materials get property keys (valid values or null)
- **`error` key**: Only present for critical failures (null property values)
- **`warnings` key**: Optional array, only present for non-critical issues (valid property values with caveats)

**Why This Design**:
- ✅ **Filename-based tracking**: Results linked back to input files
- ✅ **Property-dict extensibility**: Works for SynthNN (2 properties) and other predictors (formation energy, band gap, etc.)
- ✅ **Transparent error handling**: Failed files included with null values + error message
- ✅ **Quality indicators**: Optional warnings show non-critical issues affecting result quality
- ✅ **JSON-ready output**: Compatible with JSON serialization (Python None → JSON null)
- ✅ **Consistent structure**: All files present in output (success or failure)
- ✅ **Frontend-friendly**: No need to handle missing keys or different structures
- ✅ **No redundant wrapper keys**: Direct mapping, cleaner interface
- ✅ **Uniform across all predictors**: Same structure regardless of model
- ✅ **Traceable errors**: Error messages explain what went wrong per file
- ✅ **Distinguishes severity**: Errors (critical) vs warnings (non-critical)

---

### tests/unit/test_synthnn_behaviour.py
**Focus**: Fast, isolated tests with mocked model.

```python
@pytest.mark.unit
class TestCompositionExtraction:
    """Test CIF parsing and composition normalization."""
    
    def test_extract_cif_from_file_valid(self):
        """Valid CIF file → correct formula extracted."""
        
    def test_extract_cif_invalid_syntax(self):
        """Malformed CIF → gracefully skipped."""
        
    def test_normalize_composition_variations(self):
        """Handle whitespace, stoichiometry, ordering variations."""

@pytest.mark.unit
class TestModelBehaviour:
    """Test model wrapper logic (mocked inference)."""
    
    def test_predict_batch_empty(self):
        """Empty composition list → empty results dict."""
        
    def test_predict_batch_with_mock(self):
        """Mocked model returns fixed scores deterministically."""
        
    def test_predict_batch_error_resilience(self):
        """One composition error doesn't crash batch processing."""

@pytest.mark.unit
class TestSynthnnPredictor:
    """Test orchestrator logic."""
    
    def test_predict_full_workflow(self):
        """CIF file → composition → score → {filename: {properties}} output."""
        # Input: {'Al2O3.cif': '/path/to/Al2O3.cif', ...}
        # Output: {'Al2O3.cif': {'synthesizable': True, 'synthesizability_score': 0.92}, ...}
        
    def test_predict_error_handling(self):
        """Invalid CIFs return null values with error messages."""
        # Input: {'invalid.cif': '/path/to/corrupted.cif'}
        # Output: {'invalid.cif': {'synthesizable': None, 'synthesizability_score': None, 'error': '...'}}
        
    def test_predict_output_structure(self):
        """Output has all filenames with property dicts (success or null + error)."""
        # Both successful and failed materials present in output
        
    def test_predict_mixed_batch(self):
        """Batch with both valid and invalid files handled correctly."""
        # Some succeed (properties), some fail (null + error), none skipped
        
    def test_predict_with_warnings(self):
        """Materials with non-critical issues include warnings array."""
        # Input: CIF with missing metadata
        # Output: Valid predictions + 'warnings': ['Missing symmetry info', ...]
```

**Run**: `pytest tests/unit/test_synthnn_behaviour.py -v`

---

### tests/integration/test_synthnn_sanity.py
**Focus**: Real model calls (when available), validate predictions are sensible.

```python
@pytest.mark.integration
@pytest.mark.network  # Skip in offline mode: pytest -m "not network"
@pytest.mark.slow
class TestSynthnnRealModel:
    """Test with actual SynthNN model and real materials."""
    
    def test_predict_known_materials_from_files(self, tmp_path):
        """Verify model scores known materials appropriately from CIF files."""
        # Create test CIF files for Al2O3, Fe2O3 (should score high)
        # Create test CIF for nonsense composition (should score low)
        # Verify predictions are reasonable
        
    def test_predict_output_format(self):
        """Verify output structure matches {filename: {properties}}."""
        # Input: {'Al2O3.cif': '/path/...', 'FeO.cif': '/path/...'}
        # Output: Contains same filenames as keys with property dicts
```

**Run**: `pytest tests/integration/test_synthnn_sanity.py -v`  
**Skip network**: `pytest tests/integration/test_synthnn_sanity.py -m "not network"`

---

## Dependencies

**No new dependencies required** — reuse existing:
- `pymatgen>=2024.6.0` (already in requirements.txt)
- `pytest>=8.2.2` (already in requirements.txt)

**Optional (for torch-based inference)**:
```txt
# If direct model loading needed:
torch>=2.0.0
```

Current approach uses pre-trained model → no training needed.

---

## Error & Warning Handling Strategy

### Critical Errors (Return null + error)
| Error Type | Source | Response | Logging |
|-----------|--------|----------|---------|
| Invalid CIF syntax | composition_helper | Return null + error message | ERROR |
| File read error | SynthnnPredictor | Return null + error message | ERROR |
| Malformed composition | composition_helper | Return null + error message | ERROR |
| Model load failure | synthnn_model_helper | Fallback to mock (Phase 1: N/A) | WARN |
| Model inference error | synthnn_model_helper | Return null + error message | ERROR |
| Empty input | SynthnnPredictor | Return empty dict `{}` | INFO |

### Non-Critical Warnings (Return valid values + warnings array)
| Warning Type | Source | Response | Example |
|-------------|--------|----------|---------|
| Missing CIF metadata | composition_helper | Add to warnings array | 'CIF missing symmetry information' |
| Default values used | composition_helper | Add to warnings array | 'Using default tolerance for occupancy' |
| Deprecated format | composition_helper | Add to warnings array | 'CIF uses deprecated element symbols' |
| Low model confidence | synthnn_model_helper | Add to warnings array | 'Prediction confidence below threshold (0.65)' |
| Structure normalization | composition_helper | Add to warnings array | 'Applied unusual structure corrections' |

**Key Principles**:
1. **Critical failures** (errors): Cannot produce valid prediction → null values + `'error'` key
2. **Non-critical issues** (warnings): Prediction succeeded but user should be aware → valid values + optional `'warnings'` array
3. **Fail gracefully**: Don't crash entire batch; process all materials independently

**Output Structure by Severity**:
- **Success, no issues**: `{'property1': value1, 'property2': value2}`
- **Success with warnings**: `{'property1': value1, 'property2': value2, 'warnings': [...]}`
- **Critical failure**: `{'property1': null, 'property2': null, 'error': '...'}`

**Dual Tracking**:
- **Output**: User-friendly messages (concise, actionable)
- **Logs**: Detailed technical information (stack traces, line numbers, etc.)

---

## Implementation Checklist

### Phase 1: Mock-First Implementation (Current Focus)

**Core Files**:
- [ ] Create `composition_helper.py` with CIF parsing logic
  - [ ] `extract_from_cif()` using pymatgen
  - [ ] `normalize_composition()` for standardization
  - [ ] Error handling for invalid CIFs
- [ ] Create `synthnn_model_helper.py` with mock predictions
  - [ ] `__init__()` with `use_mock=True` default
  - [ ] `_predict_mock()` with deterministic scores
  - [ ] `_predict_real()` placeholder (returns None)
- [ ] Update `SynthnnPredictor.py` with complete `predict()` method
  - [ ] File I/O and CIF reading
  - [ ] Composition extraction delegation
  - [ ] Mock prediction delegation
  - [ ] Error/warning aggregation
  - [ ] JSON output formatting

**Testing**:
- [ ] Unit tests for `composition_helper.py`
  - [ ] Valid CIF parsing
  - [ ] Invalid CIF error handling
  - [ ] Composition normalization edge cases
- [ ] Unit tests for `synthnn_model_helper.py`
  - [ ] Mock predictions are deterministic
  - [ ] Empty input handling
  - [ ] Batch processing
- [ ] Unit tests for `SynthnnPredictor.py`
  - [ ] End-to-end workflow with mock
  - [ ] Error handling (null + error message)
  - [ ] Warning handling (valid + warnings array)
  - [ ] Mixed batch (success + failure)
  - [ ] JSON output structure validation

**Documentation**:
- [ ] Update README.md with Phase 1 usage examples
- [ ] Document mock scoring rules
- [ ] Document input/output JSON format

**Phase 1 Deliverable**: Fully functional predictor returning mock scores with production-ready error handling, JSON output, and comprehensive test coverage.

---

### Phase 2/3: Real Model Integration (Future Work)

**Model Setup**:
- [ ] Clone/download [antoniuk1/SynthNN](https://github.com/antoniuk1/SynthNN) repo
- [ ] Identify model interface (Python API, CLI, or module)
- [ ] Download pretrained model weights
- [ ] Cache model in `.models/` directory

**Implementation**:
- [ ] Implement `_load_model()` in `synthnn_model_helper.py`
- [ ] Implement `_predict_real()` with actual SynthNN calls
- [ ] Add composition encoding utilities (if needed)
- [ ] Add optional torch dependency to requirements.txt

**Testing**:
- [ ] Integration tests with real model (mark `@pytest.mark.network`)
- [ ] Validate predictions on known materials
- [ ] Performance benchmarking (inference time)

**Phase 2/3 Deliverable**: Drop-in replacement for mock predictions with real SynthNN model. Unit tests from Phase 1 remain unchanged.

---

## Key Decisions Rationale

| Decision | Why |
|----------|-----|
| **Mock-first development (Phase 1)** | Complete testable implementation without model; validates architecture early |
| **Deterministic mock scores** | Unit tests are repeatable and fast; no external dependencies |
| **Lazy-load model (Phase 2/3)** | Model may be large (~100MB+); cache in memory after 1st load |
| **Separate composition_helper** | Testable independently; matches COD pattern; reusable across predictors |
| **Mock at model level** | Unit tests don't require model file; can run offline |
| **Per-material error handling** | Failed materials return null + error; don't crash batch |
| **Transparent errors in output** | User sees which files failed and why; improves UX |
| **Quality indicators (warnings)** | User aware of non-critical issues affecting results |
| **Filename-based tracking** | Results linked to input files; easy to trace issues |
| **Property dict output** | Extensible to other predictors (form. energy, band gap, forces, etc.) |
| **Consistent output structure** | All files present (success or failure); frontend-friendly |
| **No wrapper keys in input** | Direct filename→filepath mapping; simpler interface |
| **JSON-ready output** | Python None → JSON null; no serialization issues |
| **No new dependencies (Phase 1)** | Stay lightweight; only pymatgen (already in requirements.txt) |

---

## References

**Pattern Source**: `Information_Units/Databases/Cod/`
- CodDatabase.py → SynthnnPredictor.py (orchestrator)
- CodAPIHelper.py → synthnn_model_helper.py (logic isolation)

**Test Examples**: `tests/unit/test_cod_api_behaviour.py`, `tests/integration/test_cod_api_sanity.py`

**Official SynthNN**: [antoniuk1/SynthNN](https://github.com/antoniuk1/SynthNN)
- Paper: "Predicting the synthesizability of crystalline inorganic materials from the data of known material compositions" (npj Computational Materials 2023)
- Model input: Chemical composition string (e.g., "Al2O3")
- Model output: Probability score 0-1 (synthesizability likelihood)

---

## Timeline Estimate

### Phase 1: Mock-First Implementation
| Task | Time |
|------|------|
| `composition_helper.py` implementation | 1 hour |
| `synthnn_model_helper.py` with mock | 1 hour |
| `SynthnnPredictor.py` orchestrator | 1-2 hours |
| Unit tests (comprehensive) | 2-3 hours |
| Documentation & README | 1 hour |
| **Phase 1 Total** | **6-8 hours** |

### Phase 2/3: Real Model Integration (Future)
| Task | Time |
|------|------|
| Explore SynthNN repo & identify interface | 1-2 hours |
| Download/setup model weights | 0.5 hour |
| Implement `_predict_real()` | 2-3 hours |
| Integration tests | 1-2 hours |
| **Phase 2/3 Total** | **4-7 hours** |

**Note**: Phase 1 delivers a complete, testable, production-ready predictor. Phase 2/3 is independent follow-up work that swaps mock scores for real model predictions.
