from Information_Units.Databases.Cod.CodDatabase import CodDatabase
from Information_Units.Databases.Materialsproject.MaterialsprojectDatabase import MaterialsprojectDatabase
from Information_Units.Databases.Alexandria.AlexandriaDatabase import AlexandriaDatabase
from Information_Units.Databases.Mathub3d.Mathub3dDatabase import Mathub3dDatabase
from Information_Units.Databases.Jarvisdft.JarvisdftDatabase import JarvisdftDatabase
from Information_Units.Databases.Aflow.AflowDatabase import AflowDatabase

database_factory = {
    "cod": CodDatabase,
    "materialsproject": MaterialsprojectDatabase,
    "alexandria": AlexandriaDatabase,
    "mathub3d": Mathub3dDatabase,
    "jarvisdft": JarvisdftDatabase,
    "aflow": AflowDatabase,
}

database_registry = {}