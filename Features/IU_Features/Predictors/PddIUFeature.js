// Auto-generated IU Feature for predictor: pdd
class PddIUFeature extends BaseFeature {
    constructor(featureId, iuMeta = {}) {
        super(
            featureId,
            iuMeta.iuName ? `${iuMeta.iuName} IU Feature` : 'PDD IU Feature',
            iuMeta.iuDesc || 'Pointwise Distance Distribution predictor — computes PDD descriptor matrices and pairwise EMD similarity for crystal structures'
        );
        this.iuType = iuMeta.iuType || 'predictor';
        this.iuId = iuMeta.iuId || 'pdd';
        this._abortController = null;
        this._propertyDefs = [];
        this._propertyUnitByKey = {};
        this._downloadUrl = null;
        this._uploadedFiles = [];
    }

    _toDisplayLabel(propertyKey) {
        const tokenMap = {
            dos: 'DOS',
            ef: 'EF',
            xc: 'XC',
            id: 'ID',
            scan: 'SCAN',
            dft: 'DFT',
            hhi: 'HHI',
            mp: 'MP',
        };

        return String(propertyKey)
            .split('_')
            .map((token) => {
                const lower = token.toLowerCase();
                if (tokenMap[lower]) return tokenMap[lower];
                return token.charAt(0).toUpperCase() + token.slice(1).toLowerCase();
            })
            .join(' ');
    }

    _formatLabelWithUnit(propertyName, unit) {
        const displayName = this._toDisplayLabel(propertyName);
        if (!unit) return displayName;
        return `${displayName} (${unit})`;
    }

    _escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    _sanitizeDomId(value) {
        return String(value).replace(/[^a-zA-Z0-9_-]/g, '_');
    }

    _isLikelyCifText(value) {
        if (typeof value !== 'string') return false;
        const text = value.trim();
        if (!text) return false;
        return text.startsWith('data_') || text.includes('_cell_') || text.includes('loop_') || text.includes('_atom_site');
    }

    _isCifProperty(propertyKey, value) {
        if (typeof value !== 'string') return false;
        return String(propertyKey).toLowerCase().includes('cif') || this._isLikelyCifText(value);
    }

    createInputsHTML() {
        return `
            <div class="iu-input-scroll">
                <div class="input-controls">
                    <label>CIF Files
                        <div style="margin-top:6px; padding:12px; background:#f5f5f5; border-radius:4px; border:2px dashed #ccc;">
                            <input type="file" id="cifUpload_${this.featureId}" multiple accept=".cif,.zip" style="display:block; margin-bottom:8px;">
                            <small style="color:#666;">Select one or more .cif files or a .zip archive.</small>
                            <div id="fileList_${this.featureId}" style="margin-top:8px; font-size:12px; color:#333;"></div>
                        </div>
                    </label>
                    <label style="margin-top:10px; display:block;">Neighbourhood size k
                        <input type="number" id="pddK_${this.featureId}" value="100" min="1" max="500" step="1"
                               style="width:90px; margin-left:8px;">
                        <small style="color:#666; margin-left:6px;">Number of nearest neighbours for PDD descriptor (default 100)</small>
                    </label>
                </div>
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>${this.iuId} Prediction Results</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item" id="iuInputSelectorRow_${this.featureId}" style="display:none;">
                    <strong>Input Structure:</strong>
                    <select id="iuInputSelector_${this.featureId}"></select>
                </div>

                <div class="output-item" id="iuCifViewerRow_${this.featureId}" style="display:none;">
                    <strong>Crystal Structure:</strong>
                    <div id="iuStructureViewer_${this.featureId}" style="
                        width:100%; height:400px; position:relative;
                        background:#ffffff; border-radius:6px; margin-top:6px;
                    "></div>
                    <div style="margin-top:6px; text-align:right;">
                        <button id="iuToggleCifBtn_${this.featureId}" class="btn-secondary" style="
                            font-size:11px; padding:4px 10px; cursor:pointer;
                            background:#313244; color:#cdd6f4; border:1px solid #45475a;
                            border-radius:4px;
                        ">Show CIF Text</button>
                    </div>
                    <pre id="iuCifViewer_${this.featureId}" class="cif-viewer" style="
                        display:none; max-height:300px; overflow:auto; background:#1e1e2e;
                        color:#cdd6f4; padding:12px; border-radius:6px;
                        font-size:12px; white-space:pre-wrap; margin-top:6px;
                    "></pre>
                </div>

                <div class="output-item" id="iuPropertiesRow_${this.featureId}" style="display:none;">
                    <strong>Predicted Properties:</strong>
                    <div id="iuPropertiesDisplay_${this.featureId}" style="margin-top:8px;"></div>
                </div>

                <div class="output-item">
                    <strong>Prediction Results (JSON):</strong>
                    <span id="iuPredictionStatus_${this.featureId}">Pending...</span>
                    <a id="iuPredictionDownload_${this.featureId}" style="display:none; margin-left:10px;" download="${this.iuId}_predictions.json">Download</a>
                </div>
            </div>
        `;
    }

