# GBFS-2D Docker Deployment Guide

## Overview

GBFS-2D is containerized as a FastAPI service with fully integrated FastAPI server code. The service specializes in predictions for **2D layered materials** (graphite, h-BN, TMDCs, metal halides) with automatic van der Waals structure detection. All predictions are transmitted via JSON REST API with no auxiliary files generated.

## Architecture

The integrated architecture mirrors the MattergenGenerator pattern:

- **Single Source File**: `Gbfs2dPredictor.py` contains:
  - Core predictor logic with matminer featurizers for 2D materials
  - van der Waals structure detection via space group analysis
  - Pydantic models for API request/response validation
  - FastAPI endpoint implementations
  - CLI and server mode entry points

- **Service Setup**: FastAPI server automatically runs when `Gbfs2dPredictor` is invoked with `--serve`

- **Communication**: All data transmitted as JSON (pymatgen structure dicts)

- **vdW Detection**: Automatic detection included in all predictions for 2D material identification

## Docker Folder Structure

```
docker/
├── Dockerfile          – Production FastAPI image
├── docker-compose.yml  – Service orchestration
├── .dockerignore       – Build context exclusions
└── requirements.txt    – Python dependencies
```

Parent folder contains:
- `Gbfs2dPredictor.py` – Unified predictor + API server with vdW detection
- `README.md` – Usage documentation
- `bandgap_2d/`, `is_metal_2d/`, `is_stable_2d/` – Model directories

## Building

### Standard Build

```bash
cd Information_Units/Predictors/Gbfs2d
docker build -f docker/Dockerfile -t gbfs2d-pred:latest ../../../
```

### Build from EMOS Root

```bash
docker build \
  -f Information_Units/Predictors/Gbfs2d/docker/Dockerfile \
  -t gbfs2d-pred:latest \
  .
```

## Running

### Docker Run (Single Command)

```bash
# Default: runs on port 8000 inside container, mapped to 8001 externally
docker run -p 8001:8000 gbfs2d-pred:latest
```

### Docker Run with Custom Port

```bash
# Map to different host port (e.g., 9001)
docker run -p 9001:8000 gbfs2d-pred:latest
```

### Docker Compose (Recommended)

```bash
cd Information_Units/Predictors/Gbfs2d/docker
docker-compose build
docker-compose up

# View logs
docker-compose logs -f

# Run in background
docker-compose up -d

# Stop
docker-compose down
```

## API Usage

### Health Check

```bash
curl -X GET http://localhost:8001/health
```

Example response:
```json
{"status": "ok", "version": "1.0", "timestamp": "2024-04-07T10:00:00"}
```

### View Supported Properties and vdW Detection

```bash
curl -X GET http://localhost:8001/info
```

Example response:
```json
{
  "name": "GBFS-2D",
  "description": "Property predictor for 2D layered materials using LightGBM models.",
  "version": "1.0.0",
  "supported_properties": ["bandgap", "is_metal", "is_stable"],
  "properties": {
    "bandgap": {"label": "Band Gap", "unit": "eV", "type": "regression", "description": "Electronic band gap energy for 2D materials"},
    "is_metal": {"label": "Metal Classification", "unit": "boolean", "type": "classification", "description": "Whether the 2D material is metallic (1) or non-metallic (0)"},
    "is_stable": {"label": "Structural Stability", "unit": "boolean", "type": "classification", "description": "Whether the 2D material structure is dynamically stable (1) or unstable (0)"}
  }
}
```

### Single Property Prediction (bandgap)

```bash
curl -X POST http://localhost:8001/predict/bandgap \
  -H "Content-Type: application/json" \
  -d '{
    "structure": {
      "@module": "pymatgen.core.structure",
      "@class": "Structure",
      "lattice": {"matrix": [[3.16, 0, 0], [-1.58, 2.736, 0], [0, 0, 12.3]], "pbc": [true, true, true]},
      "sites": []
    }
  }'
```

Example response with vdW detection:
```json
{
  "job_id": "a1b2c3d4e5f6",
  "property": "bandgap",
  "prediction": 1.85,
  "probabilities": null,
  "is_vdw_layered": true,
  "unit": "eV",
  "type": "regression"
}
```

### Metal Classification

