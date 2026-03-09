// ── Generator Inputs Registry ────────────────────────────────────────
// Maps the sidebar checkbox `value` (e.g. "mattergen") to the script
// that exposes a `___Inputs` class (with render / attachListeners /
// collectValues methods).
//
// To register a new generator's input UI, add an entry here.
const GENERATOR_INPUTS_REGISTRY = {
    mattergen: {
        script: './Information_Units/Generators/Mattergen/MattergenInputs.js',
        className: 'MattergenInputs',
    },
    // gnome: {
    //     script: './Information_Units/Generators/Gnome/GnomeInputs.js',
    //     className: 'GnomeInputs',
    // },
    // Add more generators here as their ___Inputs.js files are created.
};

if (typeof window !== 'undefined') {
    window.GENERATOR_INPUTS_REGISTRY = GENERATOR_INPUTS_REGISTRY;
}

// Base Feature Class - Foundation for all EMOS features
class BaseFeature {
    constructor(featureId, featureName, featureDescription) {
        this.featureId = featureId;
        this.featureName = featureName;
        this.featureDescription = featureDescription;
        this.isProcessing = false;
        this.results = null;

        /** @type {Object.<string, object>} generator value → ___Inputs instance */
        this._generatorInputInstances = {};
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
            <button type="button" class="process-btn" id="processBtn_${this.featureId}" onclick="window.features[${this.featureId}].startProcessing()">Start Processing</button>
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

    createNumberInput(id, label, min = '', max = '', step = '1', required = false) {
        const req = required ? 'required' : '';
        return `
            <label>${label}: 
                <input type="number" id="${id}" min="${min}" max="${max}" step="${step}" ${req}>
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
        const processBtn = document.getElementById(`processBtn_${this.featureId}`);
        const progressFill = document.getElementById(`progressFill_${this.featureId}`);
        
        // Clear previous logs and add initial log
        this.clearLogs();
        this.addLog('Starting processing...', 'info');
        
        if (processBtn) {
            processBtn.disabled = true;
            processBtn.textContent = 'Processing...';
        }
        
        if (progressFill) {
            progressFill.style.width = '0%';
            progressFill.style.width = '100%';
        }
        
        try {
            // Try Python backend first
            this.addLog('Connecting to Python backend...', 'info');
            console.log(`Calling Python backend for feature ${this.featureId}`);
            const results = await this.callPythonBackend();
            this.results = results;
            this.addLog('Python backend processing completed successfully!', 'success');
            this.updateOutputs();
        } catch (error) {
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
        } finally {
            this.isProcessing = false;
            if (processBtn) {
                processBtn.disabled = false;
                processBtn.textContent = 'Start Processing';
            }
            if (progressFill) {
                setTimeout(() => {
                    progressFill.style.width = '0%';
                }, 1000);
            }
        }
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

    // ── Generator-inputs helpers ─────────────────────────────────────
    /**
     * Return the list of currently-checked generator checkbox values
     * from the sidebar (e.g. ["mattergen", "gnome"]).
     */
    _getActiveGeneratorKeys() {
        const checkboxes = document.querySelectorAll(
            "#generatorsList input[type='checkbox']:checked"
        );
        return Array.from(checkboxes).map(cb => cb.value);
    }

    /**
     * Build an HTML string that contains the input sections for **every
     * checked generator that has an entry in GENERATOR_INPUTS_REGISTRY**.
     *
     * Each generator gets its own `<div class="generator-inputs-block">`
     * wrapper so that styling is straightforward.
     *
     * After injecting this HTML into the DOM, call
     * `this.attachGeneratorInputListeners()` to wire up the dynamic
     * behaviour (e.g. MatterGen's model-dropdown → property-fields swap).
     */
    renderGeneratorInputsHTML() {
        const activeKeys = this._getActiveGeneratorKeys();
        let html = '';

        // Reset tracked instances – we'll (re)create them below.
        this._generatorInputInstances = {};

        for (const key of activeKeys) {
            const entry = GENERATOR_INPUTS_REGISTRY[key];
            if (!entry) continue;                       // no UI registered

            const InputClass = window[entry.className];
            if (!InputClass) continue;                  // script not loaded yet

            const instance = new InputClass(this.featureId);
            this._generatorInputInstances[key] = instance;
            html += `<div class="generator-inputs-block" data-generator="${key}">
                        ${instance.render()}
                     </div>`;
        }

        if (html === '') {
            html = '<p class="mattergen-hint"><em>Select one or more generators from the sidebar to configure their parameters.</em></p>';
        }

        return html;
    }

    /**
     * Call `attachListeners()` on every generator-input instance that was
     * created during the last `renderGeneratorInputsHTML()` call.
     *
     * **Must be called after the HTML has been injected into the DOM.**
     */
    attachGeneratorInputListeners() {
        for (const inst of Object.values(this._generatorInputInstances)) {
            if (typeof inst.attachListeners === 'function') {
                inst.attachListeners();
            }
        }
    }

    /**
     * Collect values from all active generator-input instances and return
     * an object keyed by generator name.
     * Example: `{ mattergen: { pretrained_name: "dft_band_gap", ... } }`
     */
    collectGeneratorInputValues() {
        const result = {};
        for (const [key, inst] of Object.entries(this._generatorInputInstances)) {
            if (typeof inst.collectValues === 'function') {
                result[key] = inst.collectValues();
            }
        }
        return result;
    }

    /**
     * Dynamically load the ___Inputs.js scripts for all currently-checked
     * generators that have an entry in the registry but whose class hasn't
     * been loaded yet. Returns a Promise that resolves when all scripts
     * are loaded.
     */
    async loadGeneratorInputScripts() {
        const activeKeys = this._getActiveGeneratorKeys();
        const loads = [];

        for (const key of activeKeys) {
            const entry = GENERATOR_INPUTS_REGISTRY[key];
            if (!entry) continue;
            if (window[entry.className]) continue;       // already loaded

            // Reuse the global `loadScript` helper defined in script.js
            if (typeof loadScript === 'function') {
                loads.push(loadScript(entry.script));
            } else {
                // Inline fallback if loadScript isn't global
                loads.push(new Promise((resolve, reject) => {
                    const s = document.createElement('script');
                    s.src = entry.script;
                    s.onload = resolve;
                    s.onerror = () => reject(new Error(`Failed to load ${entry.script}`));
                    document.head.appendChild(s);
                }));
            }
        }

        return Promise.all(loads);
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
        
        // Collect active generators
        const generatorCheckboxes = document.querySelectorAll("#generatorsList input[type='checkbox']:checked");
        const activeGenerators = [];
        generatorCheckboxes.forEach(checkbox => {
            const generatorName = checkbox.parentElement.textContent.trim();
            activeGenerators.push({
                value: checkbox.value,
                name: generatorName
            });
        });
        inputs['active_generators'] = activeGenerators;
        
        // Collect active predictors
        const predictorCheckboxes = document.querySelectorAll("#predictorsList input[type='checkbox']:checked");
        const activePredictors = [];
        predictorCheckboxes.forEach(checkbox => {
            const predictorName = checkbox.parentElement.textContent.trim();
            activePredictors.push({
                value: checkbox.value,
                name: predictorName
            });
        });
        inputs['active_predictors'] = activePredictors;
        
        // Collect active databases
        const databaseCheckboxes = document.querySelectorAll("#databasesList input[type='checkbox']:checked");
        const activeDatabases = [];
        databaseCheckboxes.forEach(checkbox => {
            const databaseName = checkbox.parentElement.textContent.trim();
            activeDatabases.push({
                value: checkbox.value,
                name: databaseName
            });
        });
        inputs['active_databases'] = activeDatabases;
        
        // Collect generator-specific input values (e.g. MatterGen model & properties)
        inputs['generator_inputs'] = this.collectGeneratorInputValues();

        return inputs;
    }
}

// Export for use in other files
if (typeof window !== 'undefined') {
    window.BaseFeature = BaseFeature;
}
