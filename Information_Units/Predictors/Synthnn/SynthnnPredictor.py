"""SynthNN Predictor - Synthesis Neural Network for predicting synthesizability."""

import json
from pathlib import Path
from Information_Units.Predictors.BasePredictor import BasePredictor
from Information_Units.Predictors.Synthnn.composition_helper import CompositionHelper
from Information_Units.Predictors.Synthnn.synthnn_model_helper import SynthnnModelHelper


class SynthnnPredictor(BasePredictor):
    """
    Lightweight wrapper for SynthNN deep learning model predicting synthesizability.
    
    Input format:  {filename: filepath, ...}
    Output format: {filename: {status, properties, warnings, error}, ...}
    """

    OUTPUT_PROPERTIES = ('synthesizable', 'synthesizability_score')
    
    def __init__(self, predictor_name='synthnn', logger=None):
        """
        Initialize SynthNN predictor.
        
        Args:
            predictor_name (str): Name of predictor (default: 'synthnn')
            logger: Optional logger instance
        """
        super().__init__(predictor_name, logger)
        self.model_helper = SynthnnModelHelper(logger=logger)
        self.composition_helper = CompositionHelper()
        self._mapped_output_properties = self._load_mapped_output_properties()
        self._check_output_properties_in_mapping({prop: None for prop in self.OUTPUT_PROPERTIES})

    def _load_mapped_output_properties(self) -> set:
        """Load SynthNN-mapped output properties from property_mappings.json."""
        mapping_file = Path(__file__).resolve().parents[2] / 'property_mappings.json'

        try:
            with mapping_file.open('r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load property mappings from {mapping_file}: {str(e)}"
            ) from e

        mapped = set()
        for prop_name, prop_details in data.get('properties', {}).items():
            synthnn_info = prop_details.get('synthnn')
            if isinstance(synthnn_info, dict) and synthnn_info.get('predicatble'):
                mapped.add(prop_name)

        return mapped

    def _check_output_properties_in_mapping(self, properties: dict) -> None:
        """Ensure all output properties are declared under the SynthNN block in mappings."""
        missing = sorted(set(properties.keys()) - self._mapped_output_properties)
        if missing:
            raise ValueError(
                "SynthNN output properties missing in property_mappings.json: "
                + ", ".join(missing)
            )

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
            dict: Synthesizability properties for each input file
                Example:
                {
                    'Al2O3.cif': {
                        'status': 'ok',
                        'properties': {
                            'synthesizable': True,
                            'synthesizability_score': 0.92
                        },
                        'warnings': [],
                        'error': None
                    },
                    'FeO.cif': {
                        'status': 'ok',
                        'properties': {
                            'synthesizable': False,
                            'synthesizability_score': 0.31
                        },
                        'warnings': ['Low synthesizability confidence (score near threshold)'],
                        'error': None
                    },
                    'invalid.cif': {
                        'status': 'error',
                        'properties': {
                            'synthesizable': None,
                            'synthesizability_score': None
                        },
                        'warnings': [],
                        'error': 'Failed to parse CIF: Invalid syntax'
                    }
                }
        
        Notes:
            - Empty input returns empty dict: {}
            - Each file result contains: status, properties, warnings, error
            - Failed files use status='error' with null properties
            - Non-critical warnings are included in warnings array
            - Synthesizable threshold: score >= 0.70
            - All files processed independently (one failure doesn't crash batch)
        """
        if self.logger:
            self.logger.log(f"SynthNN prediction starting for {len(input_data)} files", 'info')
        
        # Handle empty input
        if not input_data:
            return {}
        
        results = {}

        def _build_result(status, synthesizable=None, score=None, warnings=None, error=None):
            output_properties = {
                'synthesizable': synthesizable,
                'synthesizability_score': score
            }
            self._check_output_properties_in_mapping(output_properties)

            return {
                'status': status,
                'properties': output_properties,
                'warnings': warnings or [],
                'error': error
            }
        
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
                    results[filename] = _build_result(status='error', error=error_msg)
                    continue
                except Exception as e:
                    error_msg = f"Failed to read file: {str(e)}"
                    if self.logger:
                        self.logger.log(f"{filename}: {error_msg}", 'error')
                    results[filename] = _build_result(status='error', error=error_msg)
                    continue
                
                # Extract composition from CIF
                formula, success = self.composition_helper.extract_from_cif(cif_content)
                
                if not success or formula is None:
                    error_msg = "Failed to parse CIF: Invalid syntax or missing structure data"
                    if self.logger:
                        self.logger.log(f"{filename}: {error_msg}", 'error')
                    results[filename] = _build_result(status='error', error=error_msg)
                    continue
                
                # Normalize composition
                normalized_formula = self.composition_helper.normalize_composition(formula)
                
                # Predict synthesizability score
                model_scores = self.model_helper.predict_batch([normalized_formula])
                score = model_scores.get(normalized_formula)
                
                if score is None:
                    error_msg = f"Model prediction failed for composition: {normalized_formula}"
                    if self.logger:
                        self.logger.log(f"{filename}: {error_msg}", 'error')
                    results[filename] = _build_result(status='error', error=error_msg)
                    continue
                
                # Determine if synthesizable (threshold: 0.70)
                synthesizable = score >= 0.70
                
                # Add warnings if present (can be extended for various warning conditions)
                warnings = []
                
                # Check for warnings (example: low confidence, etc.)
                if 0.65 <= score < 0.70:
                    warnings.append('Low synthesizability confidence (score near threshold)')
                
                results[filename] = _build_result(
                    status='ok',
                    synthesizable=synthesizable,
                    score=round(score, 4),
                    warnings=warnings
                )
                
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
                results[filename] = _build_result(status='error', error=error_msg)
        
        if self.logger:
            successful = sum(1 for r in results.values() if r['status'] == 'ok')
            self.logger.log(
                f"SynthNN prediction complete: {successful}/{len(results)} successful",
                'info'
            )
        
        return results