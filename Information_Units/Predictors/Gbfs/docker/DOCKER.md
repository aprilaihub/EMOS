# GBFS Docker Deployment Guide

## Overview

GBFS is containerized as a FastAPI service with fully integrated FastAPI server code. The service exposes material property predictions via HTTP REST API. All data flows as JSON dictionaries — no auxiliary files are generated during prediction.

## Architecture

The new integrated architecture mirrors the MattergenGenerator pattern:

- **Single Source File**: `GbfsPredictor.py` contains:
  - Core predictor logic with matminer featurizers
  - Pydantic models for API request/response validation
  - FastAPI endpoint implementations
  - CLI and server mode entry points

- **Service Setup**: FastAPI server automatically runs when `GbfsPredictor` is invoked with `--serve`

- **Communication**: All data transmitted as JSON (pymatgen structure dicts)

## Docker Folder Structure

```
docker/
├── Dockerfile          – Production FastAPI image
├── docker-compose.yml  – Service orchestration
├── .dockerignore       – Build context exclusions
└── requirements.txt    – Python dependencies
```

Parent folder contains:
- `GbfsPredictor.py` – Unified predictor + API server
- `README.md` – Usage documentation

## Building

### Standard Build

```bash
cd Information_Units/Predictors/Gbfs
docker build -f docker/Dockerfile -t gbfs-pred:latest ../../../
```

### Build from EMOS Root

```bash
docker build \
  -f Information_Units/Predictors/Gbfs/docker/Dockerfile \
  -t gbfs-pred:latest \
  .
```

## Running

### Docker Run (Single Command)

```bash
docker run -p 8000:8000 gbfs-pred:latest
```

### Docker Compose (Recommended)

```bash
cd Information_Units/Predictors/Gbfs/docker
docker-compose build
docker-compose up

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## API Usage

### Health Check

```bash
curl -X GET http://localhost:8000/health
```

### View Supported Properties

```bash
curl -X GET http://localhost:8000/info
```

### Single Property Prediction

```bash
curl -X POST http://localhost:8000/predict/bandgap \
  -H "Content-Type: application/json" \
  -d '{
    "structure": {
      "@module": "pymatgen.core.structure",
      "@class": "Structure",
      "lattice": {...},
      "sites": [...]
    }
  }'
```

### Batch Prediction

```bash
curl -X POST http://localhost:8000/batch-predict \
  -H "Content-Type: application/json" \
  -d '{
    "structure": {...},
    "properties": ["bandgap", "e_form", "is_metal"]
  }'
```

## Python Client Example

```python
import requests
import json
from pymatgen.core import Structure

# Load a structure
structure = Structure.from_file("Si.cif")

# Convert to JSON dict (required for API)
structure_dict = structure.as_dict()

# Make prediction request
response = requests.post(
    "http://localhost:8000/predict/bandgap",
    json={"structure": structure_dict}
)

result = response.json()
print(f"Bandgap: {result['prediction']} {result['unit']}")
```

## Performance

- **Model Load Time**: ~5s per property (cached after first request)
- **Prediction Time**: ~2-5s per structure (mostly featurization)
- **Memory Usage**: ~2-3 GB (base) + per-request overhead

## Environment Variables

```bash
GBFS_HOST=0.0.0.0           # Bind address
GBFS_PORT=8000              # Port number
GBFS_LOG_LEVEL=INFO         # Logging level (DEBUG, INFO, WARNING, ERROR)
PYTHONUNBUFFERED=1          # Unbuffered output (for docker logs)
```

## Health Monitoring

The container includes an HTTP health check that validates the /health endpoint:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

## Local Development

### Run Server Locally (No Docker)

```bash
# Install dependencies
pip install -r docker/requirements.txt

# Run server
python -m Information_Units.Predictors.Gbfs.GbfsPredictor --serve

# Or with custom settings
python -m Information_Units.Predictors.Gbfs.GbfsPredictor \
  --serve \
  --host 127.0.0.1 \
  --port 8000 \
  --log-level DEBUG
```

### Call from Python

```python
from pathlib import Path
from Information_Units.Predictors.Gbfs.GbfsClient import GbfsClient

result = GbfsClient().predict([Path("structure.cif").read_text()])
```

## Interactive API Documentation

Once the server is running, interactive API docs are available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Troubleshooting

### Container fails to start

- Check logs: `docker logs <container_id>`
- Verify model files exist in `Information_Units/Predictors/Gbfs/{property}/` directories
- Ensure EMOS root is included in the build context

### Cannot connect to localhost:8000

- Verify port 8000 is exposed: Check `docker ps` output
- Port already in use: `netstat -tuln | grep 8000` (Linux) or `netstat -ano | findstr :8000` (Windows)
- Try explicit IP: `http://127.0.0.1:8000` instead of `localhost`

### Prediction timeout

- Increase request timeout if structures have many atoms
- Check container resource constraints
- Monitor logs for errors: `docker logs --follow <container_id>`

### Import errors

- Rebuild without cache: `docker build --no-cache ...`
- Verify workspace structure includes Information_Units/ at build context root
