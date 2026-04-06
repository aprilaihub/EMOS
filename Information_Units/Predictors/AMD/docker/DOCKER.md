# AMD Docker Deployment Guide

## Overview

AMD (Average Minimum Distance) Predictor is containerized as a FastAPI service with fully integrated HTTP API. The service exposes crystal structure similarity predictions via REST API. All data flows as JSON dictionaries — no auxiliary files are generated during prediction.

## Architecture

The AMD architecture follows the integration pattern:

- **Single Source File**: `AMDPredictor.py` contains:
  - Core predictor logic with average-minimum-distance package
  - Pydantic models for API request/response validation
  - FastAPI endpoint implementations
  - CLI and server mode entry points

- **Service Setup**: FastAPI server automatically runs when `AMDPredictor` is invoked with `--serve`

- **Communication**: All data transmitted as JSON (CIF file paths or raw CIF content)

## Docker Folder Structure

```
docker/
├── Dockerfile          – Production FastAPI image
├── docker-compose.yml  – Service orchestration
├── .dockerignore       – Build context exclusions
└── requirements.txt    – Python dependencies
```

Parent folder contains:
- `AMDPredictor.py` – Unified predictor + API server
- `README.md` – Usage documentation

## Building

### Standard Build

```bash
cd Information_Units/Predictors/AMD
docker build -f docker/Dockerfile -t amd-predictor:latest ../../../
```

### Build from EMOS Root

```bash
docker build \
  -f Information_Units/Predictors/AMD/docker/Dockerfile \
  -t amd-predictor:latest \
  .
```

### Build with Custom Tag

```bash
docker build \
  -f Information_Units/Predictors/AMD/docker/Dockerfile \
  -t amd-predictor:v1.0 \
  .
```

## Running

### Docker Run (Single Command)

```bash
docker run -p 8001:8001 amd-predictor:latest
```

### Docker Run with Volume Mounts

```bash
# Mount CIF input and output directories
docker run -p 8001:8001 \
  -v /path/to/cif_files:/app/cif_inputs:ro \
  -v /path/to/outputs:/app/cif_outputs \
  amd-predictor:latest
```

### Docker Compose (Recommended)

```bash
cd Information_Units/Predictors/AMD/docker
docker-compose build
docker-compose up

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild and restart
docker-compose up --build
```

## API Usage

### Health Check

```bash
curl -X GET http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "AMD Predictor API"
}
```

### View API Documentation

Interactive Swagger UI:
```
http://localhost:8001/docs
```

ReDoc documentation:
```
http://localhost:8001/redoc
```

### Compare Crystal Structures (File Paths)

```bash
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{
    "cif_paths": [
      "/app/cif_inputs/structure1.cif",
      "/app/cif_inputs/structure2.cif"
    ],
    "k": 100,
    "metric": "chebyshev"
  }'
```

### Compare Crystal Structures (Alternative Format)

```bash
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{
    "cif_path1": "/app/cif_inputs/Al2O3.cif",
    "cif_path2": "/app/cif_inputs/SiO2.cif",
    "k": 100
  }'
```

## Python Client Example

