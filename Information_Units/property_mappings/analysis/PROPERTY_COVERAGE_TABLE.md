# EMOS Property Coverage Table

**Generated:** 2026-04-27 11:44:28

This document maps every EMOS Information Unit (IU) to the property groups it supports,
and lists each individual property with its unit and description.

> **How to read:**
> - **Databases** — properties that can be *queried and filtered* when retrieving materials
> - **Generators** — properties accepted as *conditioning targets* when generating novel structures
> - **Predictors** — properties *predicted from* an input crystal structure
> - Numbers in summary tables = count of distinct properties in that group

---

## 1. Databases

| Information Unit | Structural | Composition | Electronic | Energetic | Mechanical | Magnetic | Transport | Thermal | Dielectric / Piezo | Solar / Optical | **Total** |
|---|:---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---:|:---:|
| **AFLOW** | 69 | 6 | 21 | 15 | 18 | — | — | 14 | — | — | **143** |
| **Alexandria (PBEsol + SCAN)** | 7 | 1 | 12 | 12 | — | — | — | — | — | — | **32** |
| **COD** | 3 | 1 | — | — | — | — | — | — | — | — | **4** |
| **JARVIS-DFT** | 4 | — | 8 | 4 | 3 | — | 4 | — | 3 | 1 | **27** |
| **Materials Project** | 3 | 2 | — | 2 | — | — | — | — | — | — | **7** |
| **MatHub-3d** | 7 | — | 5 | 2 | 1 | 1 | 2 | — | — | — | **18** |
| **TOTAL** | 93 | 10 | 46 | 35 | 22 | 1 | 6 | 14 | 3 | 1 | **231** |

### Database Specialisations

| Database | Specialisation |
|---|---|
| **AFLOW** | Broadest structural library; mechanical tensors (AEL), thermal (AGL: Debye, thermal conductivity, heat capacity), full symmetry analysis |
| **Alexandria (PBEsol + SCAN)** | Dual-functional: every property computed with **PBEsol** *and* **SCAN**; ideal for band-gap and stability benchmarking |
| **COD** | Experimental crystallography only — structural geometry and composition; no computed properties |
| **JARVIS-DFT** | Unique coverage: thermoelectric transport (Seebeck, power factor), dielectric, piezoelectric, and solar cell efficiency (SLME); multi-level band gaps (OPT, MBJ, HSE) |
| **Materials Project** | Thermodynamic stability via **r2SCAN**; formation energy and hull distance; standard starting point for stability screening |
| **MatHub-3d** | Thermoelectric focus: transport + electronic + magnetic in a compact 74 K entry dataset |

### Full Property Listings

#### AFLOW

**Structural** (69 properties)

