// Stability Consensus Analysis Feature
class StabilityConsensusAnalysisFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Stability Consensus Analysis', 'Query materials databases and run predictors to evaluate multi-source stability');
        this.uploadedCifFiles = [];
        this.pendingFileReads = 0;
        this.selectedCifCount = 0;
        this._abortController = null;
        this._downloadJsonUrl = null;
    }

    createInputsHTML() {
        return `
            <div class="input-controls" style="align-items:center; gap:24px;">
                <div style="width:min(100%, 640px); text-align:center;">
                    <label for="cifFile_${this.featureId}" style="align-items:stretch; gap:8px;">
                        <span>CIF Files</span>
                        <input type="file" id="cifFile_${this.featureId}" accept=".cif" multiple style="box-sizing:border-box; flex:none; width:100%; text-align:left;">
                    </label>
                    <small style="display:block; margin-top:7px; color:#6c757d;">Upload one or more crystal structure CIF files</small>
                </div>

                <div style="display:grid; grid-template-columns:1fr; gap:16px; width:min(100%, 520px);">
                    <fieldset style="box-sizing:border-box; margin:0; padding:14px 16px 16px; border:1px solid #d9dee7; border-radius:8px; background:#fff;">
                        <legend style="padding:0 7px; color:#495057; font-weight:600;">Databases</legend>
                        <div id="dbCheckboxes_${this.featureId}" style="display:flex; flex-direction:column; gap:8px;">
                            <label style="display:grid; grid-template-columns:20px minmax(0, 1fr); align-items:center; gap:10px; width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #e3e7ee; border-radius:6px; background:#f8f9fa; cursor:pointer;">
                                <input type="checkbox" name="database" value="materialsproject" style="width:18px; height:18px; margin:0; padding:0;">
                                <span style="text-align:left;">Materials Project</span>
                            </label>
                            <label style="display:grid; grid-template-columns:20px minmax(0, 1fr); align-items:center; gap:10px; width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #e3e7ee; border-radius:6px; background:#f8f9fa; cursor:pointer;">
                                <input type="checkbox" name="database" value="alexandria" style="width:18px; height:18px; margin:0; padding:0;">
                                <span style="text-align:left;">Alexandria</span>
                            </label>
                        </div>
                    </fieldset>

                    <fieldset style="box-sizing:border-box; margin:0; padding:14px 16px 16px; border:1px solid #d9dee7; border-radius:8px; background:#fff;">
                        <legend style="padding:0 7px; color:#495057; font-weight:600;">Predictors</legend>
                        <div id="predCheckboxes_${this.featureId}" style="display:flex; flex-direction:column; gap:8px;">
                            <label style="display:grid; grid-template-columns:20px minmax(0, 1fr); align-items:center; gap:10px; width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #e3e7ee; border-radius:6px; background:#f8f9fa; cursor:pointer;">
                                <input type="checkbox" name="predictor" value="mattersim" style="width:18px; height:18px; margin:0; padding:0;">
                                <span style="text-align:left;">MatterSim</span>
                            </label>
                            <label style="display:grid; grid-template-columns:20px minmax(0, 1fr); align-items:center; gap:10px; width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #e3e7ee; border-radius:6px; background:#f8f9fa; cursor:pointer;">
                                <input type="checkbox" name="predictor" value="chgnet" style="width:18px; height:18px; margin:0; padding:0;">
                                <span style="text-align:left;">CHGNet</span>
                            </label>
                        </div>
                    </fieldset>
                </div>
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div id="resultsContainer_${this.featureId}" style="display:none;">
                    <div class="output-item">
                        <strong>Batch Summary:</strong>
                        <span id="batchSummary_${this.featureId}">Pending...</span>
                    </div>

                    <div class="output-item">
                        <strong>Stability Heatmap:</strong>
                        <div id="stabilityHeatmap_${this.featureId}" style="margin-top:0.75rem; overflow-x:auto;"></div>
                    </div>

                    <div class="output-item">
                        <strong>Download Results (JSON):</strong>
                        <span id="downloadResultsJson_${this.featureId}">Pending...</span>
                    </div>
                </div>
                
                <div id="pendingMessage_${this.featureId}" style="text-align:center; color:#666;">
                    <p>Awaiting analysis...</p>
                </div>
            </div>
        `;
    }

    attachEventListeners() {
        // CIF file upload handler
        const cifInput = document.getElementById(`cifFile_${this.featureId}`);
        if (cifInput) {
            cifInput.addEventListener('change', (e) => {
                const files = Array.from(e.target.files || []);
                if (files.length > 0) {
                    this.uploadedCifFiles = [];
                    this.selectedCifCount = files.length;
                    this.pendingFileReads = files.length;
                    const processBtn = document.getElementById(`processBtn_${this.featureId}`);
                    if (processBtn) processBtn.disabled = true;
                    this.addLog(`Loading ${files.length} CIF file(s)...`, 'info');
                    files.forEach((file) => {
                        const reader = new FileReader();
                        reader.onload = (event) => {
                            this.uploadedCifFiles.push({
                                name: file.name,
                                content: event.target.result,
                            });
                            this.pendingFileReads -= 1;
                            this.addLog(`CIF file loaded: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`, 'success');
                            if (this.pendingFileReads === 0) {
                                this.addLog(`All ${this.selectedCifCount} CIF file(s) loaded. Ready to process.`, 'success');
                                if (processBtn) processBtn.disabled = false;
                            }
                        };
                        reader.readAsText(file);
                    });
                }
            });
        }
        
    }

    async processFeature() {
        throw new Error('Local fallback is not supported for this feature. Please start the Python backend.');
    }

    async callPythonBackend() {
        const inputs = this.collectInputData();
        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';
        const controller = new AbortController();
        this._abortController = controller;

        try {
            const response = await fetch(`${backendUrl}/api/process/${this.featureId}/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(inputs),
                signal: controller.signal,
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            if (!response.body) {
                throw new Error('The backend did not provide a response stream.');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalResult = null;
            let backendError = null;

            const handleBlock = (block) => {
                const lines = block.split('\n');
                let eventType = 'message';
                const dataLines = [];

                for (const line of lines) {
                    if (line.startsWith('event:')) {
                        eventType = line.slice(6).trim();
                    } else if (line.startsWith('data:')) {
                        dataLines.push(line.slice(5).trimStart());
                    }
                }

                if (dataLines.length === 0) return;

                const rawData = dataLines.join('\n');
                let eventData;
                try {
                    eventData = JSON.parse(rawData);
                } catch (_) {
                    eventData = { message: rawData };
                }

                if (eventType === 'result') {
                    finalResult = eventData;
                } else if (eventType === 'log') {
                    this.addLog(eventData.message || '', eventData.level || 'info');
                } else if (eventType === 'logs' && Array.isArray(eventData)) {
                    eventData.forEach((entry) => {
                        this.addLog(entry.message || '', entry.level || 'info');
                    });
                } else if (eventType === 'progress') {
                    const progress = Math.max(0, Math.min(1, Number(eventData.progress) || 0));
                    const progressFill = document.getElementById(`progressFill_${this.featureId}`);
                    if (progressFill) progressFill.style.width = `${Math.round(progress * 100)}%`;
                } else if (eventType === 'error') {
                    backendError = eventData.message || 'Unknown backend error';
                }
            };

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
                const blocks = buffer.split('\n\n');
                buffer = blocks.pop() || '';
                blocks.filter(block => block.trim()).forEach(handleBlock);
            }

            buffer += decoder.decode().replace(/\r\n/g, '\n');
            if (buffer.trim()) handleBlock(buffer);

            if (finalResult) return finalResult;
            if (this._cancelled) return { status: 'cancelled' };
            throw new Error(backendError || 'The backend stream ended without a result.');
        } catch (error) {
            if (error.name === 'AbortError' && this._cancelled) {
                return { status: 'cancelled' };
            }
            throw error;
        } finally {
            if (this._abortController === controller) {
                this._abortController = null;
            }
        }
    }

    collectInputData() {
        const inputs = super.collectInputData();

        if (this.pendingFileReads > 0) {
            throw new Error(`Please wait for all CIF files to finish loading (${this.pendingFileReads} remaining)`);
        }

        // Inject uploaded CIF file payloads.
        inputs.cif_files = this.uploadedCifFiles;
        // Keep backward compatibility for backend paths expecting a single CIF.
        inputs.cif_file = this.uploadedCifFiles[0]?.content || '';

        const selectedDbs = Array.from(
            document.querySelectorAll(`#dbCheckboxes_${this.featureId} input[type="checkbox"]:checked`)
        ).map(cb => ({ value: cb.value, name: cb.parentElement.textContent.trim() }));

        const selectedPreds = Array.from(
            document.querySelectorAll(`#predCheckboxes_${this.featureId} input[type="checkbox"]:checked`)
        ).map(cb => ({ value: cb.value, name: cb.parentElement.textContent.trim() }));

        if (selectedDbs.length > 0 || selectedPreds.length > 0) {
            inputs.active_databases = selectedDbs;
            inputs.active_predictors = selectedPreds;
        }

        return inputs;
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results || {};
        const resultsContainer = document.getElementById(`resultsContainer_${this.featureId}`);
        const pendingMsg = document.getElementById(`pendingMessage_${this.featureId}`);
        const batchSummaryEl = document.getElementById(`batchSummary_${this.featureId}`);
        const heatmapEl = document.getElementById(`stabilityHeatmap_${this.featureId}`);
        const downloadEl = document.getElementById(`downloadResultsJson_${this.featureId}`);

        const sourceDisplayNames = {
            materialsproject: 'Materials Project',
            alexandria: 'Alexandria',
            mattersim: 'MatterSim',
            chgnet: 'CHGNet'
        };

        const revokeDownloadUrl = () => {
            if (this._downloadJsonUrl) {
                URL.revokeObjectURL(this._downloadJsonUrl);
                this._downloadJsonUrl = null;
            }
        };

        const renderDownloadLink = (jsonData) => {
            if (!downloadEl) return;
            revokeDownloadUrl();
            downloadEl.innerHTML = '';

            if (!jsonData) {
                downloadEl.textContent = 'Unavailable';
                return;
            }

            const blob = new Blob([jsonData], { type: 'application/json' });
            this._downloadJsonUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = this._downloadJsonUrl;
            link.download = 'stability-consensus-results.json';
            link.textContent = 'Download JSON';
            link.addEventListener('click', () => this.addLog('Results downloaded', 'success'));
            downloadEl.appendChild(link);
        };

        const classifyResult = (sourceData) => {
            const stability = String(sourceData?.stability || '');
            if (stability.includes('✅')) {
                return { label: 'Stable', color: '#cfe8d3', symbol: '✓', textColor: '#256235' };
            }
            if (stability.includes('❌')) {
                return { label: 'Unstable', color: '#f2cccc', symbol: '×', textColor: '#8a2d2d' };
            }
            return { label: 'Not found / error', color: '#e1e5e8', symbol: '—', textColor: '#52616b' };
        };

        const renderHeatmap = (cifResults) => {
            if (!heatmapEl) return;
            heatmapEl.innerHTML = '';

            const sourceKeys = [];
            document.querySelectorAll(
                `#dbCheckboxes_${this.featureId} input[type="checkbox"]:checked, `
                + `#predCheckboxes_${this.featureId} input[type="checkbox"]:checked`
            ).forEach((input) => {
                if (!sourceKeys.includes(input.value)) sourceKeys.push(input.value);
            });
            cifResults.forEach((entry) => {
                Object.keys(entry.sources || {}).forEach((source) => {
                    if (!sourceKeys.includes(source)) sourceKeys.push(source);
                });
            });

            const preferredOrder = ['materialsproject', 'alexandria', 'mattersim', 'chgnet'];
            sourceKeys.sort((a, b) => {
                const aIndex = preferredOrder.includes(a) ? preferredOrder.indexOf(a) : preferredOrder.length;
                const bIndex = preferredOrder.includes(b) ? preferredOrder.indexOf(b) : preferredOrder.length;
                return aIndex - bIndex;
            });

            if (sourceKeys.length === 0) {
                heatmapEl.textContent = 'No source results available.';
                return;
            }

            const table = document.createElement('table');
            Object.assign(table.style, {
                borderCollapse: 'separate',
                borderSpacing: '4px',
                minWidth: '100%',
                width: 'max-content'
            });

            const headerRow = document.createElement('tr');
            const sourceHeader = document.createElement('th');
            sourceHeader.textContent = 'Source';
            Object.assign(sourceHeader.style, {
                minWidth: '150px',
                paddingRight: '12px',
                textAlign: 'left'
            });
            headerRow.appendChild(sourceHeader);

            cifResults.forEach((_, index) => {
                const indexHeader = document.createElement('th');
                indexHeader.textContent = String(index);
                Object.assign(indexHeader.style, {
                    minWidth: '44px',
                    textAlign: 'center'
                });
                headerRow.appendChild(indexHeader);
            });
            table.appendChild(headerRow);

            sourceKeys.forEach((source) => {
                const row = document.createElement('tr');
                const sourceCell = document.createElement('th');
                sourceCell.textContent = sourceDisplayNames[source] || source;
                Object.assign(sourceCell.style, {
                    minWidth: '150px',
                    paddingRight: '12px',
                    textAlign: 'left',
                    whiteSpace: 'nowrap'
                });
                row.appendChild(sourceCell);

                cifResults.forEach((entry, index) => {
                    const classification = classifyResult((entry.sources || {})[source]);
                    const cell = document.createElement('td');
                    cell.textContent = classification.symbol;
                    cell.title = `${index}: ${entry.cif_name || 'Unknown CIF'} — ${classification.label}`;
                    cell.setAttribute('aria-label', cell.title);
                    Object.assign(cell.style, {
                        minWidth: '44px',
                        height: '34px',
                        padding: '0',
                        borderRadius: '4px',
                        backgroundColor: classification.color,
                        color: classification.textColor,
                        fontWeight: '700',
                        textAlign: 'center'
                    });
                    row.appendChild(cell);
                });
                table.appendChild(row);
            });

            heatmapEl.appendChild(table);

            const legend = document.createElement('div');
            legend.innerHTML = `
                <span style="display:inline-flex; align-items:center; gap:5px;"><span style="width:14px; height:14px; border-radius:3px; background:#cfe8d3;"></span>Stable</span>
                <span style="display:inline-flex; align-items:center; gap:5px;"><span style="width:14px; height:14px; border-radius:3px; background:#f2cccc;"></span>Unstable</span>
                <span style="display:inline-flex; align-items:center; gap:5px;"><span style="width:14px; height:14px; border-radius:3px; background:#e1e5e8;"></span>Not found / error</span>
            `;
            Object.assign(legend.style, {
                display: 'flex',
                flexWrap: 'wrap',
                gap: '14px',
                marginTop: '10px',
                fontSize: '12px',
                color: '#5f6b7a'
            });
            heatmapEl.appendChild(legend);

            const note = document.createElement('div');
            note.textContent = 'Heatmap columns use zero-based CIF indices. Their corresponding filenames are provided in the downloadable JSON under results_per_cif.';
            Object.assign(note.style, {
                marginTop: '8px',
                fontSize: '12px',
                color: '#5f6b7a'
            });
            heatmapEl.appendChild(note);
        };

        if (finalResults.error) {
            revokeDownloadUrl();
            this.addLog(`Error: ${finalResults.error}`, 'error');
            if (resultsContainer) resultsContainer.style.display = 'none';
            if (pendingMsg) {
                pendingMsg.style.display = 'block';
                pendingMsg.textContent = `Error: ${finalResults.error}`;
            }
            return;
        }

        if (finalResults.status === 'cancelled') {
            revokeDownloadUrl();
            if (resultsContainer) resultsContainer.style.display = 'none';
            if (pendingMsg) {
                pendingMsg.style.display = 'block';
                pendingMsg.textContent = 'Analysis cancelled.';
            }
            return;
        }

        const cifResults = Array.isArray(finalResults.results_per_cif) && finalResults.results_per_cif.length > 0
            ? finalResults.results_per_cif
            : (finalResults.sources ? [finalResults] : []);

        if (cifResults.length === 0) {
            revokeDownloadUrl();
            if (resultsContainer) resultsContainer.style.display = 'none';
            if (pendingMsg) {
                pendingMsg.style.display = 'block';
                pendingMsg.textContent = 'No results available';
            }
            return;
        }

        if (resultsContainer) resultsContainer.style.display = 'block';
        if (pendingMsg) pendingMsg.style.display = 'none';

        const batchSummary = finalResults.batch_summary || {};
        const totalFiles = batchSummary.total_files ?? cifResults.length;
        const processedFiles = batchSummary.processed_files
            ?? cifResults.filter(entry => !entry.error).length;
        const failedFiles = batchSummary.failed_files
            ?? cifResults.filter(entry => entry.error).length;
        if (batchSummaryEl) {
            batchSummaryEl.textContent = `${processedFiles}/${totalFiles} processed, ${failedFiles} failed`;
        }

        renderHeatmap(cifResults);
        renderDownloadLink(finalResults.downloadResultsJson);
        this.addLog('Batch results displayed', 'success');
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

        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';
        try {
            let response = null;

            // The stream registers the feature before it starts processing. A
            // very fast click can race that registration, so retry 404s briefly.
            for (let attempt = 0; attempt < 5; attempt += 1) {
                response = await fetch(`${backendUrl}/api/process/${this.featureId}/cancel`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });
                if (response.ok || response.status !== 404) break;
                await new Promise(resolve => setTimeout(resolve, 100));
            }

            if (response?.ok) {
                const data = await response.json();
                this.addLog(`Backend: ${data.message || 'cancel acknowledged'}`, 'info');
            } else {
                this.addLog(`Backend cancel returned HTTP ${response?.status || 'unknown'}`, 'warning');
            }
        } catch (err) {
            this.addLog(`Cancel request failed: ${err.message}`, 'error');
        } finally {
            // Stop waiting for the SSE response after the backend has received
            // the cancellation signal. Backend work stops cooperatively.
            if (this._abortController) {
                this._abortController.abort();
                this._abortController = null;
            }
        }
    }
}

window.StabilityConsensusAnalysisFeature = StabilityConsensusAnalysisFeature;
