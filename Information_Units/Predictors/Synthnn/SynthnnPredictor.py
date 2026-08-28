"""SynthNN Predictor - Synthesis Neural Network for predicting synthesizability."""

from typing import Any
from Information_Units.Predictors.BasePredictor import BasePredictor
from Information_Units.Predictors.Synthnn.composition_helper import CompositionHelper
from Information_Units.Predictors.Synthnn.synthnn_model_helper import SynthnnModelHelper
from Information_Units.property_mappings.property_loader import load_source_property_mapping


class SynthnnPredictor(BasePredictor):
    """
    Lightweight wrapper for SynthNN deep learning model predicting synthesizability.
    
    Input format:  list[str]
    Output format: {"source": "synthnn", "results": list[dict]}
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
        self.source = "synthnn"
        self.model_helper = SynthnnModelHelper(logger=logger)
        self.composition_helper = CompositionHelper()
        self._mapped_output_properties = self._load_mapped_output_properties()
        self._check_output_properties_in_mapping({prop: None for prop in self.OUTPUT_PROPERTIES})

    def _load_mapped_output_properties(self) -> set:
        """Load SynthNN-mapped output properties from modular property files."""
        try:
            source_mapping = load_source_property_mapping(source='synthnn', source_type='predictors')
        except Exception as e:
            raise RuntimeError(f"Failed to load modular SynthNN property mappings: {str(e)}") from e

        mapped = set()
        for prop_name, synthnn_info in source_mapping.items():
            if isinstance(synthnn_info, dict) and synthnn_info.get('predictable'):
                mapped.add(prop_name)

        return mapped

    def _check_output_properties_in_mapping(self, properties: dict) -> None:
        """Ensure all output properties are declared under the SynthNN block in mappings."""
        missing = sorted(set(properties.keys()) - self._mapped_output_properties)
        if missing:
            raise ValueError(
                "SynthNN output properties missing in modular property mappings: "
                + ", ".join(missing)
            )

    def info(self):
        """Return description of predictor capabilities."""
        return (
            "SynthNN: Predicts synthesizability of inorganic crystalline materials "
            "from chemical composition. Returns synthesizability score (0-1) where "
            "higher values indicate higher likelihood of successful synthesis."
        )

    def predict(self, input_data: list[str]) -> dict[str, Any]:
        """
        Predict synthesizability from CIF files.
        
        Args:
            input_data (list[str]): CIF strings.
                Example:
                ["data_...", "data_..."]
        
        Returns:
            dict[str, Any]: Prediction payload with shape:
                {
                    "source": "synthnn",
                    "results": [
                        {
                            "index": int,
                            "status": "ok" | "error",
                            "properties": {
                                "synthesizable": bool | None,
                                "synthesizability_score": float | None
                            },
                            "warnings": list[str],
                            "error": str | None
                        }
                    ]
                }.
        
        Notes:
            - Empty or invalid input returns {"source": ..., "results": []}
            - Each item result contains: status, properties, warnings, error
            - Failed files use status='error' with null properties
            - Non-critical warnings are included in warnings array
            - Synthesizable threshold: score >= 0.70
            - CIF strings are processed independently (one failure doesn't crash batch)
        """
        cif_strings = self._extract_cif_strings(input_data)
        if self.logger:
            self.logger.log(f"SynthNN prediction starting for {len(cif_strings)} CIF strings", 'info')

        if not cif_strings:
            return {"source": self.source, "results": []}

        results = []

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
        
        # Process each CIF string
        for idx, cif_content in enumerate(cif_strings):
            try:
                # Extract composition from CIF
                formula, success = self.composition_helper.extract_from_cif(cif_content)
                
                if not success or formula is None:
                    error_msg = "Failed to parse CIF: Invalid syntax or missing structure data"
                    if self.logger:
                        self.logger.log(f"item[{idx}]: {error_msg}", 'error')
                    item = {
                        "index": idx,
                        "cif_input": cif_content,
                        **_build_result(status='error', error=error_msg),
                    }
                    results.append(item)
                    continue
                
                # Normalize composition
                normalized_formula = self.composition_helper.normalize_composition(formula)
                
                # Predict synthesizability score
                model_scores = self.model_helper.predict_batch([normalized_formula])
                score = model_scores.get(normalized_formula)
                
                if score is None:
                    error_msg = f"Model prediction failed for composition: {normalized_formula}"
                    if self.logger:
                        self.logger.log(f"item[{idx}]: {error_msg}", 'error')
                    item = {
                        "index": idx,
                        "cif_input": cif_content,
                        **_build_result(status='error', error=error_msg),
                    }
                    results.append(item)
                    continue
                
                # Determine if synthesizable (threshold: 0.70)
                synthesizable = score >= 0.70
                
                # Add warnings if present (can be extended for various warning conditions)
                warnings = []
                
                # Check for warnings (example: low confidence, etc.)
                if 0.65 <= score < 0.70:
                    warnings.append('Low synthesizability confidence (score near threshold)')
                
                item = {
                    "index": idx,
                    "cif_input": cif_content,
                    **_build_result(
                        status='ok',
                        synthesizable=synthesizable,
                        score=round(score, 4),
                        warnings=warnings
                    ),
                }
                results.append(item)
                
                if self.logger:
                    self.logger.log(
                        f"item[{idx}]: synthesizable={synthesizable}, score={score:.4f}",
                        'info'
                    )
                    
            except Exception as e:
                # Catch any unexpected errors
                error_msg = f"Unexpected error during prediction: {str(e)}"
                if self.logger:
                    self.logger.log(f"item[{idx}]: {error_msg}", 'error')
                item = {
                    "index": idx,
                    "cif_input": cif_content,
                    **_build_result(status='error', error=error_msg),
                }
                results.append(item)
        
        if self.logger:
            successful = sum(1 for r in results if r['status'] == 'ok')
            self.logger.log(
                f"SynthNN prediction complete: {successful}/{len(results)} successful",
                'info'
            )

        return {"source": self.source, "results": results}

    def _extract_cif_strings(self, input_data):
        """Extract valid CIF strings from direct list input."""
        if isinstance(input_data, list):
            return [s for s in input_data if isinstance(s, str) and s.strip()]
        return []