| Property | Unit | Description |
|---|---|---|
| `bravais_lattice_lattice_system` | — | Returns the Bravais lattice of the lattice system for the relaxed structure |
| `bravais_lattice_lattice_system_orig` | — | Returns the Bravais lattice of the lattice system for the unrelaxed structure |
| `bravais_lattice_lattice_type` | — | Returns the lattice centering type for the relaxed structure |
| `bravais_lattice_lattice_type_orig` | — | Returns the lattice centering type for the unrelaxed structure |
| `bravais_lattice_lattice_variation_type` | — | Returns the Bravais lattice variation of the lattice system for the relaxed structure |
| `bravais_lattice_lattice_variation_type_orig` | — | Returns the Bravais lattice variation of the lattice system for the unrelaxed structure |
| `bravais_lattice_orig` | — | Returns the Bravais lattice of the crystal for the unrelaxed structure |
| `bravais_lattice_relax` | — | Returns the Bravais lattice of the crystal for the relaxed structure |
| `bravais_superlattice_lattice_system` | — | Returns the Bravais superlattice of the lattice system for the relaxed structure |
| `bravais_superlattice_lattice_system_orig` | — | Returns the Bravais superlattice of the lattice system for the unrelaxed structure |
| `bravais_superlattice_lattice_type` | — | Returns the Bravais superlattice centering type for the relaxed structure |
| `bravais_superlattice_lattice_type_orig` | — | Returns the Bravais superlattice centering type for the unrelaxed structure |
| `bravais_superlattice_lattice_variation_type` | — | Returns the Bravais superlattice variation of the lattice system for the relaxed structure |
| `bravais_superlattice_lattice_variation_type_orig` | — | Returns the Bravais superlattice variation of the lattice system for the unrelaxed structure |
| `crystal_class` | — | Returns the crystal class for the relaxed structure |
| `crystal_class_orig` | — | Returns the crystal class for the unrelaxed structure |
| `crystal_family` | — | Returns the crystal family for the relaxed structure |
| `crystal_family_orig` | — | Returns the crystal family for the unrelaxed structure |
| `crystal_system` | — | Returns the crystal system for the relaxed structure |
| `crystal_system_orig` | — | Returns the crystal system for the unrelaxed structure |
| `density` | g/cm3 | Mass density |
| `elements` | — | List of unique chemical elements present |
| `forces` | eV/Angstrom | Forces on atoms (PBEsol) |
| `geometry` | — | Returns the lattice parameters of the relaxed simulation cell |
| `geometry_orig` | — | Returns the lattice parameters of the unrelaxed simulation cell |
| `lattice_system_orig` | — | Returns the lattice system for the unrelaxed structure |
| `lattice_system_relax` | — | Returns the lattice system for the relaxed structure |
| `lattice_variation_orig` | — | Returns the lattice variation for the unrelaxed structure |
| `lattice_variation_relax` | — | Returns the lattice variation for the relaxed structure |
| `natoms` | — | Number of atoms in unit cell |
| `nelements` | — | Number of unique chemical elements |
| `pearson_symbol_orig` | — | Returns the Pearson symbol for the unrelaxed structure |
| `pearson_symbol_relax` | — | Returns the Pearson symbol for the relaxed structure |
| `pearson_symbol_superlattice` | — | Returns the Pearson symbol of the superlattice for the relaxed structure |
| `pearson_symbol_superlattice_orig` | — | Returns the Pearson symbol of the superlattice for the unrelaxed structure |
| `point_group_hermann_mauguin` | — | Returns the point group, in Hermann-Mauguin notation, for the relaxed structure |
| `point_group_hermann_mauguin_orig` | — | Returns the point group, in Hermann-Mauguin notation, for the unrelaxed structure |
| `point_group_orbifold` | — | Returns the point group orbifold for the relaxed structure |
| `point_group_orbifold_orig` | — | Returns the point group orbifold for the unrelaxed structure |
| `point_group_order` | — | Returns the point group order for the relaxed structure |
| `point_group_order_orig` | — | Returns the point group order for the unrelaxed structure |
| `point_group_schoenflies` | — | Returns the point group, in Schoenflies notation, for the relaxed structure |
| `point_group_schoenflies_orig` | — | Returns the point group, in Schoenflies notation, for the unrelaxed structure |
| `point_group_structure` | — | Returns the point group structure for the relaxed structure |
| `point_group_structure_orig` | — | Returns the point group structure for the unrelaxed structure |
| `point_group_type` | — | Returns the point group type for the relaxed structure |
| `point_group_type_orig` | — | Returns the point group type for the unrelaxed structure |
| `positions_cartesian` | &Aring; | Returns the Cartesian coordinates of the atoms for the relaxed structure |
| `positions_fractional` | — | Returns the fractional coordinates of the atoms for the relaxed structure |
| `reciprocal_geometry` | — | Returns the reciprocal lattice parameters of the relaxed simulation cell |
| `reciprocal_geometry_orig` | — | Returns the reciprocal lattice parameters of the unrelaxed simulation cell |
| `reciprocal_lattice_type` | — | Returns the reciprocal lattice centering type for the relaxed structure |
| `reciprocal_lattice_type_orig` | — | Returns the reciprocal lattice centering type for the unrelaxed structure |
| `reciprocal_lattice_variation_type` | — | Returns the reciprocal lattice centering type variation for the relaxed structure |
| `reciprocal_lattice_variation_type_orig` | — | Returns the reciprocal lattice centering type variation for the unrelaxed structure |
| `reciprocal_volume_cell` | &Aring;<sup>-3</sup> | Returns the volume of the reciprocal cell for the relaxed structure |
| `reciprocal_volume_cell_orig` | &Aring;<sup>-3</sup> | Returns the volume of the reciprocal cell for the unrelaxed structure |
| `space_group` | — | Space group number (PBEsol) |
| `spacegroup_orig` | — | Returns the space group for the unrelaxed structure |
| `stress_tensor` | kbar | Stress tensor (PBEsol) |
| `volume` | Angstrom3 | Unit cell volume |
| `wyckoff_letters` | — | Returns the Wyckoff letters of each site for the relaxed structure |
| `wyckoff_letters_orig` | — | Returns the Wyckoff letters of each site for the unrelaxed structure |
| `wyckoff_multiplicities` | — | Returns the Wyckoff multiplicity of each site for the relaxed structure |
| `wyckoff_multiplicities_orig` | — | Returns the Wyckoff multiplicity of each site for the unrelaxed structure |
| `wyckoff_positions` | — | The Wyckoff positions of each site for the relaxed structure |
| `wyckoff_positions_orig` | — | The Wyckoff positions of each site for the unrelaxed structure |
| `wyckoff_site_symmetries` | — | Returns the Wyckoff symmetry of each site for the relaxed structure |
| `wyckoff_site_symmetries_orig` | — | Returns the Wyckoff symmetry of each site for the unrelaxed structure |

