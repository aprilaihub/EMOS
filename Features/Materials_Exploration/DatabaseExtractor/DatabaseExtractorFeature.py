from Features.BaseFeature import BaseFeature
from Information_Units.Databases.DatabaseFactory import database_factory
from Information_Units.property_mappings.property_loader import (
    load_common_properties,
    load_source_property_mapping,
)

import json
import time


class DatabaseExtractorFeature(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("Database Extractor", logger)
    
    def info(self):
        return "Database Extractor: Extract and analyze specific material properties and data from integrated databases"
    
    def extract_inputs(self, input_data):
        raw_selected = (
            input_data.get('selected_properties')
            or input_data.get('selectedProperties')
            or input_data.get('query_properties')
            or input_data.get('queryProperties')
            or []
        )

        return {
            'selected_properties': raw_selected,
            'batch_size': input_data.get('batch_size', input_data.get('batchSize', input_data.get('maximumEntries', 100))),
            'retrieval_mode': input_data.get('retrieval_mode', input_data.get('retrievalMode', 'lenient')),
            'query_values': input_data.get('query_values', input_data.get('queryValues', input_data.get('filterCriteria', {}))),
            'target_compositions': input_data.get('target_compositions', input_data.get('targetCompositions', '')),
            'feature_input': input_data.get('featureInput', input_data.get('feature_input', '')),
            'active_databases': input_data.get('active_databases', []),
        }
    
    def process_feature(self, inputs):
        started_at = time.time()

        if self.logger:
            self.logger.log('Initializing Database Extractor...', 'info')

        extraction_result = self._run_database_extraction(inputs)
        extraction_result['elapsed_seconds'] = round(time.time() - started_at, 3)

        if self.logger:
            self.logger.log('Database Extractor processing completed', 'info')

        return extraction_result
    
    def format_outputs(self, results):
        total_records = results.get('total_records', 0)
        database_count = len(results.get('databases', {}))

        return {
            'status': results.get('status', 'completed'),
            'message': results.get('message', ''),
            'recordsExtracted': total_records,
            'dataSize': f'{total_records} CIF entries',
            'fileFormat': 'json',
            'processingTime': f"{results.get('elapsed_seconds', 0.0)} s",
            'downloadPackage': 'Available in JSON response payload',
            'databaseCount': database_count,
            'skippedDatabaseCount': len(results.get('skipped_databases', [])),
            'extraction': results,
        }

    def _run_database_extraction(self, inputs):
        common_properties = load_common_properties().get('properties', {})
        selected_properties = self._normalize_properties(
            raw_selected=inputs.get('selected_properties'),
            feature_input=inputs.get('feature_input'),
            query_values=inputs.get('query_values', {}),
            common_properties=common_properties,
        )
        invalid_properties = [p for p in selected_properties if p not in common_properties]
        valid_properties = [p for p in selected_properties if p in common_properties]

        mode = self._normalize_mode(inputs.get('retrieval_mode', 'lenient'))
        batch_size = self._normalize_batch_size(inputs.get('batch_size', 100))
        query_values = self._normalize_query_values(inputs)
        target_compositions = inputs.get('target_compositions', '')
        active_database_keys = self._active_database_keys(inputs.get('active_databases', []))

        if self.logger:
            self.logger.log(
                f'Database extraction mode={mode}, batch_size={batch_size}, properties={len(valid_properties)}',
                'info',
            )

        if not active_database_keys:
            return {
                'status': 'error',
                'message': 'No active databases selected.',
                'mode': mode,
                'batch_size': batch_size,
                'query_properties': valid_properties,
                'invalid_properties': invalid_properties,
                'databases': {},
                'skipped_databases': [],
                'total_records': 0,
            }

        databases = {}
        skipped_databases = []
        total_records = 0

        for db_key in active_database_keys:
            entry = self._extract_from_database(
                db_key=db_key,
                mode=mode,
                selected_properties=valid_properties,
                query_values=query_values,
                target_compositions=target_compositions,
                batch_size=batch_size,
            )

            if entry.get('skipped'):
                skipped_databases.append(entry)
                continue

            records_count = entry.get('records_count', 0)
            total_records += records_count
            databases[db_key] = entry

        return {
            'status': 'completed',
            'message': 'Database extraction completed successfully.',
            'mode': mode,
            'batch_size': batch_size,
            'query_properties': valid_properties,
            'invalid_properties': invalid_properties,
            'query_values': query_values,
            'total_records': total_records,
            'databases': databases,
            'skipped_databases': skipped_databases,
        }

    def _extract_from_database(
        self,
        db_key,
        mode,
        selected_properties,
        query_values,
        target_compositions,
        batch_size,
    ):
        if db_key not in database_factory:
            return {
                'source': db_key,
                'skipped': True,
                'reason': 'Database not available in factory.',
            }

        try:
            source_mapping = load_source_property_mapping(db_key, source_type='databases')
        except Exception:
            source_mapping = {}

        properties_used, properties_skipped = self._partition_queryable_properties(
            selected_properties,
            source_mapping,
        )

        if mode == 'strict' and properties_skipped:
            if self.logger:
                self.logger.log(
                    f'Skipping {db_key} in strict mode. Non-queryable properties: {properties_skipped}',
                    'warning',
                )
            return {
                'source': db_key,
                'skipped': True,
                'reason': 'Strict mode: one or more properties are not queryable for this database.',
                'properties_requested': selected_properties,
                'properties_skipped': properties_skipped,
            }

        db_inputs = {'batch_size': batch_size}
        if target_compositions:
            db_inputs['target_compositions'] = target_compositions

        for prop in properties_used:
            if prop in query_values:
                db_inputs[prop] = query_values[prop]

        if self.logger:
            self.logger.log(
                f'Querying {db_key} with {len(properties_used)} properties and batch_size={batch_size}',
                'info',
            )

        db_instance = database_factory[db_key](db_key, self.logger)
        payload = db_instance.retrieve(db_inputs)
        cif_strings = payload.get('cif_strings', []) if isinstance(payload, dict) else []

        return {
            'source': db_key,
            'skipped': False,
            'properties_requested': selected_properties,
            'properties_used': properties_used,
            'properties_skipped': properties_skipped,
            'source_fields_used': {
                prop: source_mapping.get(prop, {}).get('name', prop)
                for prop in properties_used
            },
            'queries_applied': db_inputs,
            'records_count': len(cif_strings),
            'payload': payload,
        }

    def _normalize_properties(self, raw_selected, feature_input, query_values, common_properties):
        if isinstance(raw_selected, list):
            selected = [str(item).strip() for item in raw_selected if str(item).strip()]
        elif isinstance(raw_selected, str):
            selected = [item.strip() for item in raw_selected.split(',') if item.strip()]
        else:
            selected = []

        parsed_feature_input = self._parse_json_if_possible(feature_input)
        if not selected and isinstance(parsed_feature_input, dict):
            candidate = (
                parsed_feature_input.get('selected_properties')
                or parsed_feature_input.get('query_properties')
                or parsed_feature_input.get('properties')
            )
            if isinstance(candidate, list):
                selected = [str(item).strip() for item in candidate if str(item).strip()]

        if not selected and isinstance(query_values, dict):
            selected = [str(item).strip() for item in query_values.keys() if str(item).strip()]

        if not selected:
            selected = []

        # Preserve order while de-duplicating.
        return list(dict.fromkeys(selected))

    def _normalize_mode(self, mode):
        normalized = str(mode or 'lenient').strip().lower()
        if normalized not in {'strict', 'lenient'}:
            return 'lenient'
        return normalized

    def _normalize_batch_size(self, batch_size):
        try:
            parsed = int(batch_size)
        except (TypeError, ValueError):
            return 100
        return max(1, parsed)

    def _normalize_query_values(self, inputs):
        raw_values = inputs.get('query_values', {})
        parsed = self._parse_json_if_possible(raw_values)
        if isinstance(parsed, dict):
            return parsed

        parsed_feature_input = self._parse_json_if_possible(inputs.get('feature_input', ''))
        if isinstance(parsed_feature_input, dict):
            feature_values = parsed_feature_input.get('query_values') or parsed_feature_input.get('filters')
            if isinstance(feature_values, dict):
                return feature_values

        return {}

    def _active_database_keys(self, active_databases):
        keys = []
        for db in active_databases or []:
            if isinstance(db, dict):
                db_key = db.get('value')
            else:
                db_key = db

            if db_key:
                keys.append(str(db_key))

        return list(dict.fromkeys(keys))

    def _partition_queryable_properties(self, selected_properties, source_mapping):
        properties_used = []
        properties_skipped = []

        for prop in selected_properties:
            prop_cfg = source_mapping.get(prop, {})
            if prop_cfg.get('retrievable', False):
                properties_used.append(prop)
            else:
                properties_skipped.append(prop)

        return properties_used, properties_skipped

    def _parse_json_if_possible(self, raw_value):
        if isinstance(raw_value, dict):
            return raw_value
        if not isinstance(raw_value, str) or not raw_value.strip():
            return raw_value
        try:
            return json.loads(raw_value)
        except (TypeError, ValueError):
            return raw_value
