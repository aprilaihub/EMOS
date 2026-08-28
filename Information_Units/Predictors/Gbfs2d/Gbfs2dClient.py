"""HTTP client for the containerized GBFS-2D predictor."""

from typing import Any

from Information_Units.Predictors.ContainerPredictorClient import ContainerPredictorClient


class Gbfs2dPredictor(ContainerPredictorClient):
    source = "gbfs-2d"
    service_name = "gbfs-2d"
    api_url_env = "GBFS2D_API_URL"
    timeout_env = "GBFS2D_TIMEOUT"
    default_api_url = "http://localhost:8201"
    property_map = {
        "bandgap": "bandgap",
        "is_metal": "is_metal",
        "is_stable": "is_stable",
    }

    def __init__(self, predictor_name: str = "gbfs_2d", logger=None):
        super().__init__(predictor_name, logger)

    def _add_service_properties(self, payload: dict[str, Any], properties: dict[str, Any]) -> None:
        properties["is_vdw_layered"] = bool(payload.get("is_vdw_layered", False))


Gbfs2dClient = Gbfs2dPredictor