**Composition** (6 properties)

| Property | Unit | Description |
|---|---|---|
| `atoms_per_species` | — | Returns the number of atoms per type in the simulation cell |
| `chemical_formula_descriptive` | — | Descriptive chemical formula |
| `species_pp` | — | Returns the pseudopotential of the species |
| `species_pp_version` | — | Returns the pseudopotential version of the species |
| `species_pp_z_v_a_l` | e<sup>-</sup> | Returns the number of valence electrons of the species |
| `stoichiometry` | — | Returns the normalized composition of the structure |

**Electronic** (21 properties)

| Property | Unit | Description |
|---|---|---|
| `band_gap` | eV | Electronic band gap (PBEsol) |
| `band_gap_type` | — | Returns the electronic band gap type |
| `delta_electronic_energy_convergence` | eV | Returns the change in total energy from the last step of the self-consistent field (SCF) iteration |
| `delta_electronic_energy_threshold` | eV | Returns the threshold for the self-consistent field (SCF) convergence |
| `eentropy_atom` | eV/atom | Returns the electronic entropy per atom used to converge the calculation |
| `eentropy_cell` | eV/cell | Returns the electronic entropy per cell used to converge the calculation |
| `kpoints_bands_nkpts` | — | Returns the number of points, between the high-symmetry k-points, used for the band structure calculation |
| `kpoints_bands_path` | — | Returns the high-symmetry k-point path used for the band structure calculation |
| `kpoints_relax` | — | Returns the k-point grid used for the structural relaxation calculation |
| `kpoints_static` | — | Returns the k-point grid used for the static calculation |
| `ldau_j` | eV | Returns the J parameters of the DFT+U calculation |
| `ldau_l` | — | Returns The orbitals of the DFT+U calculation |
| `ldau_type` | — | Returns the type of DFT+U calculation performed |
| `ldau_u` | eV | Returns the U parameters of the DFT+U calculation |
| `magnetization` | muB/unit_cell | Total magnetization (PBEsol) |
| `spin_atom` | &mu;<sub>B</sub>/atom | Returns the magnetization of the simulation cell per atom |
| `spin_d` | &mu;<sub>B</sub> | Returns the magnetic moment on each atom |
| `spin_d_magmom_orig` | &mu;<sub>B</sub> | Returns the magnetic moment on each atom of the unrelaxed structure |
| `spin_f` | &mu;<sub>B</sub>/cell | Returns the magnetization of the simulation cell, at the Fermi energy |
| `valence_cell_iupac` | — | Returns the sum of the valence electrons, based on IUPAC standards, of the atoms in the simulation cell |
| `valence_cell_std` | — | Returns the sum of the valence electrons, based on the outermost shell(s), of the atoms in the simulation cell |

**Energetic** (15 properties)

| Property | Unit | Description |
|---|---|---|
| `bader_atomic_volumes` | &Aring;<sup>3</sup> | Returns the volume of each atom calculated by the Atoms in Molecules (AIM) Bader analysis |
| `energy_cell` | eV/cell | Returns the total ab initio energy per cell |
| `energy_cutoff` | eV | Return the plane-wave energy cut-off used for the calculation |
| `energy_per_atom` | eV/atom | Total DFT energy per atom |
| `enthalpy_atom` | eV/atom | Returns the enthalpy per atom |
| `enthalpy_cell` | eV/cell | Returns the enthalpy per cell |
| `enthalpy_formation_atom` | eV/atom | Returns the formation enthalpy per atom |
| `enthalpy_formation_cell` | eV/cell | Returns the formation enthalpy per cell |
| `entropic_temperature` | K | Returns the entropic temperature |
| `p_v_atom` | eV/atom | Returns the pressure multiplied by volume per atom for the relaxed structure |
| `p_v_cell` | eV/cell | Returns the pressure multiplied by volume per atom for the relaxed structure |
| `pressure` | kbar | Returns the hydrostatic pressure on the simulation cell for the unrelaxed structure |
| `pressure_final` | kbar | Returns the hydrostatic pressure on the simulation cell for the relaxed structure |
| `pressure_residual` | kbar | Returns the hydrostatic pressure, corrected by the Pulay stress, on the simulation cell for the relaxed structure |
| `volume_atom` | &Aring;<sup>3</sup>/atom | Returns the volume per atom of the simulation cell for the relaxed structure |