```python
import requests
import json

# Prepare comparison request
payload = {
    "cif_paths": [
        "structure1.cif",
        "structure2.cif"
    ],
    "k": 100,
    "metric": "chebyshev"
}

# Make prediction request
response = requests.post(
    "http://localhost:8001/predict",
    json=payload
)

if response.status_code == 200:
    result = response.json()
    
    # Extract comparison results
    for comparison in result["pairwise_distances"]:
        print(f"PDD/EMD Distance: {comparison['pdd_emd_distance']:.4f}")
        print(f"AMD Distance: {comparison['amd_distance']:.4f}")
        print(f"Identical: {comparison['identical']}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

## API Response Format

### Successful Comparison

```json
{
  "pairwise_distances": [
    {
      "crystal_1_index": 0,
      "crystal_2_index": 1,
      "crystal_1_file": "structure1.cif",
      "crystal_2_file": "structure2.cif",
      "pdd_emd_distance": 0.1234,
      "amd_distance": 0.0987,
      "identical": false,
      "very_similar": true,
      "similar": true
    }
  ],
  "crystal_info": [
    {
      "name": "Al2O3",
      "n_atoms": 10,
      "n_asym": 2,
      "composition": "Al4O6"
    },
    {
      "name": "SiO2",
      "n_atoms": 12,
      "n_asym": 2,
      "composition": "Si4O8"
    }
  ],
  "parameters": {
    "k": 100,
    "metric": "chebyshev",
    "n_crystals": 2,
    "n_files": 2
  },
  "n_comparisons": 1
}
```

### Error Response

```json
{
  "error": "CIF file not found: structure3.cif",
  "status": "failed"
}
```

## Performance

- **Startup Time**: ~10-15s (dependencies load on first request)
- **Prediction Time**: ~5-30s per comparison (depends on k and crystal complexity)
- **Memory Usage**: ~1-2 GB (base) + per-request overhead
- **Throughput**: Sequential processing (one comparison at a time)

## Environment Variables

```bash
AMD_HOST=0.0.0.0           # Bind address (default: 0.0.0.0)
AMD_PORT=8001              # Port number (default: 8001)
AMD_LOG_LEVEL=INFO         # Logging level (DEBUG, INFO, WARNING, ERROR)
PYTHONUNBUFFERED=1         # Unbuffered output (for docker logs)
PYTHONDONTWRITEBYTECODE=1  # Don't write Python cache files
```

Set at runtime:
```bash
docker run \
  -e AMD_PORT=9000 \
  -e AMD_LOG_LEVEL=DEBUG \
  -p 9000:9000 \
  amd-predictor:latest
```

## Volume Management

For production deployments, mount CIF files as read-only volumes:

```bash
docker run -p 8001:8001 \
  -v /data/cif_structures:/app/cif_inputs:ro \
  amd-predictor:latest
```

In compose:
```yaml
volumes:
  - /data/cif_structures:/app/cif_inputs:ro
```

## Networking

### Single Host

The container listens on `0.0.0.0:8001` inside the container, mapped to `localhost:8001`.

### Multi-Container Setup

Add to a docker-compose network:

```yaml
services:
  amd:
    networks:
      - emos-network
  
  other_service:
    networks:
      - emos-network

networks:
  emos-network:
    driver: bridge
```

Access from other containers: `http://amd:8001`

## Monitoring and Logging

### View Real-Time Logs

```bash
docker-compose logs -f amd
```

### View Last N Lines

```bash
docker-compose logs --tail=100 amd
```

### Structured Logs

Logs are written to JSON files:
```
/var/lib/docker/containers/<container_id>/<container_id>-json.log
```

## Troubleshooting

### Container Fails to Start

```bash
docker-compose logs amd
```

Check for:
- Missing dependencies (ensure requirements.txt is installed)
- Port already in use: `sudo lsof -i :8001`
- Insufficient memory: check `docker stats`

### Slow Predictions

- CPU-bound task (expected for k=100+)
- Try reducing k parameter: `"k": 50`
- Add CPU reservations in compose file
- Increase memory limits

### CIF File Not Found

Ensure paths are absolute or relative to `/app` in container:
```
/app/cif_inputs/structure.cif  ✓
./cif_inputs/structure.cif     ✗ (relative paths may fail)
```

### Out of Memory

Increase Docker memory limits:
```bash
docker run --memory=8g -p 8001:8001 amd-predictor:latest
```

Or in compose:
```yaml
deploy:
  resources:
    limits:
      memory: 8G
```

## Production Best Practices

1. **Use docker-compose** for consistent deployment
2. **Set resource limits** to prevent runaway processes
3. **Configure health checks** (already enabled)
4. **Use read-only volumes** for input data
5. **Enable restart policies** (already set to `unless-stopped`)
6. **Monitor logs** with centralized logging (ELK, Loki, etc.)
7. **Use separate networks** for microservices
8. **Pin image tags** (don't use `:latest` in production)

## Advanced: Custom Build Arguments

Create a `docker-compose.override.yml` for custom configurations:

```yaml
services:
  amd:
    build:
      args:
        - PYTHON_VERSION=3.11
```

## Integration with EMOS Platform

The AMD predictor integrates seamlessly:

```python
from Information_Units.Predictors.PredictorFactory import predictor_factory

# Create local instance
predictor = predictor_factory.create("amd")

# Or connect to Docker service
import requests
result = requests.post("http://localhost:8001/predict", json=payload)
```

## Additional Resources

- [average-minimum-distance Documentation](https://average-minimum-distance.readthedocs.io)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Docker Documentation](https://docs.docker.com)
- [Docker Compose Documentation](https://docs.docker.com/compose)
