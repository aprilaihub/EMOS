// CIF similarity Feature
class CifSimilarityFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'CIF similarity', 'Compare uploaded crystal structures using AMD or PDD Earth Movers Distance');
        this._abortController = null;
        this._uploadedFiles = [];
        this._downloadUrl = null;
    }

    createInputsHTML() {
        return `
            <p>Configure input parameters for CIF similarity</p>
            <div class="input-controls">
                <label>CIF Files
                    <div style="margin-top:6px; padding:12px; background:#f5f5f5; border-radius:4px; border:2px dashed #ccc;">
                        <input type="file" id="cifFiles_${this.featureId}" accept=".cif" multiple required
                               onchange="window.features[${this.featureId}]._handleFileSelection();">
                        <div id="cifFileList_${this.featureId}" style="margin-top:8px; font-size:12px; color:#333;"></div>
                    </div>
                </label>
                ${this.createSelectInput(`distanceMetric_${this.featureId}`, 'Distance Metric', [{value: 'amd', text: 'Average Minimum Distance (AMD)'}, {value: 'pdd_emd', text: 'PDD Earth Movers Distance'}], true)}
                ${this.createNumberInput(`k_${this.featureId}`, 'Neighbourhood size k', '1', '500', '1', '100')}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>CIF similarity results and outputs</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Distance Matrix:</strong>
                    <div id="distanceMatrix_${this.featureId}" style="max-height:500px; overflow:auto;">Pending...</div>
                </div>
                <div class="output-item">
                    <strong>Download Results (JSON):</strong>
                    <span id="downloadResultsJson_${this.featureId}">Pending...</span>
                    <a id="downloadResultsLink_${this.featureId}" style="display:none; margin-left:10px;" download="cif_similarity_results.json">Download</a>
                </div>
            </div>
        `;
    }

    _handleFileSelection() {
        const input = document.getElementById(`cifFiles_${this.featureId}`);
        const list = document.getElementById(`cifFileList_${this.featureId}`);
        if (!input || !list) return;
        this._uploadedFiles = Array.from(input.files);
        list.textContent = `${this._uploadedFiles.length} CIF file(s) selected`;
    }

    async cancelProcessing() {
        if (!this.isProcessing) return;

        this._cancelled = true;

        const cancelBtn = document.getElementById(`cancelBtn_${this.featureId}`);
        if (cancelBtn) {
            cancelBtn.disabled = true;
            cancelBtn.textContent = 'Cancelling...';
        }

        this.addLog('Requesting cancellation...', 'warning');

        if (this._abortController) this._abortController.abort();

        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';
        try {
            const resp = await fetch(`${backendUrl}/api/process/${this.featureId}/cancel`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });

            if (resp.ok) {
                const data = await resp.json();
                this.addLog(`Backend: ${data.message || 'cancel acknowledged'}`, 'info');
            } else {
                this.addLog(`Backend cancel returned HTTP ${resp.status}`, 'warning');
            }
        } catch (err) {
            this.addLog(`Cancel request failed: ${err.message}`, 'error');
        }
    }

    async callPythonBackend() {
        if (this._uploadedFiles.length < 2) {
            throw new Error('Please select at least two CIF files before running CIF similarity.');
        }
        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';
        this._abortController = new AbortController();
        const metric = document.getElementById(`distanceMetric_${this.featureId}`)?.value || 'amd';
        const k = Math.max(1, Math.min(500, parseInt(document.getElementById(`k_${this.featureId}`)?.value || '100', 10) || 100));
        const cifStrings = [];
        const labels = [];
        for (const file of this._uploadedFiles) {
            cifStrings.push(await file.text());
            labels.push(file.name.replace(/\.cif$/i, ''));
        }
        const response = await fetch(`${backendUrl}/api/process/${this.featureId}/stream`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({cif_strings: cifStrings, labels, distanceMetric: metric, k}),
            signal: this._abortController.signal,
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text()}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResult = null;
        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {stream: true});
            const blocks = buffer.split('\n\n');
            buffer = blocks.pop() || '';
            for (const block of blocks) {
                let eventType = 'log';
                let eventData = null;
                for (const line of block.split('\n')) {
                    if (line.startsWith('event:')) eventType = line.slice(6).trim();
                    if (line.startsWith('data:')) eventData = JSON.parse(line.slice(5).trim());
                }
                if (eventType === 'log') this.addLog(eventData?.message || '', eventData?.level || 'info');
                if (eventType === 'progress') {
                    const fill = document.getElementById(`progressFill_${this.featureId}`);
                    if (fill) fill.style.width = `${Math.round((eventData.progress || 0) * 100)}%`;
                    this.addLog(eventData.message || '', 'info');
                }
                if (eventType === 'result') finalResult = eventData;
            }
        }
        return finalResult || {status: 'error', message: 'Backend returned no result.'};
    }

    async processFeature() {
        return {status: 'local_fallback', message: 'CIF similarity requires the Python backend.'};
    }

    _buildDistanceHeatmapHTML(matrix, labels) {
        const n = matrix.length;
        if (n === 0) return '';

        const escape = (s) => String(s).replace(/[&<>"']/g, (c) => (
            { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
        ));

        let vmax = 0;
        for (const row of matrix) {
            for (const value of row) if (value > vmax) vmax = value;
        }
        if (vmax === 0) vmax = 1;

        const colorFor = (value) => {
            const t = Math.min(1, Math.max(0, value / vmax));
            return `rgb(255, ${Math.round(255 * (1 - 0.85 * t))}, ${Math.round(255 * (1 - 0.95 * t))})`;
        };

        const cellSize = n > 25 ? 14 : n > 15 ? 20 : 28;
        const showValues = n <= 20;
        const labelFontSize = n > 25 ? 7 : 9;
        let html = '<div style="margin-top:10px;"><strong>Distance Matrix (lower triangle):</strong>';
        html += '<div style="overflow:auto; max-width:100%; margin-top:6px;"><table style="border-collapse:collapse;">';
        html += '<tr><th></th>';
        for (let column = 0; column < n; column++) {
            const label = escape(labels[column] ?? `S${column + 1}`);
            html += `<th style="font-size:${labelFontSize}px; padding:2px; max-width:${cellSize}px; overflow:hidden; white-space:nowrap;" title="${label}">${column + 1}</th>`;
        }
        html += '</tr>';

        for (let row = 0; row < n; row++) {
            const rowLabel = escape(labels[row] ?? `S${row + 1}`);
            html += `<tr><th style="font-size:${labelFontSize}px; padding:2px; text-align:right; white-space:nowrap;" title="${rowLabel}">${row + 1}</th>`;
            for (let column = 0; column < n; column++) {
                if (column > row) {
                    html += `<td style="width:${cellSize}px; height:${cellSize}px; border:1px solid #eee;"></td>`;
                    continue;
                }
                const value = matrix[row][column];
                const title = `${escape(labels[row] ?? `S${row + 1}`)} vs ${escape(labels[column] ?? `S${column + 1}`)}: ${value.toFixed(4)}`;
                html += `<td style="width:${cellSize}px; height:${cellSize}px; background:${colorFor(value)}; border:1px solid #ddd; text-align:center; font-size:${labelFontSize}px;" title="${title}">${showValues ? value.toFixed(2) : ''}</td>`;
            }
            html += '</tr>';
        }

        html += '</table></div>';
        const stops = [0, 0.25, 0.5, 0.75, 1].map((value) => `${colorFor(value * vmax)} ${value * 100}%`).join(', ');
        html += '<div style="margin-top:8px; display:flex; align-items:center; gap:8px;">';
        html += '<span style="font-size:11px; color:#333;">0</span>';
        html += `<div style="flex:0 1 220px; height:14px; background:linear-gradient(to right, ${stops}); border:1px solid #ccc; border-radius:2px;"></div>`;
        html += `<span style="font-size:11px; color:#333;">${vmax.toFixed(3)}</span>`;
        html += '<span style="font-size:11px; color:#666; margin-left:6px;">AMD distance</span></div></div>';
        return html;
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        const matrixEl = document.getElementById(`distanceMatrix_${this.featureId}`);
        const statusEl = document.getElementById(`downloadResultsJson_${this.featureId}`);
        const linkEl = document.getElementById(`downloadResultsLink_${this.featureId}`);
        if (!finalResults || finalResults.error || finalResults.status === 'error') {
            if (matrixEl) matrixEl.textContent = `Error: ${finalResults?.error || finalResults?.message || 'Unknown error'}`;
            return;
        }

        if (matrixEl && finalResults.amd_matrix) {
            matrixEl.innerHTML = this._buildDistanceHeatmapHTML(
                finalResults.amd_matrix,
                finalResults.labels || [],
            );
        }
        if (this._downloadUrl) URL.revokeObjectURL(this._downloadUrl);
        this._downloadUrl = URL.createObjectURL(new Blob([JSON.stringify(finalResults, null, 2)], {type: 'application/json'}));
        if (statusEl) statusEl.textContent = 'Ready';
        if (linkEl) { linkEl.href = this._downloadUrl; linkEl.download = `cif_similarity_${Date.now()}.json`; linkEl.style.display = ''; }
    }
}

window.CifSimilarityFeature = CifSimilarityFeature;