**Mechanical** (18 properties)

| Property | Unit | Description |
|---|---|---|
| `ael_applied_pressure` | GPa | Returns the applied pressure for the AEL calculations |
| `ael_average_external_pressure` | GPa | Returns the average external pressure for the AEL calculations |
| `ael_bulk_modulus_reuss` | GPa | Returns the bulk modulus calculated, using the Reuss method, by AEL |
| `ael_bulk_modulus_voigt` | GPa | Returns the bulk modulus calculated, using the Voigt method, by AEL |
| `ael_compliance_tensor` | GPa<sup>-1</sup> | Returns the compliance tensor calculated by AEL |
| `ael_debye_temperature` | K | Returns the Debye temperature calculated by AEL |
| `ael_elastic_anisotropy` | — | Returns the elastic anisotropy calculated by AEL |
| `ael_pughs_modulus_ratio` | — | Returns the Pugh's modulus ratio calculated by AEL |
| `ael_shear_modulus_reuss` | GPa | Returns the shear modulus calculated, using the Reuss method, by AEL |
| `ael_shear_modulus_voigt` | GPa | Returns the shear modulus calculated, using the Voigt method, by AEL |
| `ael_speed_sound_average` | m/s | Returns the average speed of sound calculated by AEL |
| `ael_speed_sound_longitudinal` | m/s | Returns the longitudinal speed of sound calculated by AEL |
| `ael_speed_sound_transverse` | m/s | Returns the transverse speed of sound calculated by AEL |
| `ael_stiffness_tensor` | GPa | Returns the stiffness tensor calculated by AEL |
| `ael_youngs_modulus_vrh` | GPa | Returns the Young modulus calculated, using the Voigt-Reuss-Hill average, by AEL |
| `bulk_modulus` | GPa | Bulk modulus |
| `poisson_ratio` | — | Poisson ratio |
| `shear_modulus` | GPa | Shear modulus (Voigt) |

**Thermal** (14 properties)

| Property | Unit | Description |
|---|---|---|
| `agl_acoustic_debye` | K | Returns the acoustic Debye temperature calculated by AGL |
| `agl_bulk_modulus_isothermal_300_k` | GPa | Returns the isothermal bulk modulus calculated by AGL at 300 K |
| `agl_bulk_modulus_static_300_k` | GPa | Returns the static bulk modulus calculated by AGL at 300 K |
| `agl_debye` | K | Returns the Debye temperature calculated by AGL |
| `agl_gruneisen` | — | Returns the Gr&uuml;neisen parameter calculated by AGL |
| `agl_heat_capacity_cp_300_k` | k<sub>B</sub>/cell | Returns the heat capacity per cell, at constant pressure, calculated by AGL at 300 K |
| `agl_heat_capacity_cv_300_k` | k<sub>B</sub>/cell | Returns the heat capacity per cell, at constant volume, calculated by AGL at 300 K |
| `agl_poisson_ratio_source` | — | Returns the source of the Poisson ratio used for AGL calculations |
| `agl_thermal_conductivity_300_k` | W m<sup>-1</sup> K<sup>-1</sup> | Returns the thermal conductivity calculated by AGL at 300 K |
| `agl_thermal_expansion_300_k` | K<sup>-1</sup> | Returns the thermal expansion coefficient calculated by AGL at 300 K |
| `agl_vibrational_entropy_300_k_atom` | meV/(K atom) | Returns the vibrational entropy per atom calculated by AGL at 300 K |
| `agl_vibrational_entropy_300_k_cell` | meV/(K cell) | Returns the vibrational entropy per cell calculated by AGL at 300 K |
| `agl_vibrational_free_energy_300_k_atom` | meV/atom | Returns the vibrational free energy per atom calculated by AGL at 300 K |
| `agl_vibrational_free_energy_300_k_cell` | meV/cell | Returns the vibrational free energy per cell calculated by AGL at 300 K |

