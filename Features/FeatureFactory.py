# Import all feature classes
from Features.Materials_Exploration.MaterialSearch.MaterialSearchFeature import MaterialSearchFeature
from Features.Materials_Exploration.MaterialGeneration.MaterialGenerationFeature import MaterialGenerationFeature
from Features.Materials_Exploration.DatabaseExtractor.DatabaseExtractorFeature import DatabaseExtractorFeature
from Features.Materials_Exploration.MaterialCharacterization.MaterialCharacterizationFeature import MaterialCharacterizationFeature
from Features.Materials_Exploration.DftCalculation.DftCalculationFeature import DftCalculationFeature
from Features.Materials_Exploration.CrystallographicAnalysis.CrystallographicAnalysisFeature import CrystallographicAnalysisFeature
from Features.Materials_Exploration.QuantumMechanics.QuantumMechanicsFeature import QuantumMechanicsFeature
from Features.Materials_Exploration.TensorAnalysis.TensorAnalysisFeature import TensorAnalysisFeature

from Features.Electronics_Application.DeviceSynthesizability.DeviceSynthesizabilityFeature import DeviceSynthesizabilityFeature
from Features.Electronics_Application.InterfaceCalculation.InterfaceCalculationFeature import InterfaceCalculationFeature
from Features.Electronics_Application.PropertyPrediction.PropertyPredictionFeature import PropertyPredictionFeature
from Features.Electronics_Application.BandStructure.BandStructureFeature import BandStructureFeature
from Features.Electronics_Application.ThermalManagement.ThermalManagementFeature import ThermalManagementFeature
from Features.Electronics_Application.ReliabilityAssessment.ReliabilityAssessmentFeature import ReliabilityAssessmentFeature
from Features.Electronics_Application.ProcessIntegration.ProcessIntegrationFeature import ProcessIntegrationFeature
from Features.Electronics_Application.AdvancedCharacterization.AdvancedCharacterizationFeature import AdvancedCharacterizationFeature


# Feature registry - simple mapping like Information Units
feature_factory = {
    "1": MaterialSearchFeature,
    "2": MaterialGenerationFeature,
    "3": DatabaseExtractorFeature,
    "4": MaterialCharacterizationFeature,
    "5": DftCalculationFeature,
    "6": CrystallographicAnalysisFeature,
    "7": QuantumMechanicsFeature,
    "8": TensorAnalysisFeature,
    "9": DeviceSynthesizabilityFeature,
    "10": InterfaceCalculationFeature,
    "11": PropertyPredictionFeature,
    "12": BandStructureFeature,
    "13": ThermalManagementFeature,
    "14": ReliabilityAssessmentFeature,
    "15": ProcessIntegrationFeature,
    "16": AdvancedCharacterizationFeature

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