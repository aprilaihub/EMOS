# FastAPI Server for AMD (Average Minimum Distance) Predictor
#
# Build: docker build -t amd-predictor:latest -f docker/Dockerfile ..
# Run:   docker run -p 8001:8001 amd-predictor:latest
#
# The FastAPI server exposes crystal structure comparisons via HTTP:
#   POST /predict           – compare crystal structures from CIF files
#   POST /compare-files     – direct file comparison
#   GET  /health            – health check
#   GET  /docs              – interactive API documentation

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
RUN useradd -m -u 1000 amd_user

# Copy application code
# Note: CIF files can be mounted as volumes at runtime
COPY --chown=amd_user:amd_user Information_Units/ /app/Information_Units/

# Copy requirements and install dependencies
COPY --chown=amd_user:amd_user Information_Units/Predictors/AMD/docker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Switch to non-root user for security
USER amd_user

# Health check to verify container is ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Expose the FastAPI port
EXPOSE 8001

# Environment variables
ENV AMD_HOST=0.0.0.0
ENV AMD_PORT=8001
ENV AMD_LOG_LEVEL=INFO
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the FastAPI server via AMDPredictor
CMD ["python", "-m", "Information_Units.Predictors.AMD.AMDPredictor", "--serve"]
