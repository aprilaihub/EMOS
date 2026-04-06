"""Backward-compatible import path for GBFS predictor.

Deprecated: prefer Information_Units.Predictors.Gbfs.GbfsPredictor.
"""

from Information_Units.Predictors.Gbfs.GbfsPredictor import (
    GbfsPredictor,
    generate_features,
    load_cif,
)

GBFS_PredPredictor = GbfsPredictor

try:
    from Information_Units.Predictors.Gbfs.GbfsPredictor import create_app
    __all__ = [
        "GbfsPredictor",
        "GBFS_PredPredictor",
        "generate_features",
        "load_cif",
        "create_app",
    ]
except ImportError:
    __all__ = [
        "GbfsPredictor",
        "GBFS_PredPredictor",
        "generate_features",
        "load_cif",
    ]