    async initializeUI() {
        const fileInput = document.getElementById(`cifUpload_${this.featureId}`);
        if (!fileInput) return;

        fileInput.addEventListener('change', (e) => this._handleFileSelection(e));

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
                this._handleFileSelection({});
            }
        });

        await this._renderPropertyDefs();
    }

    _handleFileSelection(evt) {
        const fileInput = document.getElementById(`cifUpload_${this.featureId}`);
        const listEl = document.getElementById(`fileList_${this.featureId}`);
        if (!fileInput || !listEl) return;

        const files = Array.from(fileInput.files);
        this._uploadedFiles = files;

        listEl.textContent = `${files.length} file(s) selected`;

        this.addLog(`Loaded ${files.length} file(s)`, 'info');
    }

    async _renderPropertyDefs() {
        try {
            const [mappingRes, commonRes] = await Promise.all([
                fetch(`./Information_Units/property_mappings/sources/predictors/${this.iuId}.json`),
                fetch('./Information_Units/property_mappings/common_properties.json').catch(() => null),
            ]);
            if (!mappingRes.ok) throw new Error(`${this.iuId} mapping HTTP ${mappingRes.status}`);

            const mapping = await mappingRes.json();
            const common = commonRes && commonRes.ok ? await commonRes.json() : {};
            const properties = mapping?.properties || {};
            const commonProperties = common?.properties || {};

            const defs = Object.entries(properties)
                .map(([name, cfg]) => ({
                    uiKey: name,
                    sourceKey: (typeof cfg?.name === 'string' && cfg.name.trim()) ? cfg.name.trim() : name,
                    predictable: !!cfg?.predictable,
                    unit: commonProperties?.[name]?.unit || '',
                }))
                .filter((p) => p.predictable);

            this._propertyDefs = defs;
            this._propertyUnitByKey = {};
            defs.forEach((prop) => {
                this._propertyUnitByKey[prop.uiKey] = prop.unit || '';
                this._propertyUnitByKey[prop.sourceKey] = prop.unit || '';
            });
        } catch (error) {
            this.addLog(`Failed to load property mappings: ${error.message}`, 'error');
            this._propertyDefs = [];
            this._propertyUnitByKey = {};
        }
    }

    collectInputData() {
        return {
            cif_strings: this._uploadedFiles.length > 0 ? 'files_to_be_uploaded' : [],
        };
    }

    async callPythonBackend() {
        if (this._uploadedFiles.length === 0) {
            throw new Error('No CIF files selected. Please upload .cif files or a .zip archive.');
        }

        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';

        this._abortController = new AbortController();
        this._cancelled = false;

        this.addLog('Reading CIF files and starting PDD predictions...', 'info');

        try {
            const cifStrings = [];
            for (const file of this._uploadedFiles) {
                if (file.name.endsWith('.cif')) {
                    cifStrings.push(await file.text());
                } else if (file.name.endsWith('.zip')) {
                    this.addLog('ZIP files require backend extraction support', 'warning');
                }
            }

            if (cifStrings.length === 0) {
                throw new Error('No valid .cif files found in selection');
            }

            const kEl = document.getElementById(`pddK_${this.featureId}`);
            const kValue = kEl ? Math.max(1, parseInt(kEl.value, 10) || 100) : 100;
            this.addLog(`k = ${kValue}, processing ${cifStrings.length} structure(s)…`, 'info');

            const payload = { cif_strings: cifStrings, k: kValue };

            const response = await fetch(
                `${backendUrl}/api/process/iu/${this.iuType}/${this.iuId}/stream`,
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
                        const raw = Number(eventData.progress);
                        const pct = Number.isFinite(raw) ? Math.round(Math.max(0, Math.min(1, raw)) * 100) : null;
                        this.addLog(eventData.message || (pct !== null ? `Progress: ${pct}%` : 'Progress update'), 'info');
                    } else if (eventType === 'result') {
                        finalResult = eventData;
                        const numResults = Array.isArray(eventData.results) ? eventData.results.length : 0;
                        this.addLog(`PDD prediction complete: ${numResults} result(s)`, 'success');
                    } else if (eventType === 'error') {
                        this.addLog(eventData.message || 'Unknown error', 'error');
                    }
                }
            }

            return finalResult || { status: 'completed', cif_strings: cifStrings, results: [] };
        } catch (error) {
            if (error.name === 'AbortError') {
                this.addLog('Request cancelled by user', 'warning');
                return { status: 'cancelled', cif_strings: [], results: [] };
            }
            throw error;
        }
    }

    async cancelProcessing() {
        if (!this.isProcessing) return;

        this._cancelled = true;
        const cancelBtn = document.getElementById(`cancelBtn_${this.featureId}`);
        if (cancelBtn) {
            cancelBtn.disabled = true;
            cancelBtn.textContent = 'Cancelling...';
        }

        this.addLog('Cancel requested by user.', 'warning');

        if (this._abortController) {
            this._abortController.abort();
            this._abortController = null;
        }
    }

    async processFeature() {
        return {
            source: this.iuId,
            cif_strings: [],
            results: [],
            status: 'local_fallback',
        };
    }

    updateOutputs(results = null) {
        const data = results || this.results || {};

        if (data.error) {
            const statusEl = document.getElementById(`iuPredictionStatus_${this.featureId}`);
            const downloadEl = document.getElementById(`iuPredictionDownload_${this.featureId}`);
            if (statusEl) statusEl.textContent = `Error: ${data.error}`;
            if (downloadEl) downloadEl.style.display = 'none';
            return;
        }

        const statusEl = document.getElementById(`iuPredictionStatus_${this.featureId}`);
        const downloadEl = document.getElementById(`iuPredictionDownload_${this.featureId}`);

        if (this._downloadUrl) {
            URL.revokeObjectURL(this._downloadUrl);
            this._downloadUrl = null;
        }

        if (downloadEl) {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            this._downloadUrl = URL.createObjectURL(blob);
            downloadEl.href = this._downloadUrl;
            downloadEl.download = `${this.iuId}_predictions_${Date.now()}.json`;
            downloadEl.style.display = '';
        }

        if (statusEl) {
            statusEl.textContent = 'Ready';
        }

        const inputCifs = Array.isArray(data.cif_strings) ? data.cif_strings : [];
        const predResults = Array.isArray(data.results) ? data.results : [];
        const selectableResults = predResults
            .filter((r) => r && Number.isInteger(r.index))
            .sort((a, b) => a.index - b.index);

        const inputSelector = document.getElementById(`iuInputSelector_${this.featureId}`);
        const inputRow = document.getElementById(`iuInputSelectorRow_${this.featureId}`);
        const cifRow = document.getElementById(`iuCifViewerRow_${this.featureId}`);
        const viewerContainer = document.getElementById(`iuStructureViewer_${this.featureId}`);
        const cifViewer = document.getElementById(`iuCifViewer_${this.featureId}`);
        const toggleCifBtn = document.getElementById(`iuToggleCifBtn_${this.featureId}`);
        const propertiesRow = document.getElementById(`iuPropertiesRow_${this.featureId}`);
        const propertiesDisplay = document.getElementById(`iuPropertiesDisplay_${this.featureId}`);

        if (!inputSelector || !inputRow || !cifRow || !viewerContainer || !cifViewer || !propertiesRow || !propertiesDisplay) {
            return;
        }

        if (selectableResults.length === 0) {
            inputRow.style.display = 'none';
            cifRow.style.display = 'none';
            propertiesRow.style.display = 'none';
            return;
        }

        inputSelector.innerHTML = selectableResults
            .map((result, i) => {
                const idxLabel = Number.isInteger(result.index) ? `Input ${result.index + 1}` : `Result ${i + 1}`;
                const statusLabel = result.status === 'error' ? ' (error)' : '';
                return `<option value="${i}">${idxLabel}${statusLabel}</option>`;
            })
            .join('');
        inputRow.style.display = '';
        cifRow.style.display = '';
        propertiesRow.style.display = '';

        if (this._3dViewer) {
            viewerContainer.innerHTML = '';
            this._3dViewer = null;
        }

        const showStructure = (selectedPos) => {
            const selectedResult = selectableResults[selectedPos];
            if (!selectedResult) return;

            const cifData = (typeof selectedResult.cif_input === 'string' && selectedResult.cif_input.trim())
                ? selectedResult.cif_input
                : (Number.isInteger(selectedResult.index) ? (inputCifs[selectedResult.index] || '') : '');
            cifViewer.textContent = cifData || '(no CIF data available)';

            if (!cifData || typeof $3Dmol === 'undefined') {
                viewerContainer.innerHTML = '<p style="color:#333;padding:20px;">3D viewer unavailable</p>';
            } else {
                viewerContainer.innerHTML = '';
                const viewer = $3Dmol.createViewer(viewerContainer, {
                    backgroundColor: '#ffffff',
                });

                viewer.addModel(cifData, 'cif', { doAssembly: true, duplicateAssemblyAtoms: true });
                viewer.setStyle({}, {
                    sphere: { radius: 0.4, colorscheme: 'Jmol' },
                    stick: { radius: 0.15, colorscheme: 'Jmol' },
                });
                viewer.addUnitCell();
                viewer.zoomTo();
                viewer.render();

                this._3dViewer = viewer;
            }

            this._updateProperties(selectedResult);
        };

        showStructure(0);

        if (toggleCifBtn) {
            const newBtn = toggleCifBtn.cloneNode(true);
            toggleCifBtn.parentNode.replaceChild(newBtn, toggleCifBtn);
            newBtn.addEventListener('click', () => {
                const hidden = cifViewer.style.display === 'none';
                cifViewer.style.display = hidden ? 'block' : 'none';
                newBtn.textContent = hidden ? 'Hide CIF Text' : 'Show CIF Text';
            });
        }

        const newSelector = inputSelector.cloneNode(true);
        inputSelector.parentNode.replaceChild(newSelector, inputSelector);
        newSelector.addEventListener('change', () => showStructure(parseInt(newSelector.value, 10)));
    }

    _updateProperties(result) {
        const propertiesDisplay = document.getElementById(`iuPropertiesDisplay_${this.featureId}`);
        if (!propertiesDisplay) return;

        if (!result) {
            propertiesDisplay.innerHTML = '<p style="color:#999;">No prediction result for this input</p>';
            return;
        }

        if (result.status === 'error') {
            const errMsg = result.error ? this._escapeHtml(result.error) : 'Unknown prediction error';
            propertiesDisplay.innerHTML = `<p style="color:#c0392b;">${errMsg}</p>`;
            return;
        }

        const properties = result.properties || {};
        let html = '<div style="display:grid; gap:8px;">';

        // ── AMD vector (1-D summary) ─────────────────────────────────────────
        const vec = properties.pdd_vector;
        if (Array.isArray(vec)) {
            const preview = vec.slice(0, 8).map(v => (typeof v === 'number' ? v.toFixed(4) : String(v))).join(', ');
            const suffix = vec.length > 8 ? ` … (${vec.length} values)` : '';
            html += `
                <div style="padding:6px; background:#f9f9f9; border-radius:4px;">
                    <strong style="color:#333;">AMD Vector (mean PDD row, shape ${vec.length})</strong>
                    <div style="font-family:monospace; font-size:11px; color:#555; margin-top:4px; word-break:break-all;">[${preview}${suffix}]</div>
                </div>`;
        }

        // ── PDD matrix (shape summary) ────────────────────────────────────────
        const mat = properties.pdd_matrix;
        if (Array.isArray(mat)) {
            const rows = mat.length;
            const cols = Array.isArray(mat[0]) ? mat[0].length : 0;
            html += `
                <div style="padding:6px; background:#f9f9f9; border-radius:4px;">
                    <strong style="color:#333;">PDD Matrix (shape ${rows} × ${cols})</strong>
                    <div style="font-size:11px; color:#666; margin-top:4px;">Full matrix included in downloaded JSON.</div>
                </div>`;
        }

        // ── EMD matrix (cross-input, only when >1 structure) ─────────────────
        const emd = properties.pdd_emd_matrix;
        if (Array.isArray(emd)) {
            const n = emd.length;
            let tableHtml = `<table style="border-collapse:collapse; font-size:11px; margin-top:6px;">`;
            tableHtml += `<tr><th style="padding:3px 6px;"></th>`;
            for (let c = 0; c < n; c++) tableHtml += `<th style="padding:3px 6px; color:#555;">S${c + 1}</th>`;
            tableHtml += '</tr>';
            for (let r = 0; r < n; r++) {
                tableHtml += `<tr><th style="padding:3px 6px; color:#555;">S${r + 1}</th>`;
                for (let c = 0; c < n; c++) {
                    const v = typeof emd[r][c] === 'number' ? emd[r][c].toFixed(4) : '-';
                    const bg = r === c ? '#e8e8e8' : '#f9f9f9';
                    tableHtml += `<td style="padding:3px 6px; background:${bg}; font-family:monospace;">${v}</td>`;
                }
                tableHtml += '</tr>';
            }
            tableHtml += '</table>';
            html += `
                <div style="padding:6px; background:#f9f9f9; border-radius:4px;">
                    <strong style="color:#333;">Pairwise EMD Distance Matrix (${n} × ${n})</strong>
                    ${tableHtml}
                </div>`;
        }

        html += '</div>';
        propertiesDisplay.innerHTML = html;
    }

    destroy() {
        if (this._downloadUrl) {
            URL.revokeObjectURL(this._downloadUrl);
            this._downloadUrl = null;
        }
    }
}

window.PddIUFeature = PddIUFeature;
