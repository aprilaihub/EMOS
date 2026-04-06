"""Backward-compatible aliases for renamed GBFS predictor module."""

from Information_Units.Predictors.Gbfs import (
    GbfsPredictor,
    generate_features,
    load_cif,
)

GBFS_PredPredictor = GbfsPredictor

try:
    from Information_Units.Predictors.Gbfs import create_app
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
