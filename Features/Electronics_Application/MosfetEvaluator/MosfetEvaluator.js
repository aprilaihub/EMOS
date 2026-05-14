// MOSFET evaluator Feature
class MosfetEvaluatorFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'MOSFET evaluator', 'Evaluate MOSFET performance from uploaded CIF files and simulation parameters');
    }

    createInputsHTML() {
        return `
            <p>Configure all non-runtime solver inputs for MOSFET evaluator.</p>
            <div class="input-controls" style="max-height: 560px; overflow: auto; padding-right: 6px;">
                <p><strong>Geometry Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`channelLengthNm_${this.featureId}`, 'Channel Length (nm, default 14)', '1', '1000', '0.1', '14')}
                ${this.createNumberInput(`sourceDrainLengthNm_${this.featureId}`, 'Source/Drain Length (nm, default 4)', '0.1', '1000', '0.1', '4')}
                ${this.createNumberInput(`oxideThicknessNm_${this.featureId}`, 'Oxide Thickness (nm, default 1)', '0.1', '100', '0.1', '1')}
                ${this.createNumberInput(`channelThicknessNm_${this.featureId}`, 'Channel Thickness (nm, default 4)', '0.1', '1000', '0.1', '4')}

                <p><strong>Mesh Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`dxM_${this.featureId}`, 'Mesh dx (m, default 5e-10)', '1e-12', '1e-6', '1e-12', '5e-10')}
                ${this.createNumberInput(`dyM_${this.featureId}`, 'Mesh dy (m, default 5e-10)', '1e-12', '1e-6', '1e-12', '5e-10')}

                <p><strong>Thermal and Contact Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`temperatureK_${this.featureId}`, 'Temperature (K, default 300)', '77', '1000', '1', '300')}
                ${this.createNumberInput(`gateWorkFunctionEv_${this.featureId}`, 'Gate Work Function (eV, default 3.65)', '2', '8', '0.01', '3.65')}
                ${this.createNumberInput(`sdWorkFunctionEv_${this.featureId}`, 'Source/Drain Work Function (eV, default 0.0)', '-10', '10', '0.01', '0.0')}

                <p><strong>Doping Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`channelDopingCm3_${this.featureId}`, 'Channel Doping (cm^-3, default -1e15)', '-1e22', '1e22', '1e14', '-1e15')}
                ${this.createNumberInput(`sourceDrainDopingCm3_${this.featureId}`, 'Source/Drain Doping (cm^-3, default 1e20)', '1e15', '1e22', '1e14', '1e20')}

                <p><strong>Bias Sweep Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`gateVoltageSweepStartV_${this.featureId}`, 'Gate Sweep Start (V, default 0.0)', '-10', '10', '0.01', '0.0')}
                ${this.createNumberInput(`gateVoltageSweepStopV_${this.featureId}`, 'Gate Sweep Stop (V, default 0.7)', '-10', '10', '0.01', '0.7')}
                ${this.createNumberInput(`numberOfGatePoints_${this.featureId}`, 'Gate Sweep Points Nvg (default 14)', '2', '500', '1', '14')}
                ${this.createNumberInput(`drainVoltageSweepStartV_${this.featureId}`, 'Drain Sweep Start (V, default 0.0)', '-10', '10', '0.01', '0.0')}
                ${this.createNumberInput(`drainVoltageSweepStopV_${this.featureId}`, 'Drain Sweep Stop (V, default 0.7)', '-10', '10', '0.01', '0.7')}
                ${this.createNumberInput(`numberOfDrainPoints_${this.featureId}`, 'Drain Sweep Points Nvd (default 13)', '2', '500', '1', '13')}
                ${this.createNumberInput(`drainVoltageVd_${this.featureId}`, 'Drain Voltage VD (legacy alias)', '0', '5', '0.01', '0.7')}

                <p><strong>Channel Material Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`channelNc_${this.featureId}`, 'channel Nc (default 2.8e25)', '0', '1e30', '1e20', '2.8e25')}
                ${this.createNumberInput(`channelNv_${this.featureId}`, 'channel Nv (default 1.04e25)', '0', '1e30', '1e20', '1.04e25')}
                ${this.createNumberInput(`channelEpsRel_${this.featureId}`, 'channel relative permittivity ep (default 11.9)', '0.1', '1000', '0.1', '11.9')}
                ${this.createNumberInput(`channelUn_${this.featureId}`, 'channel electron mobility un (default 0.1500)', '0', '10', '0.0001', '0.1500')}
                ${this.createNumberInput(`channelUp_${this.featureId}`, 'channel hole mobility up (default 0.0475)', '0', '10', '0.0001', '0.0475')}
                ${this.createNumberInput(`channelXiEv_${this.featureId}`, 'channel electron affinity xi (eV, default 4.05)', '0', '10', '0.01', '4.05')}
                ${this.createNumberInput(`channelEgEv_${this.featureId}`, 'channel band gap Eg (eV, default 1.12)', '0', '20', '0.01', '1.12')}
                ${this.createNumberInput(`channelVsatN_${this.featureId}`, 'channel electron saturation velocity vsat_n (default 2e5)', '1e3', '1e8', '1e3', '2e5')}
                ${this.createNumberInput(`channelVsatP_${this.featureId}`, 'channel hole saturation velocity vsat_p (default 2e5)', '1e3', '1e8', '1e3', '2e5')}
                ${this.createNumberInput(`channelPowN_${this.featureId}`, 'channel pow_n (default 2.0)', '0.1', '10', '0.1', '2.0')}
                ${this.createNumberInput(`channelPowP_${this.featureId}`, 'channel pow_p (default 1.0)', '0.1', '10', '0.1', '1.0')}

                <p><strong>Insulator Material Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`insulatorNc_${this.featureId}`, 'insulator Nc (default 1.0)', '0', '1e30', '1', '1.0')}
                ${this.createNumberInput(`insulatorNv_${this.featureId}`, 'insulator Nv (default 1.0)', '0', '1e30', '1', '1.0')}
                ${this.createNumberInput(`insulatorEpsRel_${this.featureId}`, 'insulator relative permittivity ep (default 3.9)', '0.1', '1000', '0.1', '3.9')}
                ${this.createNumberInput(`insulatorUn_${this.featureId}`, 'insulator electron mobility un (default 1e-3)', '0', '10', '0.0001', '1e-3')}
                ${this.createNumberInput(`insulatorUp_${this.featureId}`, 'insulator hole mobility up (default 1e-3)', '0', '10', '0.0001', '1e-3')}
                ${this.createNumberInput(`insulatorXiEv_${this.featureId}`, 'insulator electron affinity xi (eV, default 0.9)', '0', '20', '0.01', '0.9')}
                ${this.createNumberInput(`insulatorEgEv_${this.featureId}`, 'insulator band gap Eg (eV, default 9.0)', '0', '30', '0.01', '9.0')}
                ${this.createNumberInput(`insulatorVsatN_${this.featureId}`, 'insulator electron saturation velocity vsat_n (default 2e5)', '1e3', '1e8', '1e3', '2e5')}
                ${this.createNumberInput(`insulatorVsatP_${this.featureId}`, 'insulator hole saturation velocity vsat_p (default 2e5)', '1e3', '1e8', '1e3', '2e5')}
                ${this.createNumberInput(`insulatorPowN_${this.featureId}`, 'insulator pow_n (default 2.0)', '0.1', '10', '0.1', '2.0')}
                ${this.createNumberInput(`insulatorPowP_${this.featureId}`, 'insulator pow_p (default 1.0)', '0.1', '10', '0.1', '1.0')}

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
