# Predictors

Predictors are machine learning models that predict material properties from structural and compositional information. They enable rapid property screening and virtual materials testing without expensive computations. All predictors implement the `BasePredictor` interface with a standardized `predict()` method.

## Available Predictors

### MatterSim - Materials Simulation Predictor
**ID**: `mattersim`

Comprehensive predictor for materials properties using advanced simulation techniques.

**Capabilities**:
- Multi-property prediction
- Electronic structure properties
- Mechanical and thermal properties
- Uncertainty quantification

**Input Parameters**:
- `structure`: Crystal structure (CIF or POSCAR)
- `properties`: List of properties to predict
- `calculation_level`: Accuracy vs. speed trade-off
- `temperature`: Temperature conditions (optional)

**Output Properties**:
- Formation energy (eV/atom)
- Band gap (eV)
- Bulk modulus (GPa)
- Density (g/cm³)
- Thermal conductivity (W/mK)

**Accuracy**: DFT-level accuracy for most properties
**Speed**: ~1-10 seconds per prediction

**Use Cases**:
- High-throughput materials screening
- Property validation for generated materials
- Multi-property optimization

### M3GNet - Materials 3D Graph Network
**ID**: `m3gnet`

Graph neural network predictor with state-of-the-art accuracy for materials properties.

**Capabilities**:
- Graph-based structure representation
- Force and energy predictions
- Transferable across material types
- Molecular dynamics integration

**Input Parameters**:
- `structure`: Atomic structure
- `property_list`: Target properties
- `ensemble_prediction`: Use ensemble for uncertainty
- `cutoff_radius`: Graph construction radius

**Output Properties**:
- Total energy (eV)
- Atomic forces (eV/Å)
- Stress tensor (GPa)
- Elastic constants (GPa)
- Phonon properties

**Accuracy**: Near-DFT accuracy for energies and forces
**Speed**: ~0.1-1 seconds per prediction

**Use Cases**:
- Structure relaxation and optimization
- Molecular dynamics simulations
- Elastic property calculations

### PFP - Property Fingerprint Predictor
**ID**: `pfp`

Fast predictor using structural fingerprints for rapid property estimation.

**Capabilities**:
- Ultra-fast predictions
- Wide range of properties
- Composition and structure-based
- Explainable predictions

**Input Parameters**:
- `composition`: Chemical composition
- `structure`: Crystal structure (optional)
- `fingerprint_type`: Type of structural fingerprint
- `property_targets`: Properties to predict

**Output Properties**:
- Formation energy (eV/atom)
- Band gap (eV)
- Density (g/cm³)
- Hardness (GPa)
- Melting point (K)

**Accuracy**: Good accuracy for screening purposes
**Speed**: ~0.01-0.1 seconds per prediction

**Use Cases**:
- Rapid initial screening
- Large-scale database analysis
- Real-time property estimation

### DeepMD - Deep Molecular Dynamics
**ID**: `deepmd`

Deep learning potential for molecular dynamics and property predictions.

**Capabilities**:
- Accurate force field generation
- Long-timescale MD simulations
- Temperature-dependent properties
- Phase transition studies

**Input Parameters**:
- `structure`: Initial structure
- `simulation_time`: MD simulation length
- `temperature`: Simulation temperature
- `pressure`: Simulation pressure
- `ensemble`: MD ensemble (NVT, NPT, etc.)

**Output Properties**:
- Dynamic properties (diffusion, viscosity)
- Thermal properties (heat capacity, expansion)
- Phase stability at conditions
- Transport properties

**Accuracy**: High accuracy for dynamic properties
**Speed**: ~minutes to hours for full MD

**Use Cases**:
- Finite temperature property prediction
- Phase diagram construction
- Transport property calculation

### SynthNN - Synthesis Neural Network
**ID**: `synthnn`

Predictor specialized in synthesizability and synthetic accessibility.

**Capabilities**:
- Synthesizability scoring
- Synthesis route prediction
- Precursor identification
- Reaction condition estimation

**Input Parameters**:
- `target_structure`: Material to synthesize
- `available_precursors`: List of available starting materials
- `synthesis_method`: Preferred synthesis approach
- `temperature_range`: Allowed temperature range

**Output Properties**:
- Synthesizability score (0-1)
- Predicted synthesis routes
- Required precursors
- Estimated synthesis conditions
- Difficulty assessment

