import base64
import io
import json
import os
import tempfile
import threading

import amd
import numpy as np

from Features.BaseFeature import BaseFeature


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
        vectors = [amd.AMD(structure, k) for _, structure in structures]
        matrix = np.asarray(amd.AMD_cdist(vectors, vectors, metric='chebyshev'), dtype=float)
        return {
            'status': 'completed',
            'message': f'AMD similarity complete. {len(labels)} structures compared.',
            'labels': labels,
            'amd_matrix': matrix.tolist(),
            'plot_base64': self._make_figure(matrix, labels, k),
            'k': k,
            'distance_metric': inputs.get('distanceMetric', 'amd'),
            'failed': failed,
        }
    
    def format_outputs(self, results):
        return {
            'status': results.get('status', 'unknown'),
            'message': results.get('message', ''),
            'labels': results.get('labels', []),
            'amd_matrix': results.get('amd_matrix'),
            'plot_base64': results.get('plot_base64', ''),
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

    def _make_figure(self, matrix, labels, k):
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
        except ImportError:
            return ''

        figure, heatmap_axis = plt.subplots(
            figsize=(max(8, len(labels) * 0.55 + 4), max(6, len(labels) * 0.55 + 3)),
        )
        mask = np.triu(np.ones_like(matrix, dtype=bool), k=1)
        heatmap_matrix = np.ma.array(matrix, mask=mask)
        image = heatmap_axis.imshow(
            heatmap_matrix, cmap='YlOrRd', vmin=0,
            vmax=float(matrix.max()) or 1.0,
        )
        heatmap_axis.set_xticks(range(len(labels)), labels, rotation=90)
        heatmap_axis.set_yticks(range(len(labels)), labels)
        if len(labels) <= 20:
            for row in range(len(labels)):
                for column in range(row + 1):
                    heatmap_axis.text(column, row, f'{matrix[row, column]:.3f}',
                                      ha='center', va='center', fontsize=7)
        figure.colorbar(image, ax=heatmap_axis, label=f'AMD distance (k={k})')
        heatmap_axis.set_title('CIF Similarity: AMD Distance Matrix')
        figure.tight_layout()
        buffer = io.BytesIO()
        figure.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        plt.close(figure)
        return base64.b64encode(buffer.getvalue()).decode('ascii')
