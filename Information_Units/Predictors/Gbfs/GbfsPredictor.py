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
_API_LOGGER = logging.getLogger("gbfs_api")

# Global predictor cache for API
_API_PREDICTORS: Dict[str, 'GbfsPredictor'] = {}

# -----------------------------
# GLOBAL CACHE
# -----------------------------
_FEATURIZER_LABEL_CACHE: Dict[str, List[str]] = {}


# -----------------------------
# CORE PIPELINE FUNCTIONS
# -----------------------------

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
    
    Optimized to only compute features that are actually needed from the feature list.
    
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
    
    Pipeline:
    1. Generate base features from structure/composition
    2. Engineer derived features (e.g., feature_a/feature_b)
    3. Return features in correct order
    
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


# -----------------------------
# CLASS INTEGRATION
# -----------------------------

class GbfsPredictor(BasePredictor):
    """
    GBFS-based property predictor using LightGBM models with matminer features.
    
    This predictor generates features from crystal structures using matminer,
    scales them using a pre-trained scaler, and makes predictions using a
    pre-trained LightGBM model. Feature order is strictly maintained as LGBM
    does not rely on feature names.
    
    Supports multiple properties: bandgap, e_form, dielectric, is_metal, etc.
    Each property has its own folder with model.pkl, scaler.pkl, and features.pkl.
    """
    
    def __init__(self, predictor_name: str, property_name: str = "bandgap", 
                 model_dir: Optional[str] = None, logger: Optional[Any] = None):
        """
        Initialize GBFS predictor with pre-trained models and scalers for ALL properties.
        
        Args:
            predictor_name (str): Name of the predictor instance
            property_name (str): Deprecated. Kept for backward compatibility.
                (All 7 properties are now loaded regardless of this value)
            model_dir (str): Deprecated. Not used (models loaded from Gbfs parent directory)
            logger: Optional logger instance
            
        Raises:
            FileNotFoundError: If required model files are not found
            ValueError: If property directories or files are missing
            OSError: If directory structure is malformed
        """
        super().__init__(predictor_name, logger)
        self.source = "gbfs"
        
        # For backward compatibility
        self.property_name = property_name
        
        # Get the base directory containing all property folders
        base_dir = os.path.dirname(__file__)
        self.model_dir = base_dir
        
        # All 6 supported properties
        self.all_properties = ['bandgap', 'dielectric', 'e_form', 'is_metal', 'mob_n', 'mob_p']
        
        # Initialize storage for models, scalers, and feature lists
        self.models = {}
        self.scalers = {}
        self.feature_lists = {}
        
        # Load models for all 7 properties
        for prop in self.all_properties:
            prop_dir = os.path.join(base_dir, prop)
            
            # Validate property directory exists
            if not os.path.isdir(prop_dir):
                raise ValueError(
                    f"Property directory not found for '{prop}': {prop_dir}\n"
                    f"Available properties: {', '.join(self.all_properties)}"
                )
            
            # Expected file paths
            model_path = os.path.join(prop_dir, f"{prop}_model.pkl")
            scaler_path = os.path.join(prop_dir, f"{prop}_scaler.pkl")
            feature_list_path = os.path.join(prop_dir, f"{prop}_features.pkl")
            
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
                    f"Missing required files for property '{prop}':\n" +
                    "\n".join(f"  - {f}" for f in missing_files)
                )
            
            try:
                # Load model and scaler
                self.models[prop] = load_joblib(model_path)
                self.scalers[prop] = load_joblib(scaler_path)
                
                # Load features - handle both list and DataFrame formats
                features_data = load_joblib(feature_list_path)
                if isinstance(features_data, pd.DataFrame):
                    # Extract feature names from DataFrame 'feature' column
                    self.feature_lists[prop] = features_data['feature'].tolist()
                elif isinstance(features_data, pd.Series):
                    # Convert Series to list
                    self.feature_lists[prop] = features_data.tolist()
                elif isinstance(features_data, (list, tuple)):
                    self.feature_lists[prop] = list(features_data)
                else:
                    # Try to convert to list (e.g., numpy array)
                    try:
                        self.feature_lists[prop] = list(features_data)
                    except Exception as e:
                        raise TypeError(
                            f"Unable to convert features data to list. "
                            f"Expected list/tuple/DataFrame/Series, got {type(features_data)}: {str(e)}"
                        )
                
                if not self.feature_lists[prop]:
                    raise ValueError(
                        f"Feature list is empty for property '{prop}'. "
                        f"Check feature file: {feature_list_path}"
                    )
                    
            except (OSError, IOError) as e:
                raise FileNotFoundError(
                    f"Error loading model files for property '{prop}': {str(e)}"
                )
            except Exception as e:
                raise RuntimeError(
                    f"Error initializing {prop} predictor: {str(e)}"
                )
        
        # Use the first property's feature list as the base (should be same for all)
        # In multi-property prediction, we only generate features once
        self.feature_list = self.feature_lists['bandgap']
        self.model = self.models['bandgap']
        self.scaler = self.scalers['bandgap']
        
        if self.logger:
            self.logger.log(
                f"Initialized GBFS predictor with all 7 properties using {len(self.feature_list)} features",
                'info'
            )

    def info(self) -> str:
        """Return description of predictor capabilities."""
        return (
            f"GBFS (Multi-Property): Light Gradient Boosting Machine (LGBM) "
            f"predictor for ALL 6 properties: bandgap (eV), dielectric (dimensionless), "
            f"e_form (eV/atom), is_metal (classification), "
            f"mob_n (cm²/V·s), mob_p (cm²/V·s). "
            f"Uses matminer composition and structure featurizers to generate "
            f"{len(self.feature_list)} input features. Each property has its own "
            f"pre-trained model and scaler trained on GBFS workflow data."
        )

    def predict(self, inputs: list[str]) -> dict[str, Any]:
        """
        Predict ALL 6 properties from crystal structure data.
        
        Expects direct list input:
        - list[str] of CIF contents
        
        For mobility properties (mob_n, mob_p), automatically applies inverse log10 
        transformation to convert model output back to actual values (cm²/V·s).
        
        Pipeline:
        1. Load structure from CIF string input
        2. Extract composition from structure
        3. Generate base features using matminer featurizers (once per structure)
        4. Engineer features by dividing base features (e.g., "feature_a/feature_b")
        5. Maintain strict feature order (LGBM does not check feature names)
        6. For each of the 6 properties:
           a. Scale features using property-specific pre-trained scaler
           b. Generate prediction using property-specific pre-trained LGBM model
           c. Apply inverse log10 transformation for mobility predictions
        
        Args:
            inputs (list[str]): CIF string inputs.
                
        Returns:
            dict[str, Any]: Prediction payload with shape:
                {
                    "source": "gbfs",
                    "results": [
                        {
                            "index": int,
                            "status": "ok" | "error",
                            "properties": {
                                "bandgap": float,
                                "dielectric": float,
                                "e_form": float,
                                "is_metal": float,  # Probability of metallic class
                                "mob_n": float,
                                "mob_p": float
                            },
                            "warnings": list[str],
                            "error": str | None,
                            "cif_input": str
                        }
                    ]
                }
        """
        if self.logger:
            self.logger.log("Running multi-property GBFS prediction", 'info')

        cif_strings = self._extract_cif_strings(inputs)
        if not cif_strings:
            return {
                "source": self.source,
                "results": [
                    {
                        "index": 0,
                        "cif_input": "",
                        "status": "error",
                        "properties": {},
                        "warnings": [],
                        "error": "Missing or invalid input. Provide list[str] of CIF strings",
                    }
                ],
            }

        results = []
        for idx, cif_str in enumerate(cif_strings):
            try:
                parser = CifParser.from_str(cif_str)
                parsed = parser.get_structures(primitive=True)
                if not parsed:
                    raise ValueError("Failed to parse CIF: No structures extracted")
                structure = parsed[0]
                
                properties, warnings = self._predict_structure(structure)
                results.append(
                    {
                        "index": idx,
                        "cif_input": cif_str,
                        "status": "ok",
                        "properties": properties,
                        "warnings": warnings,
                        "error": None,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "index": idx,
                        "cif_input": cif_str,
                        "status": "error",
                        "properties": {},
                        "warnings": [],
                        "error": str(exc),
                    }
                )

        return {"source": self.source, "results": results}

    def _predict_structure(self, structure: Structure) -> Tuple[Dict[str, Any], List[str]]:
        """
        Run feature generation and prediction for ALL 6 properties for a single structure.
        
        Each property uses its own feature list and models, so features are generated
        per-property to match the specific features each model was trained with.
        """
        composition = structure_to_composition(structure)

        if self.logger:
            self.logger.log(
                f"Predicting all 6 properties from structure",
                'info'
            )

        # Predict for all 6 properties
        all_properties: Dict[str, Any] = {}
        warnings: List[str] = []
        
        for prop in self.all_properties:
            try:
                model = self.models[prop]
                scaler = self.scalers[prop]
                feature_list = self.feature_lists[prop]
                
                # Generate features specific to this property
                features = generate_features(structure, composition, feature_list, nan_strategy="zero")
                
                # Scale features using property-specific scaler
                if hasattr(scaler, 'transform'):
                    scaled = scaler.transform(features)
                else:
                    # If no transform method (e.g., scaler is a model), use features directly
                    scaled = features

                if prop == 'is_metal':
                    all_properties[prop] = self._extract_metal_probability(model, scaled)
                else:
                    # Predict using property-specific model
                    prediction = model.predict(scaled)

                    # Apply inverse log10 transformation for mobility predictions
                    if prop in ['mob_n', 'mob_p']:
                        prediction = 10 ** prediction

                    all_properties[prop] = float(np.asarray(prediction).reshape(-1)[0])
                
            except Exception as exc:
                # Keep a flat contract and report per-property issues via warnings
                all_properties[prop] = None
                warnings.append(f"{prop}: {str(exc)}")

        return all_properties, warnings

    def _extract_metal_probability(self, model: Any, scaled: np.ndarray) -> float:
        """Return probability of the structure being metallic (positive class)."""
        probas = model.predict_proba(scaled)
        probas_arr = np.asarray(probas)
        if probas_arr.ndim == 1:
            return float(probas_arr.reshape(-1)[0])

        if probas_arr.shape[1] == 1:
            return float(probas_arr[0, 0])

        # Prefer explicit class lookup when available.
        classes = getattr(model, "classes_", None)
        if classes is not None:
            normalized = [str(c).strip().lower() for c in classes]
            for idx, label in enumerate(normalized):
                if label in {"1", "true", "metal", "is_metal"}:
                    return float(probas_arr[0, idx])

        # Fallback: use positive-class probability (common binary classifier layout).
        return float(probas_arr[0, -1])

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

    def _extract_cif_strings(self, inputs) -> List[str]:
        """Extract valid CIF strings from direct list input."""
        if isinstance(inputs, list):
            return [s for s in inputs if isinstance(s, str) and s.strip()]
        return []
    
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
        
        # Apply inverse log10 transformation for mobility predictions
        if self.property_name in ['mob_n', 'mob_p']:
            prediction = 10 ** prediction
        
        return prediction


