###############################################################################
# MatterSim Docker Image
# Uses Miniforge3 (conda-forge) to install MatterSim and dependencies,
# matching the tested local environment. Exposes a FastAPI server on port 8000.
###############################################################################
FROM condaforge/miniforge3:latest

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# ── Create conda environment with MatterSim ───────────────────────────────
# Python 3.11 (same as CHGNet): cu118 wheels for torch/torchvision/torchaudio
# are not published for 3.13. Installing the full trio up front satisfies
# MatterSim's torch>=/torchvision>=/torchaudio>= requirements, so pip does not
# pull newer CUDA builds that this cluster's driver cannot run.
RUN conda create -n mattersim python=3.11 -y \
    && conda run -n mattersim pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cu118 \
        "torch==2.5.1" "torchvision==0.20.1" "torchaudio==2.5.1" \
    && conda run -n mattersim pip install --no-cache-dir \
        "mattersim==1.2.1" \
        "ase==3.27.0" \
        pymatgen \
    && conda clean -afy

# ── Install FastAPI server dependencies ───────────────────────────────────
COPY requirements.txt /app/requirements.txt
RUN conda run -n mattersim pip install --no-cache-dir -r /app/requirements.txt

# ── Copy the FastAPI server ───────────────────────────────────────────────
COPY mattersim_api.py /app/mattersim_api.py

# Expose the FastAPI port
EXPOSE 8000

ENV MATTERSIM_DEVICE=auto
ENV CUDA_DEVICE_ORDER=PCI_BUS_ID

# Health-check
HEALTHCHECK --interval=300s --timeout=10s --retries=2 --start-period=60s \
    CMD conda run -n mattersim python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the FastAPI server inside the conda environment
CMD ["conda", "run", "--no-capture-output", "-n", "mattersim", "uvicorn", "mattersim_api:app", "--host", "0.0.0.0", "--port", "8000"]
