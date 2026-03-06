"""Utilities for CIF parsing and composition extraction."""

from pymatgen.core.structure import Structure
from pymatgen.core.composition import Composition


class CompositionHelper:
    """Utilities for CIF parsing and composition extraction."""
    
    @staticmethod
    def extract_from_cif(cif_content: str) -> tuple:
        """
        Parse CIF string using pymatgen and extract composition.
        
        Args:
            cif_content (str): CIF file content as string
            
        Returns:
            tuple: (formula_string, success: bool)
                - formula_string: Reduced formula (e.g., "Al2O3")
                - success: True if parsing succeeded, False otherwise
                
        Examples:
            >>> (formula, success) = extract_from_cif(cif_content)
            >>> if success:
            ...     print(formula)  # "Al2O3"
            
        Gracefully handles:
            - Invalid CIF syntax → return (None, False)
            - Multi-site occupancies → uses reduced formula
            - Fractional coordinates → normalized
        """
        try:
            struct = Structure.from_str(cif_content, fmt='cif')
            formula = str(struct.composition.reduced_formula)
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
