// Database Extractor Feature
class DatabaseExtractorFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Database Extractor', 'Extract and analyze specific material properties and data from integrated databases');
        this._propertyDefs = [];
    }

    createInputsHTML() {
        const propertyFiltersHTML = this._buildPropertyFiltersHTML();

        return `
            <p>Configure input parameters for Database Extractor</p>
            <div class="input-controls">
                ${this.createNumberInput(`batchSize_${this.featureId}`, 'Batch Size', '1', '10000', '1')}
                ${this.createSelectInput(`retrievalMode_${this.featureId}`, 'Retrieval Mode', [{value: 'lenient', text: 'Lenient'}, {value: 'strict', text: 'Strict'}])}
                ${this.createTextInput(`targetCompositions_${this.featureId}`, 'Target Compositions (optional)', 'e.g., Fe, Al2O3')}
                <div>
                    <label>Property Filters</label>
                    <input
                        type="text"
                        id="propertyFilterSearch_${this.featureId}"
                        placeholder="Search properties..."
                        oninput="window.features[${this.featureId}].filterPropertyFilters(this.value)"
                    >
                    <div id="propertyFilters_${this.featureId}" style="max-height: 320px; overflow: auto; margin-top: 8px; padding-right: 4px;">
                        ${propertyFiltersHTML}
                    </div>
                </div>
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

        inputs.queryValues = this._collectPropertyFilterValues();
        // Use filter keys as selected properties so strict/lenient mode applies
        // to properties users actually constrained.
        inputs.selectedProperties = Object.keys(inputs.queryValues);

        // Remove UI-only fields from payload.
        delete inputs.propertyFilterSearch;

        this._propertyDefs.forEach((prop) => {
            delete inputs[`dbx_prop_${prop.name}`];
            delete inputs[`dbx_prop_${prop.name}_min`];
            delete inputs[`dbx_prop_${prop.name}_max`];
        });

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

    _toDisplayLabel(propertyKey) {
        const tokenMap = {
            dft: 'DFT',
            hse: 'HSE',
            r2scan: 'R2SCAN',
            gga: 'GGA',
            gga_u: 'GGA+U',
            mp: 'MP',
            cod: 'COD',
            icsd: 'ICSD',
            jarvis: 'JARVIS',
            aflow: 'AFLOW',
            cif: 'CIF',
            vbm: 'VBM',
            cbm: 'CBM',
            dos: 'DOS',
            efermi: 'Efermi',
            tc: 'Tc',
            agl: 'AGL',
            ael: 'AEL',
            hhi: 'HHI',
            uv: 'UV',
            ir: 'IR',
            piezo: 'Piezo',
            xc: 'XC',
            id: 'ID',
            scan: 'SCAN',
        };

        return String(propertyKey)
            .split('_')
            .map((token) => {
                const lower = token.toLowerCase();
                if (tokenMap[lower]) return tokenMap[lower];
                return token.charAt(0).toUpperCase() + token.slice(1).toLowerCase();
            })
            .join(' ');
    }

    _formatLabelWithUnit(propertyName, unit) {
        const displayName = this._toDisplayLabel(propertyName);
        if (!unit) return displayName;
        return `${displayName} (${unit})`;
    }

    _buildPropertyFiltersHTML() {
        const mappings = (typeof _propertyMappingsCache !== 'undefined' && _propertyMappingsCache) || { properties: {} };
        const properties = mappings.properties || {};

        const defs = Object.entries(properties).map(([name, cfg]) => ({
            name,
            type: cfg?.type || 'string',
            unit: cfg?.unit || '',
            category: cfg?.category || 'other',
            description: cfg?.description || '',
        }));

        defs.sort((a, b) => {
            const catCmp = a.category.localeCompare(b.category);
            return catCmp !== 0 ? catCmp : a.name.localeCompare(b.name);
        });
        this._propertyDefs = defs;

        if (defs.length === 0) {
            return '<p>No properties found in common property mappings.</p>';
        }

        const chunks = [];
        let currentCategory = null;

        defs.forEach((prop) => {
            if (prop.category !== currentCategory) {
                currentCategory = prop.category;
                chunks.push(
                    `<div class="dbx-prop-category" data-category="${prop.category}" style="margin-top: 12px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 8px;"><strong style="text-transform: capitalize;">${prop.category}</strong></div>`
                );
            }

            chunks.push(this._buildSinglePropertyFilterHTML(prop));
        });

        return `<div class="dbx-property-list">${chunks.join('')}</div>`;
    }

    _buildSinglePropertyFilterHTML(prop) {
        const label = this._formatLabelWithUnit(prop.name, prop.unit);
        const isNumeric = prop.type === 'integer' || prop.type === 'float';
        const searchText = `${prop.name} ${prop.category} ${prop.description}`.toLowerCase();

        if (isNumeric) {
            return `
                <div class="dbx-property-row" data-search="${searchText}" style="margin-top: 6px;">
                    <label>${label}
                        <div class="iu-range-inputs">
                            <input type="number" step="any" id="dbx_prop_${prop.name}_min_${this.featureId}" placeholder="Min" title="${prop.name}">
                            <input type="number" step="any" id="dbx_prop_${prop.name}_max_${this.featureId}" placeholder="Max" title="${prop.name}">
                        </div>
                    </label>
                </div>
            `;
        }

        return `
            <div class="dbx-property-row" data-search="${searchText}" style="margin-top: 6px;">
                <label>${label}
                    <input type="text" id="dbx_prop_${prop.name}_${this.featureId}" placeholder="Enter value" title="${prop.name}">
                </label>
            </div>
        `;
    }

    _collectPropertyFilterValues() {
        const values = {};

        this._propertyDefs.forEach((prop) => {
            const isNumeric = prop.type === 'integer' || prop.type === 'float';

            if (isNumeric) {
                const minEl = document.getElementById(`dbx_prop_${prop.name}_min_${this.featureId}`);
                const maxEl = document.getElementById(`dbx_prop_${prop.name}_max_${this.featureId}`);
                const minRaw = minEl?.value?.trim() || '';
                const maxRaw = maxEl?.value?.trim() || '';

                if (minRaw === '' && maxRaw === '') return;

                if (minRaw !== '' && maxRaw !== '') {
                    const minVal = parseFloat(minRaw);
                    const maxVal = parseFloat(maxRaw);
                    if (Number.isFinite(minVal) && Number.isFinite(maxVal)) {
                        values[prop.name] = minVal <= maxVal ? [minVal, maxVal] : [maxVal, minVal];
                    }
                    return;
                }

                const exactRaw = minRaw || maxRaw;
                const exactVal = parseFloat(exactRaw);
                if (Number.isFinite(exactVal)) {
                    values[prop.name] = exactVal;
                }
                return;
            }

            const el = document.getElementById(`dbx_prop_${prop.name}_${this.featureId}`);
            const raw = el?.value?.trim() || '';
            if (raw !== '') {
                values[prop.name] = raw;
            }
        });

        return values;
    }

    filterPropertyFilters(searchTerm = '') {
        const root = document.getElementById(`propertyFilters_${this.featureId}`);
        if (!root) return;

        const normalized = String(searchTerm || '').trim().toLowerCase();
        const rows = root.querySelectorAll('.dbx-property-row');
        rows.forEach((row) => {
            const text = row.getAttribute('data-search') || '';
            row.style.display = !normalized || text.includes(normalized) ? '' : 'none';
        });

        const categories = root.querySelectorAll('.dbx-prop-category');
        categories.forEach((cat) => {
            let sibling = cat.nextElementSibling;
            let hasVisible = false;

            while (sibling && !sibling.classList.contains('dbx-prop-category')) {
                if (
                    sibling.classList.contains('dbx-property-row') &&
                    sibling.style.display !== 'none'
                ) {
                    hasVisible = true;
                    break;
                }
                sibling = sibling.nextElementSibling;
            }

            cat.style.display = hasVisible ? '' : 'none';
        });
    }
}

window.DatabaseExtractorFeature = DatabaseExtractorFeature;
