# FastAPI Server for GBFS-2D Predictor (2D Layered Materials)
#
# Build: docker build -t gbfs2d-pred:latest -f docker/Dockerfile ..
# Run:   docker run -p 8001:8000 gbfs2d-pred:latest
#
# The FastAPI server exposes predictions via HTTP:
#   POST /predict/bandgap    – predict band gap (eV)
#   POST /predict/is_metal   – predict metallic character
#   POST /predict/is_stable  – predict structural stability
#   GET  /info               – view supported properties
#   GET  /health             – health check
#
# van der Waals Structure Detection:
#   Automatically identifies 2D layered materials via space group analysis
#   Supported space groups: P6/mmc (194), P-6m2 (187), R-3m (166), etc.

FROM python:3.10-slim

WORKDIR /app

# System dependencies (required for pymatgen and numerical computing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 gbfs2d_user

# Copy application code and model files
# Note: Models must be in Information_Units/Predictors/Gbfs2d/{property}_2d/ directories
COPY --chown=gbfs2d_user:gbfs2d_user Information_Units/ /app/Information_Units/

# Copy requirements and install dependencies
COPY --chown=gbfs2d_user:gbfs2d_user Information_Units/Predictors/Gbfs2d/docker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Switch to non-root user for security
USER gbfs2d_user

# Health check to verify container is ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose the FastAPI port
EXPOSE 8000

# Environment variables
ENV GBFS2D_HOST=0.0.0.0
ENV GBFS2D_PORT=8000
ENV GBFS2D_LOG_LEVEL=INFO

# Run the FastAPI server via Gbfs2dPredictor
CMD ["python", "-m", "Information_Units.Predictors.Gbfs2d.Gbfs2dPredictor", "--serve"]
