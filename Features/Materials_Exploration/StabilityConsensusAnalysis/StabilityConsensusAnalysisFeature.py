import json
from typing import Any, Dict, List
from pymatgen.core import Structure
from Features.BaseFeature import BaseFeature
from Information_Units.Generators.GeneratorFactory import generator_factory
from Information_Units.Databases.DatabaseFactory import database_factory
from Information_Units.Predictors.PredictorFactory import predictor_factory


class StabilityConsensusAnalysisFeature(BaseFeature):
    """
    Analyzes multi-source stability consensus for crystal structures.
    
    Queries Materials Project and Alexandria for hull distances, runs MatterSim and CHGNet
    predictors in parallel, and evaluates stability using per-source thresholds.
    
    Output: Downloadable JSON report with per-structure, per-source stability assessment
    (✅ stable / ❌ unstable) with raw values for user interpretation.
    """
    
    # Stability thresholds (user can override)
    STABILITY_THRESHOLDS = {
        'materialsproject': {
            'metric': 'energy_above_hull_r2scan',
            'threshold': 0.05,  # eV/atom; below this = stable
            'unit': 'eV/atom',
            'description': 'Formation energy above convex hull'
        },
        'alexandria': {
            'metric': 'hull_distance',
            'threshold': 0.05,  # eV/atom; below this = stable
            'unit': 'eV/atom',
            'description': 'Distance to convex hull'
        },
        'mattersim': {
            'metric': 'relaxed_energy_per_atom',
            'threshold': 0.0,  # eV/atom; negative energy = stable by user rule
            'unit': 'eV/atom',
            'description': 'Predicted relaxed energy per atom (negative = stable)'
        },
        'chgnet': {
            'metric': 'relaxed_energy_per_atom',
            'threshold': 0.0,  # eV/atom; negative energy = stable by user rule
            'unit': 'eV/atom',
            'description': 'Predicted relaxed energy per atom (negative = stable)'
        }
    }
    
    def __init__(self, logger=None):
        super().__init__("Stability Consensus Analysis", logger)
    
    def info(self):
        return "Stability Consensus Analysis: Query materials databases and run predictors to evaluate multi-source stability consensus"
    
    def extract_inputs(self, input_data):
        return {
            'cif_file': input_data.get('cif_file', ''),
            'active_databases': input_data.get('active_databases', []),
            'active_predictors': input_data.get('active_predictors', []),
        }
    
    def process_feature(self, inputs):
        """Main processing pipeline for stability consensus analysis."""
        try:
            if self.logger:
                self.logger.log('Initializing Stability Consensus Analysis...', 'info')
            
            # Extract CIF content
            cif_content = inputs.get('cif_file', '')
            if not cif_content:
                raise ValueError("No CIF file provided")
            
            if self.logger:
                self.logger.log('Parsing CIF structure...', 'info')
            
            # Parse CIF and extract composition
            structure = Structure.from_str(cif_content, fmt='cif')
            # Use reduced formula for database queries (e.g., Al2O3), not spaced formula (e.g., Al4 O6).
            composition_formula = structure.composition.reduced_formula
            
            if self.logger:
                self.logger.log(f'Extracted composition: {composition_formula}', 'info')
            
            # Initialize results
            consensus_results = {
                'composition': composition_formula,
                'sources': {},
                'summary': {}
            }
            
            # Query databases
            active_databases = inputs.get('active_databases', [])
            if active_databases:
                if self.logger:
                    self.logger.log(f'Querying {len(active_databases)} databases...', 'info')
                
                db_results = self._query_databases(active_databases, composition_formula)
                consensus_results['sources'].update(db_results)
            
            # Run predictors in parallel
            active_predictors = inputs.get('active_predictors', [])
            if active_predictors:
                if self.logger:
                    self.logger.log(f'Running {len(active_predictors)} predictors in parallel...', 'info')
                
                predictor_results = self._run_predictors_parallel(active_predictors, cif_content)
                consensus_results['sources'].update(predictor_results)
            
            # Compute consensus summary
            consensus_results['summary'] = self._compute_consensus_summary(consensus_results['sources'])
            
            if self.logger:
                self.logger.log('Stability Consensus Analysis processing completed', 'info')
            
            return consensus_results
        
        except Exception as e:
            if self.logger:
                self.logger.log(f'Error: {str(e)}', 'error')
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def format_outputs(self, results):
        """Format results for frontend (JSON string for download)."""
        if 'error' in results:
            return {
                'error': results['error'],
                'downloadResultsJson': None,
            }
        
        return {
            'composition': results.get('composition'),
            'sources': results.get('sources', {}),
            'summary': results.get('summary', {}),
            'downloadResultsJson': json.dumps(results, indent=2, ensure_ascii=False),
        }
    
    def _query_databases(self, active_databases: List[Dict], composition: str):
        """Query selected databases for hull distances and formation energies."""
        results = {}
        
        for db_config in active_databases:
            db_key = db_config['value']
            db_name = db_config['name']
            
            try:
                if db_key not in database_factory:
                    if self.logger:
                        self.logger.log(f'Database {db_name} not found in factory', 'warning')
                    continue
                
                if self.logger:
                    self.logger.log(f'Querying {db_name}...', 'info')
                
                # Instantiate database and retrieve data
                db_instance = database_factory[db_key](db_key, self.logger)
                threshold_cfg = self.STABILITY_THRESHOLDS.get(db_key, {})
                metric_name = threshold_cfg.get('metric')
                threshold = threshold_cfg.get('threshold', 0.05)

                db_inputs = {'target_compositions': composition}
                # Ask DB for entries under the stability threshold so we can emit a binary decision.
                if metric_name:
                    db_inputs[metric_name] = [0.0, threshold]

                db_result = db_instance.retrieve(db_inputs)

                # Extract stability metrics
                source_name = db_result.get('source', db_key).lower()
                stability_data = self._evaluate_database_stability(source_name, db_result)
                results[source_name] = stability_data
                
                if self.logger:
                    self.logger.log(f'{db_name}: Retrieved {len(db_result.get("cif_strings", []))} structures', 'info')
            
            except Exception as e:
                if self.logger:
                    self.logger.log(f'Error querying {db_name}: {str(e)}', 'error')
                results[db_key] = {
                    'status': 'error',
                    'error': str(e),
                    'stability': None
                }

        return results
    
    def _evaluate_database_stability(self, source_name: str, db_result: Dict) -> Dict[str, Any]:
        """Evaluate stability for database results (hull distance / energy above hull)."""
        cif_strings = db_result.get('cif_strings', [])

        # Extract stability metric from queries
        queries = db_result.get('queries', {})
        threshold_cfg = self.STABILITY_THRESHOLDS.get(source_name, {})
        metric_name = threshold_cfg.get('metric', 'hull_distance')
        threshold = threshold_cfg.get('threshold', 0.05)

        if not cif_strings:
            # If we queried with a threshold filter, no matches implies unstable under that criterion.
            filter_value = queries.get(metric_name) if isinstance(queries, dict) else None
            if isinstance(filter_value, list) and len(filter_value) == 2:
                return {
                    'status': 'success',
                    'stability': '❌ Unstable',
                    'raw_value': None,
                    'threshold': threshold,
                    'unit': threshold_cfg.get('unit', ''),
                    'description': threshold_cfg.get('description', ''),
                    'num_matches': 0,
                    'message': f'No entries found with {metric_name} <= {threshold}'
                }
            return {
                'status': 'no_matches',
                'stability': None,
                'raw_value': None,
                'message': 'No matching structures found in database'
            }

        # For databases, use the first matching structure's stability metric
        if isinstance(queries, dict) and metric_name in queries:
            raw_value = queries[metric_name]
        else:
            # Try to extract from returned data
            raw_value = queries.get(metric_name) if isinstance(queries, dict) else None

        # If metric is a filter range and we got matches, infer stable from filter success.
        if isinstance(raw_value, list) and len(raw_value) == 2:
            return {
                'status': 'success',
                'stability': '✅ Stable',
                'raw_value': None,
                'threshold': threshold,
                'unit': threshold_cfg.get('unit', ''),
                'description': threshold_cfg.get('description', ''),
                'num_matches': len(cif_strings),
                'message': f'{len(cif_strings)} entries found with {metric_name} <= {threshold}'
            }

        if raw_value is None:
            return {
                'status': 'metric_unavailable',
                'stability': None,
                'raw_value': None,
                'message': f'Stability metric "{metric_name}" not available'
            }
        
        # Evaluate stability
        is_stable = raw_value < threshold
        
        return {
            'status': 'success',
            'stability': '✅ Stable' if is_stable else '❌ Unstable',
            'raw_value': round(raw_value, 4),
            'threshold': threshold,
            'unit': threshold_cfg.get('unit', ''),
            'description': threshold_cfg.get('description', ''),
            'num_matches': len(cif_strings)
        }
    
    def _run_predictors_parallel(self, active_predictors: List[Dict], cif_content: str) -> Dict[str, Any]:
        """Run predictors in parallel (async style where possible)."""
        results = {}
        
        # Prepare predictor instances
        predictor_instances = []
        for pred_config in active_predictors:
            pred_key = pred_config['value']
            pred_name = pred_config['name']
            
            if pred_key not in predictor_factory:
                if self.logger:
                    self.logger.log(f'Predictor {pred_name} not found in factory', 'warning')
                continue
            
            pred_instance = predictor_factory[pred_key](pred_key, self.logger)
            predictor_instances.append((pred_key, pred_name, pred_instance))
        
        # Run predictors (sequential for now, but ready for async)
        for pred_key, pred_name, pred_instance in predictor_instances:
            try:
                if self.logger:
                    self.logger.log(f'Running {pred_name}...', 'info')
                
                # Run prediction only on the uploaded structure.
                pred_result = pred_instance.predict([cif_content])
                
                # Evaluate stability
                source_name = pred_result.get('source', pred_key).lower()
                stability_data = self._evaluate_predictor_stability(source_name, pred_result)
                results[source_name] = stability_data
                
                if self.logger:
                    if 'error' in stability_data:
                        self.logger.log(f'{pred_name}: {stability_data["error"]}', 'error')
                    else:
                        self.logger.log(f'{pred_name}: {stability_data["stability"]}', 'info')
            
            except Exception as e:
                if self.logger:
                    self.logger.log(f'Error running {pred_name}: {str(e)}', 'error')
                results[pred_key] = {
                    'status': 'error',
                    'error': str(e),
                    'stability': None
                }
        
        return results
    
    def _evaluate_predictor_stability(self, source_name: str, pred_result: Dict) -> Dict[str, Any]:
        """Evaluate predictor stability using negative predicted energy per atom."""
        results_list = pred_result.get('results', [])
        
        if not results_list or len(results_list) == 0:
            return {
                'status': 'no_results',
                'stability': None,
                'raw_value': None,
                'error': 'No prediction results'
            }
        
        first_result = results_list[0]
        
        # Check for errors in result
        if first_result.get('error'):
            return {
                'status': 'prediction_error',
                'stability': None,
                'raw_value': None,
                'error': first_result.get('error')
            }
        
        properties = first_result.get('properties', {})
        threshold_cfg = self.STABILITY_THRESHOLDS.get(source_name, {})
        threshold = threshold_cfg.get('threshold', 0.0)

        user_num_atoms = properties.get('num_atoms')
        user_energy = properties.get('relaxed_energy', properties.get('energy'))
        if user_num_atoms in (None, 0) or user_energy is None:
            return {
                'status': 'metric_unavailable',
                'stability': None,
                'raw_value': None,
                'error': 'No predictor energy available for uploaded structure'
            }

        user_e_per_atom = float(user_energy) / float(user_num_atoms)
        is_stable = user_e_per_atom < threshold
        
        return {
            'status': 'success',
            'stability': '✅ Stable' if is_stable else '❌ Unstable',
            'raw_value': round(user_e_per_atom, 4),
            'threshold': threshold,
            'unit': threshold_cfg.get('unit', ''),
            'description': threshold_cfg.get('description', ''),
            'energy': round(float(user_energy), 4),
            'energy_unit': 'eV',
            'message': 'Stable if predicted relaxed energy per atom is negative'
        }
    
    def _compute_consensus_summary(self, sources: Dict[str, Any]) -> Dict[str, Any]:
        """Compute overall consensus summary across all sources."""
        stable_count = 0
        unstable_count = 0
        error_count = 0
        
        for source_data in sources.values():
            stability_value = source_data.get('stability')
            stability_str = stability_value if isinstance(stability_value, str) else ''
            if '✅' in stability_str:
                stable_count += 1
            elif '❌' in stability_str:
                unstable_count += 1
            else:
                error_count += 1
        
        total = stable_count + unstable_count
        
        if total == 0:
            consensus = 'Insufficient data'
        elif stable_count == total:
            consensus = '✅ All sources agree: Stable'
        elif unstable_count == total:
            consensus = '❌ All sources agree: Unstable'
        else:
            consensus = f'⚠️  Mixed opinion: {stable_count} stable, {unstable_count} unstable'
        
        return {
            'consensus': consensus,
            'stable_count': stable_count,
            'unstable_count': unstable_count,
            'error_count': error_count,
            'total_sources': len(sources)
        }
