// CIF similarity Feature
class CifSimilarityFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'CIF similarity', 'Compare uploaded crystal structures using AMD or PDD Earth Movers Distance');
    }

    createInputsHTML() {
        return `
            <p>Configure input parameters for CIF similarity</p>
            <div class="input-controls">
                <label>CIF Files:
                    <input type="file" id="cifFiles_${this.featureId}" accept=".cif" multiple required>
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
                    <pre id="distanceMatrix_${this.featureId}" style="max-height:300px; overflow:auto; white-space:pre-wrap;">Pending...</pre>
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
        // Placeholder processing logic for CIF similarity
        return {
            distanceMatrix: 'Distance Matrix - placeholder',
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        if (finalResults.error) {
            document.getElementById(`distanceMatrix_${this.featureId}`).textContent = `Error: ${finalResults.error}`;
            return;
        }
        
        if (finalResults.distanceMatrix) {
            document.getElementById(`distanceMatrix_${this.featureId}`).textContent = finalResults.distanceMatrix;
        }
    }
}

window.CifSimilarityFeature = CifSimilarityFeature;
