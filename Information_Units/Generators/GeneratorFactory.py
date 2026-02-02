from Information_Units.Generators.Mattergen.MattergenGenerator import MattergenGenerator
from Information_Units.Generators.Gnome.GnomeGenerator import GnomeGenerator
from Information_Units.Generators.Imatgen.ImatgenGenerator import ImatgenGenerator
from Information_Units.Generators.Matgan.MatganGenerator import MatganGenerator
from Information_Units.Generators.Molgan.MolganGenerator import MolganGenerator
from Information_Units.Generators.Conddfcvae.ConddfcvaeGenerator import ConddfcvaeGenerator
from Information_Units.Generators.Mygen1.Mygen1Generator import Mygen1Generator
from Information_Units.Generators.Mygen2.Mygen2Generator import Mygen2Generator

generator_factory = {
    "mattergen": MattergenGenerator,
    "gnome": GnomeGenerator,
    "imatgen": ImatgenGenerator,
    "matgan": MatganGenerator,
    "molgan": MolganGenerator,
    "conddfcvae": ConddfcvaeGenerator,
    "mygen1": Mygen1Generator,
    "mygen2": Mygen2Generator,
}

generator_registry = {}