**Accuracy**: High accuracy for known material classes
**Speed**: ~1-5 seconds per prediction

**Use Cases**:
- Synthesis planning
- Materials feasibility assessment
- Precursor optimization

### eSEN - Electronic Structure Estimation Network
**ID**: `esen`

Specialized predictor for electronic structure properties.

**Capabilities**:
- Band structure prediction
- Density of states (DOS)
- Orbital analysis
- Electronic transport properties

**Input Parameters**:
- `crystal_structure`: Input structure
- `k_point_density`: K-point mesh density
- `functional_type`: Exchange-correlation functional
- `spin_polarization`: Include spin effects

**Output Properties**:
- Band structure (eV vs k-path)
- Density of states (states/eV)
- Effective masses (m*/m_e)
- Work function (eV)
- Dielectric constants

**Accuracy**: Near-DFT accuracy for electronic properties
**Speed**: ~5-30 seconds per prediction

**Use Cases**:
- Electronic device design
- Semiconductor characterization
- Transport property analysis

### MyPred1 - Custom Predictor 1
**ID**: `mypred1`

Customizable predictor template for specialized applications.

**Capabilities**:
- Domain-specific property prediction
- Custom model architectures
- Integration with experimental data
- Research-oriented features

**Input Parameters**:
- `domain_inputs`: Domain-specific parameters
- `model_configuration`: Model setup parameters
- `prediction_targets`: Custom property targets

**Output Properties**:
- Domain-specific properties
- Custom metrics
- Research data

### MyPred2 - Custom Predictor 2
**ID**: `mypred2`

Secondary custom predictor for alternative approaches.

**Capabilities**:
- Alternative prediction methods
- Experimental validation
- Specialized algorithms
- Novel property types

**Input Parameters**:
- `method_selection`: Prediction method choice
- `validation_mode`: Validation approach
- `custom_parameters`: Method-specific inputs

**Output Properties**:
- Method-specific predictions
- Validation metrics
- Research outputs

## Usage Patterns

### Basic Property Prediction

```python
# Example of using a predictor in a Feature
pred_instance = predictor_factory["m3gnet"]("m3gnet", logger)
inputs = {
    'structure': crystal_structure,
    'properties': ['formation_energy', 'band_gap'],
    'ensemble_prediction': True
}
results = pred_instance.predict(inputs)
```

### Multi-Predictor Validation

```python
# Use multiple predictors for cross-validation
predictors = ['mattersim', 'm3gnet', 'pfp']
predictions = {}

for pred_id in predictors:
    pred_instance = predictor_factory[pred_id](pred_id, logger)
    result = pred_instance.predict(prediction_inputs)
    predictions[pred_id] = result

# Analyze consensus and uncertainty
```

### Property Screening Workflow

```python
# Screen large numbers of materials
materials_list = [...]  # List of candidate materials
screening_results = []

# Use fast predictor for initial screening
pfp_instance = predictor_factory["pfp"]("pfp", logger)
for material in materials_list:
    inputs = {'composition': material.composition}
    quick_props = pfp_instance.predict(inputs)
    
    # Filter based on criteria
    if meets_criteria(quick_props):
        # Use more accurate predictor for promising candidates
        m3gnet_instance = predictor_factory["m3gnet"]("m3gnet", logger)
        detailed_props = m3gnet_instance.predict({
            'structure': material.structure,
            'properties': ['formation_energy', 'band_gap', 'elastic_constants']
        })
        screening_results.append((material, detailed_props))
```

## Best Practices

### Predictor Selection
- **High-throughput screening**: PFP for initial filtering
- **Accurate energetics**: M3GNet or MatterSim
- **Electronic properties**: eSEN for detailed electronic structure
- **Synthesis planning**: SynthNN for feasibility assessment

### Input Preparation
- Ensure structure convergence and reasonable geometry
- Use appropriate unit cells and primitive cells
- Consider temperature and pressure conditions
- Validate input formats and units

### Result Interpretation
- Always consider prediction uncertainty
- Cross-validate with multiple methods when critical
- Check for extrapolation beyond training data
- Validate against experimental data when available

### Performance Optimization
- Use fast predictors for initial screening
- Batch predictions when possible
- Cache results for repeated calculations
- Consider accuracy vs. speed trade-offs for your application