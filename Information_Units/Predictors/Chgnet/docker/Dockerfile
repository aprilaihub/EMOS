FROM condaforge/miniforge3:latest

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN conda create -n chgnet python=3.11 -y \
    && conda run -n chgnet pip install --no-cache-dir \
        "chgnet==0.4.0" \
        "ase==3.27.0" \
        pymatgen \
    && conda clean -afy

COPY requirements.txt /app/requirements.txt
RUN conda run -n chgnet pip install --no-cache-dir -r /app/requirements.txt

COPY chgnet_api.py /app/chgnet_api.py

EXPOSE 8000

HEALTHCHECK --interval=300s --timeout=10s --retries=2 --start-period=60s \
    CMD conda run -n chgnet python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["conda", "run", "--no-capture-output", "-n", "chgnet", "uvicorn", "chgnet_api:app", "--host", "0.0.0.0", "--port", "8000"]