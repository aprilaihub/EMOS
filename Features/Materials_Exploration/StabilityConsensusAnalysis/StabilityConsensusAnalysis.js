// Stability Consensus Analysis Feature
class StabilityConsensusAnalysisFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Stability Consensus Analysis', 'Query materials databases and run predictors to evaluate multi-source stability');
        this.uploadedCifFile = null;
    }

    createInputsHTML() {
        return `
            <div class="input-controls">
                <div class="form-group">
                    <label for="cifFile_${this.featureId}">Upload CIF File:</label>
                    <input type="file" id="cifFile_${this.featureId}" accept=".cif" class="file-input">
                    <small>Single crystal structure file (CIF format)</small>
                </div>
                
                <div class="form-group">
                    <label>Select Databases:</label>
                    <div id="dbCheckboxes_${this.featureId}" class="checkbox-group">
                        <label><input type="checkbox" name="database" value="materialsproject"> Materials Project</label>
                        <label><input type="checkbox" name="database" value="alexandria"> Alexandria</label>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Select Predictors:</label>
                    <div id="predCheckboxes_${this.featureId}" class="checkbox-group">
                        <label><input type="checkbox" name="predictor" value="mattersim"> MatterSim</label>
                        <label><input type="checkbox" name="predictor" value="chgnet"> CHGNet</label>
                    </div>
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
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        this.uploadedCifFile = event.target.result;
                        this.addLog(`CIF file loaded: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`, 'success');
                    };
                    reader.readAsText(file);
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

    collectInputData() {
        const inputs = super.collectInputData();

        // Inject actual CIF content read from file (not browser file path string).
        inputs.cif_file = this.uploadedCifFile || '';

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
        
        if (finalResults.error) {
            this.addLog(`Error: ${finalResults.error}`, 'error');
            if (resultsTable) resultsTable.style.display = 'none';
            if (pendingMsg) pendingMsg.textContent = `Error: ${finalResults.error}`;
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
        
        // Populate results table
        const resultsBody = document.getElementById(`resultsBody_${this.featureId}`);
        if (resultsBody) {
            resultsBody.innerHTML = '';
            const sourceDisplayNames = {
                mattersim: 'MatterSim',
                chgnet: 'CHGNet',
                materialsproject: 'Materials Project',
                alexandria: 'Alexandria'
            };
            
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
                
                // Color code by stability
                if (stability.includes('✅')) {
                    row.style.backgroundColor = '#e8f5e9';
                } else if (stability.includes('❌')) {
                    row.style.backgroundColor = '#ffebee';
                }
                
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
}

window.StabilityConsensusAnalysisFeature = StabilityConsensusAnalysisFeature;
