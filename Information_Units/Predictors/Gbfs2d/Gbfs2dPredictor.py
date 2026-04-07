from Information_Units.Predictors.BasePredictor import BasePredictor

import os
import joblib
import logging
import traceback
import uuid
from typing import List, Tuple, Any, Dict, Optional

import numpy as np
import pandas as pd

from pymatgen.core import Structure, Composition
from pymatgen.io.cif import CifParser
from monty.json import MontyDecoder
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from matminer.featurizers.base import BaseFeaturizer
from matminer.featurizers.composition import (
    ElementProperty, ElementFraction, Stoichiometry, BandCenter,
    ValenceOrbital, AtomicOrbitals, ElectronAffinity,
    ElectronegativityDiff, TMetalFraction, OxidationStates, IonProperty
)
from matminer.featurizers.structure import (
    DensityFeatures, StructuralComplexity, GlobalSymmetryFeatures
)

from sklearn.base import TransformerMixin

# FastAPI imports (optional - only loaded if running in server mode)
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    # Provide dummy definitions so linter doesn't complain about unbound names
    # These are never used at runtime since they're guarded by FASTAPI_AVAILABLE checks
    FASTAPI_AVAILABLE = False
    FastAPI = None  # type: ignore
    HTTPException = None  # type: ignore
    BaseModel = object  # type: ignore
    Field = lambda *args, **kwargs: None  # type: ignore

# Set up logging for API server
_API_LOGGER = logging.getLogger("gbfs2d_api")

# Global predictor cache for API
_API_PREDICTORS: Dict[str, 'Gbfs2dPredictor'] = {}

# Global vdW cache
_VDW_CACHE: Dict[str, bool] = {}

# Van der Waals space group numbers (from user specification)
VDW_SPACE_GROUPS = {
    1,      # P1
    2,      # P-1
    12,     # C2/m
    148,    # R-3
    156,    # P-3m1, P3m1, or P-31m (user listed as 156)
    162,    # P-31m (alternative)
    166,    # R-3m
    187,    # P-6m2 (hexagonal vdW, e.g., some MoS2 polytypes)
    194,    # P6/mmc (most common for 2D layered materials)
}

# Cache for featurizer labels
_FEATURIZER_LABEL_CACHE: Dict[str, List[str]] = {}


# ========================
# PERIPHERAL FUNCTIONS
# ========================

def check_vdw_layered_structure(structure: Structure, tolerance: float = 0.1) -> bool:
    """
    Check whether a CIF structure has a van der Waals layered structure.
    
    Checks if the structure's space group matches known vdW layered material space groups.
    These include materials like graphite, h-BN, TMDCs, and metal halides.
    
    Key space groups:
    - P6/mmc (No. 194): Most common for 2D layered, includes graphite, h-BN, TMDCs
    - P-6m2 (No. 187): Alternative hexagonal for TMDC polytypes (e.g., some MoS2)
    - R-3m (No. 166) & R-3 (No. 148): Rhombohedral stacking of TMDCs and trihalides
    - C2/m (No. 12): Monoclinic layered materials, TPCs, metal halides
    - P-3m1 (No. 156): Specific magnetic vdW materials
    - P-31m (No. 162): Chiral or distorted vdW systems
    - P1 (No. 1) & P-1 (No. 2): Low-symmetry or distorted phases of heterostructures
    
    Args:
        structure: pymatgen Structure object
        tolerance: Tolerance for symmetry analysis (default 0.1 Å)
        
    Returns:
        bool: True if structure has vdW layered characteristics, False otherwise
        
    Raises:
        ValueError: If structure is invalid or symmetry analysis fails
    """
    try:
        if not isinstance(structure, Structure):
            raise ValueError("Input must be a pymatgen Structure object")
        
        # Use SpacegroupAnalyzer to get space group number
        analyzer = SpacegroupAnalyzer(structure, symprec=tolerance)
        space_group_number = analyzer.get_space_group_number()
        
        is_vdw = space_group_number in VDW_SPACE_GROUPS
        
        return is_vdw
        
    except Exception as e:
        raise ValueError(f"Failed to analyze vdW structure: {str(e)}")


def load_cif(cif_path: str) -> Structure:
    if not os.path.exists(cif_path):
        raise FileNotFoundError(f"CIF file not found: {cif_path}")

    parser = CifParser(cif_path)
    structures = parser.get_structures(primitive=True)

    if not structures:
        raise ValueError("No structures found in CIF file.")

    return structures[0]


