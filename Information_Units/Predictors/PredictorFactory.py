from Information_Units.Predictors.Mattersim.MattersimPredictor import MattersimPredictor
from Information_Units.Predictors.Synthnn.SynthnnPredictor import SynthnnPredictor
from Information_Units.Predictors.Chgnet.ChgnetPredictor import ChgnetPredictor
from Information_Units.Predictors.Gbfs.GbfsClient import GbfsClient
from Information_Units.Predictors.Gbfs2d.Gbfs2dClient import Gbfs2dClient

predictor_factory = {
    "mattersim": MattersimPredictor,
    "synthnn": SynthnnPredictor,
    "chgnet": ChgnetPredictor,
    "gbfs": GbfsClient,
    "gbfs_2d": Gbfs2dClient,
}

predictor_registry = {}