```bash
curl -X POST http://localhost:8001/predict/is_metal \
  -H "Content-Type: application/json" \
  -d '{
    "structure": {
      "@module": "pymatgen.core.structure",
      "@class": "Structure",
      "lattice": {"matrix": [[3.16, 0, 0], [-1.58, 2.736, 0], [0, 0, 12.3]], "pbc": [true, true, true]},
      "sites": []
    }
  }'
```

Example response (MoS2 is non-metallic):
```json
{
  "job_id": "a1b2c3d4e5f6",
  "property": "is_metal",
  "prediction": 0,
  "probabilities": [[0.92, 0.08]],
  "is_vdw_layered": true,
  "unit": "boolean",
  "type": "classification"
}
```

### Batch Prediction (All Properties)

```bash
curl -X POST http://localhost:8001/batch-predict \
  -H "Content-Type: application/json" \
  -d '{
    "structure": {
      "@module": "pymatgen.core.structure",
      "@class": "Structure",
      "lattice": {"matrix": [[3.16, 0, 0], [-1.58, 2.736, 0], [0, 0, 12.3]], "pbc": [true, true, true]},
      "sites": []
    },
    "properties": ["bandgap", "is_metal", "is_stable"]
  }'
```

Example response:
```json
{
  "job_id": "a1b2c3d4e5f6",
  "structure_formula": "MoS2",
  "is_vdw_layered": true,
  "predictions": {
    "bandgap": {"prediction": 1.85, "probabilities": null, "unit": "eV", "type": "regression"},
    "is_metal": {"prediction": 0, "probabilities": [[0.92, 0.08]], "unit": "boolean", "type": "classification"},
    "is_stable": {"prediction": 1, "probabilities": [[0.11, 0.89]], "unit": "boolean", "type": "classification"}
  }
}
```

## Python Client Examples

### Basic Prediction with vdW Detection

```python
import requests
from pymatgen.io.cif import CifParser

# Load a 2D structure (e.g., MoS2)
parser = CifParser("mp-2815.cif")  # MoS2
structures = parser.get_structures(primitive=True)
structure = structures[0]

# Make prediction
response = requests.post(
    "http://localhost:8001/predict/bandgap",
    json={"structure": structure.as_dict()}
)

result = response.json()
bandgap = result['prediction']
is_vdw = result['is_vdw_layered']

print(f"MoS2 Bandgap: {bandgap} eV")
print(f"Is 2D vdW layered: {is_vdw}")
```

### Batch Prediction on Multiple Materials

```python
import requests

materials = {
    "MoS2": "mp-2815.cif",
    "graphite": "mp-48.cif",
    "h-BN": "mp-12123.cif"
}

for name, cif_file in materials.items():
    parser = CifParser(cif_file)
    structure = parser.get_structures(primitive=True)[0]
    
    response = requests.post(
        "http://localhost:8001/batch-predict",
        json={
            "structure": structure.as_dict(),
            "properties": ["bandgap", "is_metal", "is_stable"]
        }
    )
    
    result = response.json()['predictions']
    print(f"{name}:")
    print(f"  Bandgap: {result['bandgap']['prediction']} eV")
    print(f"  Metal: {result['is_metal']['prediction']}")
    print(f"  Stable: {result['is_stable']['prediction']}")
    print(f"  vdW Layered: {response.json()['is_vdw_layered']}")
    print()
```

## Running Tests in Docker

### Unit Tests

```bash
# Build the image
docker build -f docker/Dockerfile -t gbfs2d-pred:latest ../../../

# Run unit tests inside container
docker run --rm gbfs2d-pred:latest \
  python -m pytest tests/unit/test_gbfs2d_pred_behaviour.py -v
```

### Integration Tests

```bash
# Run integration tests inside container
docker run --rm gbfs2d-pred:latest \
  python -m pytest tests/integration/test_gbfs2d_sanity.py -v --tb=short
```

### All Tests

```bash
# Run full test suite
docker run --rm gbfs2d-pred:latest \
  python -m pytest tests/unit/test_gbfs2d_pred_behaviour.py \
                    tests/integration/test_gbfs2d_sanity.py -v
```

### With Docker Compose

