FROM condaforge/miniforge3:latest

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# GRACE install guidance (gracemaker docs): use a clean env and install tensorpotential.
# Kokkos/LAMMPS builds are not needed for this HTTP predictor service.
RUN conda create -n grace python=3.11 -y \
    && conda run -n grace pip install --no-cache-dir \
        "tensorpotential" \
        "ase==3.27.0" \
        "pymatgen" \
    && conda clean -afy

COPY requirements.txt /app/requirements.txt
RUN conda run -n grace pip install --no-cache-dir -r /app/requirements.txt

COPY grace_api.py /app/grace_api.py

EXPOSE 8000

HEALTHCHECK --interval=300s --timeout=10s --retries=2 --start-period=60s \
    CMD conda run -n grace python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["conda", "run", "--no-capture-output", "-n", "grace", "uvicorn", "grace_api:app", "--host", "0.0.0.0", "--port", "8000"]
