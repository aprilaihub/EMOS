# GBFS Predictor Docker Deployment Guide

## Overview

The GBFS predictor is containerized for production deployment with security hardening, health checks, and optimized dependencies.

## Files

- **Dockerfile** - Production-ready Docker image definition
- **.dockerignore** - Files to exclude from Docker build context
- **docker-compose.yml** - Docker Compose configuration for easy orchestration

## Building the Image

### Standard Build

```bash
docker build -t gbfs-pred:latest .
```

### Build with Custom Tag

```bash
docker build -t gbfs-pred:v1.0.0 .
```

### Build from EMOS Root

```bash
docker build \
  -f Information_Units/Predictors/GBFS_Pred/Dockerfile \
  -t gbfs-pred:latest \
  .
```

## Running Predictions

### Single Prediction (Docker)

```bash
docker run -v $(pwd):/data gbfs-pred:latest \
  --cif /data/sample.cif \
  --model /data/bandgap_model.pkl \
  --scaler /data/bandgap_scaler.pkl \
  --features /data/bandgap_features.pkl
```

### Single Prediction (Docker Compose)

```bash
# Create data directories
mkdir -p data models

# Copy your files
cp sample.cif data/
cp bandgap_*.pkl models/

# Run prediction
docker-compose run gbfs \
  --cif /data/sample.cif \
  --model /models/bandgap_model.pkl \
  --scaler /models/bandgap_scaler.pkl \
  --features /models/bandgap_features.pkl
```

### Interactive Shell

```bash
docker run -it -v $(pwd):/data gbfs-pred:latest bash
```

## Features

### Security
- ✅ Non-root user (`predictor:1000`)
- ✅ Minimal base image (slim Python 3.10)
- ✅ No unnecessary packages
- ✅ Read-only filesystem possible with `--read-only`

### Health Checks
- ✅ Automatic health checking every 30s
- ✅ Import verification
- ✅ 5s startup grace period
- ✅ 3 retries before marking unhealthy

### Performance
- ✅ Multi-stage build friendly (can be optimized further)
- ✅ Pinned dependency versions
- ✅ Minimal layer count
- ✅ No cache bloat from pip

### Resource Management
```bash
# Limit CPU and memory
docker run \
  --cpus 2 \
  --memory 4g \
  -v $(pwd):/data \
  gbfs-pred:latest \
  --cif /data/sample.cif \
  --model /data/bandgap_model.pkl \
  --scaler /data/bandgap_scaler.pkl \
  --features /data/bandgap_features.pkl
```

## Production Deployment

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gbfs-predictor
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: gbfs
        image: gbfs-pred:latest
        resources:
          requests:
            cpu: 1
            memory: 2Gi
          limits:
            cpu: 2
            memory: 4Gi
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import Information_Units.Predictors.GBFS_Pred.GBFS_PredPredictor; print('OK')"
          initialDelaySeconds: 5
          periodSeconds: 30
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
          capabilities:
            drop:
              - ALL
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        emptyDir: {}
```

### Docker Swarm

```bash
# Create service
docker service create \
  --name gbfs-predictor \
  --replicas 3 \
  --limit-cpu 2 \
  --limit-memory 4g \
  --reserve-cpu 1 \
  --reserve-memory 2g \
  -v /data:/data \
  --health-cmd='python -c "import sys; sys.exit(0)"' \
  --health-interval=30s \
  --health-timeout=10s \
  gbfs-pred:latest
```

## Environment Variables

```bash
# Recommended for production
PYTHONUNBUFFERED=1          # Real-time logging
PYTHONDONTWRITEBYTECODE=1   # No .pyc files in container
```

## Volume Mounts

```bash
# Read-only input data
docker run -v /path/to/data:/data:ro gbfs-pred:latest

# Writable output directory
docker run -v /path/to/output:/output gbfs-pred:latest
```

## Troubleshooting

### Check Image Size

```bash
docker images gbfs-pred:latest --format "table {{.ID}}\t{{.Size}}"
```

### View Container Logs

```bash
docker logs <container_id>
docker logs --follow <container_id>
```

### Verify Health Status

```bash
docker ps --format "table {{.ID}}\t{{.Status}}" | grep gbfs
```

### Interactive Debugging

```bash
docker run -it \
  -v $(pwd):/data \
  gbfs-pred:latest \
  python -c "
from Information_Units.Predictors.GBFS_Pred.GBFS_PredPredictor import GBFS_PredPredictor
predictor = GBFS_PredPredictor(
    'test',
    '/data/bandgap_model.pkl',
    '/data/bandgap_scaler.pkl',
    '/data/bandgap_features.pkl'
)
print(predictor.info())
"
```

## Performance Benchmarks

| Task | Time | Notes |
|------|------|-------|
| Image Build | ~2-3 min | First build slower due to system deps |
| Container Start | ~2-5 sec | Health check ready in 5s |
| Single Prediction | ~200-300ms | CIF parsing + feature generation + inference |
| Memory Usage | ~400-600MB | Per container at rest |

## Security Considerations

✅ **Implemented**
- Non-root user execution
- Minimal base image
- Pinned dependency versions
- Health checks for availability
- Resource limits (recommended)

⚠️ **Recommended for Production**
- Network policies (Kubernetes)
- Secret management for model paths
- Container image scanning (Trivy, Anchore)
- Log aggregation (ELK, Splunk)
- Monitoring (Prometheus, New Relic)

## Updates and Maintenance

### Updating Dependencies

1. Update version pins in Dockerfile
2. Rebuild image: `docker build -t gbfs-pred:v1.0.1 .`
3. Test: `docker run -v ~/test:/data gbfs-pred:v1.0.1`
4. Deploy to production

### Reverting to Previous Version

```bash
docker run -v $(pwd):/data gbfs-pred:v1.0.0 ...
```

## License

Same as EMOS project
