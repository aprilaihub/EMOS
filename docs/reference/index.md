# Reference

This reference section provides comprehensive technical documentation for EMOS, including API specifications, configuration options, and troubleshooting resources.

## System Architecture

### Component Overview
```
EMOS Application
├── Web Interface (Frontend)
│   ├── HTML/CSS/JavaScript
│   ├── User Interface Components
│   └── Visualization Libraries
├── Backend API (Flask/Python)
│   ├── Request Handling
│   ├── Feature Processing
│   └── Response Formatting
├── Information Units
│   ├── Databases (8 types)
│   ├── Generators (8 types)
│   └── Predictors (8 types)
└── Features (16 total)
    ├── Materials Exploration (8)
    └── Electronics Application (8)
```

### Factory Pattern Implementation
EMOS uses factory patterns for component registration and instantiation:

```python
# Information Unit Factories
database_factory = {
    'icsd': ICSDDatabase,
    'cod': CODDatabase,
    'oqmd': OQMDDatabase,
    'aflowlib': AFLOWLIBDatabase,
    'mp': MPDatabase,
    'alexandria': AlexandriaDatabase,
    'nomad': NOMADDatabase,
    'jarvis': JARVISDatabase
}

generator_factory = {
    'mattergen': MatterGenGenerator,
    'gnome': GNoMEGenerator,
    'imatgen': iMatGenGenerator,
    'matgan': MatGANGenerator,
    'molgan': MolGANGenerator,
    'conddftcvae': CondDFTCVAEGenerator,
    'mygen1': MyGen1Generator,
    'mygen2': MyGen2Generator
}

predictor_factory = {
    'mattersim': MatterSimPredictor,
    'm3gnet': M3GNetPredictor,
    'pfp': PFPPredictor,
    'deepmd': DeepMDPredictor,
    'synthnn': SynthNNPredictor,
    'esen': eSENPredictor,
    'mypred1': MyPred1Predictor,
    'mypred2': MyPred2Predictor
}

feature_factory = {
    '1': MaterialSearchFeature,
    '2': MaterialGenerationFeature,
    '3': DatabaseExtractorFeature,
    '4': MaterialCharacterizationFeature,
    '5': DFTCalculationFeature,
    '6': CrystallographicAnalysisFeature,
    '7': QuantumMechanicsFeature,
    '8': TensorAnalysisFeature,
    '9': DeviceSynthesizabilityFeature,
    '10': InterfaceCalculationFeature,
    '11': PropertyPredictionFeature,
    '12': BandStructureFeature,
    '13': ThermalManagementFeature,
    '14': ReliabilityAssessmentFeature,
    '15': ProcessIntegrationFeature,
    '16': AdvancedCharacterizationFeature
}
```

## API Reference

### Base Classes

#### BaseFeature
All features inherit from the BaseFeature abstract base class:

```python
class BaseFeature(ABC):
    def __init__(self, name: str, logger=None):
        self.name = name
        self.logger = logger
    
    @abstractmethod
    def info(self) -> str:
        """Return feature description and capabilities"""
        pass
    
    @abstractmethod  
    def extract_inputs(self, input_data: dict) -> dict:
        """Extract and validate inputs from raw input_data"""
        pass
    
    @abstractmethod
    def process_feature(self, inputs: dict) -> dict:
        """Core feature processing logic"""
        pass
    
    @abstractmethod
    def format_outputs(self, results: dict) -> dict:
        """Format results to standardized output format"""
        pass
    
    def process(self, input_data: dict) -> dict:
        """Main processing method implementing template pattern"""
        inputs = self.extract_inputs(input_data)
        results = self.process_feature(inputs)
        outputs = self.format_outputs(results)
        return outputs
```

#### BaseDatabase
Database Information Units inherit from BaseDatabase:

```python
class BaseDatabase(ABC):
    def __init__(self, name: str, logger=None):
        self.name = name
        self.logger = logger
    
    @abstractmethod
    def info(self) -> str:
        """Return database description and capabilities"""
        pass
    
    @abstractmethod
    def retrieve(self, retrieve_inputs: dict) -> dict:
        """Retrieve data based on search criteria"""
        pass
```

#### BaseGenerator
Generator Information Units inherit from BaseGenerator:

```python
class BaseGenerator(ABC):
    def __init__(self, name: str, logger=None):
        self.name = name
        self.logger = logger
    
    @abstractmethod
    def info(self) -> str:
        """Return generator description and capabilities"""
        pass
    
    @abstractmethod
    def generate(self, generate_inputs: dict) -> dict:
        """Generate new materials based on input criteria"""
        pass
```

#### BasePredictor
Predictor Information Units inherit from BasePredictor:

```python
class BasePredictor(ABC):
    def __init__(self, name: str, logger=None):
        self.name = name
        self.logger = logger
    
    @abstractmethod
    def info(self) -> str:
        """Return predictor description and capabilities"""
        pass
    
    @abstractmethod
    def predict(self, predict_inputs: dict) -> dict:
        """Predict properties for given materials/structures"""
        pass
```

