// MOSFET evaluator Feature
class MosfetEvaluatorFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'MOSFET evaluator', 'Evaluate MOSFET performance from uploaded CIF files and simulation parameters');
    }

    createInputsHTML() {
        return `
            <p>Configure input parameters for MOSFET evaluator</p>
            <div class="input-controls">
                ${this.createFileInput(`cifFiles_${this.featureId}`, 'CIF Files', '.cif')}
                ${this.createSelectInput(`deviceType_${this.featureId}`, 'Device Type', [{value: 'nmos', text: 'NMOS'}, {value: 'pmos', text: 'PMOS'}])}
                ${this.createNumberInput(`channelLengthNm_${this.featureId}`, 'Channel Length (nm)', '1', '1000', '0.1')}
                ${this.createNumberInput(`channelWidthNm_${this.featureId}`, 'Channel Width (nm)', '1', '100000', '0.1')}
                ${this.createNumberInput(`oxideThicknessNm_${this.featureId}`, 'Oxide Thickness (nm)', '0.1', '100', '0.1')}
                ${this.createNumberInput(`supplyVoltageVdd_${this.featureId}`, 'Supply Voltage VDD (V)', '0.1', '5', '0.01')}
                ${this.createNumberInput(`gateWorkFunctionEv_${this.featureId}`, 'Gate Work Function (eV)', '3', '6', '0.01')}
                ${this.createNumberInput(`sourceDrainDopingCm3_${this.featureId}`, 'Source/Drain Doping (cm^-3)', '1000000000000000', '1e+22', '1000000000000000')}
                ${this.createNumberInput(`temperatureK_${this.featureId}`, 'Temperature (K)', '77', '1000', '1')}
                ${this.createNumberInput(`drainVoltageVd_${this.featureId}`, 'Drain Voltage VD (V)', '0', '5', '0.01')}
                ${this.createNumberInput(`gateVoltageSweepStartV_${this.featureId}`, 'Gate Sweep Start (V)', '-5', '5', '0.01')}
                ${this.createNumberInput(`gateVoltageSweepStopV_${this.featureId}`, 'Gate Sweep Stop (V)', '-5', '5', '0.01')}
                ${this.createNumberInput(`gateVoltageSweepStepV_${this.featureId}`, 'Gate Sweep Step (V)', '0.001', '1', '0.001')}
                ${this.createCheckboxInput(`validateBandGap_${this.featureId}`, 'Validate Band Gap from CIF', true)}
                ${this.createCheckboxInput(`validateElectronMobility_${this.featureId}`, 'Validate Electron Mobility from CIF', true)}
                ${this.createCheckboxInput(`validateHoleMobility_${this.featureId}`, 'Validate Hole Mobility from CIF', true)}
                ${this.createCheckboxInput(`validateDielectricConstant_${this.featureId}`, 'Validate Dielectric Constant from CIF', true)}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>MOSFET evaluator results and outputs</p>
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
        // Placeholder processing logic for MOSFET evaluator
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

window.MosfetEvaluatorFeature = MosfetEvaluatorFeature;
