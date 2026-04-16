// Database Extractor Feature
class DatabaseExtractorFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Database Extractor', 'Extract and analyze specific material properties and data from integrated databases');
    }

    createInputsHTML() {
        return `
            <p>Configure input parameters for Database Extractor</p>
            <div class="input-controls">
                ${this.createTextInput(`selectedProperties_${this.featureId}`, 'Properties (comma-separated keys)', 'e.g., band_gap, formation_energy_r2scan')}
                ${this.createNumberInput(`batchSize_${this.featureId}`, 'Batch Size', '1', '10000', '1')}
                ${this.createSelectInput(`retrievalMode_${this.featureId}`, 'Retrieval Mode', [{value: 'lenient', text: 'Lenient'}, {value: 'strict', text: 'Strict'}])}
                ${this.createTextInput(`targetCompositions_${this.featureId}`, 'Target Compositions (optional)', 'e.g., Fe, Al2O3')}
                <label>Property Filters (JSON object):
                    <textarea id="queryValues_${this.featureId}" placeholder='{"band_gap": [1.0, 2.0]}'></textarea>
                </label>
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
                    <strong>Databases Queried:</strong> <span id="databaseCount_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Skipped Databases:</strong> <span id="skippedDatabaseCount_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Mode:</strong> <span id="retrievalModeOut_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Download:</strong> <span id="downloadPackage_${this.featureId}">Pending...</span>
                </div>
            </div>
        `;
    }

    async processFeature() {
        return this.callPythonBackend();
    }

    collectInputData() {
        const inputs = super.collectInputData();
        const rawQueryValues = inputs.queryValues || '';

        try {
            inputs.queryValues = rawQueryValues ? JSON.parse(rawQueryValues) : {};
        } catch (err) {
            this.addLog('Invalid JSON in Property Filters. Using empty filters.', 'warning');
            inputs.queryValues = {};
        }

        return inputs;
    }

    _buildDownloadLink(extraction) {
        if (!extraction) return 'Pending...';
        const blob = new Blob([JSON.stringify(extraction, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        return `<a href="${url}" download="database_extraction_results.json">Download JSON</a>`;
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        if (finalResults.error) {
            document.getElementById(`recordsExtracted_${this.featureId}`).textContent = `Error: ${finalResults.error}`;
            return;
        }
        
        document.getElementById(`recordsExtracted_${this.featureId}`).textContent = finalResults.recordsExtracted ?? 0;
        document.getElementById(`databaseCount_${this.featureId}`).textContent = finalResults.databaseCount ?? 0;
        document.getElementById(`skippedDatabaseCount_${this.featureId}`).textContent = finalResults.skippedDatabaseCount ?? 0;
        document.getElementById(`retrievalModeOut_${this.featureId}`).textContent = finalResults.extraction?.mode || 'N/A';

        const downloadEl = document.getElementById(`downloadPackage_${this.featureId}`);
        if (downloadEl) {
            downloadEl.innerHTML = this._buildDownloadLink(finalResults.extraction);
        }
    }
}

window.DatabaseExtractorFeature = DatabaseExtractorFeature;