### Standard Input/Output Formats

#### Information Unit Configuration
```python
# Standard format for configuring Information Units
{
    'active_databases': [
        {
            'value': 'mp',           # Database identifier
            'name': 'Materials Project'  # Human-readable name
        }
    ],
    'active_generators': [
        {
            'value': 'mattergen',
            'name': 'MatterGen'
        }
    ],
    'active_predictors': [
        {
            'value': 'm3gnet',
            'name': 'M3GNet'
        }
    ]
}
```

#### Material Structure Format
```python
# Standard crystal structure representation
{
    'lattice': {
        'a': float,      # Lattice parameter a (Angstrom)
        'b': float,      # Lattice parameter b (Angstrom)
        'c': float,      # Lattice parameter c (Angstrom)
        'alpha': float,  # Lattice angle alpha (degrees)
        'beta': float,   # Lattice angle beta (degrees)
        'gamma': float,  # Lattice angle gamma (degrees)
        'matrix': [[3x3 matrix]]  # Lattice vectors
    },
    'atoms': [
        {
            'element': str,           # Element symbol
            'position': [x, y, z],   # Fractional coordinates
            'site_label': str        # Optional site label
        }
    ],
    'space_group': str,  # Space group symbol
    'formula': str,      # Chemical formula
    'identifiers': {     # External database identifiers
        'mp_id': str,
        'icsd_id': int,
        'cod_id': int
    }
}
```

#### Property Format
```python
# Standard property representation
{
    'property_name': {
        'value': float,              # Property value
        'unit': str,                # Units
        'uncertainty': float,       # Uncertainty/error estimate
        'method': str,              # Calculation/measurement method
        'conditions': {             # Conditions under which measured/calculated
            'temperature': float,    # K
            'pressure': float,      # GPa
            'composition': str      # If composition-dependent
        },
        'source': str,              # Data source/reference
        'confidence': float         # Confidence score (0-1)
    }
}
```

## Error Handling

### Standard Error Responses
```python
# Success response format
{
    'status': 'success',
    'data': {...},      # Feature-specific results
    'metadata': {
        'processing_time': float,
        'parameters_used': dict,
        'information_units_used': list
    },
    'warnings': []      # Non-fatal issues
}

# Error response format
{
    'status': 'error',
    'error_type': str,   # Error category
    'error_message': str, # Human-readable error description
    'error_details': {   # Technical details for debugging
        'traceback': str,
        'line_number': int,
        'function': str
    },
    'suggestions': []    # Suggested fixes or alternatives
}
```

### Common Error Types
- **ValidationError**: Invalid input parameters or formats
- **ProcessingError**: Errors during feature processing
- **DatabaseError**: Database connection or query failures
- **ModelError**: Issues with prediction models or generators
- **TimeoutError**: Processing exceeded time limits
- **ResourceError**: Insufficient computational resources

### Error Recovery Strategies
```python
# Example error handling in features
def process_feature(self, inputs):
    try:
        # Attempt primary processing method
        results = self._primary_processing(inputs)
        
    except DatabaseError as e:
        # Fall back to alternative databases
        if self.logger:
            self.logger.log(f'Database error: {e}, trying alternatives', 'warning')
        results = self._fallback_processing(inputs)
        
    except ModelError as e:
        # Use simpler model or empirical methods
        if self.logger:
            self.logger.log(f'Model error: {e}, using fallback method', 'warning')
        results = self._empirical_processing(inputs)
        
    except Exception as e:
        # Log error and re-raise with context
        if self.logger:
            self.logger.log(f'Unexpected error in {self.name}: {e}', 'error')
        raise ProcessingError(f"Feature {self.name} failed: {str(e)}")
    
    return results
```

## Configuration

### Database Configuration
Each database can be configured with specific parameters:

```python
# Example database configuration
database_config = {
    'mp': {
        'api_key': 'your_mp_api_key',
        'base_url': 'https://api.materialsproject.org',
        'version': 'v1',
        'timeout': 30,
        'retry_attempts': 3,
        'cache_enabled': True,
        'cache_directory': './cache/mp'
    },
    'icsd': {
        'database_path': '/path/to/icsd/database',
        'connection_params': {...},
        'query_timeout': 60
    }
}
```

### Model Configuration
Prediction models and generators can be configured:

```python
# Example model configuration
model_config = {
    'm3gnet': {
        'model_path': '/path/to/m3gnet/model',
        'device': 'cuda',  # or 'cpu'
        'batch_size': 32,
        'precision': 'float32',
        'cache_predictions': True
    },
    'mattergen': {
        'checkpoint_path': '/path/to/mattergen/checkpoint',
        'generation_temperature': 1.0,
        'max_atoms': 100,
        'generation_steps': 1000
    }
}
```

### Feature Configuration
Features can have specific configuration options:

