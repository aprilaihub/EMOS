# Features

Features are high-level workflows that combine multiple Information Units to solve specific materials science and electronics problems. Each feature implements a standardized processing pipeline while providing specialized functionality for different research domains.

Each feature follows a consistent workflow pattern:
1. **Input Extraction**: Parse and validate user inputs
2. **Feature-Specific Processing**: Execute domain-specific algorithms and any explicitly selected Information Units
3. **Output Formatting**: Structure results for presentation

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

Features that require Information Units expose feature-local selectors and process
only those selections. The global Information Units catalogue is not a workflow-wide
selection state. A database-enabled feature can use a pattern such as:

```python
def process_feature(self, inputs):
    results = []
    for db_config in inputs.get('active_databases', []):
        db_instance = database_factory[db_config['value']](
            db_config['value'], self.logger
        )
        results.append(db_instance.retrieve(retrieve_inputs))
    return {'database_results': results}
```

## Adding New Features

The modular design makes it easy to add new features:

1. **Implement BaseFeature**: Create new feature class
2. **Register in Factory**: Add to `feature_factory` dictionary
3. **Add Local IU Selection When Needed**: Do not depend on global selection state
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
            'parameter1': input_data.get('param1', 'default')
        }
    
    def process_feature(self, inputs):
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