// CIF similarity Feature
class CifSimilarityFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'CIF similarity', 'Compare uploaded crystal structures using AMD or PDD Earth Mover's Distance');
    }

    createInputsHTML() {
        return `
            <p>Configure input parameters for CIF similarity</p>
            <div class="input-controls">
                ${this.createFileInput(`cifFiles_${this.featureId}`, 'CIF Files', '.cif')}
                ${this.createSelectInput(`distanceMetric_${this.featureId}`, 'Distance Metric', [{value: 'amd', text: 'Average Minimum Distance (AMD)'}, {value: 'pdd_emd', text: 'PDD Earth Mover's Distance'}])}
                ${this.createNumberInput(`k_${this.featureId}`, 'Neighbourhood size k', '1', '500', '1')}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>CIF similarity results and outputs</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Distance Matrix:</strong> <span id="distanceMatrix_${this.featureId}">Pending...</span>
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
