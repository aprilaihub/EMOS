# GBFS-2D Predictor

GBFS-2D: Specialized predictors for 2D layered materials, implemented in Python with integrated FastAPI service and van der Waals structure detection.

## Status

✅ **2D Materials Specialized** - Designed for graphene, h-BN, TMDCs, metal halides  
✅ **vdW Detection** - Automatic identification of van der Waals layered structures  
✅ **3-Property Support** - bandgap, is_metal, is_stable  
✅ **Optimized Features** - Selective featurizer instantiation (10-100× faster)  
✅ **Unified Architecture** - Single `Gbfs2dPredictor.py` with integrated FastAPI server  
✅ **HTTP API Ready** - Full REST endpoints with Pydantic validation and vdW detection  
✅ **Docker Ready** - Production container with health checks, non-root user, orchestration  
✅ **Comprehensive Testing** - 94 tests (47 unit + 47 integration, including 18 MoS2 tests)  
✅ **Property Mappings** - Registered in Information_Units with `gbfs2d` prefix  

## Architecture Overview

Gbfs-2D uses a unified architecture following the **MattergenGenerator** pattern:

```
Gbfs2dPredictor.py        ← Single source file containing:
├── Predictor class              • Core LightGBM predictor logic
├── Feature generation           • Matminer featurizers (optimized)
├── vdW detection               • Space group analysis via pymatgen
├── API models & endpoints       • FastAPI routes with vdW detection output
└── CLI/Server entry point       • --cif or --serve modes

docker/                    ← Production container configuration
├── Dockerfile               • Multi-stage image (7 KB)
├── docker-compose.yml       • Service orchestration with port 8001
├── requirements.txt         • Pinned dependencies
└── docker-test.sh/ps1       • Test runners (Linux/macOS, Windows)

bandgap_2d/                 ← Model directories (property_2d naming convention)
is_metal_2d/
is_stable_2d/
└── Contains:
    ├── property_2d_model.pkl    • Trained LightGBM model
    ├── property_2d_scaler.pkl   • Feature scaler
    └── property_2d_features.pkl • Feature list
```

**Key Design Principles:**
- Unified predictor + API in single file (improves code navigation & deployment)
- Selective featurizer instantiation (10-100× faster than loading all featurizers)
- vdW detection available in all predictions
- Docker-first deployment (tests run in container)
- Non-root security, health checks, resource limits

## Supported van der Waals Space Groups

The predictor identifies 2D layered materials via space group detection:

| Space Group | Number | Common Materials |
|-------------|--------|------------------|
| P6₃/mmc | 194 | Graphite, h-BN, MoS₂, WS₂ |
| R-3m | 166 | Rhombohedral TMDCs, trihalides |
| R-3 | 148 | Alternative TMDC stacking |
| C2/m | 12 | Monoclinic layered, TPCs, metal halides |
| P-3m1 | 156 | Specific magnetic vdW materials |
| P-31m | 162 | Chiral/distorted vdW systems |
| P1 | 1 | Low-symmetry heterostructures |
| P-1 | 2 | Low-symmetry heterostructures |

## Usage Modes

### Mode 1: Python Library (Programmatic)

```python
from Information_Units.Predictors.Gbfs_2d.Gbfs2dPredictor import Gbfs2dPredictor
from pymatgen.core import Structure

# Load predictor
predictor = Gbfs2dPredictor(predictor_name="bandgap", property_name="bandgap")

# Load structure
structure = Structure.from_file("MoS2.cif")

# Predict using standardized I/O contract
result = predictor.predict(input_data=[structure.to(fmt="cif")])
# Returns: {"source": "gbfs-2d", "results": [...]}

# Or use numpy method for quick predictions
predictions = predictor.predict_numpy([structure.to(fmt="cif")])
print(f"Bandgap: {predictions[0]} eV")
```

**I/O Contract:**

The `predict()` method follows EMOS standardized conventions:
- **Input**: `input_data` (parameter name) - `list[str]` of CIF strings
- **Output**: `dict` with keys:
  - `source`: "gbfs-2d" (predictor identifier)
  - `results`: `list[dict]` where each dict contains:
    - `index`: int (structure index in input)
    - `status`: "ok" or "error"
    - `properties`: dict with predictions and `is_vdw_layered` flag
    - `warnings`: list[str] (empty if no warnings)
    - `error`: str or None (error message if status is "error")

### Mode 2: CLI Prediction (Legacy)

```bash
python -m Information_Units.Predictors.Gbfs_2d.Gbfs2dPredictor \
  --cif /path/to/structure.cif \
  --property bandgap
```

### Mode 3: FastAPI Server

```bash
# Run server locally
python -m Information_Units.Predictors.Gbfs_2d.Gbfs2dPredictor --serve

# Once running, API docs available at: http://localhost:8000/docs
```

## Supported Properties

