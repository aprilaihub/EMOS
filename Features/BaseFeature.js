// ── Property-mappings cache ──────────────────────────────────────────
// Loaded once from modular property-mapping files; shared by every BaseFeature
// instance via the class-level cache.
let _propertyMappingsCache = null;

const _mappingSourcePaths = [
    './Information_Units/property_mappings/sources/databases/aflow.json',
    './Information_Units/property_mappings/sources/databases/alexandria.json',
    './Information_Units/property_mappings/sources/databases/cod.json',
    './Information_Units/property_mappings/sources/databases/jarvisdft.json',
    './Information_Units/property_mappings/sources/databases/materialsproject.json',
    './Information_Units/property_mappings/sources/databases/mathub3d.json',
    './Information_Units/property_mappings/sources/generators/mattergen_bulk_modulus.json',
    './Information_Units/property_mappings/sources/generators/mattergen_chemical_system.json',
    './Information_Units/property_mappings/sources/generators/mattergen_chemical_system_stability.json',
    './Information_Units/property_mappings/sources/generators/mattergen_dft_band_gap.json',
    './Information_Units/property_mappings/sources/generators/mattergen_magnetic_density.json',
    './Information_Units/property_mappings/sources/generators/mattergen_magnetic_density_hhi.json',
    './Information_Units/property_mappings/sources/generators/mattergen_space_group.json',
    './Information_Units/property_mappings/sources/predictors/pdd.json',
    './Information_Units/property_mappings/sources/predictors/gbfs.json',
    './Information_Units/property_mappings/sources/predictors/gbfs2d.json',
    './Information_Units/property_mappings/sources/predictors/mattersim.json',
    './Information_Units/property_mappings/sources/predictors/synthnn.json',
];

function _mergeModularMappings(commonData, sourceDataList) {
    const merged = {
        description: 'Merged view of modular property mappings.',
        version: commonData?.version || '2.0',
        properties: {}
    };

    const commonProperties = commonData?.properties || {};
    for (const [name, details] of Object.entries(commonProperties)) {
        merged.properties[name] = { ...details };
    }

    for (const sourceData of sourceDataList) {
        const sourceName = sourceData?.source;
        if (!sourceName) continue;
        const sourceProperties = sourceData?.properties || {};

        for (const [commonName, sourceConfig] of Object.entries(sourceProperties)) {
            if (!merged.properties[commonName]) {
                merged.properties[commonName] = {};
            }
            merged.properties[commonName][sourceName] = sourceConfig;
        }
    }

    return merged;
}

