"""AMD screen -> PDD confirm similarity pipeline for the PDD predictor.

Typical use::

    from Information_Units.Predictors.Pdd.similarity import SimilarityConfig, run_similarity_pipeline

    config = SimilarityConfig(input_dirs=["tests/fixtures/cif_files/mp"], tau=0.1, k_amd=15, k_pdd=30)
    result = run_similarity_pipeline(config, verbose=True)

or from the command line::

    python -m Information_Units.Predictors.Pdd.similarity --config my_config.json
"""

from ._report import Reporter
from .config import ALLOWED_LINKAGES, ALLOWED_METRICS, ConfigError, SimilarityConfig
from .pipeline import PipelineResult, run_similarity_pipeline

__all__ = [
    "ALLOWED_LINKAGES",
    "ALLOWED_METRICS",
    "ConfigError",
    "PipelineResult",
    "Reporter",
    "SimilarityConfig",
    "run_similarity_pipeline",
]
