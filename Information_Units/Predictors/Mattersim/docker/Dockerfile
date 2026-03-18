###############################################################################
# MatterSim Docker Image
# Uses Miniforge3 (conda-forge) to install MatterSim and dependencies,
# matching the tested local environment. Exposes a FastAPI server on port 8000.
###############################################################################
FROM condaforge/miniforge3:latest

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# ── Create conda environment with MatterSim ───────────────────────────────
RUN conda create -n mattersim python=3.13 -y \
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

# Health-check
HEALTHCHECK --interval=300s --timeout=10s --retries=2 --start-period=60s \
    CMD conda run -n mattersim python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the FastAPI server inside the conda environment
CMD ["conda", "run", "--no-capture-output", "-n", "mattersim", "uvicorn", "mattersim_api:app", "--host", "0.0.0.0", "--port", "8000"]