```python
# Example feature configuration
feature_config = {
    'dft_calculation': {
        'default_functional': 'PBE',
        'k_point_density': 'standard',
        'convergence_criteria': {
            'energy': 1e-6,
            'force': 1e-5
        },
        'max_scf_cycles': 100,
        'mixing_parameter': 0.7
    },
    'band_structure': {
        'default_k_path': 'standard',
        'energy_range': [-10, 10],
        'interpolation_points': 100,
        'plot_format': 'matplotlib'
    }
}
```

## Performance Guidelines

### Computational Complexity

#### Database Operations
- **Search complexity**: O(log N) for indexed searches, O(N) for property filtering
- **Retrieval complexity**: O(1) for ID-based lookups, O(N) for complex queries
- **Memory usage**: Varies by database size and caching strategy

#### Generation Operations
- **Time complexity**: O(N × M) where N = number of candidates, M = generation complexity
- **Memory complexity**: O(N × A) where A = average atoms per structure
- **GPU acceleration**: Can provide 10-100× speedup for supported models

#### Prediction Operations
- **Time complexity**: O(N × P) where N = number of structures, P = prediction complexity
- **Batch processing**: Linear scaling with proper batching
- **Memory usage**: Scales with structure size and model complexity

### Optimization Strategies

#### Batch Processing
```python
# Process multiple materials efficiently
def batch_predict(self, materials_list, batch_size=32):
    results = []
    for i in range(0, len(materials_list), batch_size):
        batch = materials_list[i:i+batch_size]
        batch_results = self._predict_batch(batch)
        results.extend(batch_results)
    return results
```

#### Caching Strategies
```python
# Implement result caching
import hashlib
import pickle
import os

class CachedPredictor:
    def __init__(self, cache_dir='./cache'):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def predict(self, structure):
        # Generate cache key from structure
        cache_key = self._get_cache_key(structure)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        # Check if result is cached
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        
        # Compute prediction
        result = self._compute_prediction(structure)
        
        # Cache result
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)
        
        return result
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Memory Errors
**Symptoms**: Out of memory errors, system slowdown
**Causes**: Large datasets, inefficient memory usage
**Solutions**:
- Reduce batch sizes
- Enable incremental processing
- Use disk-based caching
- Monitor memory usage with system tools

#### 2. Timeout Errors
**Symptoms**: Operations fail with timeout messages
**Causes**: Network issues, heavy computational loads
**Solutions**:
- Increase timeout values in configuration
- Check network connectivity
- Use asynchronous processing for long operations
- Implement retry mechanisms

#### 3. Model Loading Failures
**Symptoms**: Prediction models fail to load
**Causes**: Missing model files, incompatible versions
**Solutions**:
- Verify model file paths and permissions
- Check model version compatibility
- Update model dependencies
- Use fallback models when available

#### 4. Database Connection Issues
**Symptoms**: Database queries fail or return no results
**Causes**: Network issues, API key problems, database maintenance
**Solutions**:
- Verify API keys and authentication
- Check database service status
- Test network connectivity
- Use alternative databases when available

### Debugging Tools

#### Logging Configuration
```python
import logging

# Configure logging for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('emos_debug.log'),
        logging.StreamHandler()
    ]
)

# Use in features and Information Units
logger = logging.getLogger(__name__)
logger.debug("Processing started with inputs: %s", inputs)
```

#### Performance Profiling
```python
import time
import memory_profiler

# Time profiling
def profile_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} took {end_time - start_time:.2f} seconds")
        return result
    return wrapper

# Memory profiling
@memory_profiler.profile
def memory_intensive_function():
    # Function that uses significant memory
    pass
```

## Version Information

### Current Version: 1.0.0

#### Feature Support Matrix
| Feature | Status | Dependencies |
|---------|--------|-------------|
| Material Search | Stable | Database APIs |
| Material Generation | Stable | AI Models |
| DFT Calculation | Stable | Quantum Codes |
| Interface Calculation | Stable | DFT/ML Models |
| Band Structure | Stable | Electronic Structure |
| Thermal Management | Beta | Thermal Models |
| Reliability Assessment | Beta | Reliability Data |
| Advanced Characterization | Alpha | Analysis Tools |

#### Information Unit Compatibility
| Type | Units Available | Status |
|------|----------------|--------|
| Databases | 8 | Stable |
| Generators | 8 | Stable |
| Predictors | 8 | Stable |

### API Versioning
- **v1.0**: Initial stable release
- **v1.1**: Enhanced error handling, improved caching
- **v1.2**: Additional prediction models, performance optimizations
- **v2.0**: Major architectural updates, new Information Units

### Migration Guides
For upgrading between versions, refer to the specific migration documentation provided with each release.

## Contributing

### Development Guidelines
- Follow PEP 8 style guidelines
- Include comprehensive docstrings
- Write unit tests for all new functionality
- Use type hints for function signatures
- Document configuration options and dependencies

### Adding New Components
Refer to the Feature and Information Unit development guides for detailed instructions on extending EMOS capabilities.

This reference provides the technical foundation for working with EMOS. For implementation examples and tutorials, see the User Guide and feature-specific documentation.