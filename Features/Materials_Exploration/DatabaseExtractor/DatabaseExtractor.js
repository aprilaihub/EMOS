// Database Extractor Feature
class DatabaseExtractorFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Database Extractor', 'Extract and analyze specific material properties and data from integrated databases');
    }

    createInputsHTML() {
        return `
            <p>Configure input parameters for Database Extractor</p>
            <div class="input-controls">
                ${this.createSelectInput(`databaseSource_${this.featureId}`, 'Database Source', [{value: 'all', text: 'All Databases'}, {value: 'materialsproject', text: 'Materials Project'}, {value: 'oqmd', text: 'OQMD'}, {value: 'aflow', text: 'AFLOW'}, {value: 'crystallography', text: 'Crystallography DB'}])}
                ${this.createSelectInput(`extractionType_${this.featureId}`, 'Extraction Type', [{value: 'properties', text: 'Material Properties'}, {value: 'structures', text: 'Crystal Structures'}, {value: 'thermodynamics', text: 'Thermodynamic Data'}, {value: 'experimental', text: 'Experimental Data'}])}
                ${this.createTextInput(`filterCriteria_${this.featureId}`, 'Filter Criteria', 'e.g., space_group=225, bandgap>1.0')}
                ${this.createNumberInput(`maxEntries_${this.featureId}`, 'Maximum Entries', '1', '10000', '1')}
                ${this.createFileInput(`configFile_${this.featureId}`, 'Configuration File', '.json,.yaml')}
                ${this.createCheckboxInput(`includeMetadata_${this.featureId}`, 'Include Metadata', true)}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>Database Extractor results and outputs</p>
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
        // Placeholder processing logic for Database Extractor
        return {
            recordsExtracted: 'Records Extracted - placeholder',
            dataSize: 'Data Size - placeholder',
            fileFormat: 'File Format - placeholder',
            processingTime: 'Processing Time - placeholder',
            downloadPackage: 'Download Package - placeholder',
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        if (finalResults.error) {
            document.getElementById(`recordsExtracted_${this.featureId}`).textContent = `Error: ${finalResults.error}`;
            return;
        }
        
        if (finalResults.recordsExtracted) {
            document.getElementById(`recordsExtracted_${this.featureId}`).textContent = finalResults.recordsExtracted;
        }
        if (finalResults.dataSize) {
            document.getElementById(`dataSize_${this.featureId}`).textContent = finalResults.dataSize;
        }
        if (finalResults.fileFormat) {
            document.getElementById(`fileFormat_${this.featureId}`).textContent = finalResults.fileFormat;
        }
        if (finalResults.processingTime) {
            document.getElementById(`processingTime_${this.featureId}`).textContent = finalResults.processingTime;
        }
        if (finalResults.downloadPackage) {
            document.getElementById(`downloadPackage_${this.featureId}`).textContent = finalResults.downloadPackage;
        }
    }
}

window.DatabaseExtractorFeature = DatabaseExtractorFeature;