| Property | Type | Unit | Status |
|----------|------|------|--------|
| **bandgap** | Regression | eV | ✅ Production Ready |
| **is_metal** | Classification | boolean | ✅ Production Ready |
| **is_stable** | Classification | boolean | ✅ Production Ready |

## API Endpoints

### Health Check
```
GET /health
```
Returns service status for Docker health checks and monitoring.

### Model Information
```
GET /info
```
Returns model metadata, supported properties, and vdW detection capabilities.

### Single Property Prediction
```
POST /predict/{property_name}
Content-Type: application/json

{
  "structure": {
    "lattice": {...},
    "sites": [...]
  }
}
```

**Response includes automatic vdW detection:**
```json
{
  "job_id": "a1b2c3d4e5f6",
  "property": "bandgap",
  "prediction": 2.15,
  "probabilities": null,
  "is_vdw_layered": true,
  "unit": "eV",
  "type": "regression"
}
```

### Batch Prediction (Multiple Properties)
```
POST /batch-predict
Content-Type: application/json

{
  "structure": {
    "lattice": {...},
    "sites": [...]
  },
  "properties": ["bandgap", "is_metal", "is_stable"]
}
```

**Features:**
- Single API call for multiple properties
- vdW detection included in response
- All predictions returned in a single `predictions` object keyed by property name
- JSON serializable output

## van der Waals Detection

The predictor automatically detects whether a structure has van der Waals layered characteristics:

```python
from Information_Units.Predictors.Gbfs_2d.Gbfs2dPredictor import check_vdw_layered_structure

is_vdw = check_vdw_layered_structure(structure, tolerance=0.1)
# Returns True if structure matches known 2D material space groups
```

## Model File Organization

Each property directory contains three required files with the `_2d` suffix:

```
bandgap_2d/
├── bandgap_2d_model.pkl      # Trained LightGBM model
├── bandgap_2d_scaler.pkl     # StandardScaler or similar
└── bandgap_2d_features.pkl   # List of feature names (order matters!)

is_metal_2d/
├── is_metal_2d_model.pkl
├── is_metal_2d_scaler.pkl
└── is_metal_2d_features.pkl

is_stable_2d/
├── is_stable_2d_model.pkl
├── is_stable_2d_scaler.pkl
└── is_stable_2d_features.pkl
```

**Important:** Feature order is strictly preserved. The scaler and model expect features in the exact order specified in the features file.

## Docker Deployment

### Quick Start with Docker Compose

```bash
cd Information_Units/Predictors/Gbfs2d/docker
docker-compose build
docker-compose up -d

# Server now running on http://localhost:8001
# API documentation at http://localhost:8001/docs
```

### Build the Image

```bash
# From Gbfs2d directory
docker build -f docker/Dockerfile -t gbfs2d-pred:latest ../../../

# Or from EMOS root
docker build -f Information_Units/Predictors/Gbfs2d/docker/Dockerfile -t gbfs2d-pred:latest .
```

### Run the Server

```bash
# Default: port 8001 on localhost
docker run -p 8001:8000 gbfs2d-pred:latest

# Or with docker-compose for full orchestration
cd docker
docker-compose up
```

### Running Tests in Docker

Tests can be executed inside the containerized environment:

**Linux/macOS:**
```bash
cd docker
./docker-test.sh all           # Full test suite (94 tests)
./docker-test.sh unit          # Unit tests only (47)
./docker-test.sh integration   # Integration tests only (47)
```

**Windows PowerShell:**
```powershell
cd docker
.\docker-test.ps1              # Full test suite
.\docker-test.ps1 -TestType "unit"
.\docker-test.ps1 -TestType "integration"
```

**Direct docker run:**
```bash
# All tests
docker run --rm gbfs2d-pred:latest python -m pytest tests/ -v

# Unit tests
docker run --rm gbfs2d-pred:latest python -m pytest tests/unit/ -v

# Integration tests (includes MoS2 polytype validation)
docker run --rm gbfs2d-pred:latest python -m pytest tests/integration/ -v
```

### Container Features

- **Image**: Python 3.10 slim with system dependencies
- **Port**: 8000 (internal) → 8001 (host, via compose)
- **User**: Non-root `gbfs2d_user` for security
- **Health Check**: HTTP /health endpoint (30s interval)
- **Resources**: 2 CPU cores (limit), 1 CPU (reserved); 4 GB (limit), 2 GB (reserved)
- **Restart**: unless-stopped

### Docker Documentation

For complete Docker deployment information, see:
- **[DOCKER.md](docker/DOCKER.md)** - Comprehensive deployment guide (300+ lines)
  - Build variants and contexts
  - API endpoint examples
  - Python client code
  - Performance characteristics
  - Troubleshooting
  - Production deployment (nginx, Swarm, Kubernetes)

- **[docker/README.md](docker/README.md)** - Quick reference
  - File index and purposes
  - Testing checklist
  - API examples
  - Performance metrics

## Feature Generation Pipeline

