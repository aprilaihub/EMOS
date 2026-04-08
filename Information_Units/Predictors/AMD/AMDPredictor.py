"""
AMD (Average Minimum Distance) Predictor

Uses the average-minimum-distance package to compare crystal structures and
determine their similarity based on geometric descriptors.

Reference: https://github.com/dwiddo/average-minimum-distance
"""

import os
import json
import logging
import sys
import argparse
from typing import Dict, Any, Optional, List, Union

import amd
from pathlib import Path

from Information_Units.Predictors.BasePredictor import BasePredictor

# Optional FastAPI imports (for server mode)
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


# ============================================================================
# Helper Functions
# ============================================================================

def validate_cif_file(cif_path: str) -> None:
    """
    Validate that a CIF file exists and is readable.
    
    Args:
        cif_path (str): Path to the CIF file
        
    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the file cannot be read
    """
    if not os.path.exists(cif_path):
        raise FileNotFoundError(f"CIF file not found: {cif_path}")
    
    if not os.path.isfile(cif_path):
        raise ValueError(f"Path is not a file: {cif_path}")
    
    if not cif_path.lower().endswith('.cif'):
        raise ValueError(f"File does not have .cif extension: {cif_path}")


def load_crystals_from_cif(cif_path: str) -> List[amd.PeriodicSet]:
    """
    Load one or more crystal structures from a CIF file.
    
    Args:
        cif_path (str): Path to the CIF file
        
    Returns:
        List[amd.PeriodicSet]: List of crystal structures
        
    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If no crystals can be read from the file
    """
    validate_cif_file(cif_path)
    
    try:
        reader = amd.CifReader(cif_path)
        crystals = list(reader)
        
        if not crystals:
            raise ValueError(f"No crystal structures found in {cif_path}")
        
        return crystals
    except Exception as e:
        raise ValueError(f"Failed to parse CIF file {cif_path}: {str(e)}")


def calculate_pdd_distance(crystal1: amd.PeriodicSet, crystal2: amd.PeriodicSet, 
                          k: int = 100) -> float:
    """
    Calculate Earth Mover's Distance (EMD) between two crystals using PDDs.
    
    Args:
        crystal1: First crystal structure
        crystal2: Second crystal structure
        k (int): Number of neighboring atoms to consider (default: 100)
        
    Returns:
        float: EMD distance between the PDDs
    """
    pdd1 = amd.PDD(crystal1, k)
    pdd2 = amd.PDD(crystal2, k)
    distance = amd.EMD(pdd1, pdd2)
    return float(distance)


def calculate_amd_distance(crystal1: amd.PeriodicSet, crystal2: amd.PeriodicSet,
                          k: int = 100, metric: str = "chebyshev") -> float:
    """
    Calculate Average Minimum Distance (AMD) between two crystals.
    
    Args:
        crystal1: First crystal structure
        crystal2: Second crystal structure
        k (int): Number of neighboring atoms to consider (default: 100)
        metric (str): Distance metric for AMD comparison (default: "chebyshev")
        
    Returns:
        float: AMD distance between the crystals
    """
    amd1 = amd.AMD(crystal1, k)
    amd2 = amd.AMD(crystal2, k)
    distance = amd.AMD_cdist([amd1], [amd2], metric=metric)[0][0]
    return float(distance)


