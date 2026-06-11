"""
Gbfs: Pretrained property predictors for materials science.

This module provides LightGBM models for predicting material properties:
- Band gap (eV)
- Formation energy (eV/atom)
- Dielectric constant
- Metal classification
- Electron/hole mobility (cm²/V·s)

Features are generated using matminer composition and structure featurizers.
The predictor can run in three modes:
1. Python library (programmatic)
2. CLI (command-line)
3. FastAPI server (HTTP)

Examples:
    Programmatic prediction::

        from Information_Units.Predictors.Gbfs import GbfsPredictor

        predictor = GbfsPredictor("bandgap", "bandgap")
        result = predictor.predict_numpy({"structure": structure_obj})

    CLI prediction::

        python -m Information_Units.Predictors.Gbfs.GbfsPredictor \\
            --cif structure.cif --property bandgap

    Server mode::

        python -m Information_Units.Predictors.Gbfs.GbfsPredictor \\
            --serve --host 0.0.0.0 --port 8000
"""

from Information_Units.Predictors.Gbfs.GbfsPredictor import (
    GbfsPredictor,
    generate_features,
    load_cif,
)

# Try to import FastAPI-dependent modules, but don't fail if unavailable
try:
    from Information_Units.Predictors.Gbfs.GbfsPredictor import create_app
    __all__ = [
        "GbfsPredictor",
        "generate_features",
        "load_cif",
        "create_app",
    ]
except ImportError:
    # FastAPI not installed; create_app not available
    __all__ = [
        "GbfsPredictor",
        "generate_features",
        "load_cif",
    ]

__version__ = "1.0.0"
__author__ = "EMOS Team"