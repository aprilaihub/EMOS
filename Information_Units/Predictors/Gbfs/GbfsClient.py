"""HTTP client for the containerized GBFS predictor."""

from Information_Units.Predictors.ContainerPredictorClient import ContainerPredictorClient


class GbfsClient(ContainerPredictorClient):
    source = "gbfs"
    service_name = "gbfs"
    api_url_env = "GBFS_PRED_API_URL"
    timeout_env = "GBFS_PRED_TIMEOUT"
    default_api_url = "http://localhost:8200"
    property_map = {
        "bandgap": "bandgap",
        "dielectric": "dielectric",
        "e_form": "e_form",
        "is_metal": "is_metal",
        "mob_n": "mob_n",
        "mob_p": "mob_p",
    }

    def __init__(self, predictor_name: str = "gbfs", logger=None):
        super().__init__(predictor_name, logger)