// Auto-generated IU Feature for predictor: mattersim
class MattersimIUFeature extends BaseFeature {
    constructor(featureId, iuMeta = {}) {
        super(
            featureId,
            iuMeta.iuName ? `${iuMeta.iuName} IU Feature` : 'MatterSim IU Feature',
            iuMeta.iuDesc || 'Universal neural network potential for materials simulation'
        );
        this.iuType = iuMeta.iuType || 'predictor';
        this.iuId = iuMeta.iuId || 'mattersim';
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
                            <small style="color:#666;">Select .cif files or .zip archive. Drag & drop supported.</small>
                            <div id="fileList_${this.featureId}" style="margin-top:8px; font-size:12px; color:#333;"></div>
                        </div>
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

        this.addLog('Reading CIF files and starting predictions...', 'info');

        try {
            // Read CIF files as text strings
            const cifStrings = [];
            for (const file of this._uploadedFiles) {
                if (file.name.endsWith('.cif')) {
                    const text = await file.text();
                    cifStrings.push(text);
                } else if (file.name.endsWith('.zip')) {
                    this.addLog('ZIP files require backend extraction support', 'warning');
                }
            }

            if (cifStrings.length === 0) {
                throw new Error('No valid .cif files found in selection');
            }

            const payload = {
                cif_strings: cifStrings
            };

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
                        if (line.startsWith('event:')) {
                            eventType = line.slice(6).trim();
                        } else if (line.startsWith('data:')) {
                            const dataStr = line.slice(5).trim();
                            try {
                                eventData = JSON.parse(dataStr);
                            } catch (e) {
                                eventData = { message: dataStr };
                            }
                        }
                    }

                    if (!eventData) continue;

                    if (eventType === 'log') {
                        const msg = eventData.message || '';
                        const level = eventData.level || 'info';
                        this.addLog(msg, level);
                    } else if (eventType === 'progress') {
                        const raw = Number(eventData.progress);
                        const pct = Number.isFinite(raw)
                            ? Math.round(Math.max(0, Math.min(1, raw)) * 100)
                            : null;
                        const msg = eventData.message || (pct !== null ? `Progress: ${pct}%` : 'Progress update');
                        this.addLog(msg, 'info');
                    } else if (eventType === 'result') {
                        finalResult = eventData;
                        const numResults = Array.isArray(eventData.results) ? eventData.results.length : 0;
                        this.addLog(`Prediction complete: ${numResults} result(s)`, 'success');
                    } else if (eventType === 'error') {
                        this.addLog(eventData.message || 'Unknown error', 'error');
                    }
                }
            }

            if (buffer.trim()) {
                const lines = buffer.split('\n');
                let eventType = 'log';
                let eventData = null;

                for (const line of lines) {
                    if (line.startsWith('event:')) {
                        eventType = line.slice(6).trim();
                    } else if (line.startsWith('data:')) {
                        const dataStr = line.slice(5).trim();
                        try {
                            eventData = JSON.parse(dataStr);
                        } catch (e) {
                            eventData = { message: dataStr };
                        }
                    }
                }

                if (eventData && eventType === 'result') {
                    finalResult = eventData;
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
        const entries = Object.entries(properties);
        if (entries.length === 0) {
            propertiesDisplay.innerHTML = '<p style="color:#999;">No properties returned for this input</p>';
            return;
        }

        let html = '<div style="display:grid; gap:8px;">';
        const cifPropertyViews = [];

        entries.forEach(([propKey, value]) => {
            const unit = this._propertyUnitByKey[propKey] || '';
            const displayLabel = this._formatLabelWithUnit(propKey, unit);

            if (this._isCifProperty(propKey, value)) {
                const safeId = this._sanitizeDomId(`${this.featureId}_${result.index}_${propKey}`);
                const viewerId = `iuPropStructureViewer_${safeId}`;
                const textId = `iuPropCifViewer_${safeId}`;
                const toggleId = `iuPropToggleCifBtn_${safeId}`;

                html += `
                    <div style="padding:8px; background:#f9f9f9; border-radius:4px;">
                        <strong style="color:#333;">${this._escapeHtml(displayLabel)}</strong>
                        <div id="${viewerId}" style="width:100%; height:300px; position:relative; background:#ffffff; border-radius:6px; margin-top:6px;"></div>
                        <div style="margin-top:6px; text-align:right;">
                            <button id="${toggleId}" class="btn-secondary" style="font-size:11px; padding:4px 10px; cursor:pointer; background:#313244; color:#cdd6f4; border:1px solid #45475a; border-radius:4px;">Show CIF Text</button>
                        </div>
                        <pre id="${textId}" class="cif-viewer" style="display:none; max-height:240px; overflow:auto; background:#1e1e2e; color:#cdd6f4; padding:12px; border-radius:6px; font-size:12px; white-space:pre-wrap; margin-top:6px;"></pre>
                    </div>
                `;

                cifPropertyViews.push({ viewerId, textId, toggleId, cifData: typeof value === 'string' ? value : '' });
                return;
            }

            let displayValue = 'N/A';
            if (value !== null && value !== undefined) {
                if (typeof value === 'object') {
                    displayValue = JSON.stringify(value);
                } else {
                    displayValue = String(value);
                }
            }

            const valueColor = displayValue === 'N/A' ? '#999' : '#333';
            html += `
                <div style="display:flex; justify-content:space-between; gap:12px; padding:6px; background:#f9f9f9; border-radius:4px; align-items:flex-start;">
                    <strong style="color:#333;">${this._escapeHtml(displayLabel)}</strong>
                    <span style="color:${valueColor}; font-family:monospace; text-align:right; white-space:pre-wrap; word-break:break-word;">${this._escapeHtml(displayValue)}</span>
                </div>
            `;
        });

        html += '</div>';
        propertiesDisplay.innerHTML = html;

        cifPropertyViews.forEach((entry) => {
            const viewerContainer = document.getElementById(entry.viewerId);
            const textEl = document.getElementById(entry.textId);
            const toggleBtn = document.getElementById(entry.toggleId);
            const cifData = entry.cifData || '';

            if (textEl) {
                textEl.textContent = cifData || '(no CIF data available)';
            }

            if (!viewerContainer || !cifData || typeof $3Dmol === 'undefined') {
                if (viewerContainer) {
                    viewerContainer.innerHTML = '<p style="color:#333;padding:20px;">3D viewer unavailable</p>';
                }
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
            }

            if (toggleBtn && textEl) {
                const newBtn = toggleBtn.cloneNode(true);
                toggleBtn.parentNode.replaceChild(newBtn, toggleBtn);
                newBtn.addEventListener('click', () => {
                    const hidden = textEl.style.display === 'none';
                    textEl.style.display = hidden ? 'block' : 'none';
                    newBtn.textContent = hidden ? 'Hide CIF Text' : 'Show CIF Text';
                });
            }
        });
    }

    destroy() {
        if (this._downloadUrl) {
            URL.revokeObjectURL(this._downloadUrl);
            this._downloadUrl = null;
        }
    }
}

window.MattersimIUFeature = MattersimIUFeature;
