"""SynthNN Predictor - Synthesis Neural Network for predicting synthesizability."""

from pathlib import Path
from Information_Units.Predictors.BasePredictor import BasePredictor
from Information_Units.Predictors.Synthnn.composition_helper import CompositionHelper
from Information_Units.Predictors.Synthnn.synthnn_model_helper import SynthnnModelHelper


class SynthnnPredictor(BasePredictor):
    """
    Lightweight wrapper for SynthNN deep learning model predicting synthesizability.
    
    Phase 1 (Current): Mock predictions for testing and architecture validation
    Phase 2/3 (Future): Real SynthNN model integration
    
    Input format:  {filename: filepath, ...}
    Output format: {filename: {property: value, ...}, ...}
    """
    
    def __init__(self, predictor_name='synthnn', logger=None, use_mock=True):
        """
        Initialize SynthNN predictor.
        
        Args:
            predictor_name (str): Name of predictor (default: 'synthnn')
            logger: Optional logger instance
            use_mock (bool): If True, use mock predictions (Phase 1).
                           Ignored in Phase 2/3 (always use model).
                           Default: True
        """
        super().__init__(predictor_name, logger)
        self.model_helper = SynthnnModelHelper(logger=logger, use_mock=use_mock)
        self.composition_helper = CompositionHelper()

    def info(self):
        """Return description of predictor capabilities."""
        return (
            "SynthNN: Predicts synthesizability of inorganic crystalline materials "
            "from chemical composition. Returns synthesizability score (0-1) where "
            "higher values indicate higher likelihood of successful synthesis."
        )

    def predict(self, input_data: dict) -> dict:
        """
        Predict synthesizability from CIF files.
        
        Args:
            input_data (dict): Mapping of filenames to file paths
                Example:
                {
                    'Al2O3.cif': '/path/to/Al2O3.cif',
                    'FeO.cif': '/path/to/FeO.cif',
                    'invalid.cif': '/path/to/corrupted.cif'
                }
        
        Returns:
            dict: Synthesizability predictions for each input file
                Example:
                {
                    'Al2O3.cif': {
                        'synthesizable': True,
                        'synthesizability_score': 0.92,
                        'warnings': ['CIF missing symmetry information']  # optional
                    },
                    'FeO.cif': {
                        'synthesizable': False,
                        'synthesizability_score': 0.31
                    },
                    'invalid.cif': {
                        'synthesizable': None,
                        'synthesizability_score': None,
                        'error': 'Failed to parse CIF: Invalid syntax'
                    }
                }
        
        Notes:
            - Empty input returns empty dict: {}
            - Failed files included in output with null values + 'error' key
            - Non-critical warnings included as optional 'warnings' array
            - Synthesizable threshold: score >= 0.70
            - All files processed independently (one failure doesn't crash batch)
        """
        if self.logger:
            self.logger.log(f"SynthNN prediction starting for {len(input_data)} files", 'info')
        
        # Handle empty input
        if not input_data:
            return {}
        
        results = {}
        
        # Process each file
        for filename, filepath in input_data.items():
            try:
                # Read CIF file
                try:
                    cif_content = Path(filepath).read_text()
                except FileNotFoundError:
                    error_msg = f"File not found: {filepath}"
                    if self.logger:
                        self.logger.log(f"{filename}: {error_msg}", 'error')
                    results[filename] = {
                        'synthesizable': None,
                        'synthesizability_score': None,
                        'error': error_msg
                    }
                    continue
                except Exception as e:
                    error_msg = f"Failed to read file: {str(e)}"
                    if self.logger:
                        self.logger.log(f"{filename}: {error_msg}", 'error')
                    results[filename] = {
                        'synthesizable': None,
                        'synthesizability_score': None,
                        'error': error_msg
                    }
                    continue
                
                # Extract composition from CIF
                formula, success = self.composition_helper.extract_from_cif(cif_content)
                
                if not success or formula is None:
                    error_msg = "Failed to parse CIF: Invalid syntax or missing structure data"
                    if self.logger:
                        self.logger.log(f"{filename}: {error_msg}", 'error')
                    results[filename] = {
                        'synthesizable': None,
                        'synthesizability_score': None,
                        'error': error_msg
                    }
                    continue
                
                # Normalize composition
                normalized_formula = self.composition_helper.normalize_composition(formula)
                
                # Predict synthesizability score
                predictions = self.model_helper.predict_batch([normalized_formula])
                score = predictions.get(normalized_formula)
                
                if score is None:
                    error_msg = f"Model prediction failed for composition: {normalized_formula}"
                    if self.logger:
                        self.logger.log(f"{filename}: {error_msg}", 'error')
                    results[filename] = {
                        'synthesizable': None,
                        'synthesizability_score': None,
                        'error': error_msg
                    }
                    continue
                
                # Determine if synthesizable (threshold: 0.70)
                synthesizable = score >= 0.70
                
                # Add result for successful prediction
                result_entry = {
                    'synthesizable': synthesizable,
                    'synthesizability_score': round(score, 4)
                }
                
                # Add warnings if present (can be extended for various warning conditions)
                warnings = []
                
                # Check for warnings (example: low confidence, etc.)
                if 0.65 <= score < 0.70:
                    warnings.append('Low synthesizability confidence (score near threshold)')
                
                if warnings:
                    result_entry['warnings'] = warnings
                
                results[filename] = result_entry
                
                if self.logger:
                    self.logger.log(
                        f"{filename}: synthesizable={synthesizable}, score={score:.4f}",
                        'info'
                    )
                    
            except Exception as e:
                # Catch any unexpected errors
                error_msg = f"Unexpected error during prediction: {str(e)}"
                if self.logger:
                    self.logger.log(f"{filename}: {error_msg}", 'error')
                results[filename] = {
                    'synthesizable': None,
                    'synthesizability_score': None,
                    'error': error_msg
                }
        
        if self.logger:
            successful = sum(1 for r in results.values() if r['synthesizable'] is not None)
            self.logger.log(
                f"SynthNN prediction complete: {successful}/{len(results)} successful",
                'info'
            )
        
        return results