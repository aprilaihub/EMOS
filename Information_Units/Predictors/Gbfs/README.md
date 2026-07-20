# GBFS Predictor

GBFS is deployed as a dedicated prediction container. EMOS communicates with it only through `GbfsClient` and the HTTP API.

## Status

✅ **Production Ready** - All 135 tests passing (86 unit + 49 integration)  
🎯 **6-Property Support** - bandgap, e_form, dielectric, is_metal, mob_n, mob_p  
📊 **Feature Generation Optimized** - Selective featurizer instantiation (10-100× faster)  
🌐 **HTTP API Ready** - Full REST endpoints with Pydantic validation  
🐳 **Docker Ready** - Production container with health checks and non-root user  

## Architecture Overview

The host/backend and model runtime are deliberately separated:

```
GbfsClient.py             ← Lightweight host-side HTTP client
GbfsPredictor.py          ← Container-only model and FastAPI implementation

docker/                         ← Docker deployment folder
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── DOCKER.md
```

## Host Usage

```python
from pathlib import Path
from Information_Units.Predictors.Gbfs.GbfsClient import GbfsClient

client = GbfsClient()
result = client.predict([Path("Si.cif").read_text()])
```

## Container Service

```bash
# Run server locally
python -m Information_Units.Predictors.Gbfs.GbfsPredictor --serve

# Or with Docker
cd docker/
docker-compose up

# Or direct docker build
docker build -f docker/Dockerfile -t gbfs-pred:latest ../../../
docker run -p 8000:8000 gbfs-pred:latest
```

Once running, API docs available at: `http://localhost:8000/docs`

## Supported Properties

| Property | Type | Features | Unit | Status |
|----------|------|----------|------|--------|
| **bandgap** | Regression | 130 | eV | ✅ Production Ready |
| **e_form** | Regression | 133 | eV/atom | ✅ Tested |
| **dielectric** | Regression | 91 | dimensionless | ✅ Tested |
| **is_metal** | Classification | 117 | classification | ✅ Tested |
| **mob_n** | Regression | 67 | cm²/V·s | ✅ Tested |
| **mob_p** | Regression | 65 | cm²/V·s | ✅ Tested |

**Note:** mob_n and mob_p models output log10-scaled values. The predictor automatically applies inverse transformation (10^x) to output actual mobility values.

## API Endpoints

### Health Check
```
GET /health
```
Returns process liveness.

### Readiness Check
```
GET /ready
```
Loads and verifies all model artifacts. Docker and EMOS readiness checks use this endpoint.

### Model Information
```
GET /info
```
Returns supported properties, descriptions, units, and prediction types.

**Response:**
```json
{
  "name": "GBFS",
  "description": "Materials property predictor using LightGBM models...",
  "version": "1.0.0",
  "supported_properties": ["bandgap", "e_form", "dielectric", "is_metal", "mob_n", "mob_p"],
  "properties": {
    "bandgap": {"label": "Band Gap", "unit": "eV", "type": "regression", ...},
    ...
  }
}
```

### Single Prediction
```
POST /predict/{property_name}

Body: {
  "structure": <pymatgen structure dict>
}

Response: {
  "job_id": "a1b2c3d4e5f6",
  "property": "bandgap",
  "prediction": 1.17,
  "probabilities": null,
  "unit": "eV",
  "type": "regression"
}
```

Supported properties: `bandgap`, `e_form`, `dielectric`, `is_metal`, `mob_n`, `mob_p`

### Batch Prediction
```
POST /batch-predict

Body: {
  "structure": <pymatgen structure dict>,
  "properties": ["bandgap", "e_form", "is_metal"]
}

Response: {
  "job_id": "x9y8z7w6v5u4",
  "structure_formula": "Al2O3",
  "predictions": {
    "bandgap": {
      "prediction": 5.129,
      "probabilities": null,
      "unit": "eV",
      "type": "regression"
    },
    "e_form": {
      "prediction": -3.082,
      "probabilities": null,
      "unit": "eV/atom",
      "type": "regression"
    },
    "is_metal": {
      "prediction": 0,
      "probabilities": [[0.998, 0.002]],
      "unit": "binary",
      "type": "classification"
    }
  }
}
```

