from Information_Units.Predictors.BasePredictor import BasePredictor

import os
import joblib
from typing import List, Tuple, Any, Dict, Optional

import numpy as np
import pandas as pd

from pymatgen.core import Structure, Composition
from pymatgen.io.cif import CifParser

from matminer.featurizers.base import BaseFeaturizer
from matminer.featurizers.composition import (
    ElementProperty, ElementFraction, Stoichiometry, BandCenter,
    ValenceOrbital, AtomicOrbitals, ElectronAffinity,
    ElectronegativityDiff, TMetalFraction, OxidationStates
)
from matminer.featurizers.structure import (
    DensityFeatures, StructuralComplexity, GlobalSymmetryFeatures
)

from sklearn.base import TransformerMixin

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
    
    # Get only the featurizers we actually need
    needed_featurizers = get_needed_featurizers(feature_list)
    
    feature_values: Dict[str, float] = {}

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
    
    for feat_name in engineered_features:
        try:
            feature_a, feature_b = feat_name.split('/')
            
            if feature_a not in base_features or feature_b not in base_features:
                raise ValueError(
                    f"Cannot engineer '{feat_name}': "
                    f"'{feature_a}' found={feature_a in base_features}, "
                    f"'{feature_b}' found={feature_b in base_features}"
                )
            
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
                    
        except ValueError as e:
            raise ValueError(f"Error engineering feature '{feat_name}': {str(e)}")
    
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

class GBFS_PredPredictor(BasePredictor):
    """
    GBFS-based property predictor using LightGBM models with matminer features.
    
    This predictor generates features from crystal structures using matminer,
    scales them using a pre-trained scaler, and makes predictions using a
    pre-trained LightGBM model. Feature order is strictly maintained as LGBM
    does not rely on feature names.
    """
    
    def __init__(self, predictor_name: str, model_path: str, scaler_path: str, 
                 feature_list_path: str, logger=None):
        """
        Initialize GBFS predictor with pre-trained models and scalers.
        
        Args:
            predictor_name (str): Name of the predictor instance
            model_path (str): Path to the pre-trained LGBM model (.pkl/.joblib)
            scaler_path (str): Path to the feature scaler object (.pkl/.joblib)
            feature_list_path (str): Path to the list of features to generate (.pkl/.joblib)
                Can be either a list of feature names or a DataFrame with 'feature' column
            logger: Optional logger instance
        """
        super().__init__(predictor_name, logger)

        self.model = load_joblib(model_path)
        self.scaler = load_joblib(scaler_path)
        
        # Load features - handle both list and DataFrame formats
        features_data = load_joblib(feature_list_path)
        if isinstance(features_data, pd.DataFrame):
            # Extract feature names from DataFrame 'feature' column
            self.feature_list = features_data['feature'].tolist()
        elif isinstance(features_data, (list, tuple)):
            self.feature_list = list(features_data)
        else:
            # Try to convert to list (e.g., numpy array)
            self.feature_list = list(features_data)

    def info(self) -> str:
        """Return description of predictor capabilities."""
        return (
            "GBFS_Pred: Light Gradient Boosting Machine (LGBM) predictor trained on "
            "GBFS workflow data. Uses matminer composition and structure featurizers "
            "to generate input features for property prediction."
        )

    def predict(self, inputs) -> str:  # type: ignore
        """
        Predict properties from a CIF crystal structure file.
        
        This method overrides the base class to accept CIF file paths instead of dicts.
        
        Pipeline:
        1. Load CIF file and parse structure
        2. Extract composition and structure objects
        3. Generate base features using matminer featurizers
        4. Engineer features by dividing base features (e.g., "feature_a/feature_b")
        5. Maintain strict feature order (LGBM does not check feature names)
        6. Scale features using pre-trained scaler
        7. Generate predictions using pre-trained LGBM model
        
        Args:
            inputs: Path to a CIF crystal structure file (str) or dict with 'cif_path' key
            
        Returns:
            str: JSON string representation of predicted property values
            
        Raises:
            FileNotFoundError: If CIF file does not exist
            ValueError: If no structures found or missing features cannot be generated
        """
        # Handle both string paths and dict inputs
        if isinstance(inputs, dict):
            input_data = inputs.get('cif_path', inputs.get('input_data'))
        else:
            input_data = str(inputs)
        
        if not input_data:
            raise ValueError("No CIF file path provided")
            
        if self.logger:
            self.logger.log("Running GBFS prediction", 'info')

        structure = load_cif(input_data)
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
        
        # Scale features
        scaled = self.scaler.transform(features)
        
        # Predict
        prediction = self.model.predict(scaled)
        
        # Return as JSON string for base class compatibility
        import json
        return json.dumps({"prediction": prediction.tolist()})
    
    def predict_numpy(self, input_data: str) -> np.ndarray:
        """
        Predict properties and return raw numpy array.
        
        Args:
            input_data (str): Path to a CIF crystal structure file
            
        Returns:
            np.ndarray: Predicted property values from the LGBM model
        """
        structure = load_cif(input_data)
        composition = structure_to_composition(structure)
        features = generate_features(structure, composition, self.feature_list, nan_strategy="zero")
        scaled = self.scaler.transform(features)
        prediction = self.model.predict(scaled)
        return prediction


# -----------------------------
# CLI ENTRYPOINT
# -----------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="GBFS Prediction Pipeline")
    parser.add_argument("--cif", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--scaler", required=True)
    parser.add_argument("--features", required=True)

    args = parser.parse_args()

    predictor = GBFS_PredPredictor(
        predictor_name="gbfs",
        model_path=args.model,
        scaler_path=args.scaler,
        feature_list_path=args.features
    )

    pred = predictor.predict(args.cif)
    print(pred)


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
ENTRYPOINT ["python", "-m", "Information_Units.Predictors.GBFS_Pred.GBFS_PredPredictor"]

# Usage:
# docker run -v $(pwd)/models:/models predictor:latest \
#   --cif /models/sample.cif \
#   --model /models/bandgap_model.pkl \
#   --scaler /models/bandgap_scaler.pkl \
#   --features /models/bandgap_features.pkl
"""
