// Auto-generated IU Feature for generator: mattergen_bulk_modulus
class MattergenBulkModulusIUFeature extends BaseFeature {
    constructor(featureId, iuMeta = {}) {
        super(
            featureId,
            iuMeta.iuName ? `${iuMeta.iuName} IU Feature` : 'MatterGen: Bulk Modulus IU Feature',
            iuMeta.iuDesc || 'Property-conditioned model for generating structures with a target ML-predicted bulk modulus (ml_bulk_modulus)'
        );
        this.iuType = iuMeta.iuType || 'generator';
        this.iuId = iuMeta.iuId || 'mattergen_bulk_modulus';
        this._abortController = null;
        this._propertyDefs = [];
        this._downloadUrl = null;
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

    createInputsHTML() {
        return `
            <div class="iu-input-scroll">
                <div class="input-controls">
                    <label>Batch Size
                        <input type="number" id="batch_size_${this.featureId}" min="1" max="1000" step="1">
                    </label>
                </div>
                <div class="input-controls" id="${this.iuId}PropertyFilters_${this.featureId}">
                    <p>Loading property mappings...</p>
                </div>
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>${this.iuId} IU outputs</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item" id="iuStructSelectorRow_${this.featureId}" style="display:none;">
                    <strong>Structure:</strong>
                    <select id="iuStructSelector_${this.featureId}"></select>
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

                <div class="output-item">
                    <strong>Generated Dataset (JSON):</strong>
                    <span id="iuDataGeneratedStatus_${this.featureId}">Pending...</span>
                    <a id="iuDataGeneratedDownload_${this.featureId}" style="display:none; margin-left:10px;" download="${this.iuId}_generated_dataset.json">Download</a>
                </div>
            </div>
        `;
    }

    async initializeUI() {
        const batchInput = document.getElementById(`batch_size_${this.featureId}`);
        if (batchInput && !batchInput.value) {
            batchInput.value = '10';
        }
        await this._renderPropertyFilters();
    }

    async _renderPropertyFilters() {
        const container = document.getElementById(`${this.iuId}PropertyFilters_${this.featureId}`);
        if (!container) return;

        try {
            const [mappingRes, commonRes] = await Promise.all([
                fetch(`./Information_Units/property_mappings/sources/generators/${this.iuId}.json`),
                fetch('./Information_Units/property_mappings/common_properties.json'),
            ]);
            if (!mappingRes.ok) throw new Error(`${this.iuId} mapping HTTP ${mappingRes.status}`);
            if (!commonRes.ok) throw new Error(`Common properties HTTP ${commonRes.status}`);

            const mapping = await mappingRes.json();
            const common = await commonRes.json();
            const properties = mapping?.properties || {};
            const commonProperties = common?.properties || {};

            const defs = Object.entries(properties)
                .map(([name, cfg]) => ({
                    uiKey: name,
                    sourceKey: (typeof cfg?.name === 'string' && cfg.name.trim()) ? cfg.name.trim() : name,
                    rangeSupport: !!cfg?.range_support,
                    generatable: cfg?.generatable !== false,
                    unit: commonProperties?.[name]?.unit || '',
                }))
                .filter((p) => p.generatable);

            this._propertyDefs = defs;

            if (defs.length === 0) {
                container.innerHTML = '';
                return;
            }

            let html = '<div class="iu-property-list">';
            defs.forEach((prop) => {
                const labelWithUnit = this._formatLabelWithUnit(prop.uiKey, prop.unit);
                if (prop.rangeSupport) {
                    html += `
                        <div class="iu-property-row">
                            <label>${labelWithUnit}
                                <div class="iu-range-inputs">
                                    <input type="number" step="any" id="iu_prop_${prop.uiKey}_min_${this.featureId}" placeholder="Min" title="${prop.uiKey}">
                                    <input type="number" step="any" id="iu_prop_${prop.uiKey}_max_${this.featureId}" placeholder="Max" title="${prop.uiKey}">
                                </div>
                            </label>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="iu-property-row">
                            <label>${labelWithUnit}
                                <input type="text" id="iu_prop_${prop.uiKey}_${this.featureId}" placeholder="Enter Value" title="${prop.uiKey}">
                            </label>
                        </div>
                    `;
                }
            });
            html += '</div>';
            container.innerHTML = html;
        } catch (error) {
            container.innerHTML = `<p>Failed to load property mappings: ${error.message}</p>`;
            this.addLog(`Failed to load property mappings: ${error.message}`, 'error');
        }
    }

    collectInputData() {
        const batchEl = document.getElementById(`batch_size_${this.featureId}`);

        const inputs = {
            batch_size: parseInt(batchEl?.value || '10', 10),
        };

        if (!Number.isFinite(inputs.batch_size) || inputs.batch_size <= 0) {
            inputs.batch_size = 10;
        }

        this._propertyDefs.forEach((prop) => {
            const payloadKey = prop.sourceKey || prop.uiKey;
            if (prop.rangeSupport) {
                const minEl = document.getElementById(`iu_prop_${prop.uiKey}_min_${this.featureId}`);
                const maxEl = document.getElementById(`iu_prop_${prop.uiKey}_max_${this.featureId}`);
                const minRaw = minEl?.value?.trim() || '';
                const maxRaw = maxEl?.value?.trim() || '';

                if (minRaw === '' && maxRaw === '') return;

                if (minRaw !== '' && maxRaw !== '') {
                    const minVal = parseFloat(minRaw);
                    const maxVal = parseFloat(maxRaw);
                    if (Number.isFinite(minVal) && Number.isFinite(maxVal)) {
                        inputs[payloadKey] = minVal <= maxVal ? [minVal, maxVal] : [maxVal, minVal];
                    }
                    return;
                }

                const exactValRaw = minRaw || maxRaw;
                const exactVal = parseFloat(exactValRaw);
                if (Number.isFinite(exactVal)) {
                    inputs[payloadKey] = exactVal;
                }
            } else {
                const valEl = document.getElementById(`iu_prop_${prop.uiKey}_${this.featureId}`);
                const raw = valEl?.value?.trim() || '';
                if (raw !== '') {
                    inputs[payloadKey] = raw;
                }
            }
        });

        return inputs;
    }

    async callPythonBackend() {
        const inputs = this.collectInputData();
        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';

        this._abortController = new AbortController();
        this._cancelled = false;

        this.addLog('Sending IU request to EMOS backend...', 'info');

        try {
            const response = await fetch(
                `${backendUrl}/api/process/iu/${this.iuType}/${this.iuId}/stream`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(inputs),
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
                        const numStructs = Array.isArray(eventData.cif_strings) ? eventData.cif_strings.length : 0;
                        this.addLog(`Generation complete: ${numStructs} structure(s)`, 'success');
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

            return finalResult || { status: 'completed', cif_strings: [] };
        } catch (error) {
            if (error.name === 'AbortError') {
                this.addLog('Request cancelled by user', 'warning');
                return { status: 'cancelled', cif_strings: [] };
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
            queries: this.collectInputData(),
            cif_strings: [],
            status: 'local_fallback',
        };
    }

    updateOutputs(results = null) {
        const data = results || this.results || {};

        if (data.error) {
            const statusEl = document.getElementById(`iuDataGeneratedStatus_${this.featureId}`);
            const downloadEl = document.getElementById(`iuDataGeneratedDownload_${this.featureId}`);
            if (statusEl) statusEl.textContent = `Error: ${data.error}`;
            if (downloadEl) downloadEl.style.display = 'none';
            return;
        }

        const statusEl = document.getElementById(`iuDataGeneratedStatus_${this.featureId}`);
        const downloadEl = document.getElementById(`iuDataGeneratedDownload_${this.featureId}`);

        if (this._downloadUrl) {
            URL.revokeObjectURL(this._downloadUrl);
            this._downloadUrl = null;
        }

        if (downloadEl) {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            this._downloadUrl = URL.createObjectURL(blob);
            downloadEl.href = this._downloadUrl;
            downloadEl.download = `${this.iuId}_generated_dataset_${Date.now()}.json`;
            downloadEl.style.display = '';
        }

        if (statusEl) {
            statusEl.textContent = 'Ready';
        }

        const cifList = Array.isArray(data.cif_strings) ? data.cif_strings : [];
        const structRow = document.getElementById(`iuStructSelectorRow_${this.featureId}`);
        const structSelector = document.getElementById(`iuStructSelector_${this.featureId}`);
        const cifRow = document.getElementById(`iuCifViewerRow_${this.featureId}`);
        const viewerContainer = document.getElementById(`iuStructureViewer_${this.featureId}`);
        const cifViewer = document.getElementById(`iuCifViewer_${this.featureId}`);
        const toggleCifBtn = document.getElementById(`iuToggleCifBtn_${this.featureId}`);

        if (!structRow || !structSelector || !cifRow || !viewerContainer || !cifViewer) {
            return;
        }

        if (cifList.length === 0) {
            structRow.style.display = 'none';
            cifRow.style.display = 'none';
            return;
        }

        structSelector.innerHTML = cifList.map((_, i) => `<option value="${i}">Structure ${i + 1}</option>`).join('');

        structRow.style.display = '';
        cifRow.style.display = '';

        if (this._3dViewer) {
            viewerContainer.innerHTML = '';
            this._3dViewer = null;
        }

        const showStructure = (idx) => {
            const cifData = cifList[idx];
            cifViewer.textContent = cifData || '(no CIF data available)';

            if (!cifData || typeof $3Dmol === 'undefined') {
                viewerContainer.innerHTML = '<p style="color:#333;padding:20px;">3D viewer unavailable</p>';
                return;
            }

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

        const newSelector = structSelector.cloneNode(true);
        structSelector.parentNode.replaceChild(newSelector, structSelector);
        newSelector.addEventListener('change', () => showStructure(parseInt(newSelector.value, 10)));
    }

    destroy() {
        if (this._downloadUrl) {
            URL.revokeObjectURL(this._downloadUrl);
            this._downloadUrl = null;
        }
    }
}

window.MattergenBulkModulusIUFeature = MattergenBulkModulusIUFeature;