---

#### Alexandria (PBEsol + SCAN)

**Structural** (7 properties)

| Property | Unit | Description |
|---|---|---|
| `elements` | — | List of unique chemical elements present |
| `forces` | eV/Angstrom | Forces on atoms (PBEsol) |
| `forces_scan` | eV/Angstrom | Forces on atoms (SCAN) |
| `nelements` | — | Number of unique chemical elements |
| `nperiodic_dimensions` | — | Number of periodic dimensions |
| `space_group` | — | Space group number (PBEsol) |
| `stress_tensor` | kbar | Stress tensor (PBEsol) |

**Composition** (1 properties)

| Property | Unit | Description |
|---|---|---|
| `chemical_formula_descriptive` | — | Descriptive chemical formula |

**Electronic** (12 properties)

| Property | Unit | Description |
|---|---|---|
| `band_gap` | eV | Electronic band gap (PBEsol) |
| `band_gap_direct` | eV | Direct electronic band gap (PBEsol) |
| `band_gap_direct_scan` | eV | Direct electronic band gap (SCAN) |
| `band_gap_scan` | eV | Electronic band gap (SCAN) |
| `charges` | — | Atomic charges (PBEsol) |
| `charges_scan` | — | Atomic charges (SCAN) |
| `dos_ef` | states/(eV*unit_cell) | Density of states at Fermi level (PBEsol) |
| `dos_ef_scan` | states/(eV*unit_cell) | Density of states at Fermi level (SCAN) |
| `magnetic_moments` | muB | Local magnetic moments (PBEsol) |
| `magnetic_moments_scan` | muB | Local magnetic moments (SCAN) |
| `magnetization` | muB/unit_cell | Total magnetization (PBEsol) |
| `magnetization_scan` | muB/unit_cell | Total magnetization (SCAN) |

**Energetic** (12 properties)

| Property | Unit | Description |
|---|---|---|
| `decomposition` | — | Most likely decomposition channel (PBEsol) |
| `decomposition_scan` | — | Most likely decomposition channel (SCAN) |
| `energy` | eV | Total energy (PBEsol) |
| `energy_corrected` | eV | Total energy with pymatgen corrections (PBEsol) |
| `energy_corrected_scan` | eV | Total energy with pymatgen corrections (SCAN) |
| `energy_scan` | eV | Total energy (SCAN) |
| `formation_energy_per_atom` | eV/atom | Formation energy per atom (PBEsol) |
| `formation_energy_per_atom_scan` | eV/atom | Formation energy per atom (SCAN) |
| `hull_distance` | eV/atom | Distance from convex hull (PBEsol) |
| `hull_distance_scan` | eV/atom | Distance from convex hull (SCAN) |
| `phase_separation_energy` | eV/atom | Phase separation energy (PBEsol) |
| `phase_separation_energy_scan` | eV/atom | Phase separation energy (SCAN) |

---

#### COD

**Structural** (3 properties)

| Property | Unit | Description |
|---|---|---|
| `elements` | — | List of unique chemical elements present |
| `nelements` | — | Number of unique chemical elements |
| `nperiodic_dimensions` | — | Number of periodic dimensions |

**Composition** (1 properties)

| Property | Unit | Description |
|---|---|---|
| `chemical_formula_descriptive` | — | Descriptive chemical formula |

---

#### JARVIS-DFT

**Structural** (4 properties)

| Property | Unit | Description |
|---|---|---|
| `density` | g/cm3 | Mass density |
| `nelements` | — | Number of unique chemical elements |
| `nperiodic_dimensions` | — | Number of periodic dimensions |
| `space_group` | — | Space group number (PBEsol) |

**Electronic** (8 properties)

| Property | Unit | Description |
|---|---|---|
| `Tc_supercon` | K | Superconducting critical temperature |
| `avg_elec_mass` | m_e | Average electron effective mass |
| `avg_hole_mass` | m_e | Average hole effective mass |
| `band_gap` | eV | Electronic band gap (PBEsol) |
| `hse_gap` | eV | Electronic band gap (HSE functional) |
| `magnetization` | muB/unit_cell | Total magnetization (PBEsol) |
| `mbj_bandgap` | eV | Electronic band gap (MBJ functional) |
| `spillage` | — | Spillage value for topological material screening |

**Energetic** (4 properties)

