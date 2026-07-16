FROM condaforge/miniforge3:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    gfortran \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Single runtime env for gateway and the model APIs we mount.
RUN conda create -n emos-gateway python=3.11 -y \
    && conda run -n emos-gateway pip install --no-cache-dir -r /app/deploy/model-gateway/requirements.txt \
    && conda clean -afy

WORKDIR /app/deploy/model-gateway

EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=10s --retries=3 --start-period=90s \
    CMD conda run -n emos-gateway python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["conda", "run", "--no-capture-output", "-n", "emos-gateway", "uvicorn", "gateway_api:app", "--host", "0.0.0.0", "--port", "8000"]