def get_crystal_info(crystal: amd.PeriodicSet) -> Dict[str, Any]:
    """
    Extract metadata about a crystal structure.
    
    Args:
        crystal: Crystal structure
        
    Returns:
        Dict with crystal information
    """
    try:
        # Number of atoms in the motif (asymmetric unit * multiplicities)
        n_atoms = len(crystal.motif) if hasattr(crystal, 'motif') else crystal.n_asym
        
        # Try to construct composition from types and multiplicities
        composition = "unknown"
        if hasattr(crystal, 'types') and hasattr(crystal, 'multiplicities'):
            # Map atomic numbers to element symbols
            atomic_symbols = {
                1: 'H', 6: 'C', 7: 'N', 8: 'O', 13: 'Al', 14: 'Si', 15: 'P', 16: 'S',
                17: 'Cl', 19: 'K', 20: 'Ca', 26: 'Fe', 29: 'Cu', 30: 'Zn', 79: 'Au', 82: 'Pb'
            }
            comp_parts = []
            for atom_type, multiplicity in zip(crystal.types, crystal.multiplicities):
                symbol = atomic_symbols.get(atom_type, f"Z{atom_type}")
                comp_parts.append(f"{symbol}{multiplicity}")
            composition = "".join(comp_parts)
        
        return {
            "name": crystal.name if hasattr(crystal, 'name') else "unknown",
            "n_atoms": n_atoms,
            "n_asym": crystal.n_asym if hasattr(crystal, 'n_asym') else 0,
            "composition": composition
        }
    except Exception:
        return {"name": "unknown", "n_atoms": 0, "n_asym": 0, "composition": "unknown"}


# ============================================================================
# AMD Predictor Class
# ============================================================================