| Property | Unit | Description |
|---|---|---|
| `energy` | eV | Total energy (PBEsol) |
| `exfoliation_energy` | meV/atom | Exfoliation energy for 2D materials |
| `formation_energy_per_atom` | eV/atom | Formation energy per atom (PBEsol) |
| `hull_distance` | eV/atom | Distance from convex hull (PBEsol) |

**Mechanical** (3 properties)

| Property | Unit | Description |
|---|---|---|
| `bulk_modulus` | GPa | Bulk modulus |
| `poisson_ratio` | — | Poisson ratio |
| `shear_modulus` | GPa | Shear modulus (Voigt) |

**Transport** (4 properties)

| Property | Unit | Description |
|---|---|---|
| `n_powerfact` | — | n-type thermoelectric power factor |
| `n_seebeck` | muV/K | n-type Seebeck coefficient |
| `p_powerfact` | — | p-type thermoelectric power factor |
| `p_seebeck` | muV/K | p-type Seebeck coefficient |

**Dielectric / Piezo** (3 properties)

| Property | Unit | Description |
|---|---|---|
| `dfpt_piezo_max_dij` | C/N | Maximum piezoelectric strain coefficient |
| `epsx` | — | Dielectric constant (x-direction, electronic) |
| `mepsx` | — | Dielectric constant (x-direction, ionic+electronic) |

**Solar / Optical** (1 properties)

| Property | Unit | Description |
|---|---|---|
| `slme` | % | Spectroscopic Limited Maximum Efficiency for solar cells |

---

#### Materials Project

**Structural** (3 properties)

| Property | Unit | Description |
|---|---|---|
| `elements` | — | List of unique chemical elements present |
| `nelements` | — | Number of unique chemical elements |
| `nperiodic_dimensions` | — | Number of periodic dimensions |

**Composition** (2 properties)

| Property | Unit | Description |
|---|---|---|
| `chemical_formula_descriptive` | — | Descriptive chemical formula |
| `chemical_system` | — | Chemical system identifier (e.g., 'Si', 'Fe-O', 'Al-Si-O') |

**Energetic** (2 properties)

| Property | Unit | Description |
|---|---|---|
| `energy_above_hull_r2scan` | eV/atom | Distance from convex hull using r2SCAN functional |
| `formation_energy_r2scan` | eV/atom | Formation energy per atom using r2SCAN functional |

---

#### MatHub-3d

**Structural** (7 properties)

| Property | Unit | Description |
|---|---|---|
| `density` | g/cm3 | Mass density |
| `elements` | — | List of unique chemical elements present |
| `mass` | amu | Unit cell mass |
| `natoms` | — | Number of atoms in unit cell |
| `nelements` | — | Number of unique chemical elements |
| `space_group` | — | Space group number (PBEsol) |
| `volume` | Angstrom3 | Unit cell volume |

**Electronic** (5 properties)

| Property | Unit | Description |
|---|---|---|
| `band_gap` | eV | Electronic band gap (PBEsol) |
| `cbm` | eV | Conduction band minimum |
| `efermi` | eV | Fermi energy |
| `magnetization` | muB/unit_cell | Total magnetization (PBEsol) |
| `vbm` | eV | Valence band maximum |

**Energetic** (2 properties)

| Property | Unit | Description |
|---|---|---|
| `energy` | eV | Total energy (PBEsol) |
| `energy_per_atom` | eV/atom | Total DFT energy per atom |

**Mechanical** (1 properties)

| Property | Unit | Description |
|---|---|---|
| `bulk_modulus` | GPa | Bulk modulus |

**Magnetic** (1 properties)

| Property | Unit | Description |
|---|---|---|
| `is_magnetic` | — | Whether the material is magnetic |

**Transport** (2 properties)

| Property | Unit | Description |
|---|---|---|
| `deformation_potential_n` | eV | n-type deformation potential |
| `deformation_potential_p` | eV | p-type deformation potential |

---

## 2. Generators (MatterGen Models)

Generators produce novel crystal structures *conditioned on* the listed properties. A ✓ marks that the model accepts the property group as a conditioning target.

