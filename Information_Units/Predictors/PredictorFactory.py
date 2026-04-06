from Information_Units.Predictors.Mattersim.MattersimPredictor import MattersimPredictor
from Information_Units.Predictors.M3gnet.M3gnetPredictor import M3gnetPredictor
from Information_Units.Predictors.Pfp.PfpPredictor import PfpPredictor
from Information_Units.Predictors.Deepmd.DeepmdPredictor import DeepmdPredictor
from Information_Units.Predictors.Synthnn.SynthnnPredictor import SynthnnPredictor
from Information_Units.Predictors.Esen.EsenPredictor import EsenPredictor
from Information_Units.Predictors.Mypred1.Mypred1Predictor import Mypred1Predictor
from Information_Units.Predictors.Mypred2.Mypred2Predictor import Mypred2Predictor
from Information_Units.Predictors.Gbfs.GbfsPredictor import GbfsPredictor

predictor_factory = {
    "mattersim": MattersimPredictor,
    "m3gnet": M3gnetPredictor,
    "pfp": PfpPredictor,
    "deepmd": DeepmdPredictor,
    "synthnn": SynthnnPredictor,
    "esen": EsenPredictor,
    "mypred1": Mypred1Predictor,
    "mypred2": Mypred2Predictor,
    "gbfs": GbfsPredictor,
}

predictor_registry = {}