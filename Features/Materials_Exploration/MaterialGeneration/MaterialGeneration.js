// Material Generation Feature
class MaterialGenerationFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Material Generation', 'Generate new material compositions using AI-powered algorithms and predictive models');
        // Store raw generation results per generator for the output viewer
        this._genResults = {};  // { generatorKey: { structures, cif_strings, ... } }
    }

    createInputsHTML() {
        // Dynamically render input sections for every checked generator
        // that has a registered ___Inputs.js class (e.g. MattergenInputs).
        return `
            <p>Configure input parameters for Material Generation</p>
            <div class="input-controls" id="generatorInputs_${this.featureId}">
                ${this.renderGeneratorInputsHTML()}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <!-- Status summary -->
                <div class="output-item">
                    <strong>Status:</strong>
                    <span id="genStatus_${this.featureId}">Waiting for generation…</span>
                </div>

                <!-- Generator-level selector (if multiple generators ran) -->
                <div class="output-item" id="genSelectorRow_${this.featureId}" style="display:none;">
                    <strong>Generator:</strong>
                    <select id="genSelector_${this.featureId}"></select>
                </div>

                <!-- Structure-level selector -->
                <div class="output-item" id="structSelectorRow_${this.featureId}" style="display:none;">
                    <strong>Structure:</strong>
                    <select id="structSelector_${this.featureId}"></select>
                </div>

                <!-- 3D Crystal Structure Viewer -->
                <div class="output-item" id="cifViewerRow_${this.featureId}" style="display:none;">
                    <strong>Crystal Structure:</strong>
                    <div id="structureViewer_${this.featureId}" style="
                        width:100%; height:400px; position:relative;
                        background:#ffffff; border-radius:6px; margin-top:6px;
                    "></div>
                    <div style="margin-top:6px; text-align:right;">
                        <button id="toggleCifBtn_${this.featureId}" class="btn-secondary" style="
                            font-size:11px; padding:4px 10px; cursor:pointer;
                            background:#313244; color:#cdd6f4; border:1px solid #45475a;
                            border-radius:4px;
                        ">Show CIF Text</button>
                    </div>
                    <pre id="cifViewer_${this.featureId}" class="cif-viewer" style="
                        display:none; max-height:300px; overflow:auto; background:#1e1e2e;
                        color:#cdd6f4; padding:12px; border-radius:6px;
                        font-size:12px; white-space:pre-wrap; margin-top:6px;
                    "></pre>
                </div>
            </div>
        `;
    }

    // ── Processing ───────────────────────────────────────────────────
    // Override callPythonBackend so we can stream the log messages
    // into the Processing Log section as they come back.
    async callPythonBackend() {
        const inputs = this.collectInputData();
        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';

        // Log what we're sending
        const genInputs = inputs.generator_inputs || {};
        for (const [genKey, params] of Object.entries(genInputs)) {
            this.addLog(`${genKey}: model=${params.pretrained_name}, batch_size=${params.batch_size}, num_batches=${params.num_batches}`, 'info');
            const props = params.properties_to_condition_on || {};
            if (Object.keys(props).length > 0) {
                this.addLog(`${genKey}: conditioning on ${JSON.stringify(props)}`, 'info');
            }
        }

        this.addLog('Sending request to EMOS backend…', 'info');

        const response = await fetch(`${backendUrl}/api/process/${this.featureId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(inputs),
        });

        if (!response.ok) {
            const errBody = await response.text();
            throw new Error(`HTTP ${response.status}: ${errBody}`);
        }

        const data = await response.json();

        // Replay backend logs into the Processing Log panel
        if (data.logs && Array.isArray(data.logs)) {
            for (const log of data.logs) {
                this.addLog(log.message, log.level);
            }
        }

        return data.results || data;
    }

    // ── Output rendering ─────────────────────────────────────────────
    updateOutputs(results = null) {
        const data = results || this.results;
        const statusEl = document.getElementById(`genStatus_${this.featureId}`);

        if (data && data.error) {
            if (statusEl) statusEl.textContent = `Error: ${data.error}`;
            return;
        }

        // data.generation_results = { mattergen: { status, num_structures, structures, cif_strings, ... }, ... }
        const genResults = (data && data.generation_results) || {};
        this._genResults = genResults;

        const genKeys = Object.keys(genResults);
        if (genKeys.length === 0) {
            if (statusEl) statusEl.textContent = 'No generation results returned.';
            return;
        }

        // Summarise
        let totalStructs = 0;
        for (const key of genKeys) {
            totalStructs += genResults[key].num_structures || 0;
        }
        if (statusEl) {
            statusEl.textContent = `Completed — ${totalStructs} structure(s) from ${genKeys.length} generator(s).`;
        }

        // ── Generator selector (only if >1 generator) ───────────────
        const genSelectorRow = document.getElementById(`genSelectorRow_${this.featureId}`);
        const genSelector    = document.getElementById(`genSelector_${this.featureId}`);

        if (genKeys.length > 1) {
            genSelectorRow.style.display = '';
            genSelector.innerHTML = genKeys.map(k =>
                `<option value="${k}">${k} (${genResults[k].num_structures || 0} structures)</option>`
            ).join('');
            genSelector.addEventListener('change', () => this._populateStructSelector(genSelector.value));
        } else {
            genSelectorRow.style.display = 'none';
        }

        // Populate structure selector for the first generator
        this._populateStructSelector(genKeys[0]);
    }

    _populateStructSelector(genKey) {
        const res = this._genResults[genKey];
        if (!res) return;

        const structures  = res.structures   || [];
        const cifStrings  = res.cif_strings  || [];
        const numStructs  = structures.length;

        const structRow      = document.getElementById(`structSelectorRow_${this.featureId}`);
        const structSelector = document.getElementById(`structSelector_${this.featureId}`);
        const cifRow         = document.getElementById(`cifViewerRow_${this.featureId}`);
        const viewerContainer = document.getElementById(`structureViewer_${this.featureId}`);
        const cifViewer      = document.getElementById(`cifViewer_${this.featureId}`);
        const toggleCifBtn   = document.getElementById(`toggleCifBtn_${this.featureId}`);

        if (numStructs === 0) {
            structRow.style.display = 'none';
            cifRow.style.display = 'none';
            return;
        }

        // Build options — show reduced formula if available
        structSelector.innerHTML = structures.map((s, i) => {
            let label = `Structure ${i + 1}`;
            // pymatgen JSON has a "sites" array and sometimes "@module"
            if (s && s.sites) {
                // Try to derive a rough formula from species
                const counts = {};
                for (const site of s.sites) {
                    const el = (site.species && site.species[0] && site.species[0].element) || site.label || '?';
                    counts[el] = (counts[el] || 0) + 1;
                }
                const formula = Object.entries(counts).map(([el, n]) => `${el}${n > 1 ? n : ''}`).join('');
                if (formula) label += ` — ${formula}`;
            }
            return `<option value="${i}">${label}</option>`;
        }).join('');

        structRow.style.display = '';
        cifRow.style.display    = '';

        // ── 3Dmol.js viewer ──────────────────────────────────────────
        // Destroy any previous viewer instance
        if (this._3dViewer) {
            viewerContainer.innerHTML = '';
            this._3dViewer = null;
        }

        const showStructure = (idx) => {
            const cifData = cifStrings[idx];

            // Also update the CIF text panel
            cifViewer.textContent = cifData || '(no CIF data available)';

            if (!cifData || typeof $3Dmol === 'undefined') {
                viewerContainer.innerHTML = '<p style="color:#333;padding:20px;">3D viewer unavailable</p>';
                return;
            }

            // Clear and re-create viewer (cleanest approach for model swap)
            viewerContainer.innerHTML = '';
            const viewer = $3Dmol.createViewer(viewerContainer, {
                backgroundColor: '#ffffff',
            });

            viewer.addModel(cifData, 'cif', { doAssembly: true, duplicateAssemblyAtoms: true });

            // Crystal-appropriate styling: ball-and-stick + unit cell
            viewer.setStyle({}, {
                sphere: { radius: 0.4, colorscheme: 'Jmol' },
                stick:  { radius: 0.15, colorscheme: 'Jmol' },
            });

            viewer.addUnitCell();
            viewer.zoomTo();
            viewer.render();

            this._3dViewer = viewer;
        };

        showStructure(0);

        // ── CIF text toggle ──────────────────────────────────────────
        if (toggleCifBtn) {
            const newBtn = toggleCifBtn.cloneNode(true);
            toggleCifBtn.parentNode.replaceChild(newBtn, toggleCifBtn);
            newBtn.addEventListener('click', () => {
                const hidden = cifViewer.style.display === 'none';
                cifViewer.style.display = hidden ? 'block' : 'none';
                newBtn.textContent = hidden ? 'Hide CIF Text' : 'Show CIF Text';
            });
        }

        // Re-attach change listener (remove previous first)
        const newSelector = structSelector.cloneNode(true);
        structSelector.parentNode.replaceChild(newSelector, structSelector);
        newSelector.addEventListener('change', () => showStructure(parseInt(newSelector.value, 10)));
    }
}

window.MaterialGenerationFeature = MaterialGenerationFeature;
