import json
import threading

from Features.BaseFeature import BaseFeature
from Information_Units.Generators.GeneratorFactory import generator_factory
from Information_Units.Databases.DatabaseFactory import database_factory
from Information_Units.Predictors.PredictorFactory import predictor_factory


class AmdScreeningFeature(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("AMD screening", logger)
        self._cancelled = False
        self._cancel_lock = threading.Lock()

    def info(self):
        return "AMD screening: Screen uploaded CIF structures for AMD-based candidate selection"

    def extract_inputs(self, input_data):
        return {
            'cif_strings': input_data.get('cif_strings', []),
            'k': input_data.get('k', 100),
            'metric': input_data.get('metric', 'chebyshev'),
            'active_databases': input_data.get('active_databases', []),
            'active_generators': input_data.get('active_generators', []),
            'active_predictors': input_data.get('active_predictors', []),
        }

    def process_feature(self, inputs):
        if self.logger:
            self.logger.log('Initializing AMD screening...', 'info')

        with self._cancel_lock:
            self._cancelled = False

        cif_strings = inputs.get('cif_strings', [])
        if not cif_strings or len(cif_strings) < 2:
            if self.logger:
                self.logger.log(
                    f'AMD screening requires at least 2 CIF files. '
                    f'Got {len(cif_strings)}.', 'warning'
                )
            return {
                'status': 'error',
                'message': f'AMD screening requires at least 2 CIF files. Got {len(cif_strings)}.',
                'results': None,
            }

        if self.logger:
            self.logger.log(
                f'Running AMD pairwise comparison on {len(cif_strings)} structures...', 'info'
            )

        amd_cls = predictor_factory.get('amd')
        if amd_cls is None:
            if self.logger:
                self.logger.log('AMD predictor not found in factory.', 'error')
            return {'status': 'error', 'message': 'AMD predictor not available.', 'results': None}

        k = int(inputs.get('k', 100))
        metric = inputs.get('metric', 'chebyshev')
        predictor = amd_cls(predictor_name='amd_screening', logger=self.logger)
        predictor.k = k
        predictor.metric = metric

        result = predictor.predict(cif_strings)

        if self._cancelled:
            if self.logger:
                self.logger.log('AMD screening cancelled.', 'warning')
            return {'status': 'cancelled', 'message': 'Processing was cancelled.', 'results': None}

        if self.logger:
            first = (result.get('results') or [{}])[0]
            if first.get('status') == 'success':
                n = first.get('properties', {}).get('n_comparisons', 0)
                self.logger.log(f'AMD comparison complete: {n} pair(s) evaluated.', 'success')
            else:
                self.logger.log(
                    f'AMD comparison returned an error: {first.get("error")}', 'error'
                )

        return {
            'status': 'completed',
            'message': 'AMD screening completed successfully.',
            'results': result,
        }

    def process_feature_stream(self, inputs):
        """Yield SSE events while running AMD screening, supporting cancellation."""
        with self._cancel_lock:
            self._cancelled = False

        cif_strings = inputs.get('cif_strings', [])
        n = len(cif_strings)

        yield f"event: log\ndata: {json.dumps({'message': 'Initializing AMD screening...', 'level': 'info'})}\n\n"

        if n < 2:
            msg = f'AMD screening requires at least 2 CIF files. Got {n}.'
            yield f"event: log\ndata: {json.dumps({'message': msg, 'level': 'warning'})}\n\n"
            yield f"event: result\ndata: {json.dumps({'status': 'error', 'message': msg, 'results': None})}\n\n"
            return

        yield f"event: log\ndata: {json.dumps({'message': f'Running AMD pairwise comparison on {n} structures...', 'level': 'info'})}\n\n"
        yield f"event: progress\ndata: {json.dumps({'progress': 0.1, 'message': 'Preparing AMD predictor...'})}\n\n"

        if self._cancelled:
            yield f"event: result\ndata: {json.dumps({'status': 'cancelled', 'message': 'Cancelled before starting.', 'results': None})}\n\n"
            return

        result = self.process_feature(inputs)
        yield f"event: progress\ndata: {json.dumps({'progress': 1.0, 'message': 'Done.'})}\n\n"
        yield f"event: result\ndata: {json.dumps(result)}\n\n"

    def format_outputs(self, results):
        return {
            'status': results.get('status', 'unknown'),
            'message': results.get('message', ''),
            'results': results.get('results'),
        }

    def cancel(self) -> dict:
        with self._cancel_lock:
            self._cancelled = True
        if self.logger:
            self.logger.log('Cancel requested — stopping after current operation.', 'warning')
        return {'status': 'ok', 'message': 'Cancel signal sent to AMD screening.'}

    def _process_information_units(self, inputs):
        """Process active databases, generators, and predictors with proper logging."""
        active_databases = inputs.get('active_databases', [])
        if not active_databases:
            if self.logger:
                self.logger.log('No active databases.', 'warning')
        else:
            names = ', '.join(db['name'] for db in active_databases)
            if self.logger:
                self.logger.log(f'Active databases ({len(active_databases)}): {names}', 'info')
            for dtbs in active_databases:
                db_key = dtbs['value']
                if db_key in database_factory:
                    instance = database_factory[db_key](db_key, self.logger)
                    if self.logger:
                        self.logger.log(instance.info(), 'info')

        active_generators = inputs.get('active_generators', [])
        if not active_generators:
            if self.logger:
                self.logger.log('No active generators.', 'warning')
        else:
            names = ', '.join(gen['name'] for gen in active_generators)
            if self.logger:
                self.logger.log(f'Active generators ({len(active_generators)}): {names}', 'info')
            for gnrtr in active_generators:
                gen_key = gnrtr['value']
                if gen_key in generator_factory:
                    instance = generator_factory[gen_key](gen_key, self.logger)
                    if self.logger:
                        self.logger.log(instance.info(), 'info')

        active_predictors = inputs.get('active_predictors', [])
        if not active_predictors:
            if self.logger:
                self.logger.log('No active predictors.', 'warning')
        else:
            names = ', '.join(pred['name'] for pred in active_predictors)
            if self.logger:
                self.logger.log(f'Active predictors ({len(active_predictors)}): {names}', 'info')
            for prdctr in active_predictors:
                pred_key = prdctr['value']
                if pred_key in predictor_factory:
                    instance = predictor_factory[pred_key](pred_key, self.logger)
                    if self.logger:
                        self.logger.log(instance.info(), 'info')
