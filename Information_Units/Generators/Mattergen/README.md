# MatterGen Generator

MatterGen (Microsoft's diffusion-based generative model for inorganic crystal structures)
runs in its own Docker container and is accessed by the EMOS backend over HTTP.

## Architecture

```
┌─────────────────────┐         HTTP (port 8100)        ┌──────────────────────────┐
│  EMOS Backend       │  ──────────────────────────────► │  MatterGen Container     │
│  (Flask :5001)      │                                  │  (FastAPI :8000 → :8100) │
│                     │  ◄────────────────────────────── │                          │
│  MattergenGenerator │         JSON responses           │  mattergen_api.py        │
│  .py (HTTP client)  │                                  │  + mattergen library     │
└─────────────────────┘                                  └──────────────────────────┘
```

## Quick Start

```bash
# 1. Build and start the MatterGen container (CPU)
docker compose up mattergen -d --build

# 1b. With GPU support
docker compose --profile gpu up mattergen-gpu -d --build

# 2. Verify it's running
curl http://localhost:8100/health
# → {"status":"ok","service":"mattergen"}

# 3. Start EMOS backend (separate terminal)
python backend/app.py


# 4. Check container logs
docker logs -f emos-mattergen
```

## Container Endpoints

| Method | Path               | Description                            |
|--------|--------------------|----------------------------------------|
| GET    | `/health`          | Liveness check                         |
| GET    | `/info`            | Model metadata & available checkpoints |
| POST   | `/generate`        | Generate crystal structures            |
| GET    | `/results/{job_id}`| Retrieve results of a past job         |

## Generate Request Example

```bash
curl -X POST http://localhost:8100/generate \
  -H "Content-Type: application/json" \
  -d '{
    "pretrained_name": "mattergen_base",
    "batch_size": 4,
    "num_batches": 1
  }'
```

## Configuration

| Environment Variable     | Default                    | Description                     |
|--------------------------|----------------------------|---------------------------------|
| `MATTERGEN_API_URL`     | `http://localhost:8100`    | Container URL (set on host)     |
| `MATTERGEN_TIMEOUT`     | `600`                      | HTTP timeout in seconds         |
| `MATTERGEN_PORT`        | `8100`                     | Host port mapped to container   |
| `MATTERGEN_DEVICE`      | `auto`                     | Force `cpu` or `cuda`           |
| `MATTERGEN_OUTPUT_DIR`  | `/app/outputs`             | Output dir inside container     |

## Key Methods (MattergenGenerator.py)

- `info()` — Returns model description from the container (or fallback)
- `generate(inputs)` — Sends generation request; returns structures as dicts
- `is_healthy()` — Quick health check
- `get_available_models()` — Lists pretrained model names
- `get_results(job_id)` — Polls results for a previously submitted job

## API Documentation

For the base interface, see [BaseGenerator.py](../BaseGenerator.py)
