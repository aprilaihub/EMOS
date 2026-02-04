// Process Integration Feature
class ProcessIntegrationFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Process Integration', 'Process integration workflows for electronic device manufacturing');
    }

    createInputsHTML() {
        return `
            <p>Configure parameters for ${this.featureName}</p>
            <div class="input-controls">
                ${this.createSelectInput(`processStep_${this.featureId}`, 'Process Step', [
                    { value: 'deposition', text: 'Deposition' },
                    { value: 'etching', text: 'Etching' },
                    { value: 'annealing', text: 'Annealing' },
                    { value: 'doping', text: 'Doping' }
                ])}
                ${this.createNumberInput(`processTemp_${this.featureId}`, 'Process Temperature (°C)', '20', '1200', '10')}
                ${this.createTextInput(`gasFlow_${this.featureId}`, 'Gas Flow Rates', 'sccm values')}
                ${this.createCheckboxInput(`inSituMonitoring_${this.featureId}`, 'In-situ Monitoring', true)}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>Process integration results and optimization status</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Integration Status:</strong> <span id="integrationStatus_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Yield Prediction:</strong> <span id="yieldPrediction_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Recipe Parameters:</strong> <span id="recipeParameters_${this.featureId}">Pending...</span>
                </div>
            </div>
        `;
    }

    async processFeature() {
        // Simple fixed results for process integration
        return {
            integrationStatus: 'Process integration optimized',
            yieldPrediction: 'Yield prediction: 82.3%',
            recipeParameters: 'Recipe parameters saved'
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        document.getElementById(`integrationStatus_${this.featureId}`).textContent = finalResults.integrationStatus;
        document.getElementById(`yieldPrediction_${this.featureId}`).textContent = finalResults.yieldPrediction;
        document.getElementById(`recipeParameters_${this.featureId}`).textContent = finalResults.recipeParameters;
    }
}

window.ProcessIntegrationFeature = ProcessIntegrationFeature;
