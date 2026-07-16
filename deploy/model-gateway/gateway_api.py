from __future__ import annotations

import importlib
import logging
import pathlib
import sys
from typing import Callable

from fastapi import FastAPI


# Ensure repository root is importable when running from deploy/model-gateway.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("emos_model_gateway")

app = FastAPI(
    title="EMOS Model Gateway",
    description="Single private gateway exposing MatterGen, MatterSim, CHGNet, and GBFS APIs.",
    version="0.1.0",
)


def _stub(name: str, reason: str) -> FastAPI:
    stub = FastAPI(title=f"{name} unavailable")

    @stub.get("/health")
    def health() -> dict:
        return {"status": "degraded", "service": name, "message": reason}

    @stub.get("/info")
    def info() -> dict:
        return {"status": "degraded", "service": name, "reason": reason}

    return stub


def _mount(prefix: str, module_path: str, *, app_attr: str = "app", app_factory: str | None = None, name: str) -> None:
    try:
        module = importlib.import_module(module_path)
        if app_factory:
            factory: Callable[[], FastAPI] = getattr(module, app_factory)
            subapp = factory()
        else:
            subapp = getattr(module, app_attr)
        app.mount(prefix, subapp)
        logger.info("Mounted %s at %s", name, prefix)
    except Exception as exc:
        logger.exception("Failed to mount %s: %s", name, exc)
        app.mount(prefix, _stub(name, str(exc)))


_mount(
    "/mattergen",
    "Information_Units.Generators.MattergenBaseModel.docker.mattergen_api",
    name="mattergen",
)
_mount(
    "/mattersim",
    "Information_Units.Predictors.Mattersim.docker.mattersim_api",
    name="mattersim",
)
_mount(
    "/chgnet",
    "Information_Units.Predictors.Chgnet.docker.chgnet_api",
    name="chgnet",
)
_mount(
    "/gbfs",
    "Information_Units.Predictors.Gbfs.GbfsPredictor",
    app_factory="create_app",
    name="gbfs",
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "model-gateway",
        "mounted": ["/mattergen", "/mattersim", "/chgnet", "/gbfs"],
    }
