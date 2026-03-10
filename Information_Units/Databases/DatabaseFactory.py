from Information_Units.Databases.Cod.CodDatabase import CodDatabase
from Information_Units.Databases.Materialsproject.MaterialsprojectDatabase import MaterialsprojectDatabase
from Information_Units.Databases.Alexandria.AlexandriaDatabase import AlexandriaDatabase

database_factory = {
    "cod": CodDatabase,
    "materialsproject": MaterialsprojectDatabase,
    "alexandria": AlexandriaDatabase,
}

database_registry = {}