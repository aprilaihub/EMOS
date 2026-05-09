# Features

Features are high-level workflows that combine multiple Information Units to solve specific materials science and electronics problems. Each feature implements a standardized processing pipeline while providing specialized functionality for different research domains.

Each feature follows a consistent workflow pattern:
1. **Input Extraction**: Parse and validate user inputs
2. **Information Unit Processing**: Activate selected databases, generators, and predictors
3. **Feature-Specific Processing**: Execute domain-specific algorithms
4. **Output Formatting**: Structure results for presentation

## Feature Architecture

### Base Feature Interface

All features inherit from `BaseFeature` and implement four key methods:

```python
class BaseFeature(ABC):
    @abstractmethod
    def info(self) -> str:
        """Return feature description"""
        pass
    
    @abstractmethod  
    def extract_inputs(self, input_data: dict) -> dict:
        """Extract and validate inputs from input_data"""
        pass
    
    @abstractmethod
    def process_feature(self, inputs: dict) -> dict:
        """Core feature processing logic"""
        pass
    
    @abstractmethod
    def format_outputs(self, results: dict) -> dict:
        """Format results to expected output format"""
        pass
```

### Template Method Pattern

Features follow a standard template method pattern:

```python
def process(self, input_data: dict) -> dict:
    """Main process method - template pattern"""
    # Step 1: Extract inputs
    inputs = self.extract_inputs(input_data)
    
    # Step 2: Process feature
    results = self.process_feature(inputs)
    
    # Step 3: Format outputs
    outputs = self.format_outputs(results)
    
    return outputs
```

### Information Unit Integration

All features can utilize any combination of Information Units:

```python
def _process_information_units(self, inputs):
    """Standard pattern for processing Information Units"""
    
    # Process databases
    for db_config in inputs.get('active_databases', []):
        db_instance = database_factory[db_config['value']](
            db_config['value'], self.logger
        )
        db_results = db_instance.retrieve(retrieve_inputs)
    
    # Process generators
    for gen_config in inputs.get('active_generators', []):
        gen_instance = generator_factory[gen_config['value']](
            gen_config['value'], self.logger
        )
        gen_results = gen_instance.generate(generate_inputs)
    
    # Process predictors
    for pred_config in inputs.get('active_predictors', []):
        pred_instance = predictor_factory[pred_config['value']](
            pred_config['value'], self.logger
        )
        pred_results = pred_instance.predict(predict_inputs)
```

## Adding New Features

The modular design makes it easy to add new features:

1. **Implement BaseFeature**: Create new feature class
2. **Register in Factory**: Add to `feature_factory` dictionary
3. **Follow Patterns**: Use standard information unit processing
4. **Document Interface**: Specify inputs, outputs, and behavior

Example of adding a new feature:

```python
class NewFeature(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("New Feature", logger)
    
    def info(self):
        return "New Feature: Description of capabilities"
    
    def extract_inputs(self, input_data):
        return {
            'parameter1': input_data.get('param1', 'default'),
            'active_databases': input_data.get('active_databases', []),
            'active_generators': input_data.get('active_generators', []),
            'active_predictors': input_data.get('active_predictors', [])
        }
    
    def process_feature(self, inputs):
        # Process information units
        self._process_information_units(inputs)
        
        # Feature-specific logic
        results = self._custom_processing(inputs)
        
        return results
    
    def format_outputs(self, results):
        return {
            'result1': results.get('output1', 'N/A'),
            'result2': results.get('output2', 'N/A')
        }

# Register in factory
feature_factory["17"] = NewFeature
```

This modular approach ensures that EMOS can easily grow with new research capabilities while maintaining consistency and reliability.