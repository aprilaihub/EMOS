###############################################################################
# GRACE Docker Image with GPU Support
# Uses Miniforge3 (conda-forge) to install GRACE and dependencies.
# Exposes a FastAPI server on port 8000 with GPU acceleration via TensorFlow.
###############################################################################
FROM condaforge/miniforge3:latest

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# ── Create conda environment with GRACE and PyTorch GPU support ───────────
# Python 3.11 with CUDA 11.8 wheels for torch/torchvision/torchaudio.
# tensorpotential (TensorFlow-based) auto-detects CUDA from PyTorch installation.
RUN conda create -n grace python=3.11 -y \
    && conda run -n grace pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cu118 \
        "torch==2.5.1" "torchvision==0.20.1" "torchaudio==2.5.1" \
    && conda run -n grace pip install --no-cache-dir \
        "tensorpotential" \
        "ase==3.27.0" \
        "pymatgen" \
    && conda clean -afy

# ── Install FastAPI server dependencies ───────────────────────────────────
COPY requirements.txt /app/requirements.txt
RUN conda run -n grace pip install --no-cache-dir -r /app/requirements.txt

# ── Copy the FastAPI server ───────────────────────────────────────────────
COPY grace_api.py /app/grace_api.py

# Expose the FastAPI port
EXPOSE 8000

# ── GPU Configuration ──────────────────────────────────────────────────────
# TensorFlow/tensorpotential auto-detects available CUDA devices.
# PCI_BUS_ID ensures consistent GPU ordering across restarts.
ENV GRACE_DEVICE=auto
ENV CUDA_DEVICE_ORDER=PCI_BUS_ID

# Health-check
HEALTHCHECK --interval=300s --timeout=10s --retries=2 --start-period=60s \
    CMD conda run -n grace python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the FastAPI server inside the conda environment
CMD ["conda", "run", "--no-capture-output", "-n", "grace", "uvicorn", "grace_api:app", "--host", "0.0.0.0", "--port", "8000"]
