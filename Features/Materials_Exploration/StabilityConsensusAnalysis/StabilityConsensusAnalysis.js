// Stability Consensus Analysis Feature
class StabilityConsensusAnalysisFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Stability Consensus Analysis', 'Analyze and aggregate stability consensus from uploaded CIF structures');
    }

    createInputsHTML() {
        return `
            <p>Configure input parameters for Stability Consensus Analysis</p>
            <div class="input-controls">
                ${this.createFileInput(`cifFiles_${this.featureId}`, 'CIF Files', '.cif')}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>Stability Consensus Analysis results and outputs</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Download Results (JSON):</strong> <span id="downloadResultsJson_${this.featureId}">Pending...</span>
                </div>
            </div>
        `;
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

    async processFeature() {
        // Placeholder processing logic for Stability Consensus Analysis
        return {
            downloadResultsJson: 'Download Results (JSON) - placeholder',
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        if (finalResults.error) {
            document.getElementById(`downloadResultsJson_${this.featureId}`).textContent = `Error: ${finalResults.error}`;
            return;
        }
        
        if (finalResults.downloadResultsJson) {
            document.getElementById(`downloadResultsJson_${this.featureId}`).textContent = finalResults.downloadResultsJson;
        }
    }
}

window.StabilityConsensusAnalysisFeature = StabilityConsensusAnalysisFeature;