def structure_to_composition(structure: Structure) -> Composition:
    return structure.composition


def load_joblib(path: str) -> Any:
    """
    Load a serialized object from a joblib file.
    
    Args:
        path (str): Path to the .pkl or .joblib file
        
    Returns:
        Any: The deserialized object
        
    Raises:
        FileNotFoundError: If the file does not exist
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    return joblib.load(path)


def get_preset_elementproperty_featurizers() -> Dict[str, ElementProperty]:
    """Get ElementProperty featurizers for all available presets."""
    presets = {}
    for preset in ['magpie', 'matminer', 'deml', 'megnet_el']:
        try:
            presets[preset] = ElementProperty.from_preset(preset)
        except Exception:
            pass
    return presets


def get_compositional_featurizers() -> Dict[str, BaseFeaturizer]:
    """Get all compositional featurizers."""
    return {
        'ElementFraction': ElementFraction(),
        'Stoichiometry': Stoichiometry(),
        'BandCenter': BandCenter(),
        'ValenceOrbital': ValenceOrbital(),
        'AtomicOrbitals': AtomicOrbitals(),
        'ElectronAffinity': ElectronAffinity(),
        'ElectronegativityDiff': ElectronegativityDiff(),
        'TMetalFraction': TMetalFraction(),
        'OxidationStates': OxidationStates(),
        'IonProperty': IonProperty(),
    }


def get_structural_featurizers() -> Dict[str, BaseFeaturizer]:
    """Get all structural featurizers."""
    return {
        'DensityFeatures': DensityFeatures(),
        'StructuralComplexity': StructuralComplexity(),
        'GlobalSymmetryFeatures': GlobalSymmetryFeatures(),
    }


def get_labels_cached(featurizer: BaseFeaturizer, featurizer_name: Optional[str] = None) -> List[str]:
    """Get feature labels from a featurizer with caching."""
    name = featurizer_name or featurizer.__class__.__name__

    if name not in _FEATURIZER_LABEL_CACHE:
        try:
            _FEATURIZER_LABEL_CACHE[name] = featurizer.feature_labels()
        except Exception:
            _FEATURIZER_LABEL_CACHE[name] = []

    return _FEATURIZER_LABEL_CACHE[name]


def is_composition_featurizer(featurizer: BaseFeaturizer) -> bool:
    """Check if a featurizer is for composition."""
    return "composition" in featurizer.__module__


def get_needed_featurizers(feature_list: List[str]) -> Dict[str, Tuple[BaseFeaturizer, List[str]]]:
    """
    Determine which featurizers are needed and which features to extract from each.
    
    Args:
        feature_list: List of desired feature names
        
    Returns:
        Dict mapping featurizer name to (featurizer_instance, needed_features_list)
    """
    needed = {}
    base_features = [f for f in feature_list if '/' not in f]
    
    # Check ElementProperty featurizers
    ep_featurizers = get_preset_elementproperty_featurizers()
    for preset_name, featurizer in ep_featurizers.items():
        labels = get_labels_cached(featurizer, f"ElementProperty_{preset_name}")
        common = [f for f in base_features if f in labels]
        if common:
            needed[f"ElementProperty_{preset_name}"] = (featurizer, common)
    
    # Check compositional featurizers
    comp_featurizers = get_compositional_featurizers()
    for featurizer_name, featurizer in comp_featurizers.items():
        labels = get_labels_cached(featurizer, featurizer_name)
        common = [f for f in base_features if f in labels]
        if common:
            needed[featurizer_name] = (featurizer, common)
    
    # Check structural featurizers
    struct_featurizers = get_structural_featurizers()
    for featurizer_name, featurizer in struct_featurizers.items():
        labels = get_labels_cached(featurizer, featurizer_name)
        common = [f for f in base_features if f in labels]
        if common:
            needed[featurizer_name] = (featurizer, common)
    
    return needed


def map_features_to_featurizers(feature_list: List[str]) -> Dict[BaseFeaturizer, List[str]]:
    """
    Map desired features to their source featurizers.
    Only instantiates and uses featurizers for which we need features.
    """
    mapping = {}
    needed_featurizers = get_needed_featurizers(feature_list)
    
    for featurizer_name, (featurizer, needed_features) in needed_featurizers.items():
        mapping[featurizer] = needed_features
    
    found = set(sum(mapping.values(), []))
    missing = set([f for f in feature_list if '/' not in f]) - found
    
    if missing:
        raise ValueError(f"Missing features not found: {missing}")
    
    return mapping


def handle_nan(values: List[float], strategy: str = "raise") -> List[float]:
    arr = np.array(values, dtype=float)

    if np.isnan(arr).any():
        if strategy == "raise":
            raise ValueError("NaN values encountered")
        elif strategy == "zero":
            arr = np.nan_to_num(arr)
        else:
            raise ValueError(f"Unknown NaN strategy: {strategy}")

    return arr.tolist()


def generate_base_features(structure, composition, feature_list, nan_strategy="raise") -> Dict[str, float]:
    """
    Generate base (raw) features from structure and composition using matminer featurizers.
    
    Args:
        structure: pymatgen Structure object
        composition: pymatgen Composition object
        feature_list: List of all features (including engineered feature names)
        nan_strategy: How to handle NaN values ("raise", "zero")
        
    Returns:
        Dict mapping feature names to their values
    """
    # Extract only base features (those without '/' in the name)
    base_features = [f for f in feature_list if '/' not in f]
    
    # Pre-fill special computed features with zeros (not from standard featurizers)
    special_features = {'LUMO_energy', 'HOMO_energy', 'gap_AO'}
    feature_values: Dict[str, float] = {f: 0.0 for f in base_features if f in special_features}
    
    # Get only the featurizers we actually need (excluding special features)
    features_to_generate = [f for f in feature_list if '/' not in f and f not in special_features]
    needed_featurizers = get_needed_featurizers(features_to_generate)
    
    for featurizer_name, (featurizer, needed_features) in needed_featurizers.items():
        try:
            # Get all labels from this featurizer
            labels = get_labels_cached(featurizer, featurizer_name)
            
            # Determine if this is a composition or structure featurizer
            is_composition_based = is_composition_featurizer(featurizer)
            
            # Featurize with error handling
            try:
                if is_composition_based:
                    # For composition-based featurizers, use featurize method
                    values = featurizer.featurize(composition)
                else:
                    # For structure-based featurizers, use featurize method
                    values = featurizer.featurize(structure)
            except Exception as e:
                # If featurization fails, log and continue with NaN values
                if nan_strategy == "raise":
                    raise
                else:
                    values = [np.nan] * len(labels)
            
            # Handle NaN values
            values = handle_nan(values, nan_strategy)
            
            # Map labels to values
            for label, val in zip(labels, values):
                # Only keep features we need
                if label in needed_features:
                    feature_values[label] = val
                    
        except Exception as e:
            if nan_strategy == "raise":
                raise ValueError(f"Error featurizing with {featurizer_name}: {str(e)}")
            else:
                # Log warning but continue with zero strategy
                pass

    # Verify all base features were generated
    missing = [f for f in base_features if f not in feature_values]
    if missing:
        raise ValueError(f"Missing base features after featurization: {missing}")

    return feature_values


def engineer_features(base_features: Dict[str, float], feature_list: List[str]) -> Dict[str, float]:
    """
    Generate engineered features by dividing one base feature by another.
    
    Engineered features are identified by having '/' in their name, e.g., "feature_a/feature_b"
    means divide feature_a by feature_b.
    
    Args:
        base_features: Dictionary of base feature values
        feature_list: List of all features (including engineered feature names)
        
    Returns:
        Combined dictionary with both base and engineered features
    """
    engineered_features = {f: None for f in feature_list if '/' in f}
    all_features = {**base_features}
    
    missing_engineered = []
    for feat_name in engineered_features:
        try:
            feature_a, feature_b = feat_name.split('/')
            
            # Skip if either feature is missing
            if feature_a not in base_features or feature_b not in base_features:
                missing_engineered.append(feat_name)
                # Use 0.0 as fallback for missing engineered features
                all_features[feat_name] = 0.0
                continue
            
            numerator = base_features[feature_a]
            denominator = base_features[feature_b]
            
            # Handle division by zero and NaN/Inf
            if denominator == 0:
                all_features[feat_name] = 1.0
            else:
                result = numerator / denominator
                if np.isnan(result) or np.isinf(result):
                    all_features[feat_name] = 0.0 if np.isnan(result) else (1.0 if result > 0 else 0.0)
                else:
                    all_features[feat_name] = float(result)
                    
        except Exception as e:
            # Fallback for any errors in engineering
            missing_engineered.append(feat_name)
            all_features[feat_name] = 0.0
    
    return all_features


def generate_features(structure, composition, feature_list, nan_strategy="raise"):
    """
    Generate all features (base + engineered) and return as scaled array.
    
    Args:
        structure: pymatgen Structure object
        composition: pymatgen Composition object
        feature_list: List of all features to generate (base + engineered)
        nan_strategy: How to handle NaN values
        
    Returns:
        np.ndarray: Feature values in the order specified by feature_list (1 x n_features)
    """
    # Generate base features
    base_features = generate_base_features(structure, composition, feature_list, nan_strategy)
    
    # Engineer derived features
    all_features = engineer_features(base_features, feature_list)
    
    # Extract features in the correct order
    feature_array = np.array([all_features[f] for f in feature_list]).reshape(1, -1)
    
    return feature_array


# ========================
# CLASS INTEGRATION
# ========================

class Gbfs2dPredictor(BasePredictor):
    """
    GBFS-2D: Property predictor for 2D layered materials using LightGBM models.
    
    This predictor extends GBFS with van der Waals structure detection to specifically
    target 2D layered materials (graphite, h-BN, TMDCs, metal halides, etc.).
    
    Predicts three properties:
    - is_stable: Structural stability classifier
    - is_metal: Metallic character classifier  
    - bandgap: Electronic band gap regressor (eV)
    
    Each property uses matminer features from composition and structure data.
    """
    
    def __init__(self, predictor_name: str, property_name: str = "bandgap", 
                 model_dir: Optional[str] = None, logger: Optional[Any] = None):
        """
        Initialize GBFS-2D predictor with pre-trained models and scalers.
        
        Args:
            predictor_name (str): Name of the predictor instance
            property_name (str): Name of property to predict
                Supported: 'bandgap', 'is_metal', 'is_stable'
                Default: 'bandgap'
            model_dir (str): Optional directory containing models. If None, defaults to 
                Information_Units/Predictors/Gbfs-2d/{property_name}/
            logger: Optional logger instance
            
        Raises:
            FileNotFoundError: If required model files are not found
            ValueError: If property_name is invalid or files are missing
        """
        super().__init__(predictor_name, logger)
        self.source = "gbfs-2d"
        
        self.property_name = property_name
        
        # Validate supported properties
        supported_properties = ['bandgap', 'is_metal', 'is_stable']
        if property_name not in supported_properties:
            raise ValueError(
                f"Unsupported property: {property_name}. "
                f"Supported: {', '.join(supported_properties)}"
            )
        
        # Determine model directory
        if model_dir is None:
            model_dir = os.path.join(
                os.path.dirname(__file__),
                f"{property_name}_2d"
            )
        
        self.model_dir = model_dir
        
        # Validate directory exists
        if not os.path.isdir(model_dir):
            raise ValueError(
                f"Model directory not found for property '{property_name}': {model_dir}\n"
                f"Supported properties: bandgap, is_metal, is_stable"
            )
        
        # Expected file paths (using property_2d naming convention)
        model_path = os.path.join(model_dir, f"{property_name}_2d_model.pkl")
        scaler_path = os.path.join(model_dir, f"{property_name}_2d_scaler.pkl")
        feature_list_path = os.path.join(model_dir, f"{property_name}_2d_features.pkl")
        
        # Validate all required files exist
        missing_files = []
        for file_path, file_type in [
            (model_path, "model"),
            (scaler_path, "scaler"),
            (feature_list_path, "features")
        ]:
            if not os.path.exists(file_path):
                missing_files.append(f"{file_type}: {file_path}")
        
        if missing_files:
            raise FileNotFoundError(
                f"Missing required files for property '{property_name}':\n" +
                "\n".join(f"  - {f}" for f in missing_files)
            )
        
        try:
            # Load model, scaler, and features
            self.model = load_joblib(model_path)
            self.scaler = load_joblib(scaler_path)
            
            # Load features - handle both list and DataFrame formats
            features_data = load_joblib(feature_list_path)
            if isinstance(features_data, pd.DataFrame):
                # Extract feature names from DataFrame 'feature' column
                self.feature_list = features_data['feature'].tolist()
            elif isinstance(features_data, pd.Series):
                # Convert Series to list
                self.feature_list = features_data.tolist()
            elif isinstance(features_data, (list, tuple)):
                self.feature_list = list(features_data)
            else:
                # Try to convert to list (e.g., numpy array)
                try:
                    self.feature_list = list(features_data)
                except Exception as e:
                    raise TypeError(
                        f"Unable to convert features data to list. "
                        f"Expected list/tuple/DataFrame/Series, got {type(features_data)}: {str(e)}"
                    )
        except (OSError, IOError) as e:
            raise FileNotFoundError(
                f"Error loading model files for property '{property_name}': {str(e)}"
            )
        except Exception as e:
            raise RuntimeError(
                f"Error initializing {property_name} predictor: {str(e)}"
            )
        
        if not self.feature_list:
            raise ValueError(
                f"Feature list is empty for property '{property_name}'. "
                f"Check feature file: {feature_list_path}"
            )
        
        if self.logger:
            self.logger.log(
                f"Initialized {property_name} predictor with {len(self.feature_list)} features",
                'info'
            )

    def info(self) -> str:
        """Return description of predictor capabilities."""
        return (
            f"GBFS-2D ({self.property_name}): Property predictor for 2D layered materials "
            f"using LightGBM models trained on van der Waals materials. "
            f"Detects structures from specific space groups (P6/mmc, R-3m, C2/m, etc.). "
            f"Uses matminer composition and structure featurizers to generate "
            f"{len(self.feature_list)} input features for property prediction. "
            f"Supported properties: bandgap (eV), is_metal (classification), "
            f"is_stable (classification)."
        )

    def predict(self, input_data) -> dict:  # type: ignore
        """
        Predict properties from crystal structure data.
        
        Expects direct list input:
        - list[str] of CIF contents
        
        Pipeline:
        1. Load structure from CIF string input
        2. Check if structure is van der Waals layered
        3. Extract composition from structure
        4. Generate base features using matminer featurizers
        5. Engineer features by dividing base features
        6. Maintain strict feature order (LGBM does not check feature names)
        7. Scale features using pre-trained scaler
        8. Generate predictions using pre-trained LGBM model
        
        Args:
            input_data: list[str]
                
        Returns:
            dict: standardized predictor envelope
        """
        if self.logger:
            self.logger.log(f"Running {self.property_name} prediction", 'info')

        structures = self._extract_structures(input_data)
        if not structures:
            return {
                "source": self.source,
                "results": [
                    {
                        "index": 0,
                        "status": "error",
                        "properties": {},
                        "warnings": [],
                        "error": "Missing or invalid input. Provide list[str] of CIF strings",
                    }
                ],
            }

        results = []
        for idx, structure in enumerate(structures):
            try:
                # Check vdW structure
                is_vdw = check_vdw_layered_structure(structure)
                warning = None if is_vdw else "Structure may not be van der Waals layered"
                
                properties = self._predict_structure(structure)
                properties['is_vdw_layered'] = is_vdw
                
                results.append(
                    {
                        "index": idx,
                        "status": "ok",
                        "properties": properties,
                        "warnings": [warning] if warning else [],
                        "error": None,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "index": idx,
                        "status": "error",
                        "properties": {},
                        "warnings": [],
                        "error": str(exc),
                    }
                )

        return {"source": self.source, "results": results}

    def _predict_structure(self, structure: Structure) -> Dict[str, Any]:
        """Run feature generation and prediction for a single structure."""
        composition = structure_to_composition(structure)

        # Generate base features
        features = generate_features(structure, composition, self.feature_list, nan_strategy="zero")

        if self.logger:
            base_count = sum(1 for f in self.feature_list if '/' not in f)
            eng_count = sum(1 for f in self.feature_list if '/' in f)
            self.logger.log(
                f"Generated {base_count} base + {eng_count} engineered features",
                'info'
            )

        # Scale features if scaler has transform method
        if hasattr(self.scaler, 'transform'):
            scaled = self.scaler.transform(features)
        else:
            # If no transform method (e.g., scaler is a model), use features directly
            scaled = features

        # Predict
        prediction = self.model.predict(scaled)

        result: Dict[str, Any] = {
            "property": self.property_name,
            "prediction": prediction.tolist(),
        }
        
        # Add probabilities for classifiers
        if hasattr(self.model, 'predict_proba'):
            try:
                probas = self.model.predict_proba(scaled)
                result["probabilities"] = probas.tolist()
            except Exception:
                pass
                
        return result

    def _extract_structures(self, inputs) -> List[Structure]:
        """Extract structures from direct list input."""
        structures: List[Structure] = []

        if isinstance(inputs, list):
            for cif_str in inputs:
                if not isinstance(cif_str, str) or not cif_str.strip():
                    continue
                parser = CifParser.from_str(cif_str)
                parsed = parser.get_structures(primitive=True)
                if parsed:
                    structures.append(parsed[0])
        return structures
    
    def predict_numpy(self, input_data) -> np.ndarray:
        """
        Predict properties and return raw numpy array.
        
        Expects direct list input:
        - list[str] of CIF contents
        
        Args:
            input_data: list[str]
            
        Returns:
            np.ndarray: Predicted property values from the LGBM model
        """
        structures = self._extract_structures(input_data)
        if not structures:
            raise ValueError("Missing or invalid input. Provide list[str] of CIF strings")
        structure = structures[0]
        
        composition = structure_to_composition(structure)
        features = generate_features(structure, composition, self.feature_list, nan_strategy="zero")
        
        # Scale features if scaler has transform method
        if hasattr(self.scaler, 'transform'):
            scaled = self.scaler.transform(features)
        else:
            # If no transform method (e.g., scaler is a model), use features directly
            scaled = features
        
        # Predict
        prediction = self.model.predict(scaled)
        
        return prediction


# ========================
# FASTAPI SERVER INTEGRATION
# ========================

# Supported properties and metadata
SUPPORTED_PROPERTIES = ["bandgap", "is_metal", "is_stable"]

PROPERTY_INFO = {
    "bandgap": {
        "label": "Band Gap",
        "unit": "eV",
        "type": "regression",
        "description": "Electronic band gap energy for 2D materials"
    },
    "is_metal": {
        "label": "Metal Classification",
        "unit": "boolean",
        "type": "classification",
        "description": "Whether the 2D material is metallic (1) or non-metallic (0)"
    },
    "is_stable": {
        "label": "Structural Stability",
        "unit": "boolean",
        "type": "classification",
        "description": "Whether the 2D material structure is dynamically stable (1) or unstable (0)"
    },
}


if FASTAPI_AVAILABLE:
    # Pydantic models for API
    class PredictRequest(BaseModel):
        """Parameters accepted by the /predict endpoint."""
        structure: Dict[str, Any] = Field(
            ...,
            description=(
                "Crystal structure as a JSON dictionary in pymatgen format. "
                "Can be obtained from a Structure object via json.dumps(s.as_dict())"
            ),
        )

    class PredictResponse(BaseModel):
        """Response from the /predict endpoint."""
        job_id: str = Field(..., description="Unique job identifier")
        property: str = Field(..., description="Property predicted")
        prediction: List[float] | float = Field(..., description="Predicted value(s)")
        probabilities: Optional[List[List[float]]] = Field(
            None, description="Class probabilities (for classifiers only)"
        )
        is_vdw_layered: bool = Field(..., description="Whether structure is vdW layered")
        unit: str = Field(..., description="Unit of the prediction")
        type: str = Field(..., description="Prediction type (regression or classification)")

    class HealthResponse(BaseModel):
        """Response from /health endpoint."""
        status: str
        service: str
        message: str

    class InfoResponse(BaseModel):
        """Response from /info endpoint."""
        name: str
        description: str
        version: str
        supported_properties: List[str]
        properties: Dict[str, Dict[str, str]]

    class BatchPredictRequest(BaseModel):
        """Parameters for batch prediction endpoint."""
        structure: Dict[str, Any] = Field(
            ...,
            description=(
                "Crystal structure as a JSON dictionary in pymatgen format. "
                "Can be obtained from a Structure object via json.dumps(s.as_dict())"
            ),
        )
        properties: Optional[List[str]] = Field(
            None,
            description=(
                "List of properties to predict. If not provided, predicts all supported properties. "
                f"Supported: {SUPPORTED_PROPERTIES}"
            ),
        )

    # Helper functions
    def _get_or_load_predictor(property_name: str) -> Gbfs2dPredictor:
        """Get a predictor from cache, or load it if not cached."""
        if property_name not in _API_PREDICTORS:
            _API_LOGGER.info(f"Loading {property_name} predictor...")
            _API_PREDICTORS[property_name] = Gbfs2dPredictor(
                predictor_name=property_name,
                property_name=property_name,
                model_dir=None,
                logger=None
            )
            _API_LOGGER.info(f"Loaded {property_name} predictor")
        return _API_PREDICTORS[property_name]

    def _structure_from_dict(struct_dict: Dict[str, Any]) -> Structure:
        """Load a Structure from a pymatgen JSON dictionary."""
        try:
            decoder = MontyDecoder()
            return decoder.process_decoded(struct_dict)
        except Exception as e:
            raise ValueError(f"Failed to deserialize structure: {str(e)}")

    def create_app() -> FastAPI:
        """Create and configure the FastAPI application for GBFS-2D."""
        app = FastAPI(
            title="GBFS-2D API",
            description="2D materials property prediction powered by GBFS-2D models",
            version="1.0.0",
        )

        @app.get("/health", response_model=HealthResponse)
        def health():
            """Liveness / readiness check."""
            _API_LOGGER.debug("Health check requested")
            return HealthResponse(
                status="ok",
                service="gbfs-2d",
                message="GBFS-2D service is operational"
            )

        @app.get("/info", response_model=InfoResponse)
        def info():
            """Return model metadata and supported properties."""
            _API_LOGGER.debug("Info endpoint requested")
            return InfoResponse(
                name="GBFS-2D",
                description=(
                    "Property predictor for 2D layered materials using LightGBM models. "
                    "Specialized for van der Waals materials including graphite, h-BN, TMDCs, "
                    "and metal halides. Automatically detects vdW structures."
                ),
                version="1.0.0",
                supported_properties=SUPPORTED_PROPERTIES,
                properties=PROPERTY_INFO,
            )

        @app.post("/predict/{property_name}", response_model=PredictResponse)
        def predict(property_name: str, request: PredictRequest):
            """Predict a material property from a crystal structure."""
            job_id = uuid.uuid4().hex[:12]
            
            if property_name not in SUPPORTED_PROPERTIES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown property: {property_name}. Supported: {', '.join(SUPPORTED_PROPERTIES)}"
                )
            
            _API_LOGGER.info(f"[{job_id}] Prediction request for {property_name}")
            
            try:
                structure = _structure_from_dict(request.structure)
                _API_LOGGER.debug(f"[{job_id}] Loaded structure: {structure.composition.reduced_formula}")
                
                # Check vdW structure
                is_vdw = check_vdw_layered_structure(structure)
                _API_LOGGER.debug(f"[{job_id}] vdW layered: {is_vdw}")
                
                predictor = _get_or_load_predictor(property_name)
                numpy_pred = predictor.predict_numpy([structure.to(fmt="cif")])
                
                probabilities = None
                if hasattr(predictor.model, 'predict_proba'):
                    try:
                        composition = structure.composition
                        features = generate_features(structure, composition, predictor.feature_list, nan_strategy="zero")
                        if hasattr(predictor.scaler, 'transform'):
                            scaled = predictor.scaler.transform(features)
                        else:
                            scaled = features
                        probas = predictor.model.predict_proba(scaled)
                        probabilities = probas.tolist()
                    except Exception as e:
                        _API_LOGGER.debug(f"[{job_id}] Could not get probabilities: {str(e)}")
                
                _API_LOGGER.info(f"[{job_id}] Prediction complete for {property_name}: {numpy_pred}")
                
                prop_info = PROPERTY_INFO[property_name]
                prediction_value = numpy_pred.tolist()
                
                if isinstance(prediction_value, list) and len(prediction_value) == 1:
                    prediction_value = prediction_value[0]
                
                return PredictResponse(
                    job_id=job_id,
                    property=property_name,
                    prediction=prediction_value,
                    probabilities=probabilities,
                    is_vdw_layered=is_vdw,
                    unit=prop_info["unit"],
                    type=prop_info["type"],
                )
                
            except ValueError as e:
                _API_LOGGER.error(f"[{job_id}] Validation error: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                _API_LOGGER.error(f"[{job_id}] Prediction failed: {str(e)}")
                _API_LOGGER.error(f"[{job_id}] Traceback: {traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

        @app.post("/batch-predict")
        def batch_predict(request: BatchPredictRequest):
            """Predict multiple properties for a single structure."""
            job_id = uuid.uuid4().hex[:12]
            
            structure_dict = request.structure
            properties = request.properties or SUPPORTED_PROPERTIES
            
            _API_LOGGER.info(f"[{job_id}] Batch prediction request for {len(properties)} properties")
            
            try:
                structure = _structure_from_dict(structure_dict)
                _API_LOGGER.debug(f"[{job_id}] Loaded structure: {structure.composition.reduced_formula}")
                
                # Check vdW structure
                is_vdw = check_vdw_layered_structure(structure)
                _API_LOGGER.debug(f"[{job_id}] vdW layered: {is_vdw}")
                
                results = {}
                for prop in properties:
                    if prop not in SUPPORTED_PROPERTIES:
                        _API_LOGGER.warning(f"[{job_id}] Skipping unsupported property: {prop}")
                        continue
                    
                    try:
                        predictor = _get_or_load_predictor(prop)
                        pred_result = predictor.predict_numpy([structure.to(fmt="cif")])
                        
                        prop_info = PROPERTY_INFO[prop]
                        prediction_value = pred_result.tolist()
                        
                        if isinstance(prediction_value, list) and len(prediction_value) == 1:
                            prediction_value = prediction_value[0]
                        
                        probabilities = None
                        if hasattr(predictor.model, 'predict_proba'):
                            try:
                                composition = structure.composition
                                features = generate_features(structure, composition, predictor.feature_list, nan_strategy="zero")
                                if hasattr(predictor.scaler, 'transform'):
                                    scaled = predictor.scaler.transform(features)
                                else:
                                    scaled = features
                                probas = predictor.model.predict_proba(scaled)
                                probabilities = probas.tolist()
                            except Exception as pe:
                                _API_LOGGER.debug(f"[{job_id}] Could not get probabilities for {prop}: {str(pe)}")
                        
                        results[prop] = {
                            "prediction": prediction_value,
                            "probabilities": probabilities,
                            "unit": prop_info["unit"],
                            "type": prop_info["type"],
                        }
                        
                    except Exception as e:
                        _API_LOGGER.error(f"[{job_id}] Failed to predict {prop}: {str(e)}")
                        results[prop] = {"error": str(e)}
                
                _API_LOGGER.info(f"[{job_id}] Batch prediction complete: {len(results)} properties")
                
                return {
                    "job_id": job_id,
                    "structure_formula": structure.composition.reduced_formula,
                    "is_vdw_layered": is_vdw,
                    "predictions": results,
                }
                
            except Exception as e:
                _API_LOGGER.error(f"[{job_id}] Batch prediction failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

        return app


# ========================
# CLI ENTRYPOINT
# ========================

def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="GBFS-2D Prediction Pipeline")
    
    # Server mode
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run as FastAPI server instead of CLI predictor"
    )
    
    # CLI mode
    parser.add_argument("--cif", default=None, help="Path to CIF structure file")
    parser.add_argument("--property", default="bandgap", 
                        help="Property to predict: bandgap, is_metal, is_stable")
    parser.add_argument("--model-dir", default=None,
                        help="Optional path to model directory. If not provided, uses default GBFS-2d/{property}/")
    
    # Server configuration
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--log-level", default="INFO", help="Logging level (default: INFO)")

    args = parser.parse_args()

    # Configure logging
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.serve:
        # Server mode
        if not FASTAPI_AVAILABLE:
            print("FastAPI not installed. Install with: pip install fastapi uvicorn")
            return
        
        print(f"\n{'='*60}")
        print(f"GBFS-2D API Server")
        print(f"{'='*60}")
        print(f"Starting on http://{args.host}:{args.port}")
        print(f"Docs available at http://{args.host}:{args.port}/docs")
        print(f"{'='*60}\n")
        
        import uvicorn
        app = create_app()
        uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level.lower())
    else:
        # CLI mode
        if not args.cif:
            print("Error: --cif required for CLI mode. Use --serve for server mode.")
            return
        
        try:
            structure = load_cif(args.cif)
            print(f"\nLoaded structure: {structure.composition.reduced_formula}")
            
            # Check vdW structure
            is_vdw = check_vdw_layered_structure(structure)
            print(f"vdW layered structure: {is_vdw}")
            
            # Run prediction
            predictor = Gbfs2dPredictor(
                predictor_name=args.property,
                property_name=args.property,
                model_dir=args.model_dir
            )
            
            result = predictor.predict([structure.to(fmt="cif")])
            print(f"\nPrediction results:")
            print(json.dumps(result, indent=2))
            
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