async function _loadPropertyMappings() {
    if (_propertyMappingsCache) return _propertyMappingsCache;

    try {
        const commonResp = await fetch('./Information_Units/property_mappings/common_properties.json');
        if (!commonResp.ok) throw new Error(`HTTP ${commonResp.status} for common properties`);
        const commonData = await commonResp.json();

        const sourceResponses = await Promise.all(
            _mappingSourcePaths.map(async (path) => {
                const resp = await fetch(path);
                if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${path}`);
                return resp.json();
            })
        );

        _propertyMappingsCache = _mergeModularMappings(commonData, sourceResponses);
    } catch (err) {
        console.error('Failed to load modular property mappings:', err);
        _propertyMappingsCache = { properties: {} };
    }

    return _propertyMappingsCache;
}

if (typeof window !== 'undefined') {
    window._loadPropertyMappings = _loadPropertyMappings;
}

// Base Feature Class - Foundation for all EMOS features
class BaseFeature {
    constructor(featureId, featureName, featureDescription) {
        this.featureId = featureId;
        this.featureName = featureName;
        this.featureDescription = featureDescription;
        this.isProcessing = false;
        this._cancelled = false;
        this.results = null;
    }

    // Create the complete feature interface
    createFeatureHTML() {
        return `
            <div class="feature-header">
                <div class="feature-title-section">
                    <h3><span id="featureTitle">${this.featureName}</span> Processing</h3>
                    <p class="feature-subtitle" id="featureSubtitle">${this.featureDescription}</p>
                </div>
                <button class="close-feature" id="closeFeature">×</button>
            </div>
            
            <div class="process-section">
                <h3>Inputs</h3>
                <div class="process-content" id="inputsContent">
                    ${this.createInputsHTML()}
                </div>
            </div>
            
            <div class="process-section">
                <h3>Processing</h3>
                <div class="process-content" id="processingContent">
                    ${this.createProcessingHTML()}
                </div>
            </div>
            
            <div class="process-section">
                <h3>Outputs</h3>
                <div class="process-content" id="outputsContent">
                    ${this.createOutputsHTML()}
                </div>
            </div>
        `;
    }

    // Override in subclasses for specific inputs
    createInputsHTML() {
        return `
            <p>Configure your input parameters for ${this.featureName}</p>
            <div class="input-controls">
                <label>Parameter 1: <input type="text" placeholder="Enter value" id="param1_${this.featureId}"></label>
                <label>Parameter 2: <input type="text" placeholder="Enter value" id="param2_${this.featureId}"></label>
                <label>Parameter 3: <input type="text" placeholder="Enter value" id="param3_${this.featureId}"></label>
            </div>
        `;
    }

    // Override in subclasses for specific processing UI
    createProcessingHTML() {
        return `
            <p>Processing ${this.featureName}...</p>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill_${this.featureId}"></div>
            </div>
            <div class="log-terminal" id="logTerminal_${this.featureId}">
                <div class="log-header">
                    <span>Processing Log</span>
                    <button type="button" class="log-clear-btn" onclick="window.features[${this.featureId}].clearLogs()">Clear</button>
                </div>
                <div class="log-content" id="logContent_${this.featureId}"></div>
            </div>
            <div class="process-btn-group">
                <button type="button" class="process-btn" id="processBtn_${this.featureId}" onclick="window.features[${this.featureId}].startProcessing()">Start Processing</button>
                <button type="button" class="cancel-btn" id="cancelBtn_${this.featureId}" onclick="window.features[${this.featureId}].cancelProcessing()" style="display:none;">Cancel</button>
            </div>
        `;
    }

    // Override in subclasses for specific outputs
    createOutputsHTML() {
        return `
            <p>Results for ${this.featureName}</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Result 1:</strong> <span id="result1_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Result 2:</strong> <span id="result2_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Result 3:</strong> <span id="result3_${this.featureId}">Pending...</span>
                </div>
            </div>
        `;
    }

    // Utility methods for creating different input types
    createTextInput(id, label, placeholder = '', required = false) {
        const req = required ? 'required' : '';
        return `
            <label>${label}: 
                <input type="text" id="${id}" placeholder="${placeholder}" ${req}>
            </label>
        `;
    }

    createNumberInput(id, label, min = '', max = '', step = '1', defaultValueOrRequired = false, requiredMaybe = false) {
        let required = false;
        let defaultValue = '';

        if (typeof defaultValueOrRequired === 'boolean') {
            required = defaultValueOrRequired;
        } else {
            defaultValue = defaultValueOrRequired;
            required = !!requiredMaybe;
        }

        const req = required ? 'required' : '';
        const valueAttr = defaultValue !== '' ? `value="${defaultValue}"` : '';
        return `
            <label>${label}: 
                <input type="number" id="${id}" min="${min}" max="${max}" step="${step}" ${valueAttr} ${req}>
            </label>
        `;
    }

    createSelectInput(id, label, options, required = false) {
        const req = required ? 'required' : '';
        const optionsHTML = options.map(opt => 
            `<option value="${opt.value}">${opt.text}</option>`
        ).join('');
        return `
            <label>${label}: 
                <select id="${id}" ${req}>
                    ${optionsHTML}
                </select>
            </label>
        `;
    }

    createFileInput(id, label, accept = '') {
        return `
            <label>${label}: 
                <input type="file" id="${id}" accept="${accept}">
            </label>
        `;
    }

    createCheckboxInput(id, label, checked = false) {
        const checkedAttr = checked ? 'checked' : '';
        return `
            <label>
                <input type="checkbox" id="${id}" ${checkedAttr}> ${label}
            </label>
        `;
    }

    // Processing methods
    async startProcessing() {
        if (this.isProcessing) return;
        
        this.isProcessing = true;
        this._cancelled = false;
        const processBtn = document.getElementById(`processBtn_${this.featureId}`);
        const cancelBtn = document.getElementById(`cancelBtn_${this.featureId}`);
        const progressFill = document.getElementById(`progressFill_${this.featureId}`);
        
        // Clear previous logs and add initial log
        this.clearLogs();
        this.addLog('Starting processing...', 'info');
        
        if (processBtn) {
            processBtn.disabled = true;
            processBtn.textContent = 'Processing...';
        }
        if (cancelBtn) {
            cancelBtn.style.display = '';
            cancelBtn.disabled = false;
            cancelBtn.textContent = 'Cancel';
        }
        
        if (progressFill) {
            progressFill.style.width = '0%';
            progressFill.style.transition = 'width 0.3s ease';
            progressFill.style.width = '5%'; // small initial indication
        }
        
        try {
            // Try Python backend first
            this.addLog('Connecting to Python backend...', 'info');
            console.log(`Calling Python backend for feature ${this.featureId}`);
            const results = await this.callPythonBackend();
            this.results = results;
            if (results && results.status === 'cancelled') {
                this.addLog('Job cancelled.', 'warning');
            } else {
                this.addLog('Python backend processing completed successfully!', 'success');
            }
            this.updateOutputs();
        } catch (error) {
            // If the user cancelled, don't fall back to local processing
            if (this._cancelled) {
                this.addLog('Job cancelled.', 'warning');
                this.results = { status: 'cancelled', generation_results: {} };
                this.updateOutputs();
            } else {
                this.addLog(`Backend error: ${error.message}`, 'error');
                this.addLog('Backend unavailable, using local processing...', 'warning');
                console.log('Backend failed, using local processing:', error);
                
                try {
                    // Simulate processing time
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    // Fallback to local processFeature
                    this.addLog('Running local feature processing...', 'info');
                    this.results = await this.processFeature();
                    this.addLog('Local processing completed successfully!', 'success');
                    this.updateOutputs();
                } catch (localError) {
                    console.error('Processing error:', localError);
                    this.addLog(`Processing error: ${localError.message}`, 'error');
                    this.updateOutputs({ error: localError.message });
                }
            }
        } finally {
            this.isProcessing = false;
            if (processBtn) {
                processBtn.disabled = false;
                processBtn.textContent = 'Start Processing';
            }
            if (cancelBtn) {
                cancelBtn.style.display = 'none';
            }
            if (progressFill) {
                setTimeout(() => {
                    progressFill.style.width = '0%';
                }, 1000);
            }
        }
    }

    /**
     * Cancel the current processing.
     * Subclasses should override this to implement feature-specific cancellation
     * (e.g. calling the backend cancel endpoint, aborting an SSE reader, etc.).
     * The base implementation is a no-op.
     */
    async cancelProcessing() {
        this.addLog('Cancel requested — this feature does not support cancellation.', 'warning');
    }

    // Add log entry to the processing log
    addLog(message, type = 'info') {
        // Also log to console for debugging
        console.log(`[Feature ${this.featureId}] ${type.toUpperCase()}: ${message}`);
        
        const logContent = document.getElementById(`logContent_${this.featureId}`);
        if (!logContent) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${type}`;
        logEntry.innerHTML = `<span class="log-time">[${timestamp}]</span> <span class="log-message">${message}</span>`;
        
        logContent.appendChild(logEntry);
        logContent.scrollTop = logContent.scrollHeight;
    }

    // Clear all log entries
    clearLogs() {
        const logContent = document.getElementById(`logContent_${this.featureId}`);
        if (logContent) {
            logContent.innerHTML = '';
        }
    }

    // Simulate processing for features that don't have complex processing
    async simulateProcessing() {
        return new Promise(resolve => setTimeout(resolve, 1500));
    }

    // Override in subclasses for specific processing logic
    async processFeature() {
        this.addLog('Initializing feature processing...', 'info');
        await new Promise(resolve => setTimeout(resolve, 500));
        
        this.addLog('Loading configuration parameters...', 'info');
        await new Promise(resolve => setTimeout(resolve, 500));
        
        this.addLog('Processing data with algorithms...', 'info');
        await new Promise(resolve => setTimeout(resolve, 500));
        
        this.addLog('Generating results...', 'info');
        await new Promise(resolve => setTimeout(resolve, 500));
        
        return {
            result1: 'Processing complete',
            result2: 'Analysis finished',
            result3: 'Results generated'
        };
    }

    // Override in subclasses for specific output updates
    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        if (finalResults.error) {
            document.getElementById(`result1_${this.featureId}`).textContent = `Error: ${finalResults.error}`;
            return;
        }
        
        if (finalResults.result1) {
            document.getElementById(`result1_${this.featureId}`).textContent = finalResults.result1;
        }
        if (finalResults.result2) {
            document.getElementById(`result2_${this.featureId}`).textContent = finalResults.result2;
        }
        if (finalResults.result3) {
            document.getElementById(`result3_${this.featureId}`).textContent = finalResults.result3;
        }
    }

    // Utility method to get input values
    getInputValue(id) {
        const element = document.getElementById(id);
        if (!element) return null;
        
        if (element.type === 'checkbox') {
            return element.checked;
        }
        return element.value;
    }

    escapeHTML(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // ── Property-mappings-driven generator inputs ─────────────────────
    /**
     * Return the Information Units registered in the global catalogue.
     * Features can use this catalogue to build their own local selectors.
     */
    getInformationUnitOptions(iuType) {
        const options = [];
        const seen = new Set();

        document.querySelectorAll(`.iu-feature-btn[data-iu-type="${iuType}"]`).forEach(button => {
            const value = button.dataset.iuFeature;
            if (!value || seen.has(value)) return;

            seen.add(value);
            options.push({
                value,
                label: button.dataset.iuName || value,
            });
        });

        return options;
    }

    /** Normalize a feature-local generator selection into generator keys. */
    _getActiveGeneratorKeys(activeGenerators = []) {
        return activeGenerators
            .map(generator => typeof generator === 'string' ? generator : generator?.value)
            .filter(Boolean);
    }

    /** Return the display label for a generator in a feature-local selection. */
    _getGeneratorDisplayName(genKey, activeGenerators = []) {
        const selected = activeGenerators.find(generator => (
            typeof generator === 'string' ? generator : generator?.value
        ) === genKey);
        if (selected && typeof selected !== 'string') {
            return selected.name || selected.label || genKey;
        }
        // Fallback: prettify the key
        return genKey.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    /**
    * Scan merged modular property mappings and return, for each requested generator
     * key, the list of properties it conditions on together with their
     * metadata (type, description, unit, etc.).
     *
     * Returns: { generatorKey: [ { propKey, name, type, description, unit, range_support }, … ] }
     *
     * The `name` field is the property name as the model expects it
     * (e.g. "dft_band_gap"), while `propKey` is the universal property
     * key from property_mappings (e.g. "band_gap_direct").
     */
    _getGeneratorProperties(propertyMappings, generatorKeys) {
        const result = {};
        for (const gk of generatorKeys) {
            result[gk] = [];
        }

        const props = propertyMappings.properties || {};
        for (const [propKey, propDef] of Object.entries(props)) {
            for (const gk of generatorKeys) {
                if (propDef[gk]) {
                    result[gk].push({
                        propKey,
                        name:          propDef[gk].name,
                        type:          propDef.type        || 'string',
                        description:   propDef.description || '',
                        unit:          propDef.unit        || null,
                        range_support: propDef[gk].range_support || false,
                    });
                }
            }
        }
        return result;
    }

    /**
     * Build an HTML string that contains an <h4> section for each selected
     * generator, with input fields for every property the model conditions
    * on (derived from modular property mappings).
     *
     * Generators that have no conditioning properties (unconditional
     * models) get a short hint message instead of input fields.
     *
     * Also renders shared generation parameters (batch_size) per generator.
     *
     * @param {object} propertyMappings – the merged modular property mappings
     * @param {Array<string|object>} activeGenerators – feature-local selection
     * @returns {string} HTML
     */
    buildGeneratorPropertyInputsHTML(propertyMappings, activeGenerators = []) {
        const activeKeys = this._getActiveGeneratorKeys(activeGenerators);
        if (activeKeys.length === 0) {
            return '<p class="mattergen-hint"><em>Select one or more generators in this feature to configure their parameters.</em></p>';
        }

        const genProps = this._getGeneratorProperties(propertyMappings, activeKeys);
        let html = '';

        for (const gk of activeKeys) {
            const displayName = this._getGeneratorDisplayName(gk, activeGenerators);
            const props = genProps[gk];

            html += `<div class="generator-inputs-block" data-generator="${gk}">`;
            html += `<h4>${displayName}</h4>`;

            // Shared generation parameter: batch_size
            html += `
                <label>Batch Size:
                    <input type="number" id="gen_batch_size_${gk}_${this.featureId}"
                           value="10" min="1" max="1000" step="1">
                </label>`;

            if (props.length === 0) {
                html += `<p class="mattergen-hint"><em>This model generates structures unconditionally — no property targets needed.</em></p>`;
            } else {
                html += `<div class="generator-property-fields">`;
                for (const p of props) {
                    const inputId = `gen_prop_${gk}_${p.name}_${this.featureId}`;
                    const unitStr = p.unit ? ` (${p.unit})` : '';
                    // Human-readable label: capitalise description or fall back to name
                    const label = p.description || p.name;
                    const labelText = `${label}${unitStr}`;

                    if (p.type === 'string') {
                        html += `
                            <label>${labelText}:
                                <input type="text" id="${inputId}"
                                       placeholder="e.g. Si-O"
                                       title="${p.description}">
                            </label>`;
                    } else if (p.type === 'integer') {
                        html += `
                            <label>${labelText}:
                                <input type="number" id="${inputId}"
                                       step="1" min="0"
                                       title="${p.description}">
                            </label>`;
                    } else {
                        // float or other numeric
                        html += `
                            <label>${labelText}:
                                <input type="number" id="${inputId}"
                                       step="any" 
                                       title="${p.description}">
                            </label>`;
                    }
                }
                html += `</div>`;
            }

            html += `</div>`;
        }

        return html;
    }

    /**
     * Collect the values from the property-mappings-driven input fields.
     * Returns an object keyed by generator:
     * {
     *   mattergen_dft_band_gap: {
     *     batch_size: 10,
     *     properties_to_condition_on: { dft_band_gap: 1.5 }
     *   },
     *   ...
     * }
     */
    collectGeneratorPropertyValues(propertyMappings, activeGenerators = []) {
        const activeKeys = this._getActiveGeneratorKeys(activeGenerators);
        const genProps = this._getGeneratorProperties(propertyMappings, activeKeys);
        const result = {};

        for (const gk of activeKeys) {
            const batchEl = document.getElementById(`gen_batch_size_${gk}_${this.featureId}`);
            const entry = {
                batch_size: parseInt(batchEl?.value || '10', 10),
                properties_to_condition_on: {},
            };

            for (const p of (genProps[gk] || [])) {
                const el = document.getElementById(`gen_prop_${gk}_${p.name}_${this.featureId}`);
                if (!el || el.value === '') continue;

                if (p.type === 'integer') {
                    entry.properties_to_condition_on[p.name] = parseInt(el.value, 10);
                } else if (p.type === 'float') {
                    entry.properties_to_condition_on[p.name] = parseFloat(el.value);
                } else {
                    entry.properties_to_condition_on[p.name] = el.value;
                }
            }

            result[gk] = entry;
        }

        return result;
    }

    async callPythonBackend() {
        // Collect input data for this feature
        const inputs = this.collectInputData();
        
        // Get the backend URL from the global configuration
        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';
        
        // Call Python backend
        const response = await fetch(`${backendUrl}/api/process/${this.featureId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(inputs)
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        // Display logs if available (but don't clear existing logs - they should already be cleared)
        if (data.logs && Array.isArray(data.logs)) {
            data.logs.forEach(log => {
                this.addLog(log.message, log.level);
            });
        }
        
        // Return the actual results
        return data.results || data;
    }

    collectInputData() {
        // Collect all input values for this feature
        const inputs = {};
        const inputElements = document.querySelectorAll(`[id$="_${this.featureId}"]`);
        
        inputElements.forEach(element => {
            const key = element.id.replace(`_${this.featureId}`, '');
            if (element.type === 'checkbox') {
                inputs[key] = element.checked;
            } else {
                inputs[key] = element.value;
            }
        });
        
        return inputs;
    }
}

// Export for use in other files
if (typeof window !== 'undefined') {
    window.BaseFeature = BaseFeature;
}
