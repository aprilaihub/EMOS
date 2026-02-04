// Property Prediction Feature
class PropertyPredictionFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Property Prediction', 'Electronic property prediction and optimization for semiconductor applications');
    }

    createInputsHTML() {
        return `
            <p>Configure parameters for ${this.featureName}</p>
            <div class="input-controls">
                ${this.createTextInput(`materialSystem_${this.featureId}`, 'Material System', 'e.g., III-V, II-VI')}
                ${this.createSelectInput(`propertyPrediction_${this.featureId}`, 'Property to Predict', [
                    { value: 'bandgap', text: 'Band Gap' },
                    { value: 'mobility', text: 'Carrier Mobility' },
                    { value: 'conductivity', text: 'Electrical Conductivity' }
                ])}
                ${this.createNumberInput(`temperature_${this.featureId}`, 'Temperature (K)', '0', '1000', '1')}
                ${this.createCheckboxInput(`includeDefects_${this.featureId}`, 'Include Defects', false)}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>Electronic property prediction results</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Prediction Status:</strong> <span id="predictionStatus_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Band Gap:</strong> <span id="bandGap_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Carrier Mobility:</strong> <span id="carrierMobility_${this.featureId}">Pending...</span>
                </div>
            </div>
        `;
    }

    async processFeature() {
        // Simple fixed results for property prediction
        return {
            predictionStatus: 'Electronic properties predicted',
            bandGap: '2.7 eV (direct)',
            carrierMobility: '745 cm²/Vs'
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        document.getElementById(`predictionStatus_${this.featureId}`).textContent = finalResults.predictionStatus;
        document.getElementById(`bandGap_${this.featureId}`).textContent = finalResults.bandGap;
        document.getElementById(`carrierMobility_${this.featureId}`).textContent = finalResults.carrierMobility;
    }
}

window.PropertyPredictionFeature = PropertyPredictionFeature;
