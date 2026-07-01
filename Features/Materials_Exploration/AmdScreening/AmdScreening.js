// AMD screening Feature
class AmdScreeningFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'AMD screening', 'Screen uploaded CIF structures for AMD-based candidate selection');
        this._abortController = null;
        this._uploadedFiles = [];
        this._downloadUrl = null;
    }

    createInputsHTML() {
        return `
            <p>Upload two or more CIF files to run AMD pairwise similarity screening.</p>
            <div class="input-controls">
                <label>CIF Files
                    <div style="margin-top:6px; padding:12px; background:#f5f5f5; border-radius:4px; border:2px dashed #ccc;">
                        <input type="file" id="cifFiles_${this.featureId}" multiple accept=".cif"
                               style="display:block; margin-bottom:8px;">
                        <small style="color:#666;">Select two or more .cif files. Drag &amp; drop supported.</small>
                        <div id="cifFileList_${this.featureId}" style="margin-top:8px; font-size:12px; color:#333;"></div>
                    </div>
                </label>
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>AMD screening results</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item" id="amdSummaryRow_${this.featureId}" style="display:none;">
                    <strong>Summary:</strong>
                    <div id="amdSummary_${this.featureId}" style="margin-top:6px; font-size:13px;"></div>
                </div>
                <div class="output-item">
                    <strong>Download Results (JSON):</strong>
                    <span id="downloadResultsJson_${this.featureId}">Pending...</span>
                    <a id="downloadResultsLink_${this.featureId}" style="display:none; margin-left:10px;" download="amd_screening_results.json">Download</a>
                </div>
            </div>
        `;
    }

    async initializeUI() {
        const fileInput = document.getElementById(`cifFiles_${this.featureId}`);
        if (!fileInput) return;

        fileInput.addEventListener('change', () => this._handleFileSelection());

        const dropZone = fileInput.parentElement;
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.style.background = '#efefef';
        });
        dropZone.addEventListener('dragleave', () => {
            dropZone.style.background = '#f5f5f5';
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.background = '#f5f5f5';
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                this._handleFileSelection();
            }
        });
    }

    _handleFileSelection() {
        const fileInput = document.getElementById(`cifFiles_${this.featureId}`);
        const listEl = document.getElementById(`cifFileList_${this.featureId}`);
        if (!fileInput || !listEl) return;

        this._uploadedFiles = Array.from(fileInput.files);
        listEl.textContent = `${this._uploadedFiles.length} file(s) selected: ${this._uploadedFiles.map(f => f.name).join(', ')}`;
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

        // Abort the in-flight SSE request immediately
        if (this._abortController) {
            this._abortController.abort();
            this._abortController = null;
        }

        // Also notify the backend cancel endpoint
        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';
        try {
            const resp = await fetch(`${backendUrl}/api/process/${this.featureId}/cancel`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (resp.ok) {
                const data = await resp.json();
                this.addLog(`Backend: ${data.message || 'cancel acknowledged'}`, 'info');
            }
        } catch (err) {
            this.addLog(`Cancel request failed: ${err.message}`, 'warning');
        }
    }

    collectInputData() {
        // Inputs are sent as CIF strings in callPythonBackend — return empty here
        return {};
    }

    async callPythonBackend() {
        if (this._uploadedFiles.length < 2) {
            throw new Error('Please select at least two CIF files before running AMD screening.');
        }

        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';
        this._abortController = new AbortController();
        this._cancelled = false;

        this.addLog(`Reading ${this._uploadedFiles.length} CIF file(s)...`, 'info');
        const cifStrings = [];
        for (const file of this._uploadedFiles) {
            cifStrings.push(await file.text());
        }
        this.addLog('Files loaded, sending to backend...', 'info');

        const payload = { cif_strings: cifStrings };

        const response = await fetch(
            `${backendUrl}/api/process/${this.featureId}/stream`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal: this._abortController.signal,
            }
        );

        if (!response.ok) {
            const errBody = await response.text();
            throw new Error(`HTTP ${response.status}: ${errBody}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResult = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const blocks = buffer.split('\n\n');
            buffer = blocks.pop() || '';

            for (const block of blocks) {
                if (!block.trim()) continue;
                const lines = block.split('\n');
                let eventType = 'log';
                let eventData = null;

                for (const line of lines) {
                    if (line.startsWith('event:')) eventType = line.slice(6).trim();
                    else if (line.startsWith('data:')) {
                        try { eventData = JSON.parse(line.slice(5).trim()); }
                        catch { eventData = { message: line.slice(5).trim() }; }
                    }
                }

                if (!eventData) continue;

                if (eventType === 'log') {
                    this.addLog(eventData.message || '', eventData.level || 'info');
                } else if (eventType === 'progress') {
                    const pct = Math.round((Number(eventData.progress) || 0) * 100);
                    const progressFill = document.getElementById(`progressFill_${this.featureId}`);
                    if (progressFill) progressFill.style.width = `${pct}%`;
                    this.addLog(eventData.message || `Progress: ${pct}%`, 'info');
                } else if (eventType === 'result') {
                    finalResult = eventData;
                    this.addLog('AMD screening complete.', 'success');
                } else if (eventType === 'error') {
                    this.addLog(eventData.message || 'Unknown error', 'error');
                }
            }
        }

        return finalResult || { status: 'completed', results: null };
    }

    async processFeature() {
        return { status: 'local_fallback', results: null };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;

        const statusEl = document.getElementById(`downloadResultsJson_${this.featureId}`);
        const linkEl = document.getElementById(`downloadResultsLink_${this.featureId}`);
        const summaryRow = document.getElementById(`amdSummaryRow_${this.featureId}`);
        const summaryEl = document.getElementById(`amdSummary_${this.featureId}`);

        if (!finalResults || finalResults.error) {
            if (statusEl) statusEl.textContent = `Error: ${finalResults?.error || 'Unknown error'}`;
            return;
        }

        if (finalResults.status === 'cancelled') {
            if (statusEl) statusEl.textContent = 'Cancelled.';
            return;
        }

        if (finalResults.status === 'error') {
            if (statusEl) statusEl.textContent = `Error: ${finalResults.message || 'Unknown error'}`;
            return;
        }

        // Build summary from pairwise distances
        const amdResults = finalResults.results;
        if (amdResults) {
            const resultItems = Array.isArray(amdResults.results) ? amdResults.results : [];
            const first = resultItems[0];
            if (first && first.status === 'success' && summaryEl && summaryRow) {
                const pairs = first.properties?.pairwise_distances || [];
                const identical = pairs.filter(p => p.identical).length;
                const verySimilar = pairs.filter(p => p.very_similar && !p.identical).length;
                const similar = pairs.filter(p => p.similar && !p.very_similar).length;
                summaryEl.innerHTML = `
                    <strong>Total pairs compared:</strong> ${pairs.length}<br>
                    <strong>Identical:</strong> ${identical} &nbsp;
                    <strong>Very similar (PDD/EMD &lt; 0.1):</strong> ${verySimilar} &nbsp;
                    <strong>Similar (PDD/EMD &lt; 0.5):</strong> ${similar}
                `;
                summaryRow.style.display = '';
            }
        }

        // Create download link
        if (this._downloadUrl) {
            URL.revokeObjectURL(this._downloadUrl);
            this._downloadUrl = null;
        }

        const blob = new Blob([JSON.stringify(finalResults, null, 2)], { type: 'application/json' });
        this._downloadUrl = URL.createObjectURL(blob);

        if (statusEl) statusEl.textContent = 'Ready';
        if (linkEl) {
            linkEl.href = this._downloadUrl;
            linkEl.download = `amd_screening_${Date.now()}.json`;
            linkEl.style.display = '';
        }
    }
}

window.AmdScreeningFeature = AmdScreeningFeature;

