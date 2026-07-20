# FastAPI Server for Gbfs Predictor
#
# Build: docker build -t gbfs-pred:latest -f docker/Dockerfile ..
# Run:   docker run -p 8000:8000 gbfs-pred:latest
#
# The FastAPI server exposes predictions via HTTP:
#   POST /predict/bandgap  – predict band gap
#   POST /predict/e_form   – predict formation energy
#   GET  /info             – view supported properties
#   GET  /health           – health check

FROM python:3.10-slim

WORKDIR /app

# System dependencies (required for pymatgen and numerical computing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 gbfs_user

# Copy application code and model files
# Note: Models must be in Information_Units/Predictors/Gbfs/{property}/ directories
COPY --chown=gbfs_user:gbfs_user Information_Units/ /app/Information_Units/

# Copy requirements and install dependencies
COPY --chown=gbfs_user:gbfs_user Information_Units/Predictors/Gbfs/docker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Switch to non-root user for security
USER gbfs_user

# Health check to verify container is ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready')" || exit 1

# Expose the FastAPI port
EXPOSE 8000

# Environment variables
ENV GBFS_HOST=0.0.0.0
ENV GBFS_PORT=8000
ENV GBFS_LOG_LEVEL=INFO
ENV EMOS_GBFS_CONTAINER=1

# Run the FastAPI server via GbfsPredictor
CMD ["python", "-m", "Information_Units.Predictors.Gbfs.GbfsPredictor", "--serve"]
