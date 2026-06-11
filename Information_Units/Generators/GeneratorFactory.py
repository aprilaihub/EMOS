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