```bash
cd docker

# Build and run tests
docker-compose build
docker-compose run --rm gbfs2d python -m pytest tests/unit/test_gbfs2d_pred_behaviour.py -v

# Run integration tests
docker-compose run --rm gbfs2d python -m pytest tests/integration/test_gbfs2d_sanity.py -v

# Run full suite
docker-compose run --rm gbfs2d python -m pytest tests/ -v
```

## Performance Characteristics

- **Cold Start**: ~15s (model loading on first prediction)
- **Warm Start**: ~100ms per prediction
- **Featurization Time**: ~2-5s per structure (depends on size)
- **Total Prediction Latency**: ~2-5s per structure (includes featurization)
- **Memory Usage**: ~2-3 GB base + per-request overhead
- **vdW Detection**: ~100ms per structure (negligible vs featurization)

## Environment Variables

```bash
GBFS2D_HOST=0.0.0.0           # Bind address (default: 0.0.0.0)
GBFS2D_PORT=8000              # Port number (default: 8000)
GBFS2D_LOG_LEVEL=INFO         # Logging level (DEBUG, INFO, WARNING, ERROR)
PYTHONUNBUFFERED=1            # Unbuffered output (for docker logs)
PYTHONDONTWRITEBYTECODE=1     # Don't write .pyc files
```

## Health Monitoring

The container includes an HTTP health check:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

Check container health:
```bash
docker ps  # Check HEALTH column
docker inspect <container-id> | grep -A 10 '"Health"'
```

## Logging

### View Logs

```bash
# Follow logs
docker logs -f <container-id>

# Last 100 lines
docker logs --tail 100 <container-id>

# With docker-compose
docker-compose logs -f gbfs2d
```

### Log Levels

```bash
# Run with DEBUG logging
docker run -e GBFS2D_LOG_LEVEL=DEBUG -p 8001:8000 gbfs2d-pred:latest
```

## Local Development (No Docker)

### Install Dependencies

```bash
pip install -r docker/requirements.txt
```

### Run Server Locally

```bash
# Default (localhost:8000)
python -m Information_Units.Predictors.Gbfs2d.Gbfs2dPredictor --serve

# Custom host/port
python -m Information_Units.Predictors.Gbfs2d.Gbfs2dPredictor \
  --serve \
  --host 127.0.0.1 \
  --port 8000 \
  --log-level DEBUG
```

### CLI Prediction (Local)

```bash
# Single prediction
python -m Information_Units.Predictors.Gbfs2d.Gbfs2dPredictor \
  --cif /path/to/mos2.cif \
  --property bandgap

# Get vdW detection
python -m Information_Units.Predictors.Gbfs2d.Gbfs2dPredictor \
  --cif mp-2815.cif \
  --property is_metal
# Output includes: is_vdw_layered: True
```

## Interactive API Documentation

Once the server is running, interactive API docs are available at:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs <container-id>

# Verify image built successfully
docker build -f docker/Dockerfile -t gbfs2d-pred:latest ../../../

# Check for missing models
docker run --rm gbfs2d-pred:latest ls -la Information_Units/Predictors/Gbfs2d/
```

### Out of Memory

```bash
# Increase limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 8G  # Increase from 4G
```

### Port Already in Use

```bash
# Use different port
docker run -p 9001:8000 gbfs2d-pred:latest

# Or update docker-compose.yml ports
ports:
  - "9001:8000"
```

### Slow Predictions

- **First prediction slow**: Models are loaded on-demand (~10s)
- **Subsequent predictions slow**: featurization overhead (2-5s typical)
- **Check logs**: `docker logs <container-id> | grep -i time`

## Production Deployment

### Behind a Reverse Proxy (nginx)

```nginx
server {
  listen 443 ssl http2;
  server_name api.example.com;
  
  location /gbfs2d {
    proxy_pass http://gbfs2d:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

### Docker Swarm Deployment

```bash
docker service create \
  --name gbfs2d-api \
  --publish 8001:8000 \
  --replicas 3 \
  -e GBFS2D_LOG_LEVEL=INFO \
  gbfs2d-pred:latest
```

### Kubernetes Deployment

See repo examples: `k8s/gbfs2d-deployment.yaml`

## Additional Resources

- **Gbfs2d README**: `../README.md`
- **Model Documentation**: `../README.md` (Model File Organization section)
- **Code Reference**: `../Gbfs2dPredictor.py`
- **Test Suite**: `../../../tests/`
