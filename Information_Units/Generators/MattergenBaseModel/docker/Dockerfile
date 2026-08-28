###############################################################################
# MatterGen Docker Image
# Clones mattergen from the aprilaihub fork and installs it with uv
# (the officially recommended method).  Exposes a FastAPI server on port 8000.
###############################################################################
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

# Prevent interactive prompts during package install
ENV DEBIAN_FRONTEND=noninteractive

# ── System dependencies ────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        git-lfs \
        python3.10 \
        python3.10-venv \
        python3.10-dev \
        python3-pip \
        build-essential \
        curl \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

# Make python3.10 the default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/python  python  /usr/bin/python3.10 1

# ── Install uv (the package manager mattergen recommends) ─────────────────
RUN pip install --no-cache-dir uv

WORKDIR /app

# ── Clone mattergen ────────────────────────────────────────────────────────
ARG MATTERGEN_REPO=https://github.com/aprilaihub/mattergen.git
ARG MATTERGEN_BRANCH=main
RUN git clone --depth 1 --branch ${MATTERGEN_BRANCH} ${MATTERGEN_REPO} /app/mattergen

# ── Install mattergen with uv (official method from README) ───────────────
WORKDIR /app/mattergen
RUN uv venv .venv --python 3.10 \
    && . .venv/bin/activate \
    && uv pip install -e .

# Make the uv venv the default Python for all subsequent commands
ENV VIRTUAL_ENV=/app/mattergen/.venv
ENV PATH="/app/mattergen/.venv/bin:${PATH}"

# ── Install the FastAPI server deps into the same venv ─────────────────────
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN uv pip install -r /app/requirements.txt

# ── Copy the FastAPI server ────────────────────────────────────────────────
COPY mattergen_api.py /app/mattergen_api.py

# Create directory for model cache (generation output uses temp dirs)
RUN mkdir -p /app/models

# Expose the FastAPI port
EXPOSE 8000

# Health-check: hit the /health endpoint every 5 minutes (sparse to avoid log flooding)
HEALTHCHECK --interval=300s --timeout=10s --retries=2 --start-period=30s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the FastAPI server
CMD ["uvicorn", "mattergen_api:app", "--host", "0.0.0.0", "--port", "8000"]
