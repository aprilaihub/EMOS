from Information_Units.Predictors.Mattersim.MattersimPredictor import MattersimPredictor
from Information_Units.Predictors.Synthnn.SynthnnPredictor import SynthnnPredictor
from Information_Units.Predictors.Gbfs.GbfsPredictor import GbfsPredictor

predictor_factory = {
    "mattersim": MattersimPredictor,
    "synthnn": SynthnnPredictor,
    "gbfs": GbfsPredictor,
}

predictor_registry = {}