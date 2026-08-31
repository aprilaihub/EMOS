// Stability Consensus Analysis Feature
class StabilityConsensusAnalysisFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Stability Consensus Analysis', 'Query materials databases and run predictors to evaluate multi-source stability');
        this.uploadedCifFiles = [];
        this.pendingFileReads = 0;
        this.selectedCifCount = 0;
        this._abortController = null;
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
                <div id="resultsTable_${this.featureId}" style="display:none;">
                    <h3>Stability Consensus Results</h3>
                    
                    <div class="consensus-summary" id="consensusSummary_${this.featureId}">
                        <!-- Summary will be populated here -->
                    </div>

                    <div id="stabilityPlot_${this.featureId}" style="margin: 14px 0 18px 0;">
                        <!-- Stacked stability bars will be populated here -->
                    </div>
                    
                    <table class="results-table">
                        <thead>
                            <tr>
                                <th>Stability</th>
                            </tr>
                        </thead>
                        <tbody id="resultsBody_${this.featureId}">
                            <!-- Results rows will be populated here -->
                        </tbody>
                    </table>
                    
                    <div class="output-controls" style="margin-top: 20px;">
                        <button class="download-btn" id="downloadJson_${this.featureId}">
                            📥 Download Results (JSON)
                        </button>
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
        
        // Download JSON handler
        const downloadBtn = document.getElementById(`downloadJson_${this.featureId}`);
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                const jsonData = this.results?.downloadResultsJson;
                if (jsonData) {
                    const blob = new Blob([jsonData], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'stability-consensus-results.json';
                    a.click();
                    URL.revokeObjectURL(url);
                    this.addLog('Results downloaded', 'success');
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
        const finalResults = results || this.results;
        
        const resultsTable = document.getElementById(`resultsTable_${this.featureId}`);
        const pendingMsg = document.getElementById(`pendingMessage_${this.featureId}`);
        const plotDiv = document.getElementById(`stabilityPlot_${this.featureId}`);

        const sourceDisplayNames = {
            mattersim: 'MatterSim',
            chgnet: 'CHGNet',
            materialsproject: 'Materials Project',
            alexandria: 'Alexandria'
        };

        const applyStabilityRowColor = (row, stability, status) => {
            const stabilityText = String(stability || '');
            const statusText = String(status || '').toLowerCase();

            if (stabilityText.includes('✅')) {
                row.style.backgroundColor = '#e8f5e9';
                return;
            }

            if (statusText === 'not_found' || stabilityText.includes('⚠️') || stabilityText.toLowerCase().includes('not found')) {
                row.style.backgroundColor = '#eceff1';
                row.style.color = '#455a64';
                return;
            }

            if (stabilityText.includes('❌')) {
                row.style.backgroundColor = '#ffebee';
            }
        };

        const renderStackedPlot = (plotData = {}) => {
            if (!plotDiv) return;
            const entries = Object.entries(plotData || {});
            if (entries.length === 0) {
                plotDiv.innerHTML = '';
                return;
            }

            const rows = entries.map(([source, stats]) => {
                const stableCount = Number(stats.stable_count || 0);
                const unstableCount = Number(stats.unstable_count || 0);
                const errorCount = Number(stats.error_count || 0);
                const stablePct = Number(stats.stable_pct || 0);
                const unstablePct = Number(stats.unstable_pct || 0);
                const errorPct = Number(stats.error_pct || 0);
                const sourceName = sourceDisplayNames[source] || source;
                const stableSegment = (stableCount > 0 && stablePct > 0)
                    ? `
                            <div style="width:${stablePct}%; background:#2e7d32; color:#fff; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:600; white-space:nowrap;">
                                ${stableCount} (${stablePct}%)
                            </div>
                        `
                    : '';
                const unstableSegment = (unstableCount > 0 && unstablePct > 0)
                    ? `
                            <div style="width:${unstablePct}%; background:#c62828; color:#fff; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:600; white-space:nowrap;">
                                ${unstableCount} (${unstablePct}%)
                            </div>
                        `
                    : '';
                const errorSegment = (errorCount > 0 && errorPct > 0)
                    ? `
                            <div style="width:${errorPct}%; background:#90a4ae; color:#fff; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:600; white-space:nowrap;">
                                ${errorCount} (${errorPct}%)
                            </div>
                        `
                    : '';

                return `
                    <div style="display:flex; align-items:center; gap:10px; margin:8px 0;">
                        <div style="min-width:160px; font-weight:600;">${sourceName}</div>
                        <div style="display:flex; width:100%; max-width:620px; height:28px; border-radius:6px; overflow:hidden; border:1px solid #c8ced8; background:#fff;">
                            ${stableSegment}
                            ${unstableSegment}
                            ${errorSegment}
                        </div>
                    </div>
                `;
            }).join('');

            plotDiv.innerHTML = `
                <div style="margin-bottom:6px; font-weight:700;">Stable vs Unstable by Source</div>
                <div style="font-size:12px; color:#5f6b7a; margin-bottom:8px;">Green = stable, Red = unstable, Grey = not found / error</div>
                ${rows}
            `;
        };
        
        if (finalResults.error) {
            this.addLog(`Error: ${finalResults.error}`, 'error');
            if (resultsTable) resultsTable.style.display = 'none';
            if (pendingMsg) pendingMsg.textContent = `Error: ${finalResults.error}`;
            if (plotDiv) plotDiv.innerHTML = '';
            return;
        }

        if (finalResults.status === 'cancelled') {
            if (resultsTable) resultsTable.style.display = 'none';
            if (pendingMsg) {
                pendingMsg.style.display = 'block';
                pendingMsg.textContent = 'Analysis cancelled.';
            }
            if (plotDiv) plotDiv.innerHTML = '';
            return;
        }

        // Batch mode: render each CIF result as its own grouped section.
        if (Array.isArray(finalResults.results_per_cif) && finalResults.results_per_cif.length > 0) {
            if (resultsTable) resultsTable.style.display = 'block';
            if (pendingMsg) pendingMsg.style.display = 'none';

            const batchSummary = finalResults.batch_summary || {};
            const summaryDiv = document.getElementById(`consensusSummary_${this.featureId}`);
            if (summaryDiv) {
                summaryDiv.innerHTML = `
                    <div class="summary-box">
                        <p><strong>Batch Summary:</strong> ${batchSummary.processed_files || 0}/${batchSummary.total_files || 0} processed, ${batchSummary.failed_files || 0} failed</p>
                        <p><strong>Votes:</strong> ${batchSummary.stable_votes || 0} stable, ${batchSummary.unstable_votes || 0} unstable</p>
                    </div>
                `;
            }

            renderStackedPlot(finalResults.plot_data || {});

            const resultsBody = document.getElementById(`resultsBody_${this.featureId}`);
            if (resultsBody) {
                resultsBody.innerHTML = '';

                finalResults.results_per_cif.forEach((entry) => {
                    const headerRow = document.createElement('tr');
                    const headerText = entry.error
                        ? `${entry.cif_name}: Error (${entry.error})`
                        : `${entry.cif_name} (${entry.composition || 'Unknown composition'})`;
                    headerRow.innerHTML = `<td style="font-weight:700; background:#f2f4f8;">${headerText}</td>`;
                    resultsBody.appendChild(headerRow);

                    if (!entry.error) {
                        Object.entries(entry.sources || {}).forEach(([source, data]) => {
                            const row = document.createElement('tr');
                            const stability = data.stability || 'N/A';
                            const displayName = sourceDisplayNames[source] || source;
                            const sourceLabel = data.num_matches !== undefined
                                ? `${displayName} (${data.num_matches} matches)`
                                : displayName;
                            row.innerHTML = `<td style="font-weight:bold; font-size:1.05em;">${sourceLabel}: ${stability}</td>`;

                            applyStabilityRowColor(row, stability, data.status);
                            resultsBody.appendChild(row);
                        });
                    }
                });
            }

            this.addLog('Batch results displayed', 'success');
            return;
        }
        
        if (!finalResults.sources) {
            if (pendingMsg) pendingMsg.textContent = 'No results available';
            return;
        }
        
        // Display results table
        if (resultsTable) resultsTable.style.display = 'block';
        if (pendingMsg) pendingMsg.style.display = 'none';
        
        // Populate consensus summary
        const summary = finalResults.summary || {};
        const summaryDiv = document.getElementById(`consensusSummary_${this.featureId}`);
        if (summaryDiv) {
            summaryDiv.innerHTML = `
                <div class="summary-box">
                    <p><strong>Overall Consensus:</strong> ${summary.consensus || 'N/A'}</p>
                    <p><strong>Sources:</strong> ${summary.stable_count || 0} stable, ${summary.unstable_count || 0} unstable out of ${summary.total_sources || 0}</p>
                </div>
            `;
        }

        renderStackedPlot(finalResults.plot_data || {});
        
        // Populate results table
        const resultsBody = document.getElementById(`resultsBody_${this.featureId}`);
        if (resultsBody) {
            resultsBody.innerHTML = '';
            
            Object.entries(finalResults.sources).forEach(([source, data]) => {
                const row = document.createElement('tr');
                
                const stability = data.stability || 'N/A';
                const displayName = sourceDisplayNames[source] || source;
                const sourceLabel = data.num_matches !== undefined
                    ? `${displayName} (${data.num_matches} matches)`
                    : displayName;
                
                row.innerHTML = `
                    <td style="font-weight:bold; font-size:1.1em;">${sourceLabel}: ${stability}</td>
                `;

                applyStabilityRowColor(row, stability, data.status);
                
                resultsBody.appendChild(row);
            });
        }
        
        this.addLog('Results displayed', 'success');
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