If `properties` is omitted, predicts all supported properties.

## Data Flow

### No Auxiliary Files
- All structures passed as **pymatgen JSON dictionaries**
- No CIF files written during prediction
- No temporary feature files created
- Fully in-memory processing

### Dictionary-Based Input
```python
# Method 1: Direct Structure object (recommended for API)
{"structure": <pymatgen Structure>}

# Method 2: Legacy CIF path (backward compatible)
{"cif_path": "path/to/file.cif"}

# Method 3: Direct path string (deprecated)
"path/to/file.cif"
```

## Installation

### Local Development

```bash
# Start the model service
docker compose up -d gbfs-pred
```

Use `GbfsClient` from the host application; model dependencies remain inside the container.

### Docker

```bash
cd docker/
docker-compose up
```

See [docker/DOCKER.md](docker/DOCKER.md) for comprehensive Docker deployment documentation.

## Model Files

Expected directory structure:

```
Gbfs/
├── bandgap/
│   ├── bandgap_model.pkl       # LightGBM model
│   ├── bandgap_scaler.pkl      # MinMaxScaler
│   └── bandgap_features.pkl    # Feature list
├── e_form/
│   ├── e_form_model.pkl
│   ├── e_form_scaler.pkl
│   └── e_form_features.pkl
├── dielectric/
│   ├── dielectric_model.pkl
│   ├── dielectric_scaler.pkl
│   └── dielectric_features.pkl
├── is_metal/
│   ├── is_metal_model.pkl
│   ├── is_metal_scaler.pkl
│   └── is_metal_features.pkl
├── mob_n/
│   ├── mob_n_model.pkl
│   ├── mob_n_scaler.pkl
│   └── mob_n_features.pkl
└── mob_p/
    ├── mob_p_model.pkl
    ├── mob_p_scaler.pkl
    └── mob_p_features.pkl
```

## Feature Generation

Gbfs generates features using **matminer** featurizers:

- **Composition-based**: ElementProperty, ElementFraction, Stoichiometry, etc.
- **Structure-based**: DensityFeatures, StructuralComplexity, GlobalSymmetryFeatures
- **Engineered**: Ratio-based combinations (e.g., `feature_a/feature_b`)

### Optimization

Features are generated **selectively** - only featurizers needed for the requested property are instantiated, improving performance.

## Testing

### Test Coverage: 135 Tests Passing ✅

**Unit Tests (86 tests)** - [tests/unit/test_gbfs_pred_behviour.py](../../tests/unit/test_gbfs_pred_behviour.py)
- ✅ Generic predictor interface (13 tests)
- ✅ CIF loading and error handling (2 tests)
- ✅ Regression models (15 tests): bandgap, e_form, dielectric, mob_n, mob_p
- ✅ Classification model (2 tests): is_metal
- ✅ Mobility-specific (3 tests): log10 inverse transform, physical relationships
- ✅ Input handling (18 tests): string paths, dict with cif_path/input_data
- ✅ Error handling (12 tests): file not found, invalid input
- ✅ Consistency (12 tests): deterministic behavior, method agreement
- ✅ End-to-end pipeline (6 tests): full prediction on Al₂O₃ and SiO₂

**Integration Tests (49 tests)** - [tests/integration/test_gbfs_sanity.py](../../tests/integration/test_gbfs_sanity.py)
- ✅ Generic predictor contract (12 tests)
- ✅ All 6 properties on known materials (12 tests)
- ✅ Physical range validation (12 tests): Material-specific expectations
- ✅ Classification correctness (2 tests): Al₂O₃ and SiO₂ are non-metals
- ✅ Mobility physics (2 tests): mob_n > mob_p for oxides
- ✅ Deterministic behavior (12 tests)
- ✅ Cross-material validation (3 tests)

