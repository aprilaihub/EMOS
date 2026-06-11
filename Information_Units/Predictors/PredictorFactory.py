from Information_Units.Predictors.Mattersim.MattersimPredictor import MattersimPredictor
from Information_Units.Predictors.Synthnn.SynthnnPredictor import SynthnnPredictor
from Information_Units.Predictors.AMD.AMDPredictor import AMDPredictor
from Information_Units.Predictors.Gbfs.GbfsPredictor import GbfsPredictor
from Information_Units.Predictors.Gbfs2d.Gbfs2dPredictor import Gbfs2dPredictor

predictor_factory = {
    "mattersim": MattersimPredictor,
    "synthnn": SynthnnPredictor,
    "amd": AMDPredictor,
    "gbfs": GbfsPredictor,
    "gbfs_2d": Gbfs2dPredictor,
}

predictor_registry = {}