| Model | Structural | Composition | Electronic | Energetic | Mechanical | Magnetic | **Conditioning Props** |
|---|:---: | :---: | :---: | :---: | :---: | :---:|:---:|
| **MatterGen — Base Model** | — | — | — | — | — | — | **0** |
| **MatterGen — Bulk Modulus** | — | — | — | — | ✓ | — | **1** |
| **MatterGen — Chemical System** | — | ✓ | — | — | — | — | **1** |
| **MatterGen — Chem. System + Stability** | — | ✓ | — | ✓ | — | — | **2** |
| **MatterGen — DFT Band Gap** | — | — | ✓ | — | — | — | **1** |
| **MatterGen — Magnetic Density** | — | — | — | — | — | ✓ | **1** |
| **MatterGen — Magnetic Density + HHI** | — | — | — | — | — | ✓ | **1** |
| **MatterGen — MP-20 Base** | — | — | — | — | — | — | **0** |
| **MatterGen — Space Group** | ✓ | — | — | — | — | — | **1** |

### Model Notes

| Model | Description |
|---|---|
| **MatterGen — Base Model** | Unconditional generation — no property constraint |
| **MatterGen — Bulk Modulus** | Condition on target bulk modulus |
| **MatterGen — Chemical System** | Condition on target chemical system (element set) |
| **MatterGen — Chem. System + Stability** | Condition on chemical system **and** thermodynamic stability (hull distance) |
| **MatterGen — DFT Band Gap** | Condition on target direct DFT band gap |
| **MatterGen — Magnetic Density** | Condition on target magnetic density |
| **MatterGen — Magnetic Density + HHI** | Condition on magnetic density **and** earth-abundance (HHI score) |
| **MatterGen — MP-20 Base** | Unconditional generation trained on MP-20 dataset |
| **MatterGen — Space Group** | Condition on target space group symmetry |

### Full Conditioning Property Listings

#### MatterGen — Bulk Modulus

| Property | Unit | Description |
|---|---|---|
| `bulk_modulus` | GPa | Bulk modulus |

#### MatterGen — Chemical System

| Property | Unit | Description |
|---|---|---|
| `chemical_system` | — | Chemical system identifier (e.g., 'Si', 'Fe-O', 'Al-Si-O') |

#### MatterGen — Chem. System + Stability

| Property | Unit | Description |
|---|---|---|
| `chemical_system` | — | Chemical system identifier (e.g., 'Si', 'Fe-O', 'Al-Si-O') |
| `hull_distance` | eV/atom | Distance from convex hull (PBEsol) |

#### MatterGen — DFT Band Gap

| Property | Unit | Description |
|---|---|---|
| `band_gap_direct` | eV | Direct electronic band gap (PBEsol) |

#### MatterGen — Magnetic Density

| Property | Unit | Description |
|---|---|---|
| `mag_density` | T | Mag density |

#### MatterGen — Magnetic Density + HHI

| Property | Unit | Description |
|---|---|---|
| `hhi_score` | ??? | HII score (?) |
| `mag_density` | T | Mag density |

#### MatterGen — Space Group

| Property | Unit | Description |
|---|---|---|
| `space_group` | — | Space group number (PBEsol) |

---

## 3. Predictors

Predictors take a crystal structure as input and return the listed properties.

| Predictor | Structural | Electronic | Energetic | Simulation Output | **Total** |
|---|:---: | :---: | :---: | :---:|:---:|
| **GBFS (3D)** | — | 5 | 1 | — | **6** |
| **GBFS-2D** | 1 | 2 | — | — | **3** |
| **MatterSim** | 2 | — | 1 | 6 | **9** |
| **SynthNN** | — | — | — | 2 | **2** |

### Predictor Notes

| Predictor | Specialisation |
|---|---|
| **GBFS (3D)** | LightGBM model for 3D bulk materials: band gap, dielectric constant, carrier mobilities (e⁻/h⁺), formation energy, metal/insulator class |
| **GBFS-2D** | Same as GBFS but specialised for 2D layered materials; includes stability prediction |
| **MatterSim** | Universal ML force-field: energies, forces, stresses on any structure + full structure relaxation pipeline (relaxed CIF, energy, forces, stress) |
| **SynthNN** | Synthesizability scoring — probability that a given structure can be experimentally synthesised |

### Full Predicted Property Listings

#### GBFS (3D)

| Property | Unit | Description |
|---|---|---|
| `band_gap_gbfs` | eV | Predicted electronic band gap using GBFS LightGBM model |
| `dielectric_constant_gbfs` | dimensionless | Predicted dielectric constant using GBFS LightGBM model |
| `electron_mobility_gbfs` | cm²/V·s | Predicted electron mobility using GBFS LightGBM model (log10 scaled internally, returned as actual value) |
| `formation_energy_gbfs` | eV/atom | Predicted formation energy per atom using GBFS LightGBM model |
| `hole_mobility_gbfs` | cm²/V·s | Predicted hole mobility using GBFS LightGBM model (log10 scaled internally, returned as actual value) |
| `is_metal_gbfs` | — | Predicted metal/non-metal classification using GBFS LightGBM classifier |