The predictor automatically generates features from crystal structures:

1. **Composition Features** - ElementFraction, Stoichiometry, BandCenter, ValenceOrbital, etc.
2. **Structure Features** - DensityFeatures, StructuralComplexity, GlobalSymmetryFeatures
3. **Element Properties** - magpie, matminer, deml, megnet_el presets
4. **Engineered Features** - Derived features (e.g., `feature_a/feature_b` for ratios)

Features are generated only as needed, keeping computation efficient.

## Logging

Configure logging level with the `--log-level` argument:

```bash
python -m Information_Units.Predictors.Gbfs_2d.Gbfs2dPredictor \
  --serve \
  --log-level DEBUG
```

## Error Handling

The predictor handles common errors gracefully:
- **Invalid CIF files** - Returns error status with message
- **Missing features** - Falls back to zero strategy (configurable)
- **Symmetry analysis failures** - Continues prediction with warning
- **Scaler/model loading failures** - Clear error messages with file paths

## Performance Notes

- vdW detection via space group analysis: ~10-50 ms per structure
- Feature generation: ~100-500 ms depending on featurizers needed
- Model inference: <10 ms
- API response time: ~200-700 ms total including serialization

## Property Mappings

Gbfs-2D properties are registered in the central property mapping system:

**File**: `Information_Units/property_mappings.json`

| Property | Mapping Name | Description | Category |
|----------|---|---|---|
| **bandgap** | `band_gap_gbfs2d` | 2D material band gap (eV) | electronic |
| **is_metal** | `is_metal_gbfs2d` | 2D material metal classification | electronic |
| **is_stable** | `is_stable_gbfs2d` | 2D material structural stability | structural |

**Mapping Features:**
- ✅ `supports_2d_detection: true` - Identifies as specialized 2D predictor
- ✅ `predictable: true` - Discoverable by data generation systems
- ✅ `range_support` - Regression (bandgap); range queries not supported for classifications
- ✅ Proper categorization for filtering and UI

This enables Gbfs-2D properties to be discovered and accessed through the standard Information_Units property system.

## References

### Docker & Deployment Documentation
- **[docker/DOCKER.md](docker/DOCKER.md)** - Comprehensive 300+ line deployment guide
  - Build from multiple contexts
  - All API endpoint examples with curl
  - Python client code examples
  - Performance benchmarks and characteristics
  - Full troubleshooting section
  - Production deployment patterns (nginx, Docker Swarm, Kubernetes)

- **[docker/README.md](docker/README.md)** - Docker quick reference
  - 3-step quick start
  - File structure and purposes
  - Test execution methods (all platforms)
  - Resource limits and configuration

### 2D Materials & Crystallography

Key space groups for 2D layered materials:
- **Graphite & h-BN**: P6₃/mmc (194) - Most common
- **TMDCs**: P6₃/mmc (194), R-3m (166), R-3 (148), P-6m2 (187)
- **Metal halides**: C2/m (12)
- **Magnetic vdW**: P-3m1 (156), P-31m (162)
- **Low-symmetry phases**: P1 (1), P-1 (2)

## Testing

### Test Suite Overview

**94 Total Tests** (All Passing ✅)

| Category | Count | Coverage |
|----------|-------|----------|
| Unit Tests | 47 | API correctness, initialization, CIF loading, regression/classification validation, vdW detection, error handling |
| Integration Tests | 47 | Real predictions on Al₂O₃, SiO₂, MoS₂ (2 polytypes - 18 tests), vdW detection, deterministic behavior |
| **Total** | **94** | **Complete end-to-end validation** |

### Running Tests Locally

```bash
# Unit tests only
pytest tests/unit/test_gbfs2d_pred_behaviour.py -v

# Integration tests only  
pytest tests/integration/test_gbfs2d_sanity.py -v

# Full test suite
pytest tests/unit/ tests/integration/ -v

# With coverage
pytest tests/ --cov=Information_Units.Predictors.Gbfs2d --cov-report=term-missing
```

### Running Tests in Docker

See [Docker Deployment](#docker-deployment) section for containerized test execution with multiple platforms.

**Quick command:**
```bash
docker run --rm gbfs2d-pred:latest python -m pytest tests/ -v
```

### Test Highlights

- ✅ **MoS₂ Polymorphs**: mp-2815 (space group 194) and mp-1025874 (space group 187)
- ✅ **vdW Detection**: Verified on all 2D materials (returns `is_vdw_layered: true`)
- ✅ **Deterministic Behavior**: Identical predictions on repeated input
- ✅ **API Contract**: JSON schema validation and standardized response format
- ✅ **Property Ranges**: Regression predictions within physical bounds
- ✅ **Classification Accuracy**: Binary outputs (0.0 or 1.0) for is_metal, is_stable
- ✅ **Cross-Material Validation**: Different materials produce different predictions
- ✅ **Serialization**: All predictions JSON-serializable without auxiliary files
