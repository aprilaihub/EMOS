# Databases

Databases provide access to existing materials data from various sources including experimental measurements, computational results, and curated collections. All databases implement the `BaseDatabase` interface with a standardized `retrieve()` method.

## Available Databases

### ICSD - Inorganic Crystal Structure Database
**ID**: `icsd`

The world's largest database for inorganic crystal structures, containing over 200,000 entries.

**Capabilities**:
- Crystal structure data for inorganic compounds
- Crystallographic parameters (space groups, lattice parameters)
- Experimental conditions and synthesis information
- Literature references

**Input Parameters**:
- `search_term`: Material formula or name
- `space_group`: Crystal space group filter
- `element_list`: Required/forbidden elements

**Output Format**:
- Crystal structure files (CIF format)
- Crystallographic data
- Database entry IDs and references

### COD - Crystallography Open Database  
**ID**: `cod`

Open-access database of crystal structures of organic, inorganic, and organometallic compounds.

**Capabilities**:
- Over 500,000 crystal structures
- Both organic and inorganic compounds
- Quality indicators for each entry
- Free and open access

**Input Parameters**:
- `formula`: Chemical formula
- `compound_name`: Compound name
- `quality_filter`: Minimum quality threshold

**Output Format**:
- CIF files with crystal structures
- Quality metrics
- Publication information

### OQMD - Open Quantum Materials Database
**ID**: `oqmd`

Database of DFT-calculated structures and properties for materials discovery.

**Capabilities**:
- Over 800,000 DFT calculations
- Formation energies and stability
- Electronic properties (band gaps, DOS)
- Thermodynamic data

**Input Parameters**:
- `composition`: Chemical composition
- `stability_range`: Formation energy range
- `band_gap_range`: Electronic band gap range

**Output Format**:
- DFT-calculated properties
- Crystal structures
- Formation energies and phase diagrams

### AFLOWLIB - Automatic-FLOW Database
**ID**: `aflowlib`

High-throughput database for materials discovery with comprehensive property data.

**Capabilities**:
- Over 3 million entries
- Automated DFT calculations
- Mechanical, electronic, and thermal properties
- Materials genome approach

**Input Parameters**:
- `prototype`: Crystal prototype
- `species`: Chemical species
- `property_filter`: Property range filters

**Output Format**:
- Comprehensive property data
- Crystal prototypes
- Computed structures and energies

### MP - Materials Project Database
**ID**: `mp`

Comprehensive collection of computed materials properties using high-throughput DFT.

**Capabilities**:
- Over 150,000 materials
- Electronic, ionic, and structural properties
- Phase diagrams and stability analysis
- Battery and photovoltaic applications data

**Input Parameters**:
- `material_id`: Materials Project ID
- `formula`: Chemical formula
- `property_criteria`: Property-based search

**Output Format**:
- Complete property datasets
- Crystal structures
- Phase stability information

### Alexandria - DFT Materials Database (PBEsol)
**ID**: `alexandria`

Curated DFT-calculated materials database using PBEsol functional, optimized for band gap accuracy in semiconductors and optoelectronic materials.

**Overview**:
- 415K structures (PBEsol-calculated)
- Formation energies and phase stability data
- Electronic properties (band gaps, DOS)
- Stress tensors and other DFT outputs
- Dual-functional data (PBEsol + SCAN calculations)

**Capabilities**:
- Band gap filtering for electronics materials
- Formation energy and stability analysis
- Dual-functional property comparison (PBEsol vs SCAN)
- Magnetic properties tracking
- Thermodynamic stability assessment

**Input Parameters (via standard property names)**:
- `query`: Material formula or element (e.g., 'Al2O3', 'Fe')
- `limit`: Maximum number of results (default: 10)

**Advanced Filters (PBEsol)**:
- `band_gap`: [min, max] eV - electronic band gap
- `band_gap_direct`: [min, max] eV - direct band gap
- `formation_energy_per_atom`: [min, max] eV/atom - formation energy
- `space_group`: [min, max] - space group number
- `hull_distance`: [min, max] eV/atom - distance from convex hull
- `magnetization`: [min, max] μB/unit_cell - total magnetization
- `energy`: [min, max] eV - total energy
- `energy_corrected`: [min, max] eV - energy with corrections
- `phase_separation_energy`: [min, max] eV/atom - phase stability
- `decomposition`: string - decomposition products
- `xc_functional`: string - functional used
- `dos_ef`: [min, max] - density of states at Fermi level
- `charges`: [min, max] - atomic charges
- `forces`: [min, max] eV/Å - forces on atoms
- `stress_tensor`: [min, max] kbar - stress tensor
- `magnetic_moments`: [min, max] μB - local magnetic moments

