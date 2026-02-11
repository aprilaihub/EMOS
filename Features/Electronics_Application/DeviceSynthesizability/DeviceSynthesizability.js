// Device Synthesizability Feature
class DeviceSynthesizabilityFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Device Synthesizability', 'Evaluate the feasibility and methods for synthesizing electronic devices from selected materials');
    }

    createInputsHTML() {
        return `
            <p>Configure device synthesis evaluation parameters</p>
            <div class="input-controls">
                ${this.createSelectInput(`deviceType_${this.featureId}`, 'Device Type', [
                    { value: 'transistor', text: 'Transistor' },
                    { value: 'diode', text: 'Diode' },
                    { value: 'solar_cell', text: 'Solar Cell' },
                    { value: 'led', text: 'LED' },
                    { value: 'sensor', text: 'Sensor' }
                ])}
                ${this.createTextInput(`materialComposition_${this.featureId}`, 'Material Composition', 'e.g., GaAs, SiC, InGaN')}
                ${this.createSelectInput(`substrateType_${this.featureId}`, 'Substrate Type', [
                    { value: 'silicon', text: 'Silicon' },
                    { value: 'sapphire', text: 'Sapphire' },
                    { value: 'sic', text: 'Silicon Carbide' },
                    { value: 'gan', text: 'Gallium Nitride' }
                ])}
                ${this.createNumberInput(`operatingTemp_${this.featureId}`, 'Operating Temperature (°C)', '-50', '500', '1')}
                ${this.createSelectInput(`fabricationMethod_${this.featureId}`, 'Preferred Fabrication Method', [
                    { value: 'mocvd', text: 'MOCVD' },
                    { value: 'mbe', text: 'MBE' },
                    { value: 'sputtering', text: 'Sputtering' },
                    { value: 'cvd', text: 'CVD' }
                ])}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>Device synthesis feasibility analysis</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Synthesis Feasibility:</strong> <span id="feasibility_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Recommended Process:</strong> <span id="recommendedProcess_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Estimated Cost:</strong> <span id="estimatedCost_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Processing Temperature:</strong> <span id="processTemp_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Yield Prediction:</strong> <span id="yieldPrediction_${this.featureId}">Pending...</span>
                </div>
            </div>
        `;
    }

    async processFeature() {
        // Simple fixed results for device synthesizability
        return {
            feasibility: '78% (High)',
            recommendedProcess: 'MOCVD with 3-step annealing',
            estimatedCost: '$245/wafer',
            processTemp: '650°C',
            yieldPrediction: '85%'
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        document.getElementById(`feasibility_${this.featureId}`).textContent = finalResults.feasibility;
        document.getElementById(`recommendedProcess_${this.featureId}`).textContent = finalResults.recommendedProcess;
        document.getElementById(`estimatedCost_${this.featureId}`).textContent = finalResults.estimatedCost;
        document.getElementById(`processTemp_${this.featureId}`).textContent = finalResults.processTemp;
        document.getElementById(`yieldPrediction_${this.featureId}`).textContent = finalResults.yieldPrediction;
    }
}

window.DeviceSynthesizabilityFeature = DeviceSynthesizabilityFeature;
