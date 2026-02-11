// Material Search Feature
class MaterialSearchFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Material Search', 'Search and explore materials from comprehensive databases using various criteria');
    }

    createInputsHTML() {
        return `
            <p>Configure search parameters for material database exploration</p>
            <div class="input-controls">
                ${this.createTextInput(`materialName_${this.featureId}`, 'Material Name/Formula', 'e.g., Al2O3, Silicon, etc.')}
                ${this.createSelectInput(`propertyType_${this.featureId}`, 'Property Type', [
                    { value: '', text: 'Select Property' },
                    { value: 'mechanical', text: 'Mechanical Properties' },
                    { value: 'thermal', text: 'Thermal Properties' },
                    { value: 'electrical', text: 'Electrical Properties' },
                    { value: 'optical', text: 'Optical Properties' }
                ])}
                ${this.createNumberInput(`minValue_${this.featureId}`, 'Minimum Value', '0', '10000', '0.1')}
                ${this.createNumberInput(`maxValue_${this.featureId}`, 'Maximum Value', '0', '10000', '0.1')}
                ${this.createCheckboxInput(`includeComposites_${this.featureId}`, 'Include Composite Materials', true)}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>Search results for material database query</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Materials Found:</strong> <span id="materialsCount_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Top Match:</strong> <span id="topMatch_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Property Range:</strong> <span id="propertyRange_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Download:</strong> <span id="downloadLink_${this.featureId}">Pending...</span>
                </div>
            </div>
        `;
    }

    async processFeature() {
        // Simple fixed results for material search
        return {
            materialsCount: '42 materials found',
            topMatch: 'Silicon Carbide (SiC)',
            propertyRange: '2.5 - 45.2 GPa',
            downloadLink: 'search_results.csv (Ready)'
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        document.getElementById(`materialsCount_${this.featureId}`).textContent = finalResults.materialsCount;
        document.getElementById(`topMatch_${this.featureId}`).textContent = finalResults.topMatch;
        document.getElementById(`propertyRange_${this.featureId}`).textContent = finalResults.propertyRange;
        document.getElementById(`downloadLink_${this.featureId}`).innerHTML = `<a href="#" style="color: #4CAF50;">${finalResults.downloadLink}</a>`;
    }
}

window.MaterialSearchFeature = MaterialSearchFeature;
