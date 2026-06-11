"""Utilities for CIF parsing and composition extraction."""

from pymatgen.core.structure import Structure
from pymatgen.core.composition import Composition
import re


class CompositionHelper:
    """Utilities for CIF parsing and composition extraction."""
    
    @staticmethod
    def extract_from_cif(cif_content: str) -> tuple:
        """
        Parse CIF string and extract composition.
        
        Tries to extract composition from:
        1. _chemical_formula_sum field (if present)
        2. Calculated from structure (if CIF parse succeeds)
        
        Args:
            cif_content (str): CIF file content as string
            
        Returns:
            tuple: (formula_string, success: bool)
                - formula_string: Formula (e.g., "Al2O3")
                - success: True if parsing succeeded, False otherwise
                
        Examples:
            >>> (formula, success) = extract_from_cif(cif_content)
            >>> if success:
            ...     print(formula)  # "Al2O3"
            
        Gracefully handles:
            - Invalid CIF syntax → return (None, False)
            - Multi-site occupancies → uses formula from structure
            - Fractional coordinates → normalized
        """
        try:
            # Try to extract _chemical_formula_sum from CIF first
            # This is more reliable than calculating from atom positions
            formula_sum_match = re.search(r"_chemical_formula_sum\s+'([^']+)'", cif_content)
            if not formula_sum_match:
                formula_sum_match = re.search(r'_chemical_formula_sum\s+"([^"]+)"', cif_content)
            if not formula_sum_match:
                formula_sum_match = re.search(r'_chemical_formula_sum\s+(\S+)', cif_content)
            
            if formula_sum_match:
                # Parse the formula sum (e.g., "Al2 O3" -> "Al2O3")
                formula_sum = formula_sum_match.group(1).replace(' ', '')
                # Normalize using Composition to get alphabetical format
                try:
                    comp = Composition(formula_sum)
                    formula = comp.alphabetical_formula.replace(' ', '')
                    return (formula, True)
                except:
                    pass  # Fall through to structure-based extraction
            
            # Fall back to extracting from structure
            struct = Structure.from_str(cif_content, fmt='cif')
            formula = str(struct.composition.alphabetical_formula).replace(' ', '')
            return (formula, True)
        except Exception as e:
            return (None, False)
    
    @staticmethod
    def normalize_composition(formula: str) -> str:
        """
        Normalize composition for model input.
        
        Args:
            formula (str): Chemical formula string (e.g., "Al2O3", "Al4O6", " Al2O3 ")
            
        Returns:
            str: Normalized formula string suitable for SynthNN model
            
        Examples:
            >>> normalize_composition("Al2O3")
            'Al2O3'
            >>> normalize_composition("Al4O6")
            'Al2O3'
            >>> normalize_composition(" Al2O3 ")
            'Al2O3'
            
        Handles:
            - Whitespace removal
            - Stoichiometry standardization (Al4O6 → Al2O3)
            - Element ordering (alphabetical)
        """
        try:
            # Use pymatgen Composition to normalize
            comp = Composition(formula)
            # Return reduced formula as string
            return str(comp.reduced_formula)
        except Exception:
            # If normalization fails, return as-is after stripping whitespace
            return formula.strip()
