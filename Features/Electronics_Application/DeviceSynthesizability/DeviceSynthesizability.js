// Device Synthesizability Feature
class DeviceSynthesizabilityFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Device Synthesizability', 'Evaluate the feasibility and methods for synthesizing electronic devices from selected materials');
    }

    createInputsHTML() {
        return `
            <p>Configure input parameters for Device Synthesizability</p>
            <div class="input-controls">
                ${this.createSelectInput(`deviceType_${this.featureId}`, 'Device Type', [{value: 'transistor', text: 'Transistor'}, {value: 'diode', text: 'Diode'}, {value: 'solar_cell', text: 'Solar Cell'}, {value: 'led', text: 'LED'}, {value: 'sensor', text: 'Sensor'}])}
                ${this.createTextInput(`materialComposition_${this.featureId}`, 'Material Composition', 'e.g., GaAs, SiC, InGaN')}
                ${this.createSelectInput(`substrateType_${this.featureId}`, 'Substrate Type', [{value: 'silicon', text: 'Silicon'}, {value: 'sapphire', text: 'Sapphire'}, {value: 'sic', text: 'Silicon Carbide'}, {value: 'gan', text: 'Gallium Nitride'}])}
                ${this.createNumberInput(`operatingTemp_${this.featureId}`, 'Operating Temperature (°C)', '-50', '500', '1')}
                ${this.createSelectInput(`fabricationMethod_${this.featureId}`, 'Preferred Fabrication Method', [{value: 'mocvd', text: 'MOCVD'}, {value: 'mbe', text: 'MBE'}, {value: 'sputtering', text: 'Sputtering'}, {value: 'cvd', text: 'CVD'}])}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>Device Synthesizability results and outputs</p>
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
        // Placeholder processing logic for Device Synthesizability
        return {
            feasibility: 'Synthesis Feasibility - placeholder',
            recommendedProcess: 'Recommended Process - placeholder',
            estimatedCost: 'Estimated Cost - placeholder',
            processTemp: 'Processing Temperature - placeholder',
            yieldPrediction: 'Yield Prediction - placeholder',
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        if (finalResults.error) {
            document.getElementById(`feasibility_${this.featureId}`).textContent = `Error: ${finalResults.error}`;
            return;
        }
        
        if (finalResults.feasibility) {
            document.getElementById(`feasibility_${this.featureId}`).textContent = finalResults.feasibility;
        }
        if (finalResults.recommendedProcess) {
            document.getElementById(`recommendedProcess_${this.featureId}`).textContent = finalResults.recommendedProcess;
        }
        if (finalResults.estimatedCost) {
            document.getElementById(`estimatedCost_${this.featureId}`).textContent = finalResults.estimatedCost;
        }
        if (finalResults.processTemp) {
            document.getElementById(`processTemp_${this.featureId}`).textContent = finalResults.processTemp;
        }
        if (finalResults.yieldPrediction) {
            document.getElementById(`yieldPrediction_${this.featureId}`).textContent = finalResults.yieldPrediction;
        }
    }
}

window.DeviceSynthesizabilityFeature = DeviceSynthesizabilityFeature;