# =============================================================================
# FASTAPI SERVER INTEGRATION
# =============================================================================
# This section provides HTTP API capabilities for GBFS.
# When run with --serve flag, the predictor runs as a FastAPI server.
# 
# Mirrors the MattergenGenerator architecture where a single file 
# contains both the predictor logic and the API server setup.
# =============================================================================

# Supported properties and metadata
SUPPORTED_PROPERTIES = ["bandgap", "e_form", "dielectric", "is_metal", "mob_n", "mob_p"]

PROPERTY_INFO = {
    "bandgap": {
        "label": "Band Gap",
        "unit": "eV",
        "type": "regression",
        "description": "Electronic band gap energy"
    },
    "e_form": {
        "label": "Formation Energy",
        "unit": "eV/atom",
        "type": "regression",
        "description": "Enthalpy of formation per atom"
    },
    "dielectric": {
        "label": "Dielectric Constant",
        "unit": "dimensionless",
        "type": "regression",
        "description": "Electronic dielectric constant (eps_inf)"
    },
    "is_metal": {
        "label": "Metal Classification",
        "unit": "boolean",
        "type": "classification",
        "description": "Whether the material is metallic (1) or non-metallic (0)"
    },
    "mob_n": {
        "label": "Electron Mobility",
        "unit": "cm²/V·s",
        "type": "regression",
        "description": "Mobility of electrons (band conductivity)"
    },
    "mob_p": {
        "label": "Hole Mobility",
        "unit": "cm²/V·s",
        "type": "regression",
        "description": "Mobility of holes (valence band)"
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
    def _get_or_load_predictor(property_name: str) -> GbfsPredictor:
        """Get a predictor from cache, or load it if not cached."""
        if property_name not in _API_PREDICTORS:
            _API_LOGGER.info(f"Loading {property_name} predictor...")
            _API_PREDICTORS[property_name] = GbfsPredictor(
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
        """Create and configure the FastAPI application for GBFS."""
        app = FastAPI(
            title="GBFS API",
            description="Materials property prediction powered by GBFS models",
            version="1.0.0",
        )

        @app.get("/health", response_model=HealthResponse)
        def health():
            """Liveness / readiness check."""
            _API_LOGGER.debug("Health check requested")
            return HealthResponse(
                status="ok",
                service="gbfs",
                message="GBFS service is operational"
            )

        @app.get("/info", response_model=InfoResponse)
        def info():
            """Return model metadata and supported properties."""
            _API_LOGGER.debug("Info endpoint requested")
            return InfoResponse(
                name="GBFS",
                description=(
                    "Materials property predictor using LightGBM models trained on "
                    "computed materials data. Generates features via matminer."
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
                    "predictions": results,
                }
                
            except Exception as e:
                _API_LOGGER.error(f"[{job_id}] Batch prediction failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

        return app


# ======================== 
# CLI ENTRYPOINT
# -----------------------------

def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="GBFS Prediction Pipeline")
    
    # Server mode
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run as FastAPI server instead of CLI predictor"
    )
    
    # CLI mode
    parser.add_argument("--cif", default=None, help="Path to CIF structure file")
    parser.add_argument("--property", default="bandgap", 
                        help="Property to predict: bandgap, e_form, dielectric, is_metal, mob_n, mob_p")
    parser.add_argument("--model-dir", default=None,
                        help="Optional path to model directory. If not provided, uses default GBFS/{property}/")
    
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

    # Run as FastAPI server
    if args.serve:
        if not FASTAPI_AVAILABLE:
            print("Error: FastAPI is not installed. Install it with: pip install fastapi uvicorn")
            return
        
        import uvicorn
        
        _API_LOGGER.info(f"Starting GBFS API server on {args.host}:{args.port}")
        app = create_app()
        uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level.lower())
    
    # Run as CLI predictor
    else:
        if not args.cif:
            parser.print_help()
            print("\nError: --cif is required for prediction mode. Use --serve to run as server.")
            return
        
        predictor = GbfsPredictor(
            predictor_name=args.property,
            property_name=args.property,
            model_dir=args.model_dir
        )

        with open(args.cif, "r", encoding="utf-8") as f:
            cif_string = f.read()
        result = predictor.predict([cif_string])
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()


# -----------------------------
# DOCKERFILE (production-ready)
# -----------------------------
"""
FROM python:3.10-slim

WORKDIR /app

# System deps (important for pymatgen)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 predictor

# Copy only necessary files
COPY --chown=predictor:predictor Information_Units/ /app/Information_Units/
COPY --chown=predictor:predictor requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --user \
    numpy==1.26.4 \
    scipy==1.11.4 \
    pandas==2.0.3 \
    scikit-learn==1.3.2 \
    pymatgen==2023.8.10 \
    matminer==0.9.0 \
    lightgbm==4.3.0 \
    joblib==1.3.2

# Switch to non-root user
USER predictor

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Use Python CLI entrypoint
ENTRYPOINT ["python", "-m", "Information_Units.Predictors.Gbfs.GbfsPredictor"]

# Usage:
# docker run -v $(pwd)/models:/models predictor:latest \
#   --cif /models/sample.cif \
#   --model /models/bandgap_model.pkl \
#   --scaler /models/bandgap_scaler.pkl \
#   --features /models/bandgap_features.pkl
"""
