"""
Shared fixtures and utilities for integration tests.

Import CIF utilities as needed:
    from conftest import validate_cif_file, extract_nelements_from_cif, etc.
"""

import pytest


def validate_cif_file(path):
    """Validate CIF file has correct structure and content."""
    with open(path, 'r') as f:
        content = f.read()
    
    # Check required CIF format fields
    assert 'data_' in content, "Missing CIF data block"
    assert '_cell_length_a' in content, "Missing lattice parameter"
    assert '_atom_site_label' in content or '_atom_site_type_symbol' in content, \
        "Missing atomic site information"
    
    return content


def validate_cif_string(content):
    """Validate CIF text has correct structure and content."""
    # Check required CIF format fields
    assert 'data_' in content, "Missing CIF data block"
    assert '_cell_length_a' in content, "Missing lattice parameter"
    assert '_atom_site_label' in content or '_atom_site_type_symbol' in content, \
        "Missing atomic site information"
    return content


def extract_formula_from_cif(content):
    """Extract chemical formula from CIF file."""
    for line in content.split('\n'):
        # Try _chemical_formula_sum first
        if line.startswith('_chemical_formula_sum'):
            parts = line.split("'")
            if len(parts) >= 2:
                return parts[1].strip()
        # Try _chemical_formula_structural
        if line.startswith('_chemical_formula_structural'):
            parts = line.split("'")
            if len(parts) >= 2:
                return parts[1].strip()
    return None


def extract_nelements_from_cif(content):
    """Extract number of unique chemical elements from CIF file."""
    elements = set()
    in_atom_site_block = False
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Check if we're in the atom site block
        if line.startswith('_atom_site_type_symbol'):
            in_atom_site_block = True
            continue
        
        # If we hit another loop or data block, we're done
        if in_atom_site_block and (line.startswith('loop_') or line.startswith('_') or line.startswith('data_')):
            if not line.startswith('_atom_site'):
                break
        
        # Extract element symbols from atom site lines
        if in_atom_site_block and line and not line.startswith('_'):
            parts = line.split()
            if parts:
                element = parts[0]
                # Remove oxidation states and other suffixes
                element = ''.join(c for c in element if c.isalpha())
                if element and element[0].isupper():
                    elements.add(element)
    
    return len(elements)


def extract_nperiodic_dimensions_from_cif(content):
    """
    Extract number of periodic dimensions from CIF file.
    Returns 3 for typical crystal structures with all cell parameters defined.
    """
    has_a = False
    has_b = False
    has_c = False
    
    for line in content.split('\n'):
        if line.startswith('_cell_length_a'):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    val = float(parts[1])
                    if val > 0:
                        has_a = True
                except ValueError:
                    pass
        elif line.startswith('_cell_length_b'):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    val = float(parts[1])
                    if val > 0:
                        has_b = True
                except ValueError:
                    pass
        elif line.startswith('_cell_length_c'):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    val = float(parts[1])
                    if val > 0:
                        has_c = True
                except ValueError:
                    pass
    
    # If all three cell dimensions are present and positive, it's 3D
    if has_a and has_b and has_c:
        return 3
    elif has_a and has_b:
        return 2
    elif has_a:
        return 1
    return 0