class AMDPredictor(BasePredictor):
    """
    Crystal structure similarity predictor using Average Minimum Distance (AMD).
    
    Compares crystal structures using geometric descriptors based on the
    average-minimum-distance package. Takes two or more CIF files and returns
    similarity/distance metrics between them.
    
    Features:
    - Pointwise Distance Distribution (PDD) comparison using Earth Mover's Distance (EMD)
    - Average Minimum Distance (AMD) vector comparison
    - Support for multiple crystals in single CIF file
    - Configurable k parameter for neighborhood size
    - Multiple distance metrics
    """
    
    def __init__(self, predictor_name: str = "AMD", k: int = 100, 
                 metric: str = "chebyshev", logger: Optional[Any] = None):
        """
        Initialize AMD predictor.
        
        Args:
            predictor_name (str): Name of the predictor instance
            k (int): Number of neighboring atoms to consider (default: 100)
            metric (str): Distance metric for AMD comparison (default: "chebyshev")
            logger: Optional logger instance
        """
        super().__init__(predictor_name=predictor_name, logger=logger)
        self.k = k
        self.metric = metric
        
        if self.logger:
            self.logger.log(f"Initialized {predictor_name} with k={k}, metric={metric}", 'info')
    
    def info(self) -> str:
        """
        Return information about this predictor.
        
        Returns:
            str: Description of the predictor
        """
        return (
            f"AMD (Average Minimum Distance) Predictor: {self.predictor_name}\n"
            f"Compares crystal structures using geometric descriptors.\n"
            f"Parameters: k={self.k}, metric={self.metric}\n"
            f"Uses: PDD/EMD and AMD distance calculations"
        )
    
    def predict(self, inputs: Dict[str, Any]) -> str:
        """
        Compare crystal structures and return similarity metrics.
        
        Follows the standardized predictor I/O contract:
        Input: {"input_data": [list of CIF file paths], "k": int (optional), "metric": str (optional)}
        Output: JSON string with standardized structure:
        {
            "source": "AMD",
            "results": [
                {
                    "index": int,
                    "status": "success" | "failed",
                    "properties": dict with pairwise_distances and crystal_info,
                    "warnings": list of strings,
                    "error": null | error message string
                },
                ...
            ]
        }
        
        Args:
            inputs: Dict with required key 'input_data' (list of CIF file paths)
                   Optional keys: 'k' (int), 'metric' (str)
            
        Returns:
            str: JSON string with standardized predictor output
            
        Raises:
            ValueError: If input format is invalid
            FileNotFoundError: If CIF files don't exist
        """
        if self.logger:
            self.logger.log(f"Running AMD prediction", 'info')
        
        results_list = []
        
        try:
            # Extract input_data
            if not isinstance(inputs, dict):
                raise ValueError("Inputs must be a dictionary with 'input_data' key")
            
            input_data = inputs.get('input_data', [])
            if not isinstance(input_data, list):
                raise ValueError("'input_data' must be a list of CIF file paths")
            
            if len(input_data) < 2:
                raise ValueError(
                    f"AMD predictor requires at least 2 CIF files. Got {len(input_data)}"
                )
            
            # Extract optional parameters
            k = inputs.get('k', self.k)
            metric = inputs.get('metric', self.metric)
            
            # Load all crystals from CIF files
            all_crystals = []
            crystal_sources = []
            warnings = []
            
            for cif_path in input_data:
                try:
                    crystals = load_crystals_from_cif(cif_path)
                    for crystal in crystals:
                        all_crystals.append(crystal)
                        crystal_sources.append(cif_path)
                except Exception as e:
                    warnings.append(f"Warning: Failed to load {cif_path}: {str(e)}")
            
            if len(all_crystals) < 2:
                raise ValueError(
                    f"At least 2 crystal structures needed. Got {len(all_crystals)} "
                    f"from {len(input_data)} file(s)"
                )
            
            # Calculate distances between all pairs
            pairwise_results = self._calculate_pairwise_distances(all_crystals, crystal_sources, k, metric)
            
            # Get crystal metadata
            crystal_info = [get_crystal_info(c) for c in all_crystals]
            
            # Create standardized result format
            result_dict = {
                "index": 0,
                "status": "success",
                "properties": {
                    "pairwise_distances": pairwise_results["pairwise_distances"],
                    "crystal_info": crystal_info,
                    "parameters": {
                        "k": k,
                        "metric": metric,
                        "n_crystals": len(all_crystals),
                        "n_files": len(input_data)
                    },
                    "n_comparisons": pairwise_results["n_comparisons"]
                },
                "warnings": warnings,
                "error": None
            }
            results_list.append(result_dict)
            
        except Exception as e:
            # Return error in standardized format
            result_dict = {
                "index": 0,
                "status": "failed",
                "properties": {},
                "warnings": [],
                "error": str(e)
            }
            results_list.append(result_dict)
        
        # Return standardized output
        output = {
            "source": self.predictor_name,
            "results": results_list
        }
        return json.dumps(output)
    
    def predict_numpy(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare crystal structures and return dict output (non-JSON).
        
        Useful for programmatic access within Python. Uses same I/O contract
        as predict() but returns dict instead of JSON string.
        
        Args:
            inputs: Dict with 'input_data' key (list of CIF file paths)
            
        Returns:
            Dict with standardized predictor output
            
        Raises:
            ValueError: If inputs are invalid
            FileNotFoundError: If CIF files don't exist
        """
        result_json = self.predict(inputs)
        return json.loads(result_json)
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    
    def _calculate_pairwise_distances(self, crystals: List[amd.PeriodicSet],
                                     crystal_sources: List[str], 
                                     k: int = None, 
                                     metric: str = None) -> Dict[str, Any]:
        """
        Calculate pairwise distances between all crystal structures.
        
        Args:
            crystals: List of crystal structures
            crystal_sources: List of source file paths for each crystal
            k: Number of atoms to consider (uses self.k if None)
            metric: Distance metric to use (uses self.metric if None)
            
        Returns:
            Dict with pairwise distance results
        """
        # Use provided k and metric, or fall back to instance defaults
        if k is None:
            k = self.k
        if metric is None:
            metric = self.metric
            
        pairwise_distances = []
        
        n = len(crystals)
        for i in range(n):
            for j in range(i + 1, n):
                try:
                    # Calculate both PDD/EMD and AMD distances
                    pdd_distance = calculate_pdd_distance(crystals[i], crystals[j], k)
                    amd_distance = calculate_amd_distance(crystals[i], crystals[j], 
                                                         k, metric)
                    
                    pair_result = {
                        'crystal_1_index': i,
                        'crystal_2_index': j,
                        'crystal_1_file': crystal_sources[i],
                        'crystal_2_file': crystal_sources[j],
                        'pdd_emd_distance': pdd_distance,
                        'amd_distance': amd_distance,
                        'identical': pdd_distance < 1e-6,
                        'very_similar': pdd_distance < 0.1,
                        'similar': pdd_distance < 0.5,
                    }
                    pairwise_distances.append(pair_result)
                    
                except Exception as e:
                    pairwise_distances.append({
                        'crystal_1_index': i,
                        'crystal_2_index': j,
                        'error': str(e),
                        'status': 'failed'
                    })
        
        return {
            'pairwise_distances': pairwise_distances,
            'n_comparisons': len(pairwise_distances)
        }


# ============================================================================
# FastAPI Server Components (Optional, for Docker deployment)
# ============================================================================

if FASTAPI_AVAILABLE:
    
    class PredictRequest(BaseModel):
        """Request schema for AMD predictor API (standardized I/O contract)."""
        input_data: List[str] = Field(
            ...,
            description="List of CIF file paths to compare"
        )
        k: int = Field(
            100,
            description="Number of atoms to consider in descriptor calculation"
        )
        metric: str = Field(
            "chebyshev",
            description="Distance metric for AMD calculation"
        )
        
        class Config:
            schema_extra = {
                "example": {
                    "input_data": ["structure1.cif", "structure2.cif"],
                    "k": 100,
                    "metric": "chebyshev"
                }
            }
    
    
    class HealthResponse(BaseModel):
        """Response schema for health check."""
        status: str = "healthy"
        service: str = "AMD Predictor API"
    
    
    def create_amd_app() -> FastAPI:
        """Create and configure FastAPI application for AMD Predictor."""
        app = FastAPI(
            title="AMD Predictor API",
            description="Crystal structure comparison using Average Minimum Distance",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Initialize predictor instance
        amd_predictor = AMDPredictor(predictor_name="amd_server")
        
        @app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint."""
            return HealthResponse(
                status="healthy",
                service="AMD Predictor API"
            )
        
        @app.post("/predict")
        async def predict(request: PredictRequest):
            """
            Compare crystal structures and return similarity metrics.
            
            Follows standardized EMOS predictor I/O contract.
            
            Args:
                input_data: List of CIF file paths to compare (minimum 2)
                k: Optional neighborhood size for descriptors (default: 100)
                metric: Optional distance metric (default: chebyshev)
            
            Returns:
                JSON with standardized predictor output format
            """
            try:
                inputs = {
                    'input_data': request.input_data,
                    'k': request.k,
                    'metric': request.metric
                }
                
                # Run prediction
                result_json = amd_predictor.predict(inputs)
                result = json.loads(result_json)
                
                # Check for errors using standardized format
                if result["results"][0]["status"] == "failed":
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Prediction failed: {result['results'][0]['error']}"
                    )
                
                return JSONResponse(content=result)
                
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except FileNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/info")
        async def info():
            """Get information about the AMD predictor."""
            return {
                "service": "AMD Predictor",
                "description": "Crystal structure comparison using Average Minimum Distance",
                "endpoints": {
                    "/predict": "Compare crystal structures",
                    "/health": "Health check",
                    "/info": "Service information",
                    "/docs": "Interactive API documentation",
                    "/redoc": "ReDoc API documentation"
                },
                "parameters": {
                    "k": "Number of atoms for descriptor (default: 100)",
                    "metric": "Distance metric: chebyshev, euclidean, etc."
                }
            }
        
        return app


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for CLI and server modes."""
    parser = argparse.ArgumentParser(
        description="AMD (Average Minimum Distance) Predictor"
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run as FastAPI server"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("AMD_HOST", "0.0.0.0"),
        help="Server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("AMD_PORT", "8001")),
        help="Server port (default: 8001)"
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("AMD_LOG_LEVEL", "info").upper(),
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    if args.serve:
        if not FASTAPI_AVAILABLE:
            print("Error: FastAPI is required for server mode.")
            print("Install with: pip install fastapi uvicorn")
            sys.exit(1)
        
        print(f"Starting AMD Predictor API server on {args.host}:{args.port}")
        print(f"API Documentation: http://{args.host}:{args.port}/docs")
        
        app = create_amd_app()
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower()
        )
    else:
        print("AMD Predictor initialized")
        print("Run with --serve to start API server")


if __name__ == "__main__":
    main()