**Advanced Filters (SCAN variant)**:
- `band_gap_scan`, `band_gap_direct_scan`, `formation_energy_per_atom_scan`, `hull_distance_scan`, `magnetization_scan`, `energy_scan`, `energy_corrected_scan`, `phase_separation_energy_scan`, `decomposition_scan`, `dos_ef_scan`, `charges_scan`, `forces_scan`, `stress_tensor_scan`, `magnetic_moments_scan`

**Output Format**:
- CIF files with crystal structures
- DFT-calculated properties
- Both PBEsol and SCAN functional results

**Example - Electronics Materials with Band Gap Filter**:
```python
db.retrieve({
    'query': 'Al2O3',
    'limit': 5,
    'band_gap': [2.0, 6.0]  # Filter for semiconductors
})
```

**Example - Thermodynamic Stability Analysis**:
```python
db.retrieve({
    'query': 'Fe',
    'limit': 10,
    'formation_energy_per_atom': [-1.0, 0.0],
    'hull_distance': [0.0, 0.05]  # Stable/near-stable structures
})
```

**Example - PBEsol vs SCAN Comparison**:
```python
db.retrieve({
    'query': 'GaAs',
    'limit': 5,
    'band_gap': [1.0, 2.0],
    'band_gap_scan': [1.0, 2.0]  # Compare both functionals
})
```

### NOMAD - Novel Materials Discovery Repository
**ID**: `nomad`

Repository for computational materials science data with standardized formats.

**Capabilities**:
- FAIR data principles compliance
- Multiple computational codes support
- Raw calculation data access
- Metadata and provenance tracking

**Input Parameters**:
- `calculation_type`: Type of computation
- `code_name`: Computational software used
- `material_formula`: Chemical formula

**Output Format**:
- Raw calculation files
- Standardized metadata
- Calculation provenance information

### JARVIS - Joint Automated Repository for Various Integrated Simulations
**ID**: `jarvis`

Database of materials properties from various computational methods and experiments.

**Capabilities**:
- Multi-scale modeling data
- Classical and quantum simulations
- Experimental data integration
- Machine learning ready datasets

**Input Parameters**:
- `property_name`: Specific property of interest
- `method_type`: Computational method
- `material_type`: Class of materials

**Output Format**:
- Multi-method property data
- Calculation details
- Experimental correlations

## Usage Patterns

### Basic Database Query

```python
# Example of using a database in a Feature
db_instance = database_factory["icsd"]("icsd", logger)
inputs = {
    'search_term': 'silicon dioxide',
    'space_group': 'P6422'
}
results = db_instance.retrieve(inputs)
```

### Multiple Database Integration

```python
# Using multiple databases for comprehensive coverage
active_databases = [
    {'value': 'icsd', 'name': 'ICSD'},
    {'value': 'mp', 'name': 'Materials Project'},
    {'value': 'oqmd', 'name': 'OQMD'}
]

for db_config in active_databases:
    db_instance = database_factory[db_config['value']](
        db_config['value'], logger
    )
    results = db_instance.retrieve(search_inputs)
    # Combine and analyze results
```

### Error Handling

```python
try:
    results = db_instance.retrieve(inputs)
    logger.log(f"Database query successful: {len(results)} entries found", 'info')
except Exception as e:
    logger.log(f"Database query failed: {str(e)}", 'error')
    # Handle error gracefully
```

## Best Practices

### Database Selection
- **ICSD**: Best for inorganic crystal structures and experimental data
- **MP/OQMD**: Ideal for DFT-calculated properties and stability
- **COD**: Good for organic/organometallic structures
- **JARVIS**: Excellent for machine learning applications

### Query Optimization
- Use specific search terms to reduce result sets
- Apply appropriate filters for property ranges
- Consider database-specific capabilities
- Cache frequently used results

### Data Validation
- Cross-reference between multiple databases
- Verify data quality indicators
- Check calculation convergence criteria
- Validate experimental conditions