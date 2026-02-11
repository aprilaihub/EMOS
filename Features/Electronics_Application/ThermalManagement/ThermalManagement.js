// Thermal Management Feature
class ThermalManagementFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Thermal Management', 'Thermal management analysis for electronic device performance optimization');
    }

    createInputsHTML() {
        return `
            <p>Configure parameters for ${this.featureName}</p>
            <div class="input-controls">
                ${this.createSelectInput(`thermalProperty_${this.featureId}`, 'Thermal Property', [
                    { value: 'conductivity', text: 'Thermal Conductivity' },
                    { value: 'expansion', text: 'Thermal Expansion' },
                    { value: 'capacity', text: 'Heat Capacity' }
                ])}
                ${this.createNumberInput(`operatingPower_${this.featureId}`, 'Operating Power (W)', '0.1', '1000', '0.1')}
                ${this.createNumberInput(`ambientTemp_${this.featureId}`, 'Ambient Temperature (°C)', '-50', '200', '1')}
                ${this.createCheckboxInput(`includeConvection_${this.featureId}`, 'Include Convection', true)}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>Thermal management analysis results and optimization</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Optimization Status:</strong> <span id="optimizationStatus_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Maximum Temperature:</strong> <span id="maxTemperature_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Cooling Solution:</strong> <span id="coolingSolution_${this.featureId}">Pending...</span>
                </div>
            </div>
        `;
    }

    async processFeature() {
        // Simple fixed results for thermal management
        return {
            optimizationStatus: 'Thermal management optimized',
            maxTemperature: '73.5°C',
            coolingSolution: 'Cooling solution recommended'
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        document.getElementById(`optimizationStatus_${this.featureId}`).textContent = finalResults.optimizationStatus;
        document.getElementById(`maxTemperature_${this.featureId}`).textContent = finalResults.maxTemperature;
        document.getElementById(`coolingSolution_${this.featureId}`).textContent = finalResults.coolingSolution;
    }
}

window.ThermalManagementFeature = ThermalManagementFeature;