#### GBFS-2D

| Property | Unit | Description |
|---|---|---|
| `band_gap_gbfs2d` | eV | Predicted electronic band gap for 2D layered materials using GBFS-2D LightGBM model with van der Waals detection |
| `is_metal_gbfs2d` | — | Predicted metal/non-metal classification for 2D layered materials using GBFS-2D LightGBM classifier with van der Waals detection |
| `is_stable_gbfs2d` | — | Predicted structural stability for 2D layered materials using GBFS-2D LightGBM classifier with van der Waals detection |

#### MatterSim

| Property | Unit | Description |
|---|---|---|
| `atomic_numbers` | — | Atomic numbers for atoms in the structure |
| `energy` | eV | Total energy (PBEsol) |
| `forces` | eV/Angstrom | Forces on atoms (PBEsol) |
| `num_atoms` | — | Number of atoms in the structure |
| `relaxed_cif` | — | Path to saved relaxed CIF output from MatterSim |
| `relaxed_energy` | eV | Total energy after MatterSim structure relaxation |
| `relaxed_forces` | eV/Angstrom | Forces on atoms after MatterSim structure relaxation |
| `relaxed_stress` | GPa | Stress tensor after MatterSim structure relaxation |
| `stress_tensor` | kbar | Stress tensor (PBEsol) |

#### SynthNN

| Property | Unit | Description |
|---|---|---|
| `synthesizability_score` | probability | Predicted SynthNN synthesizability score |
| `synthesizable` | — | Predicted SynthNN synthesizability label |

---

## 4. Combined Overview

| Property Group | Databases | Generators | Predictors |
|---|---|---|---|
| **Structural** | AFLOW, Alexandria (PBEsol + SCAN), COD, JARVIS-DFT, Materials Project, MatHub-3d | MatterGen — Space Group | GBFS-2D, MatterSim |
| **Composition** | AFLOW, Alexandria (PBEsol + SCAN), COD, Materials Project | MatterGen — Chemical System, MatterGen — Chem. System + Stability | — |
| **Electronic** | AFLOW, Alexandria (PBEsol + SCAN), JARVIS-DFT, MatHub-3d | MatterGen — DFT Band Gap | GBFS (3D), GBFS-2D |
| **Energetic** | AFLOW, Alexandria (PBEsol + SCAN), JARVIS-DFT, Materials Project, MatHub-3d | MatterGen — Chem. System + Stability | GBFS (3D), MatterSim |
| **Mechanical** | AFLOW, JARVIS-DFT, MatHub-3d | MatterGen — Bulk Modulus | — |
| **Magnetic** | MatHub-3d | MatterGen — Magnetic Density, MatterGen — Magnetic Density + HHI | — |
| **Transport** | JARVIS-DFT, MatHub-3d | — | — |
| **Thermal** | AFLOW | — | — |
| **Dielectric / Piezo** | JARVIS-DFT | — | — |
| **Solar / Optical** | JARVIS-DFT | — | — |
| **Simulation Output** | — | — | MatterSim, SynthNN |

## 5. Coverage Gaps

The following property groups are present in some IUs but absent from others, representing potential areas for future extension.

| Property Group | Gap |
|---|---|
| **Thermal** | Only **AFLOW** provides thermal properties (Debye temperature, thermal conductivity, heat capacity, vibrational entropy). No generator or predictor support. |
| **Dielectric / Piezo** | Exclusive to **JARVIS-DFT**. No ML predictor or generator for dielectric or piezoelectric properties. |
| **Solar / Optical** | Only **JARVIS-DFT** exposes SLME (Spectroscopic Limited Maximum Efficiency). No generator or predictor. |
| **Magnetic** | Only **MatHub-3d** (database) and MatterGen magnetic models (generators). No ML predictor available. |
| **Transport** | Only **JARVIS-DFT** and **MatHub-3d**. No ML predictor for Seebeck coefficient or carrier mobility across databases. |
| **Composition** | All databases offer composition filtering; only **MatterGen** generators condition on it. No predictor returns composition. |
| **Simulation Output** | Exclusive to **MatterSim** (relaxation pipeline) and **SynthNN** (synthesizability). Not covered by any database. |

---

*Generated from `Information_Units/property_mappings/` — EMOS repository*