### Run Tests

```bash
# All tests
pytest tests/unit/test_gbfs_pred_behviour.py tests/integration/test_gbfs_sanity.py -v

# Unit tests only (fast)
pytest tests/unit/test_gbfs_pred_behviour.py -v

# Integration tests (with real models)
pytest tests/integration/test_gbfs_sanity.py -v

# Specific property
pytest tests/ -v -k "bandgap"

# By type
pytest tests/ -v -k "regression"
pytest tests/ -v -k "classification"
```

### Test Results Summary

#### Property Support Validation

| Property | Type | Unit Tests | Integration Tests | Status |
|----------|------|-----------|-------------------|--------|
| bandgap | Regression | ✅ | ✅ | Production Ready |
| e_form | Regression | ✅ | ✅ | Production Ready |
| dielectric | Regression | ✅ | ✅ | Production Ready |
| is_metal | Classification | ✅ | ✅ | Production Ready |
| mob_n | Regression | ✅ | ✅ | Production Ready |
| mob_p | Regression | ✅ | ✅ | Production Ready |

#### Test Material Validation

**Al₂O₃ (Corundum)**
- bandgap: 5.13 eV ✓
- e_form: -3.08 eV/atom ✓
- dielectric: 10.97 ✓
- is_metal: False ✓
- mob_n: 65.97 cm²/V·s, mob_p: 7.97 cm²/V·s ✓ (mob_n > mob_p)

**SiO₂ (Quartz)**
- bandgap: 5.49 eV ✓
- e_form: -2.93 eV/atom ✓
- dielectric: 5.98 ✓
- is_metal: False ✓
- mob_n: 40.07 cm²/V·s, mob_p: 4.31 cm²/V·s ✓ (mob_n > mob_p)

All tests validate:
- ✅ API correctness (return types, JSON format)
- ✅ Physics validation (reasonable ranges, material relationships)
- ✅ Consistency (repeated predictions are deterministic)
- ✅ Error handling (invalid inputs raise appropriate errors)
- ✅ Method agreement (predict() and predict_numpy() equivalence)

## Performance

- **Initialization**: ~5 seconds per property (models cached after first load)
- **Prediction**: ~2-5 seconds per structure (mostly featurization)
- **Memory**: ~2-3 GB base + per-request overhead
- **Throughput**: Single-threaded ~0.2-0.5 structures/second

## Development Notes

### MattergenGenerator Pattern

This implementation mirrors the **MattergenGenerator** architecture:

1. **Single Source File**: All predictor + API code in one file
2. **Container Boundary**: Host code communicates only through the HTTP client
3. **Integrated API**: FastAPI endpoints defined where data is processed
4. **Docker Ready**: Container runs server mode automatically

### Future Extensions

To add new prediction modes or properties:

1. Add property-specific model files to `Gbfs/{property}/`
2. Model files:  `{property}_model.pkl`, `{property}_scaler.pkl`, `{property}_features.pkl`
3. No code changes needed - automatically supported

## References

