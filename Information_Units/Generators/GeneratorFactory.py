from Information_Units.Generators.Gnome.GnomeGenerator import GnomeGenerator
from Information_Units.Generators.Imatgen.ImatgenGenerator import ImatgenGenerator
from Information_Units.Generators.Matgan.MatganGenerator import MatganGenerator
from Information_Units.Generators.Molgan.MolganGenerator import MolganGenerator
from Information_Units.Generators.Conddfcvae.ConddfcvaeGenerator import ConddfcvaeGenerator
from Information_Units.Generators.Mygen1.Mygen1Generator import Mygen1Generator
from Information_Units.Generators.Mygen2.Mygen2Generator import Mygen2Generator
from Information_Units.Generators.MattergenBaseModel.MattergenBaseModelGenerator import MattergenBaseModelGenerator
from Information_Units.Generators.MattergenMp20Base.MattergenMp20BaseGenerator import MattergenMp20BaseGenerator
from Information_Units.Generators.MattergenChemicalSystem.MattergenChemicalSystemGenerator import MattergenChemicalSystemGenerator
from Information_Units.Generators.MattergenChemicalSystemStability.MattergenChemicalSystemStabilityGenerator import MattergenChemicalSystemStabilityGenerator
from Information_Units.Generators.MattergenDftBandGap.MattergenDftBandGapGenerator import MattergenDftBandGapGenerator
from Information_Units.Generators.MattergenMagneticDensity.MattergenMagneticDensityGenerator import MattergenMagneticDensityGenerator
from Information_Units.Generators.MattergenMagneticDensityHhi.MattergenMagneticDensityHhiGenerator import MattergenMagneticDensityHhiGenerator
from Information_Units.Generators.MattergenBulkModulus.MattergenBulkModulusGenerator import MattergenBulkModulusGenerator
from Information_Units.Generators.MattergenSpaceGroup.MattergenSpaceGroupGenerator import MattergenSpaceGroupGenerator

generator_factory = {
    "gnome": GnomeGenerator,
    "imatgen": ImatgenGenerator,
    "matgan": MatganGenerator,
    "molgan": MolganGenerator,
    "conddfcvae": ConddfcvaeGenerator,
    "mygen1": Mygen1Generator,
    "mygen2": Mygen2Generator,
    "mattergen_base_model": MattergenBaseModelGenerator,
    "mattergen_mp_20_base": MattergenMp20BaseGenerator,
    "mattergen_chemical_system": MattergenChemicalSystemGenerator,
    "mattergen_chemical_system_stability": MattergenChemicalSystemStabilityGenerator,
    "mattergen_dft_band_gap": MattergenDftBandGapGenerator,
    "mattergen_magnetic_density": MattergenMagneticDensityGenerator,
    "mattergen_magnetic_density_hhi": MattergenMagneticDensityHhiGenerator,
    "mattergen_bulk_modulus": MattergenBulkModulusGenerator,
    "mattergen_space_group": MattergenSpaceGroupGenerator,
}

generator_registry = {}

