import json
import os
import tempfile
import threading

import amd
import numpy as np

from Features.BaseFeature import BaseFeature
from Information_Units.Predictors.Pdd.PddPredictor import PddPredictor


class CifSimilarityFeature(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("CIF similarity", logger)
        self._cancelled = False
        self._cancel_lock = threading.Lock()
    
    def info(self):
        return "CIF similarity: Compare uploaded crystal structures using AMD or PDD Earth Mover's Distance"
    
    def extract_inputs(self, input_data):
        return {
            'cif_strings': input_data.get('cif_strings', []),
            'labels': input_data.get('labels', []),
            'distanceMetric': input_data.get('distanceMetric', 'amd'),
            'k': int(input_data.get('k', 100) or 100),
        }
    
    def process_feature(self, inputs):
        cif_strings = inputs.get('cif_strings', [])
        labels = inputs.get('labels', [])
        k = max(1, min(500, int(inputs.get('k', 100) or 100)))
        if len(cif_strings) < 2:
            return {'status': 'error', 'message': 'CIF similarity requires at least 2 CIF files.'}

        structures = []
        failed = []
        for index, cif_text in enumerate(cif_strings):
            label = labels[index] if index < len(labels) else f'S{index + 1}'
            path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.cif', delete=False, encoding='utf-8') as temp:
                    temp.write(cif_text)
                    path = temp.name
                crystals = list(amd.CifReader(path))
                if not crystals:
                    raise ValueError('No crystal structures found in CIF.')
                structures.append((label, crystals[0]))
            except Exception as exc:
                failed.append(f'{label}: {exc}')
            finally:
                if path:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass

        if len(structures) < 2:
            return {'status': 'error', 'message': 'Fewer than two valid CIF structures were loaded.', 'failed': failed}

        labels = [label for label, _ in structures]
        metric = inputs.get('distanceMetric', 'amd')
        if metric == 'pdd_emd':
            predictor = PddPredictor(predictor_name='cif_similarity_pdd', k=k, logger=self.logger)
            pdd_result = predictor.predict(cif_strings)
            pdd_items = [item for item in pdd_result.get('results', []) if item.get('status') == 'ok']
            if len(pdd_items) != len(structures):
                return {
                    'status': 'error',
                    'message': 'PDD descriptor calculation failed for one or more CIF structures.',
                    'failed': failed,
                }
            pdd_matrices = [np.asarray(item['properties']['pdd_matrix'], dtype=float) for item in pdd_items]
            matrix = np.zeros((len(pdd_matrices), len(pdd_matrices)))
            for row in range(len(pdd_matrices)):
                for column in range(row + 1, len(pdd_matrices)):
                    distance = float(amd.EMD(pdd_matrices[row], pdd_matrices[column]))
                    matrix[row, column] = distance
                    matrix[column, row] = distance
        else:
            vectors = [amd.AMD(structure, k) for _, structure in structures]
            matrix = np.asarray(amd.AMD_cdist(vectors, vectors, metric='chebyshev'), dtype=float)
            metric = 'amd'
        return {
            'status': 'completed',
            'message': f'{metric.upper()} similarity complete. {len(labels)} structures compared.',
            'labels': labels,
            'distance_matrix': matrix.tolist(),
            'k': k,
            'distance_metric': inputs.get('distanceMetric', 'amd'),
            'failed': failed,
        }
    
    def format_outputs(self, results):
        return {
            'status': results.get('status', 'unknown'),
            'message': results.get('message', ''),
            'labels': results.get('labels', []),
            'distance_matrix': results.get('distance_matrix'),
            'k': results.get('k'),
            'distance_metric': results.get('distance_metric', 'amd'),
            'failed': results.get('failed', []),
        }
    
    def process_feature_stream(self, inputs):
        yield f"event: log\ndata: {json.dumps({'message': 'Initialising CIF similarity...', 'level': 'info'})}\n\n"
        yield f"event: progress\ndata: {json.dumps({'progress': 0.05, 'message': 'Loading CIF structures...'})}\n\n"
        result = self.process_feature(inputs)
        yield f"event: progress\ndata: {json.dumps({'progress': 1.0, 'message': 'Done.'})}\n\n"
        yield f"event: result\ndata: {json.dumps(result)}\n\n"

    def cancel(self):
        with self._cancel_lock:
            self._cancelled = True
        return {'status': 'ok', 'message': 'Cancel signal sent to CIF similarity.'}
