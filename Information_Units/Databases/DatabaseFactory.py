from Information_Units.Databases.Icsd.IcsdDatabase import IcsdDatabase
from Information_Units.Databases.Cod.CodDatabase import CodDatabase
from Information_Units.Databases.Oqmd.OqmdDatabase import OqmdDatabase
from Information_Units.Databases.Aflowlib.AflowlibDatabase import AflowlibDatabase
from Information_Units.Databases.Materialsproject.MaterialsprojectDatabase import MaterialsprojectDatabase
from Information_Units.Databases.Alexandria.AlexandriaDatabase import AlexandriaDatabase
from Information_Units.Databases.Nomad.NomadDatabase import NomadDatabase
from Information_Units.Databases.Jarvis.JarvisDatabase import JarvisDatabase

database_factory = {
    "icsd": IcsdDatabase,
    "cod": CodDatabase,
    "oqmd": OqmdDatabase,
    "aflowlib": AflowlibDatabase,
    "materialsproject": MaterialsprojectDatabase,
    "alexandria": AlexandriaDatabase,
    "nomad": NomadDatabase,
    "jarvis": JarvisDatabase,
}

database_registry = {}