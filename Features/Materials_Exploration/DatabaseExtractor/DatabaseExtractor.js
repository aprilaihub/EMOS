// Database Extractor Feature
class DatabaseExtractorFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Database Extractor', 'Extract and analyze specific material properties and data from integrated databases');
    }

    createInputsHTML() {
        return `
            <p>Configure database extraction parameters</p>
            <div class="input-controls">
                ${this.createSelectInput(`databaseSource_${this.featureId}`, 'Database Source', [
                    { value: 'all', text: 'All Databases' },
                    { value: 'materialsproject', text: 'Materials Project' },
                    { value: 'oqmd', text: 'OQMD' },
                    { value: 'aflow', text: 'AFLOW' },
                    { value: 'crystallography', text: 'Crystallography DB' }
                ])}
                ${this.createSelectInput(`extractionType_${this.featureId}`, 'Extraction Type', [
                    { value: 'properties', text: 'Material Properties' },
                    { value: 'structures', text: 'Crystal Structures' },
                    { value: 'thermodynamics', text: 'Thermodynamic Data' },
                    { value: 'experimental', text: 'Experimental Data' }
                ])}
                ${this.createTextInput(`filterCriteria_${this.featureId}`, 'Filter Criteria', 'e.g., space_group=225, bandgap>1.0')}
                ${this.createNumberInput(`maxEntries_${this.featureId}`, 'Maximum Entries', '1', '10000', '1')}
                ${this.createFileInput(`configFile_${this.featureId}`, 'Configuration File (optional)', '.json,.yaml')}
                ${this.createCheckboxInput(`includeMetadata_${this.featureId}`, 'Include Metadata', true)}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>Database extraction results and statistics</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Records Extracted:</strong> <span id="recordsExtracted_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Data Size:</strong> <span id="dataSize_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>File Format:</strong> <span id="fileFormat_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Processing Time:</strong> <span id="processingTime_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Download Package:</strong> <span id="downloadPackage_${this.featureId}">Pending...</span>
                </div>
            </div>
        `;
    }

    async processFeature() {
        // Simple fixed results for database extraction
        return {
            recordsExtracted: '2,847 records',
            dataSize: '425.3 MB',
            fileFormat: 'JSON with metadata',
            processingTime: '28.5 seconds',
            downloadPackage: 'extracted_data.zip (Ready)'
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        document.getElementById(`recordsExtracted_${this.featureId}`).textContent = finalResults.recordsExtracted;
        document.getElementById(`dataSize_${this.featureId}`).textContent = finalResults.dataSize;
        document.getElementById(`fileFormat_${this.featureId}`).textContent = finalResults.fileFormat;
        document.getElementById(`processingTime_${this.featureId}`).textContent = finalResults.processingTime;
        document.getElementById(`downloadPackage_${this.featureId}`).innerHTML = `<a href="#" style="color: #4CAF50;">${finalResults.downloadPackage}</a>`;
    }
}

window.DatabaseExtractorFeature = DatabaseExtractorFeature;
