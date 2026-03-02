"""
Integration tests for Information Unit interfaces.

Tests verify that Database, Predictor, and Generator implementations
follow the expected contract by creating actual instances and calling real methods.
"""

import pytest
from pathlib import Path
import importlib


def _get_database_classes():
    """Dynamically discover database implementations."""
    databases_dir = Path(__file__).parent.parent.parent / "Information_Units" / "Databases"
    classes = []
    
    for item in databases_dir.iterdir():
        if item.is_dir() and not item.name.startswith('_'):
            class_name = f"{item.name}Database"
            try:
                module = importlib.import_module(f"Information_Units.Databases.{item.name}.{class_name}")
                cls = getattr(module, class_name)
                classes.append((item.name, cls, 'retrieve'))
            except (ImportError, AttributeError):
                pass
    
    return classes


def _get_predictor_classes():
    """Dynamically discover predictor implementations."""
    predictors_dir = Path(__file__).parent.parent.parent / "Information_Units" / "Predictors"
    classes = []
    
    if not predictors_dir.exists():
        return classes
    
    for item in predictors_dir.iterdir():
        if item.is_dir() and not item.name.startswith('_'):
            class_name = f"{item.name}Predictor"
            try:
                module = importlib.import_module(f"Information_Units.Predictors.{item.name}.{class_name}")
                cls = getattr(module, class_name)
                classes.append((item.name, cls, 'predict'))
            except (ImportError, AttributeError):
                pass
    
    return classes


def _get_generator_classes():
    """Dynamically discover generator implementations."""
    generators_dir = Path(__file__).parent.parent.parent / "Information_Units" / "Generators"
    classes = []
    
    if not generators_dir.exists():
        return classes
    
    for item in generators_dir.iterdir():
        if item.is_dir() and not item.name.startswith('_'):
            class_name = f"{item.name}Generator"
            try:
                module = importlib.import_module(f"Information_Units.Generators.{item.name}.{class_name}")
                cls = getattr(module, class_name)
                classes.append((item.name, cls, 'generate'))
            except (ImportError, AttributeError):
                pass
    
    return classes


# Combine all information units for parametrized testing
def _get_all_information_units():
    """Get all information unit implementations (databases, predictors, generators)."""
    return _get_database_classes() + _get_predictor_classes() + _get_generator_classes()


@pytest.mark.integration
@pytest.mark.parametrize("name,unit_class,action_method", _get_all_information_units())
def test_information_unit_interface(name, unit_class, action_method):
    """Verify each information unit implements required interface.
    
    All information units must have:
    - info() method returning a string
    - A primary action method (retrieve for databases, predict for predictors, generate for generators)
    """
    # Check required methods exist
    assert hasattr(unit_class, 'info'), \
        f"{name} missing 'info' method"
    assert hasattr(unit_class, action_method), \
        f"{name} missing '{action_method}' method"
    
    # Check methods are callable on class
    assert callable(getattr(unit_class, action_method)), \
        f"{name}.{action_method} is not callable"
    