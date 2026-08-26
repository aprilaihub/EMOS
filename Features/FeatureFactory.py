# Import all feature classes

from Features.Materials_Exploration.DatabaseExtractor.DatabaseExtractorFeature import DatabaseExtractorFeature
from Features.Materials_Exploration.StabilityConsensusAnalysis.StabilityConsensusAnalysisFeature import StabilityConsensusAnalysisFeature
from Features.Materials_Exploration.AmdScreening.AmdScreeningFeature import AmdScreeningFeature
from Features.Electronics_Application.MosfetEvaluator.MosfetEvaluatorFeature import MosfetEvaluatorFeature
from Features.Materials_Exploration.CifSimilarity.CifSimilarityFeature import CifSimilarityFeature


# Feature registry - simple mapping like Information Units
feature_factory = {
    "1": DatabaseExtractorFeature,
    "2": StabilityConsensusAnalysisFeature,
    "3": AmdScreeningFeature,
    "4": CifSimilarityFeature,
    "5": MosfetEvaluatorFeature

}


def create_feature(feature_id, logger=None):
    """Create a feature instance by ID - simple like Information Units"""
    if feature_id not in feature_factory:
        raise ValueError(f"Feature {feature_id} not found in factory")
    
    feature_class = feature_factory[feature_id]
    return feature_class(logger)


def get_available_features():
    """Get list of available feature IDs"""
    return list(feature_factory.keys())


def get_feature_info(feature_id):
    """Get info about a specific feature"""
    if feature_id not in feature_factory:
        return None
    
    feature_class = feature_factory[feature_id]
    # Create temporary instance to get info (logger=None is default)
    temp_feature = feature_class(logger=None)
    return temp_feature.info()