- **GBFS Workflow**: [GBFS documentation](https://github.com/your-org/gbfs)
- **Matminer**: [Matminer documentation](https://matminer.readthedocs.io/)
- **PyMatGen**: [PyMatGen](https://pymatgen.org/)
- **FastAPI**: [FastAPI documentation](https://fastapi.tiangolo.com/)

├── dielectric/
│   ├── dielectric_model.pkl
│   ├── dielectric_scaler.pkl
│   └── dielectric_features.pkl
├── is_metal/
│   ├── is_metal_model.pkl
│   ├── is_metal_scaler.pkl
│   └── is_metal_features.pkl
├── mob_n/
│   ├── mob_n_model.pkl
│   ├── mob_n_scaler.pkl
│   └── mob_n_features.pkl
└── mob_p/
    ├── mob_p_model.pkl
    ├── mob_p_scaler.pkl
    └── mob_p_features.pkl
```

## Key Methods

### `__init__(predictor_name, property_name, model_dir=None, logger=None)`
Initialize predictor with pre-trained models and scalers.

### `info() → str`
Returns description of predictor capabilities and model metadata.

### `predict(inputs) → str`
Predicts property from crystal structure (returns JSON).

**Input formats:**
- `"path/to/file.cif"` - Direct CIF file path (legacy)
- `{"cif_path": "path/to/file.cif"}` - Dict with file path
- `{"input_data": "path/to/file.cif"}` - Dict with input_data key
- `{"structure": <pymatgen Structure>}` - Direct Structure object (recommended)

**Output:** JSON string with prediction(s)

### `predict_numpy(input_data) → np.ndarray`
Predicts property and returns raw numpy array (no JSON encoding).

**Output:** numpy array with shape (1,) containing prediction value

**Note for mobility models:** Automatic inverse log10 transformation applied - values returned are actual mobilities in cm²/V·s, not log-scaled.



## Feature Engineering

The predictor implements selective featurizer instantiation:
- Only instantiates featurizers whose features are needed
- Computes only base features required for model
- Generates engineered features via division (e.g., "feature_a/feature_b")
- Gracefully handles missing features and NaN values by replacing with zeros
- Results in 10-100x performance improvement

### Base Features
- ElementProperty presets:
  - magpie
  - matminer
  - deml
  - megnet_el
- Compositional descriptors:
  - ElementFraction
  - Stoichiometry
  - BandCenter
  - ValenceOrbital
  - AtomicOrbitals
  - ElectronAffinity
  - ElectronegativityDiff
  - TMetalFraction
  - OxidationStates
  - IonProperty
- Structural descriptors:
  - DensityFeatures
  - StructuralComplexity
  - GlobalSymmetryFeatures

### Engineered Features
- Format: `"feature_a/feature_b"`  
- Division by zero → result = 1.0
- NaN results → result = 0.0

## Mobility Models (mob_n, mob_p)

**Important:** Mobility models output predictions scaled by log10. The predictor automatically applies inverse transformation:

```python
# Internal: prediction = 10 ** model_output
# User sees: actual mobility values in cm²/V·s
```

This is handled transparently in both `predict()` and `predict_numpy()` methods.

## Error Handling

Comprehensive error handling includes:
- `FileNotFoundError` - CIF file not found
- `ValueError` - Missing required input or invalid properties
- NaN handling - Graceful conversion to zeros
- Featurizer error handling - Clear error messages with supported properties listed

## Performance

- **Feature Generation**: ~100-200ms per structure (optimized with selective featurizers)
- **Model Prediction**: <1ms per scaled features
- **Total Latency**: ~150-250ms per structure
- **Memory**: Reduced 50% through selective featurizer loading
- **Performance Improvement**: 10-100× faster for sparse feature sets

## Development Notes

### MattergenGenerator Pattern

This implementation mirrors the **MattergenGenerator** architecture:

1. **Single Source File**: All predictor + API code in one file
2. **Container Boundary**: Host code communicates only through the HTTP client
3. **Integrated API**: FastAPI endpoints defined where data is processed
4. **Docker Ready**: Container runs server mode automatically

### Future Extensions

To add new prediction modes or properties:

1. Add property-specific model files to `Gbfs/{property}/`
2. Model files: `{property}_model.pkl`, `{property}_scaler.pkl`, `{property}_features.pkl`
3. No code changes needed - automatically supported

## References

- **GBFS Workflow**: [GBFS documentation](https://github.com/Songyosk/GBFS4MPPML)
- **Matminer**: [Matminer documentation](https://matminer.readthedocs.io/)
- **PyMatGen**: [PyMatGen](https://pymatgen.org/)
- **FastAPI**: [FastAPI documentation](https://fastapi.tiangolo.com/)
- **Docker**: [Docker documentation](https://docs.docker.com/)