import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from pymatgen.core import Structure, Composition
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from Features.BaseFeature import BaseFeature
from Information_Units.Databases.DatabaseFactory import database_factory
from Information_Units.Predictors.PredictorFactory import predictor_factory


class StabilityConsensusAnalysisCancelled(Exception):
    """Raised internally when a user cancels an active analysis."""


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
            'metric': 'formation_enthalpy_per_atom',
            'threshold': 0.0,  # eV/atom; negative ΔHf indicates thermodynamic favorability
            'unit': 'eV/atom',
            'description': 'MLIP formation enthalpy per atom (ΔHf < 0 => stable)'
        },
        'chgnet': {
            'metric': 'formation_enthalpy_per_atom',
            'threshold': 0.0,  # eV/atom; negative ΔHf indicates thermodynamic favorability
            'unit': 'eV/atom',
            'description': 'MLIP formation enthalpy per atom (ΔHf < 0 => stable)'
        }
    }
    
    def __init__(self, logger=None):
        super().__init__("Stability Consensus Analysis", logger)
        self._cancel_event = threading.Event()

    def cancel(self) -> Dict[str, str]:
        """Request cooperative termination of the active analysis."""
        self._cancel_event.set()
        if self.logger:
            self.logger.log('Stability Consensus Analysis cancellation requested', 'warning')
        return {
            'status': 'cancelled',
            'message': 'Cancellation requested. Stopping Stability Consensus Analysis.',
        }

    def _check_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise StabilityConsensusAnalysisCancelled(
                'Stability Consensus Analysis was cancelled by the user.'
            )
    
    def info(self):
        return "Stability Consensus Analysis: Query materials databases and run predictors to evaluate multi-source stability consensus"
    
    def extract_inputs(self, input_data):
        cif_files = input_data.get('cif_files', [])
        if isinstance(cif_files, str):
            try:
                cif_files = json.loads(cif_files)
            except Exception:
                cif_files = []

        return {
            'cif_file': input_data.get('cif_file', ''),
            'cif_files': cif_files,
            'active_databases': input_data.get('active_databases', []),
            'active_predictors': input_data.get('active_predictors', []),
        }

    def _normalize_cif_inputs(self, inputs: Dict[str, Any]) -> List[Dict[str, str]]:
        """Return list of CIF entries in shape: [{name, content}, ...]."""
        normalized: List[Dict[str, str]] = []

        raw_batch = inputs.get('cif_files', []) or []
        for idx, item in enumerate(raw_batch):
            if isinstance(item, dict):
                content = item.get('content', '')
                if content:
                    normalized.append({
                        'name': item.get('name', f'cif_{idx + 1}.cif'),
                        'content': content,
                    })
            elif isinstance(item, str) and item.strip():
                normalized.append({
                    'name': f'cif_{idx + 1}.cif',
                    'content': item,
                })

        # Backward-compatible single-CIF path.
        if not normalized:
            single = inputs.get('cif_file', '')
            if single:
                normalized.append({'name': 'uploaded.cif', 'content': single})

        return normalized

    def _process_single_cif(
        self,
        cif_name: str,
        cif_content: str,
        inputs: Dict[str, Any],
        db_cache: Dict[str, Dict[str, Any]],
        element_ref_cache: Dict[str, Optional[float]],
    ) -> Dict[str, Any]:
        """Process one CIF and return per-file result payload."""
        self._check_cancelled()
        if self.logger:
            self.logger.log(f'Processing {cif_name}...', 'info')

        # Parse CIF and extract composition, space group
        structure = Structure.from_str(cif_content, fmt='cif')
        self._check_cancelled()
        composition = structure.composition
        composition_formula = composition.reduced_formula
        mp_materials_id = self._extract_materials_project_id(cif_content)
        element_fractions = {
            el.symbol: float(composition.get_atomic_fraction(el))
            for el in composition.elements
        }
        
        # Extract space group number and symbol for database search refinement
        space_group_number = None
        space_group_symbol = None
        try:
            analyzer = SpacegroupAnalyzer(structure, symprec=0.1)
            space_group_number = analyzer.get_space_group_number()
            space_group_symbol = analyzer.get_space_group_symbol()
            if self.logger:
                self.logger.log(
                    f'Extracted space group #{space_group_number} ({space_group_symbol}) from {cif_name}',
                    'info',
                )
        except Exception as e:
            if self.logger:
                self.logger.log(f'Could not determine space group for {cif_name}: {e}', 'warning')

        if self.logger:
            self.logger.log(f'Extracted composition for {cif_name}: {composition_formula}', 'info')

        result = {
            'cif_name': cif_name,
            'composition': composition_formula,
            'space_group_number': space_group_number,
            'space_group_symbol': space_group_symbol,
            'materialsproject_id': mp_materials_id,
            'sources': {},
            'summary': {},
        }

        active_databases = inputs.get('active_databases', [])
        if active_databases:
            self._check_cancelled()
            cache_bits = [composition_formula]
            if space_group_number is not None:
                cache_bits.append(str(space_group_number))
            if mp_materials_id:
                cache_bits.append(mp_materials_id)
            cache_key = '_'.join(cache_bits)
            if cache_key in db_cache:
                db_results = db_cache[cache_key]
                if self.logger:
                    self.logger.log(f'Using cached database results for composition {composition_formula} (space group #{space_group_number})', 'info')
            else:
                db_results = self._query_databases(
                    active_databases,
                    composition_formula,
                    space_group_number,
                    mp_materials_id,
                )
                self._check_cancelled()
                db_cache[cache_key] = db_results
                # Annotate each source result with the CIF space group for UI transparency
                for src_data in db_results.values():
                    if isinstance(src_data, dict) and space_group_symbol:
                        src_data['cif_space_group'] = space_group_symbol
            result['sources'].update(db_results)

        active_predictors = inputs.get('active_predictors', [])
        if active_predictors:
            self._check_cancelled()
            element_reference_cifs = self._get_element_reference_cifs(
                inputs.get('active_databases', []),
                list(element_fractions.keys()),
                element_ref_cache,
            )
            predictor_results = self._run_predictors_parallel(
                active_predictors,
                cif_content,
                element_fractions,
                element_reference_cifs,
            )
            self._check_cancelled()
            result['sources'].update(predictor_results)

        result['summary'] = self._compute_consensus_summary(result['sources'])
        return result

    def _get_element_reference_cifs(
        self,
        active_databases: List[Dict],
        element_symbols: List[str],
        element_ref_cache: Dict[str, Optional[str]],
    ) -> Dict[str, str]:
        """Get one elemental CIF reference per element, preferring Materials Project."""
        refs: Dict[str, str] = {}

        # Primary source for elemental references: Materials Project.
        mp_db_config = {'value': 'materialsproject', 'name': 'Materials Project'}

        # Fallback order only when MP is not available/reachable.
        fallback_configs = [db for db in active_databases if db.get('value') != 'materialsproject']

        for symbol in element_symbols:
            self._check_cancelled()
            if symbol in element_ref_cache:
                cached = element_ref_cache[symbol]
                if cached:
                    refs[symbol] = cached
                continue

            found_cif: Optional[str] = None
            lookup_order = [mp_db_config] + fallback_configs
            for db_config in lookup_order:
                self._check_cancelled()
                db_key = db_config.get('value')
                if db_key not in database_factory:
                    continue
                try:
                    db_instance = database_factory[db_key](db_key, self.logger)
                    db_result = db_instance.retrieve({'target_compositions': symbol, 'batch_size': 1})
                    self._check_cancelled()
                    cifs = db_result.get('cif_strings', []) if isinstance(db_result, dict) else []
                    if cifs:
                        found_cif = cifs[0]
                        if self.logger:
                            self.logger.log(f'Element reference found for {symbol} from {db_config.get("name", db_key)}', 'info')
                        break
                except StabilityConsensusAnalysisCancelled:
                    raise
                except Exception as ref_err:
                    if self.logger:
                        self.logger.log(f'Element reference lookup failed for {symbol} in {db_key}: {str(ref_err)}', 'warning')

            element_ref_cache[symbol] = found_cif
            if found_cif:
                refs[symbol] = found_cif

        return refs

    def _get_element_reference_formation_energies(
        self,
        active_databases: List[Dict],
        element_symbols: List[str],
        element_ref_cache: Dict[str, Optional[float]],
    ) -> Dict[str, float]:
        """Get elemental formation energies (eV/atom), preferring Materials Project."""
        refs: Dict[str, float] = {}

        mp_db_config = {'value': 'materialsproject', 'name': 'Materials Project'}
        fallback_configs = [db for db in active_databases if db.get('value') != 'materialsproject']

        for symbol in element_symbols:
            cached = element_ref_cache.get(symbol)
            if isinstance(cached, (int, float)):
                refs[symbol] = float(cached)
                continue

            found_energy: Optional[float] = None
            lookup_order = [mp_db_config] + fallback_configs
            for db_config in lookup_order:
                db_key = db_config.get('value')
                if db_key not in database_factory:
                    continue
                try:
                    db_instance = database_factory[db_key](db_key, self.logger)
                    db_result = db_instance.retrieve({'target_compositions': symbol, 'batch_size': 3})
                    entries = db_result.get('entries', []) if isinstance(db_result, dict) else []
                    if not isinstance(entries, list) or not entries:
                        continue

                    values: List[float] = []
                    for entry in entries:
                        if not isinstance(entry, dict):
                            continue
                        raw = entry.get('formation_energy_r2scan')
                        if raw is None:
                            raw = entry.get('formation_energy_per_atom')
                        if raw is None:
                            continue
                        try:
                            values.append(float(raw))
                        except (TypeError, ValueError):
                            continue

                    if values:
                        found_energy = min(values)
                        if self.logger:
                            self.logger.log(
                                f'Element reference energy found for {symbol} from {db_config.get("name", db_key)}: {found_energy:.4f} eV/atom',
                                'info'
                            )
                        break
                except Exception as ref_err:
                    if self.logger:
                        self.logger.log(
                            f'Element reference energy lookup failed for {symbol} in {db_key}: {str(ref_err)}',
                            'warning'
                        )

            if found_energy is not None:
                element_ref_cache[symbol] = found_energy
                refs[symbol] = found_energy

        return refs

    def _compute_batch_summary(self, results_per_cif: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate lightweight summary across all CIF files."""
        processed = 0
        failed = 0
        stable_votes = 0
        unstable_votes = 0

        for entry in results_per_cif:
            if entry.get('error'):
                failed += 1
                continue
            processed += 1
            summary = entry.get('summary', {})
            stable_votes += int(summary.get('stable_count', 0) or 0)
            unstable_votes += int(summary.get('unstable_count', 0) or 0)

        return {
            'total_files': len(results_per_cif),
            'processed_files': processed,
            'failed_files': failed,
            'stable_votes': stable_votes,
            'unstable_votes': unstable_votes,
        }

    def process_feature(self, inputs):
        """Main processing pipeline for stability consensus analysis."""
        try:
            self._check_cancelled()
            if self.logger:
                self.logger.log('Initializing Stability Consensus Analysis...', 'info')

            cif_entries = self._normalize_cif_inputs(inputs)
            if not cif_entries:
                raise ValueError("No CIF file provided")

            if self.logger:
                self.logger.log(f'Found {len(cif_entries)} CIF file(s) for batch processing', 'info')

            results_per_cif: List[Dict[str, Any]] = []
            db_cache: Dict[str, Dict[str, Any]] = {}
            element_ref_cache: Dict[str, Optional[float]] = {}
            for entry in cif_entries:
                self._check_cancelled()
                try:
                    results_per_cif.append(
                        self._process_single_cif(
                            entry['name'],
                            entry['content'],
                            inputs,
                            db_cache,
                            element_ref_cache,
                        )
                    )
                    self._check_cancelled()
                except StabilityConsensusAnalysisCancelled:
                    raise
                except Exception as single_err:
                    if self.logger:
                        self.logger.log(f'Error in {entry["name"]}: {str(single_err)}', 'error')
                    results_per_cif.append({
                        'cif_name': entry['name'],
                        'error': str(single_err),
                        'sources': {},
                        'summary': self._compute_consensus_summary({}),
                    })

            consensus_results = {
                'results_per_cif': results_per_cif,
                'batch_summary': self._compute_batch_summary(results_per_cif),
            }

            # Backward compatibility: expose first file result on top-level fields used by older UI code.
            first_ok = next((r for r in results_per_cif if not r.get('error')), None)
            if first_ok:
                consensus_results['composition'] = first_ok.get('composition')
                consensus_results['sources'] = first_ok.get('sources', {})
                consensus_results['summary'] = first_ok.get('summary', {})
            
            if self.logger:
                self.logger.log('Stability Consensus Analysis processing completed', 'info')
            
            return consensus_results

        except StabilityConsensusAnalysisCancelled as exc:
            if self.logger:
                self.logger.log(str(exc), 'warning')
            return {
                'status': 'cancelled',
                'message': str(exc),
            }
        except Exception as e:
            if self.logger:
                self.logger.log(f'Error: {str(e)}', 'error')
            return {
                'error': str(e),
                'status': 'failed'
            }

    def process_feature_stream(self, inputs):
        """Stream an initial event, then the formatted result.

        Using the feature stream keeps this instance registered with the
        backend cancellation endpoint for the full lifetime of the analysis.
        """
        start_event = {
            'message': 'Stability Consensus Analysis started',
            'level': 'info',
        }
        yield f"event: log\ndata: {json.dumps(start_event)}\n\n"

        results = self.process_feature(inputs)
        formatted = self.format_outputs(results)
        yield f"event: result\ndata: {json.dumps(formatted, ensure_ascii=False)}\n\n"

    def format_outputs(self, results):
        """Format results for frontend (JSON string for download)."""
        if results.get('status') == 'cancelled':
            return {
                'status': 'cancelled',
                'message': results.get('message', 'Analysis cancelled.'),
                'downloadResultsJson': None,
            }

        if 'error' in results:
            return {
                'error': results['error'],
                'downloadResultsJson': None,
            }

        download_results = {
            key: value for key, value in results.items()
            if key != 'plot_data'
        }

        return {
            'composition': results.get('composition'),
            'sources': results.get('sources', {}),
            'summary': results.get('summary', {}),
            'results_per_cif': results.get('results_per_cif', []),
            'batch_summary': results.get('batch_summary', {}),
            'downloadResultsJson': json.dumps(download_results, indent=2, ensure_ascii=False),
        }
    
    def _query_databases(
        self,
        active_databases: List[Dict],
        composition: str,
        space_group_number: Optional[int] = None,
        mp_materials_id: Optional[str] = None,
    ):
        """Query selected databases for hull distances and formation energies."""
        results = {}
        
        # Databases that support space_group filtering
        SPACE_GROUP_CAPABLE_DBS = {'alexandria', 'jarvisdft', 'mathub3d', 'aflow', 'cod'}
        
        for db_config in active_databases:
            self._check_cancelled()
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

                # If CIF carries an MP ID, query that exact MP entry to avoid polymorph mixing.
                if db_key == 'materialsproject' and mp_materials_id:
                    db_inputs['id'] = mp_materials_id
                
                # Add space group constraint ONLY if database supports it
                if space_group_number is not None and db_key in SPACE_GROUP_CAPABLE_DBS:
                    db_inputs['space_group'] = space_group_number
                    if self.logger:
                        self.logger.log(f'Adding space group #{space_group_number} filter to {db_name}', 'info')
                
                # For Materials Project, retrieve composition matches and evaluate with hierarchy:
                # predicted_stable -> energy_above_hull -> formation_energy.
                # For other DBs, keep threshold-filtered query behavior.
                if metric_name and db_key != 'materialsproject':
                    db_inputs[metric_name] = [0.0, threshold]

                db_result = db_instance.retrieve(db_inputs)
                self._check_cancelled()

                # If strict MP-ID query misses, fall back to composition-only MP lookup.
                if db_key == 'materialsproject' and mp_materials_id and not db_result.get('cif_strings'):
                    if self.logger:
                        self.logger.log(
                            f'MP ID {mp_materials_id} not found via OPTIMADE; falling back to composition-only MP query',
                            'warning',
                        )
                    fallback_inputs = {'target_compositions': composition}
                    db_result = db_instance.retrieve(fallback_inputs)
                    self._check_cancelled()

                fallback_result = None
                if metric_name and not db_result.get('cif_strings'):
                    # Fallback to a lightweight unfiltered lookup to recover raw thermodynamic value.
                    fallback_result = db_instance.retrieve({
                        'target_compositions': composition,
                        'batch_size': 1,
                    })
                    self._check_cancelled()

                # Extract stability metrics
                source_name = db_result.get('source', db_key).lower()
                stability_data = self._evaluate_database_stability(
                    source_name,
                    db_result,
                    fallback_result,
                    composition,
                    mp_materials_id,
                    space_group_number,
                )
                results[source_name] = stability_data
                
                if self.logger:
                    self.logger.log(f'{db_name}: Retrieved {len(db_result.get("cif_strings", []))} structures', 'info')
            
            except StabilityConsensusAnalysisCancelled:
                raise
            except Exception as e:
                if self.logger:
                    self.logger.log(f'Error querying {db_name}: {str(e)}', 'error')
                results[db_key] = {
                    'status': 'error',
                    'error': str(e),
                    'stability': None,
                    'matched_entry_ids': [],
                    'selected_entry_id': None,
                }

        return results
    
    def _evaluate_database_stability(
        self,
        source_name: str,
        db_result: Dict,
        fallback_result: Optional[Dict[str, Any]] = None,
        target_formula: Optional[str] = None,
        target_entry_id: Optional[str] = None,
        target_space_group: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Evaluate stability for database results (hull distance / energy above hull)."""
        cif_strings = db_result.get('cif_strings', [])
        entries = db_result.get('entries', [])

        if source_name == 'materialsproject' and target_entry_id:
            entries = self._filter_entries_by_id(entries, target_entry_id)

        if target_formula:
            entries = self._filter_entries_by_formula(entries, target_formula)

        # For MP, apply space group post-filter only when we have entries to filter
        # (local computation is in entry metadata; skip if it drops every entry).
        if source_name == 'materialsproject' and target_space_group is not None and entries:
            sg_filtered = self._filter_entries_by_space_group(entries, target_space_group)
            if sg_filtered:  # only apply if at least one entry matches
                entries = sg_filtered

        matched_entry_ids = self._extract_database_entry_ids(entries)

        # Extract stability metric from queries
        queries = db_result.get('queries', {})
        threshold_cfg = self.STABILITY_THRESHOLDS.get(source_name, {})
        metric_name = threshold_cfg.get('metric', 'hull_distance')
        threshold = threshold_cfg.get('threshold', 0.05)
        fallback_entries = (fallback_result or {}).get('entries', []) if isinstance(fallback_result, dict) else []
        if source_name == 'materialsproject' and target_entry_id:
            fallback_entries = self._filter_entries_by_id(fallback_entries, target_entry_id)
        if target_formula:
            fallback_entries = self._filter_entries_by_formula(fallback_entries, target_formula)
        fallback_metric_entry = self._select_database_metric_entry(fallback_entries, metric_name)
        fallback_raw = (
            float(fallback_metric_entry[metric_name])
            if fallback_metric_entry is not None
            else None
        )

        if target_formula and not entries and cif_strings:
            return {
                'status': 'no_exact_formula_match',
                'stability': None,
                'raw_value': None,
                'threshold': threshold,
                'unit': threshold_cfg.get('unit', ''),
                'description': threshold_cfg.get('description', ''),
                'num_matches': 0,
                'matched_entry_ids': [],
                'selected_entry_id': None,
                'message': f'No exact formula match found for {target_formula} in returned entries'
            }

        if not cif_strings:
            if fallback_raw is not None:
                return {
                    'status': 'success',
                    'stability': '✅ Stable' if fallback_raw < threshold else '❌ Unstable',
                    'raw_value': round(fallback_raw, 4),
                    'threshold': threshold,
                    'unit': threshold_cfg.get('unit', ''),
                    'description': threshold_cfg.get('description', ''),
                    'num_matches': 0,
                    'matched_entry_ids': self._extract_database_entry_ids(fallback_entries),
                    'selected_entry_id': fallback_metric_entry.get('id'),
                    'message': f'No entries under threshold; fallback {metric_name} value used'
                }

            # If we queried with a threshold filter, no matches means composition not found in database.
            filter_value = queries.get(metric_name) if isinstance(queries, dict) else None
            if isinstance(filter_value, list) and len(filter_value) == 2:
                return {
                    'status': 'not_found',
                    'stability': '⚠️ Not found',
                    'raw_value': None,
                    'threshold': threshold,
                    'unit': threshold_cfg.get('unit', ''),
                    'description': threshold_cfg.get('description', ''),
                    'num_matches': 0,
                    'matched_entry_ids': [],
                    'selected_entry_id': None,
                    'message': f'No entries found with {metric_name} <= {threshold}'
                }
            return {
                'status': 'no_matches',
                'stability': None,
                'raw_value': None,
                'matched_entry_ids': [],
                'selected_entry_id': None,
                'message': 'No matching structures found in database'
            }

        if source_name == 'materialsproject':
            # Hierarchy requested by user:
            # 1) predicted_stable, 2) energy_above_hull, 3) formation_energy (< 0 => stable).
            predicted_stable = None
            predicted_stable_field = None
            for field_name in ('predicted_stable_r2scan', 'predicted_stable', 'is_stable'):
                predicted_stable = self._extract_database_boolean(entries, field_name)
                if predicted_stable is not None:
                    predicted_stable_field = field_name
                    break

            if predicted_stable is not None:
                selected_entry = self._select_database_boolean_entry(
                    entries,
                    predicted_stable_field,
                    predicted_stable,
                )
                return {
                    'status': 'success',
                    'stability': '✅ Stable' if predicted_stable else '❌ Unstable',
                    'raw_value': predicted_stable,
                    'threshold': None,
                    'unit': '',
                    'description': 'Materials Project predicted stable (r2SCAN)',
                    'num_matches': len(cif_strings),
                    'matched_entry_ids': matched_entry_ids,
                    'selected_entry_id': selected_entry.get('id') if selected_entry else None,
                    'message': 'Decision from Materials Project predicted stable field'
                }

            hull_entry = self._select_database_metric_entry(entries, 'energy_above_hull_r2scan')
            if hull_entry is not None:
                hull_value = float(hull_entry['energy_above_hull_r2scan'])
                return {
                    'status': 'success',
                    'stability': '✅ Stable' if hull_value < threshold else '❌ Unstable',
                    'raw_value': round(hull_value, 4),
                    'threshold': threshold,
                    'unit': threshold_cfg.get('unit', ''),
                    'description': threshold_cfg.get('description', ''),
                    'num_matches': len(cif_strings),
                    'matched_entry_ids': matched_entry_ids,
                    'selected_entry_id': hull_entry.get('id'),
                    'message': f'Decision from energy_above_hull_r2scan ({hull_value:.4f} eV/atom)'
                }

            formation_entry = self._select_database_metric_entry(entries, 'formation_energy_r2scan')
            if formation_entry is not None:
                formation_value = float(formation_entry['formation_energy_r2scan'])
                return {
                    'status': 'success',
                    'stability': '✅ Stable' if formation_value < 0.0 else '❌ Unstable',
                    'raw_value': round(formation_value, 4),
                    'threshold': 0.0,
                    'unit': 'eV/atom',
                    'description': 'Formation energy fallback (negative => stable)',
                    'num_matches': len(cif_strings),
                    'matched_entry_ids': matched_entry_ids,
                    'selected_entry_id': formation_entry.get('id'),
                    'message': 'Fallback decision from formation_energy_r2scan'
                }

            return {
                'status': 'metric_unavailable',
                'stability': None,
                'raw_value': None,
                'threshold': threshold,
                'unit': threshold_cfg.get('unit', ''),
                'description': threshold_cfg.get('description', ''),
                'num_matches': len(cif_strings),
                'matched_entry_ids': matched_entry_ids,
                'selected_entry_id': None,
                'message': 'No usable MP stability fields found (predicted_stable, energy_above_hull, formation_energy)'
            }

        selected_entry = self._select_database_metric_entry(entries, metric_name)

        if selected_entry is not None:
            raw_value = float(selected_entry[metric_name])
            return {
                'status': 'success',
                'stability': '✅ Stable' if raw_value < threshold else '❌ Unstable',
                'raw_value': round(raw_value, 4),
                'threshold': threshold,
                'unit': threshold_cfg.get('unit', ''),
                'description': threshold_cfg.get('description', ''),
                'num_matches': len(cif_strings),
                'matched_entry_ids': matched_entry_ids,
                'selected_entry_id': selected_entry.get('id'),
                'message': f'{len(cif_strings)} entries evaluated for {metric_name}'
            }

        return {
            'status': 'metric_unavailable',
            'stability': None,
            'raw_value': None,
            'threshold': threshold,
            'unit': threshold_cfg.get('unit', ''),
            'description': threshold_cfg.get('description', ''),
            'num_matches': len(cif_strings),
            'matched_entry_ids': matched_entry_ids,
            'selected_entry_id': None,
            'message': f'Stability metric "{metric_name}" not available in database response'
        }

    def _extract_database_entry_ids(self, entries: List[Dict[str, Any]]) -> List[str]:
        """Return unique database IDs from the entries retained for evaluation."""
        entry_ids: List[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_id = entry.get('id')
            if entry_id is not None and entry_id not in entry_ids:
                entry_ids.append(entry_id)
        return entry_ids

    def _select_database_metric_entry(
        self,
        entries: List[Dict[str, Any]],
        metric_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Return the entry with the lowest usable value for a metric."""
        selected_entry = None
        selected_value = None

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            raw = entry.get(metric_name)
            if raw is None:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if selected_value is None or value < selected_value:
                selected_entry = entry
                selected_value = value

        return selected_entry

    def _select_database_boolean_entry(
        self,
        entries: List[Dict[str, Any]],
        field_name: str,
        selected_value: bool,
    ) -> Optional[Dict[str, Any]]:
        """Return the first entry carrying the boolean used for an MP decision."""
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            raw = entry.get(field_name)
            if isinstance(raw, bool) and raw is selected_value:
                return entry
            if isinstance(raw, str):
                normalized = raw.strip().lower()
                if normalized in ('true', '1', 'yes'):
                    parsed = True
                elif normalized in ('false', '0', 'no'):
                    parsed = False
                else:
                    continue
                if parsed is selected_value:
                    return entry
        return None

    def _extract_database_metric(self, entries: List[Dict[str, Any]], metric_name: str) -> Optional[float]:
        """Extract a representative thermodynamic metric value from DB entries."""
        if not entries:
            return None

        values: List[float] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            raw = entry.get(metric_name)
            if raw is None:
                continue
            try:
                values.append(float(raw))
            except (TypeError, ValueError):
                continue

        if not values:
            return None

        # For hull metrics, lower is better; report best value in returned set.
        return min(values)

    def _normalize_formula(self, formula: str) -> Optional[str]:
        """Normalize formula to reduced-form string for robust comparisons."""
        if not formula:
            return None
        try:
            return Composition(formula).reduced_formula
        except Exception:
            return None

    def _filter_entries_by_formula(self, entries: List[Dict[str, Any]], target_formula: str) -> List[Dict[str, Any]]:
        """Keep only DB entries whose reduced formula matches the target formula."""
        normalized_target = self._normalize_formula(target_formula)
        if not normalized_target:
            return entries

        filtered: List[Dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_formula = entry.get('chemical_formula_reduced')
            if self._normalize_formula(str(entry_formula) if entry_formula is not None else '') == normalized_target:
                filtered.append(entry)

        return filtered

    def _filter_entries_by_id(self, entries: List[Dict[str, Any]], target_entry_id: str) -> List[Dict[str, Any]]:
        """Keep only entries that match the requested database ID exactly."""
        if not target_entry_id:
            return entries
        return [e for e in entries if isinstance(e, dict) and e.get('id') == target_entry_id]

    def _filter_entries_by_space_group(self, entries: List[Dict[str, Any]], space_group_number: int) -> List[Dict[str, Any]]:
        """Keep only entries whose locally-computed space group number matches."""
        return [
            e for e in entries
            if isinstance(e, dict) and e.get('space_group_number') == space_group_number
        ]

    def _extract_materials_project_id(self, cif_content: str) -> Optional[str]:
        """Extract Materials Project ID (e.g. mp-1234) if present in CIF text."""
        if not cif_content:
            return None

        match = re.search(r'\bmp-\d+\b', cif_content)
        if match:
            return match.group(0)
        return None

    def _extract_database_boolean(self, entries: List[Dict[str, Any]], field_name: str) -> Optional[bool]:
        """Extract a representative boolean field from DB entries."""
        if not entries:
            return None

        observed: List[bool] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            raw = entry.get(field_name)
            if raw is None:
                continue
            if isinstance(raw, bool):
                observed.append(raw)
                continue
            if isinstance(raw, str):
                val = raw.strip().lower()
                if val in ('true', '1', 'yes'):
                    observed.append(True)
                elif val in ('false', '0', 'no'):
                    observed.append(False)

        if not observed:
            return None

        # If any matched entry is predicted stable, mark stable.
        return any(observed)
    
    def _run_predictors_parallel(
        self,
        active_predictors: List[Dict],
        cif_content: str,
        element_fractions: Dict[str, float],
        elemental_reference_cifs: Dict[str, str],
    ) -> Dict[str, Any]:
        """Run predictors concurrently for a single CIF and evaluate ΔHf using elemental predictor references."""
        results = {}
        
        # Prepare predictor instances
        predictor_instances = []
        for pred_config in active_predictors:
            self._check_cancelled()
            pred_key = pred_config['value']
            pred_name = pred_config['name']
            
            if pred_key not in predictor_factory:
                if self.logger:
                    self.logger.log(f'Predictor {pred_name} not found in factory', 'warning')
                continue
            
            pred_instance = predictor_factory[pred_key](pred_key, self.logger)
            predictor_instances.append((pred_key, pred_name, pred_instance))
        
        if not predictor_instances:
            return results

        def _run_single_predictor(pred_key: str, pred_name: str, pred_instance):
            try:
                self._check_cancelled()
                if self.logger:
                    self.logger.log(f'Running {pred_name}...', 'info')

                element_order = sorted(element_fractions.keys())
                predictor_inputs = [cif_content]
                predictor_inputs.extend([
                    elemental_reference_cifs[sym]
                    for sym in element_order
                    if sym in elemental_reference_cifs and elemental_reference_cifs[sym]
                ])

                # Stability consensus only needs per-atom energies for ΔHf.
                # Skip expensive relaxation/forces/stress to keep single-CIF latency low,
                # especially when running MLIP services on CPU in Docker.
                pred_result = pred_instance.predict(
                    predictor_inputs,
                    compute_energy=True,
                    compute_forces=False,
                    compute_stress=False,
                    relax=True,
                    relax_atoms=True,
                    relax_cell=True,
                )
                self._check_cancelled()

                # Evaluate stability
                source_name = pred_result.get('source', pred_key).lower()
                stability_data = self._evaluate_predictor_stability(
                    source_name,
                    pred_result,
                    element_fractions,
                    element_order,
                    None,
                )

                if self.logger:
                    if 'error' in stability_data:
                        self.logger.log(f'{pred_name}: {stability_data["error"]}', 'error')
                    else:
                        self.logger.log(f'{pred_name}: {stability_data["stability"]}', 'info')

                return source_name, stability_data
            except StabilityConsensusAnalysisCancelled:
                raise
            except Exception as e:
                if self.logger:
                    self.logger.log(f'Error running {pred_name}: {str(e)}', 'error')
                return pred_key, {
                    'status': 'error',
                    'error': str(e),
                    'stability': None
                }

        max_workers = min(len(predictor_instances), 2)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(_run_single_predictor, pred_key, pred_name, pred_instance): pred_key
                for pred_key, pred_name, pred_instance in predictor_instances
            }
            for future in as_completed(future_map):
                self._check_cancelled()
                source_name, stability_data = future.result()
                results[source_name] = stability_data

        self._check_cancelled()

        return results
    
    def _evaluate_predictor_stability(
        self,
        source_name: str,
        pred_result: Dict,
        element_fractions: Dict[str, float],
        element_order: List[str],
        elemental_reference_energies: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Evaluate predictor stability using MLIP ΔHf per atom."""
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

        compound_e_per_atom = float(user_energy) / float(user_num_atoms)

        if elemental_reference_energies:
            missing = [sym for sym in element_fractions.keys() if sym not in elemental_reference_energies]
            if missing:
                return {
                    'status': 'insufficient_reference',
                    'stability': None,
                    'raw_value': None,
                    'threshold': threshold,
                    'unit': threshold_cfg.get('unit', ''),
                    'description': threshold_cfg.get('description', ''),
                    'energy': round(float(user_energy), 4),
                    'energy_unit': 'eV',
                    'error': f'Missing elemental reference energies for: {", ".join(missing)}'
                }

            reference_sum = sum(
                element_fractions[sym] * float(elemental_reference_energies[sym])
                for sym in element_fractions.keys()
            )
            delta_hf = compound_e_per_atom - reference_sum
            is_stable = delta_hf < threshold

            return {
                'status': 'success',
                'stability': '✅ Stable' if is_stable else '❌ Unstable',
                'raw_value': round(delta_hf, 4),
                'threshold': threshold,
                'unit': threshold_cfg.get('unit', ''),
                'description': threshold_cfg.get('description', ''),
                'energy': round(float(user_energy), 4),
                'energy_unit': 'eV',
                'message': 'ΔHf using Materials Project elemental formation energies',
                'formation_energy_details': {
                    'compound_energy_eV': round(float(user_energy), 6),
                    'compound_num_atoms': int(user_num_atoms),
                    'compound_energy_per_atom_eV': round(compound_e_per_atom, 6),
                    'reference_energies_eV_per_atom': {
                        sym: round(float(elemental_reference_energies[sym]), 6)
                        for sym in element_fractions.keys()
                    },
                    'element_fractions': {
                        sym: round(element_fractions[sym], 6)
                        for sym in element_fractions.keys()
                    },
                    'reference_sum_eV_per_atom': round(reference_sum, 6),
                    'delta_hf_eV_per_atom': round(delta_hf, 6),
                },
            }

        # Expected indexing: result[0]=compound, result[1..]=elemental refs in element_order.
        elemental_e_per_atom: Dict[str, float] = {}
        for idx, symbol in enumerate(element_order, start=1):
            if idx >= len(results_list):
                continue
            ref_result = results_list[idx]
            if ref_result.get('error'):
                continue
            ref_props = ref_result.get('properties', {})
            ref_n = ref_props.get('num_atoms')
            ref_e = ref_props.get('relaxed_energy', ref_props.get('energy'))
            if ref_n in (None, 0) or ref_e is None:
                continue
            elemental_e_per_atom[symbol] = float(ref_e) / float(ref_n)

        missing = [sym for sym in element_fractions.keys() if sym not in elemental_e_per_atom]
        if missing:
            return {
                'status': 'insufficient_reference',
                'stability': None,
                'raw_value': None,
                'threshold': threshold,
                'unit': threshold_cfg.get('unit', ''),
                'description': threshold_cfg.get('description', ''),
                'energy': round(float(user_energy), 4),
                'energy_unit': 'eV',
                'error': f'Missing elemental MLIP references for: {", ".join(missing)}'
            }

        reference_sum = sum(
            element_fractions[sym] * elemental_e_per_atom[sym]
            for sym in element_fractions.keys()
        )
        delta_hf = compound_e_per_atom - reference_sum
        is_stable = delta_hf < threshold
        
        return {
            'status': 'success',
            'stability': '✅ Stable' if is_stable else '❌ Unstable',
            'raw_value': round(delta_hf, 4),
            'threshold': threshold,
            'unit': threshold_cfg.get('unit', ''),
            'description': threshold_cfg.get('description', ''),
            'energy': round(float(user_energy), 4),
            'energy_unit': 'eV',
            'message': 'ΔHf = E(compound) − Σ x_i E(element_i), stable if ΔHf < 0',
            'formation_energy_details': {
                'compound_energy_eV': round(float(user_energy), 6),
                'compound_num_atoms': int(user_num_atoms),
                'compound_energy_per_atom_eV': round(compound_e_per_atom, 6),
                'reference_energies_eV_per_atom': {
                    sym: round(elemental_e_per_atom[sym], 6)
                    for sym in element_fractions.keys()
                },
                'element_fractions': {
                    sym: round(element_fractions[sym], 6)
                    for sym in element_fractions.keys()
                },
                'reference_sum_eV_per_atom': round(reference_sum, 6),
                'delta_hf_eV_per_atom': round(delta_hf, 6),
            },
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
