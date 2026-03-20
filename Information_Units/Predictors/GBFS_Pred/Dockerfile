# Production-Ready Dockerfile for GBFS_PredPredictor
# 
# Build: docker build -t gbfs-pred:latest .
# Run:   docker run -v $(pwd):/data gbfs-pred:latest \
#          --cif /data/sample.cif \
#          --model /data/bandgap_model.pkl \
#          --scaler /data/bandgap_scaler.pkl \
#          --features /data/bandgap_features.pkl

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
RUN useradd -m -u 1000 predictor

# Copy only necessary application code
COPY --chown=predictor:predictor Information_Units/ /app/Information_Units/

# Install Python dependencies with no cache to reduce layer size
RUN pip install --no-cache-dir --user \
    numpy==1.26.4 \
    scipy==1.11.4 \
    pandas==2.0.3 \
    scikit-learn==1.3.2 \
    pymatgen==2023.8.10 \
    matminer==0.9.0 \
    lightgbm==4.3.0 \
    joblib==1.3.2

# Switch to non-root user for security
USER predictor

# Health check to verify container is ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import Information_Units.Predictors.GBFS_Pred.GBFS_PredPredictor; print('OK')" || exit 1

# Use Python module execution as entrypoint
ENTRYPOINT ["python", "-m", "Information_Units.Predictors.GBFS_Pred.GBFS_PredPredictor"]

# Set default command to show help
CMD ["--help"]
