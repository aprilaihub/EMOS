# Information Units

Information Units are the foundational components of EMOS that provide access to data, generation capabilities, and prediction models. They are designed with standardized interfaces to ensure consistency and enable easy integration within Features.

## Overview

EMOS includes three types of Information Units:

- **Databases**: Access to external materials databases and repositories
- **Generators**: AI-powered tools for generating new materials and structures  
- **Predictors**: Machine learning models for property prediction and analysis

Each type follows a common design pattern with:
- Standardized base classes
- Factory-based instantiation
- Consistent method interfaces
- Error handling and logging

## Design Principles

### Standardized Interface

All Information Units implement standard base classes:

```python
# Base classes define common interface
class BaseDatabase:
    def __init__(self, database_name, logger=None)
    def info(self) -> str
    def retrieve(self, inputs: dict) -> str

class BaseGenerator:
    def __init__(self, generator_name, logger=None)
    def info(self) -> str  
    def generate(self, inputs: dict) -> str

class BasePredictor:
    def __init__(self, predictor_name, logger=None)
    def info(self) -> str
    def predict(self, inputs: dict) -> str
```

### Factory Pattern

Information Units are registered in factory dictionaries for dynamic instantiation:

```python
# Factory dictionaries enable easy extension
database_factory = {
    "icsd": ICSD,
    "mp": MP,
    # Easy to add new databases
}

generator_factory = {
    "mattergen": MattergenGenerator,
    "gnome": GnomeGenerator,
    # Easy to add new generators
}

predictor_factory = {
    "m3gnet": M3gnetPredictor,
    "mattersim": MattersimPredictor,
    # Easy to add new predictors
}
```

### Consistent Usage Pattern

All Information Units follow the same usage pattern within Features:

```python
# Standard pattern for using Information Units
active_databases = inputs.get('active_databases', [])
for db_config in active_databases:
    db_key = db_config['value']
    if db_key in database_factory:
        db_instance = database_factory[db_key](db_key, self.logger)
        result = db_instance.retrieve(retrieve_inputs)
```

## Adding New Information Units

The modular design makes it easy to add new Information Units:

1. **Implement Base Class**: Create new class inheriting from appropriate base
2. **Register in Factory**: Add to corresponding factory dictionary
3. **No Changes Required**: Existing Features automatically discover new units

Example of adding a new database:

```python
# 1. Implement the database
class NewDatabase(BaseDatabase):
    def info(self):
        return "NewDatabase: Description of capabilities"
    
    def retrieve(self, inputs):
        # Implementation here
        return results

# 2. Register in factory
database_factory["newdb"] = NewDatabase

# 3. Automatically available in all Features
```

This modular approach ensures that EMOS can easily grow and adapt to new tools and databases as they become available.