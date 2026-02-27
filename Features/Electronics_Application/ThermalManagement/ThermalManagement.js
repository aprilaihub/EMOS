// Thermal Management Feature
class ThermalManagementFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Thermal Management', 'Thermal management analysis for electronic device performance optimization');
    }

    createInputsHTML() {
        return `
            <p>Configure input parameters for Thermal Management</p>
            <div class="input-controls">
                ${this.createSelectInput(`thermalProperty_${this.featureId}`, 'Thermal Property', [{value: 'conductivity', text: 'Thermal Conductivity'}, {value: 'expansion', text: 'Thermal Expansion'}, {value: 'capacity', text: 'Heat Capacity'}])}
                ${this.createNumberInput(`operatingPower_${this.featureId}`, 'Operating Power (W)', '0.1', '1000', '0.1')}
                ${this.createNumberInput(`ambientTemp_${this.featureId}`, 'Ambient Temperature (°C)', '-50', '200', '1')}
                ${this.createCheckboxInput(`includeConvection_${this.featureId}`, 'Include Convection', true)}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>Thermal Management results and outputs</p>
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
        // Placeholder processing logic for Thermal Management
        return {
            optimizationStatus: 'Optimization Status - placeholder',
            maxTemperature: 'Maximum Temperature - placeholder',
            coolingSolution: 'Cooling Solution - placeholder',
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        if (finalResults.error) {
            document.getElementById(`optimizationStatus_${this.featureId}`).textContent = `Error: ${finalResults.error}`;
            return;
        }
        
        if (finalResults.optimizationStatus) {
            document.getElementById(`optimizationStatus_${this.featureId}`).textContent = finalResults.optimizationStatus;
        }
        if (finalResults.maxTemperature) {
            document.getElementById(`maxTemperature_${this.featureId}`).textContent = finalResults.maxTemperature;
        }
        if (finalResults.coolingSolution) {
            document.getElementById(`coolingSolution_${this.featureId}`).textContent = finalResults.coolingSolution;
        }
    }
}

window.ThermalManagementFeature = ThermalManagementFeature;
