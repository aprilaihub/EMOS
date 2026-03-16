// Material Generation Feature
class MaterialGenerationFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Material Generation', 'Generate new material compositions using AI-powered algorithms and predictive models');
        // Store raw generation results per generator for the output viewer
        this._genResults = {};  // { generatorKey: { structures, cif_strings, ... } }
        // Cancel support: reader reference for aborting the SSE stream
        this._sseReader = null;
        this._cancelled = false;
    }

    createInputsHTML() {
        // Build input sections from property_mappings.json for every
        // checked generator.  The cache is pre-loaded by script.js
        // before createFeatureHTML() is called.
        const mappings = _propertyMappingsCache || { properties: {} };
        return `
            <p>Configure input parameters for Material Generation</p>
            <div class="input-controls" id="generatorInputs_${this.featureId}">
                ${this.buildGeneratorPropertyInputsHTML(mappings)}
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
            this.addLog(`${genKey}: batch_size=${params.batch_size}`, 'info');
            const props = params.properties_to_condition_on || {};
            if (Object.keys(props).length > 0) {
                this.addLog(`${genKey}: conditioning on ${JSON.stringify(props)}`, 'info');
            }
        }

        this.addLog('Sending streaming request to EMOS backend…', 'info');

        // ── SSE streaming via fetch + ReadableStream ─────────────────
        const response = await fetch(`${backendUrl}/api/process/${this.featureId}/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(inputs),
        });

        if (!response.ok) {
            const errBody = await response.text();
            throw new Error(`HTTP ${response.status}: ${errBody}`);
        }

        // Update the progress bar element (if available)
        const progressFill = document.getElementById(`progressFill_${this.featureId}`);

        // Read the SSE stream
        const reader = response.body.getReader();
        this._sseReader = reader;  // store for cancel support
        this._cancelled = false;
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResult = null;

        // Track the last progress log element so we can update it in-place
        let lastProgressEl = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE blocks (separated by double newlines)
            const blocks = buffer.split('\n\n');
            // Keep the last (possibly incomplete) chunk in the buffer
            buffer = blocks.pop() || '';

            for (const block of blocks) {
                if (!block.trim()) continue;

                let eventType = 'log';
                let dataStr = '';

                for (const line of block.split('\n')) {
                    if (line.startsWith('event: ')) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        dataStr += line.slice(6);
                    } else if (line.startsWith(':')) {
                        // SSE comment (keepalive) — ignore
                    }
                }

                if (!dataStr) continue;

                let data;
                try {
                    data = JSON.parse(dataStr);
                } catch {
                    continue;
                }

                // Handle each event type
                if (eventType === 'log') {
                    this.addLog(data.message || JSON.stringify(data), data.level || 'info');
                    // If a real log line arrives, don't let the next progress
                    // update overwrite it — force a new progress element.
                    lastProgressEl = null;
                } else if (eventType === 'progress') {
                    const pct = Math.round((data.progress || 0) * 100);
                    const msg = `⏳ ${data.message || `${pct}%`}`;
                    if (lastProgressEl) {
                        // Update the existing progress line in-place
                        lastProgressEl.textContent = msg;
                    } else {
                        // Create a new log entry and remember it
                        this.addLog(msg, 'info');
                        const logContent = document.getElementById(`logContent_${this.featureId}`);
                        if (logContent && logContent.lastElementChild) {
                            lastProgressEl = logContent.lastElementChild;
                        }
                    }
                    if (progressFill) {
                        progressFill.style.transition = 'width 0.3s ease';
                        progressFill.style.width = `${pct}%`;
                    }
                } else if (eventType === 'result') {
                    finalResult = data;
                    this.addLog('Generation result received.', 'success');
                } else if (eventType === 'logs') {
                    // Batch of accumulated backend logs
                    if (Array.isArray(data)) {
                        // These were already streamed in real-time, skip duplicates
                    }
                } else if (eventType === 'error') {
                    this.addLog(`Error: ${data.message || 'Unknown error'}`, 'error');
                } else if (eventType === 'cancelled') {
                    this._cancelled = true;
                    this.addLog(`⛔ ${data.message || 'Generation cancelled.'}`, 'warning');
                } else if (eventType === 'done') {
                    // Stream ended
                }
            }
        }

        if (progressFill) {
            progressFill.style.width = '100%';
        }

        // Clean up reader reference
        this._sseReader = null;

        if (this._cancelled) {
            // Return a minimal result so updateOutputs doesn't crash
            return {
                status: 'cancelled',
                generation_results: {},
            };
        }

        if (finalResult) {
            return finalResult;
        }

        // If no streaming result arrived, something went wrong
        throw new Error('No result received from streaming endpoint');
    }

    // ── Cancel support ───────────────────────────────────────────────
    async cancelProcessing() {
        if (!this.isProcessing) return;

        // Set cancelled flag FIRST so the catch block in startProcessing
        // sees it immediately when the reader abort causes an error.
        this._cancelled = true;

        const cancelBtn = document.getElementById(`cancelBtn_${this.featureId}`);
        if (cancelBtn) {
            cancelBtn.disabled = true;
            cancelBtn.textContent = 'Cancelling…';
        }

        this.addLog('Requesting cancellation…', 'warning');

        // 1. Abort the SSE reader so the read loop exits immediately
        if (this._sseReader) {
            try {
                await this._sseReader.cancel();
            } catch { /* already closed */ }
            this._sseReader = null;
        }

        // 2. Tell the Flask backend to cancel the feature's active generation
        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';
        try {
            const resp = await fetch(`${backendUrl}/api/process/${this.featureId}/cancel`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (resp.ok) {
                const data = await resp.json();
                this.addLog(`Backend: ${data.message || 'cancel acknowledged'}`, 'info');
            } else {
                this.addLog(`Backend cancel returned HTTP ${resp.status}`, 'warning');
            }
        } catch (err) {
            this.addLog(`Cancel request failed: ${err.message}`, 'error');
        }
    }

    // ── Output rendering ─────────────────────────────────────────────
    updateOutputs(results = null) {
        const data = results || this.results;
        const statusEl = document.getElementById(`genStatus_${this.featureId}`);

        if (data && data.error) {
            if (statusEl) statusEl.textContent = `Error: ${data.error}`;
            return;
        }

        if (data && data.status === 'cancelled') {
            if (statusEl) statusEl.textContent = '⛔ Generation cancelled.';
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
