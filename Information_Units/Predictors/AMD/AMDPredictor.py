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
    
    def predict(self, inputs: Union[str, Dict[str, Any]]) -> str:
        """
        Compare crystal structures and return similarity metrics.
        
        Supports flexible input formats:
        - str: path to a single CIF file (will be compared with itself)
        - dict with 'cif_paths': list of paths to CIF files
        - dict with 'cif_path1', 'cif_path2': two CIF file paths
        - dict with 'input_data': dict containing CIF paths
        
        Returns a JSON string with:
        - pairwise_distances: List of distances between crystal pairs
        - crystal_info: Metadata about each crystal
        - parameters: AMD calculation parameters used
        
        Args:
            inputs: Input specification (see above)
            
        Returns:
            str: JSON string with comparison results
            
        Raises:
            ValueError: If inputs are invalid or insufficient
            FileNotFoundError: If CIF files don't exist
        """
        if self.logger:
            self.logger.log(f"Running AMD prediction", 'info')
        
        try:
            # Extract CIF file paths from inputs
            cif_paths = self._extract_cif_paths(inputs)
            
            if len(cif_paths) < 2:
                raise ValueError(
                    f"AMD predictor requires at least 2 CIF files. Got {len(cif_paths)}"
                )
            
            # Load all crystals from CIF files
            all_crystals = []
            crystal_sources = []  # Track which crystal came from which file
            
            for cif_path in cif_paths:
                crystals = load_crystals_from_cif(cif_path)
                for crystal in crystals:
                    all_crystals.append(crystal)
                    crystal_sources.append(cif_path)
            
            if len(all_crystals) < 2:
                raise ValueError(
                    f"At least 2 crystal structures needed. Got {len(all_crystals)} "
                    f"from {len(cif_paths)} file(s)"
                )
            
            # Calculate distances between all pairs
            results = self._calculate_pairwise_distances(all_crystals, crystal_sources)
            
            # Get crystal metadata
            results['crystal_info'] = [get_crystal_info(c) for c in all_crystals]
            results['parameters'] = {
                'k': self.k,
                'metric': self.metric,
                'n_crystals': len(all_crystals),
                'n_files': len(cif_paths)
            }
            
            # Return as JSON string (following GBFS convention)
            return json.dumps(results)
            
        except Exception as e:
            error_result = {
                "error": str(e),
                "predictor": self.predictor_name,
                "status": "failed"
            }
            return json.dumps(error_result)
    
    def predict_numpy(self, inputs: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare crystal structures and return similarity metrics as dict.
        
        This is the numpy-compatible version that returns a dict instead of
        JSON string, useful for programmatic access.
        
        Args:
            inputs: Input specification (see predict() docstring)
            
        Returns:
            Dict with comparison results
            
        Raises:
            ValueError: If inputs are invalid
            FileNotFoundError: If CIF files don't exist
        """
        result_json = self.predict(inputs)
        return json.loads(result_json)
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    def _extract_cif_paths(self, inputs: Union[str, Dict[str, Any]]) -> List[str]:
        """
        Extract list of CIF file paths from flexible input formats.
        
        Args:
            inputs: Input in various formats
            
        Returns:
            List[str]: Paths to CIF files
            
        Raises:
            ValueError: If no valid CIF paths found
        """
        paths = []
        
        if isinstance(inputs, str):
            # Single file path
            paths = [inputs]
        elif isinstance(inputs, dict):
            # Dictionary with CIF paths
            if 'cif_paths' in inputs:
                cif_paths = inputs['cif_paths']
                if isinstance(cif_paths, list):
                    paths = cif_paths
                else:
                    paths = [cif_paths]
            elif 'cif_path' in inputs:
                paths = [inputs['cif_path']]
            elif 'cif_path1' in inputs and 'cif_path2' in inputs:
                paths = [inputs['cif_path1'], inputs['cif_path2']]
            elif 'input_data' in inputs:
                data = inputs['input_data']
                if isinstance(data, dict):
                    if 'cif_paths' in data:
                        cif_paths = data['cif_paths']
                        paths = cif_paths if isinstance(cif_paths, list) else [cif_paths]
                    elif 'cif_path' in data:
                        paths = [data['cif_path']]
            else:
                raise ValueError("No CIF paths found in input dictionary")
        else:
            raise ValueError(f"Invalid input type: {type(inputs)}")
        
        if not paths:
            raise ValueError("No CIF file paths provided")
        
        return paths
    
    def _calculate_pairwise_distances(self, crystals: List[amd.PeriodicSet],
                                     crystal_sources: List[str]) -> Dict[str, Any]:
        """
        Calculate pairwise distances between all crystal structures.
        
        Args:
            crystals: List of crystal structures
            crystal_sources: List of source file paths for each crystal
            
        Returns:
            Dict with pairwise distance results
        """
        pairwise_distances = []
        
        n = len(crystals)
        for i in range(n):
            for j in range(i + 1, n):
                try:
                    # Calculate both PDD/EMD and AMD distances
                    pdd_distance = calculate_pdd_distance(crystals[i], crystals[j], self.k)
                    amd_distance = calculate_amd_distance(crystals[i], crystals[j], 
                                                         self.k, self.metric)
                    
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
        """Request schema for AMD predictor API."""
        cif_paths: Optional[List[str]] = Field(
            None, 
            description="List of CIF file paths to compare"
        )
        cif_path1: Optional[str] = Field(
            None,
            description="First CIF file path"
        )
        cif_path2: Optional[str] = Field(
            None,
            description="Second CIF file path"
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
                    "cif_paths": ["structure1.cif", "structure2.cif"],
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
            
            Accepts either:
            - cif_paths: list of file paths
            - cif_path1 and cif_path2: two individual file paths
            """
            try:
                # Prepare inputs for predictor
                if request.cif_paths:
                    inputs = {
                        'cif_paths': request.cif_paths,
                        'k': request.k,
                        'metric': request.metric
                    }
                elif request.cif_path1 and request.cif_path2:
                    inputs = {
                        'cif_path1': request.cif_path1,
                        'cif_path2': request.cif_path2,
                        'k': request.k,
                        'metric': request.metric
                    }
                else:
                    raise ValueError(
                        "Must provide either 'cif_paths' or both 'cif_path1' and 'cif_path2'"
                    )
                
                # Run prediction
                result_json = amd_predictor.predict(inputs)
                result = json.loads(result_json)
                
                # Check for errors in result
                if "error" in result:
                    raise HTTPException(status_code=400, detail=result["error"])
                
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
