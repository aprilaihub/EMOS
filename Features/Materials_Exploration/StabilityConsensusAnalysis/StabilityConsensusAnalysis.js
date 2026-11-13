// Stability Analysis Feature
class StabilityConsensusAnalysisFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Stability Analysis', 'Query materials databases and run predictors to evaluate multi-source stability');
        this.uploadedCifFiles = [];
        this.pendingFileReads = 0;
        this.selectedCifCount = 0;
        this._abortController = null;
        this._downloadJsonUrl = null;
    }

    createInputsHTML() {
        return `
            <div class="input-controls" style="align-items:center; gap:24px;">
                <div style="width:min(100%, 640px); text-align:center;">
                    <label for="cifFile_${this.featureId}" style="align-items:stretch; gap:8px;">
                        <span>CIF Files</span>
                        <input type="file" id="cifFile_${this.featureId}" accept=".cif" multiple style="box-sizing:border-box; flex:none; width:100%; text-align:left;">
                    </label>
                    <small style="display:block; margin-top:7px; color:#6c757d;">Upload one or more crystal structure CIF files</small>
                </div>

                <div style="display:grid; grid-template-columns:1fr; gap:16px; width:min(100%, 520px);">
                    <fieldset style="box-sizing:border-box; margin:0; padding:14px 16px 16px; border:1px solid #d9dee7; border-radius:8px; background:#fff;">
                        <legend style="padding:0 7px; color:#495057; font-weight:600;">Databases</legend>
                        <div id="dbCheckboxes_${this.featureId}" style="display:flex; flex-direction:column; gap:8px;">
                            <label style="display:grid; grid-template-columns:20px minmax(0, 1fr); align-items:center; gap:10px; width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #e3e7ee; border-radius:6px; background:#f8f9fa; cursor:pointer;">
                                <input type="checkbox" name="database" value="materialsproject" style="width:18px; height:18px; margin:0; padding:0;">
                                <span style="text-align:left;">Materials Project</span>
                            </label>
                            <label style="display:grid; grid-template-columns:20px minmax(0, 1fr); align-items:center; gap:10px; width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #e3e7ee; border-radius:6px; background:#f8f9fa; cursor:pointer;">
                                <input type="checkbox" name="database" value="alexandria" style="width:18px; height:18px; margin:0; padding:0;">
                                <span style="text-align:left;">Alexandria</span>
                            </label>
                        </div>
                    </fieldset>

                    <fieldset style="box-sizing:border-box; margin:0; padding:14px 16px 16px; border:1px solid #d9dee7; border-radius:8px; background:#fff;">
                        <legend style="padding:0 7px; color:#495057; font-weight:600;">Predictors</legend>
                        <div id="predCheckboxes_${this.featureId}" style="display:flex; flex-direction:column; gap:8px;">
                            <label style="display:grid; grid-template-columns:20px minmax(0, 1fr); align-items:center; gap:10px; width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #e3e7ee; border-radius:6px; background:#f8f9fa; cursor:pointer;">
                                <input type="checkbox" name="predictor" value="mattersim" style="width:18px; height:18px; margin:0; padding:0;">
                                <span style="text-align:left;">MatterSim</span>
                            </label>
                            <label style="display:grid; grid-template-columns:20px minmax(0, 1fr); align-items:center; gap:10px; width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #e3e7ee; border-radius:6px; background:#f8f9fa; cursor:pointer;">
                                <input type="checkbox" name="predictor" value="chgnet" style="width:18px; height:18px; margin:0; padding:0;">
                                <span style="text-align:left;">CHGNet</span>
                            </label>
                            <label style="display:grid; grid-template-columns:20px minmax(0, 1fr); align-items:center; gap:10px; width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #e3e7ee; border-radius:6px; background:#f8f9fa; cursor:pointer;">
                                <input type="checkbox" name="predictor" value="grace" style="width:18px; height:18px; margin:0; padding:0;">
                                <span style="text-align:left;">GRACE</span>
                            </label>
                        </div>
                    </fieldset>
                </div>
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div id="resultsContainer_${this.featureId}" style="display:none;">
                    <div class="output-item">
                        <strong>Batch Summary:</strong>
                        <span id="batchSummary_${this.featureId}">Pending...</span>
                    </div>

                    <div class="output-item">
                        <div id="stabilityHeatmap_${this.featureId}" style="width:100%; margin-top:0.75rem;"></div>
                    </div>

                    <div class="output-item">
                        <strong>Download Results (JSON):</strong>
                        <span id="downloadResultsJson_${this.featureId}">Pending...</span>
                    </div>
                </div>
                
                <div id="pendingMessage_${this.featureId}" style="text-align:center; color:#666;">
                    <p>Awaiting analysis...</p>
                </div>
            </div>
        `;
    }

    attachEventListeners() {
        // CIF file upload handler
        const cifInput = document.getElementById(`cifFile_${this.featureId}`);
        if (cifInput) {
            cifInput.addEventListener('change', (e) => {
                const files = Array.from(e.target.files || []);
                if (files.length > 0) {
                    this.uploadedCifFiles = [];
                    this.selectedCifCount = files.length;
                    this.pendingFileReads = files.length;
                    const processBtn = document.getElementById(`processBtn_${this.featureId}`);
                    if (processBtn) processBtn.disabled = true;
                    this.addLog(`Loading ${files.length} CIF file(s)...`, 'info');
                    files.forEach((file) => {
                        const reader = new FileReader();
                        reader.onload = (event) => {
                            this.uploadedCifFiles.push({
                                name: file.name,
                                content: event.target.result,
                            });
                            this.pendingFileReads -= 1;
                            this.addLog(`CIF file loaded: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`, 'success');
                            if (this.pendingFileReads === 0) {
                                this.addLog(`All ${this.selectedCifCount} CIF file(s) loaded. Ready to process.`, 'success');
                                if (processBtn) processBtn.disabled = false;
                            }
                        };
                        reader.readAsText(file);
                    });
                }
            });
        }
        
    }

    async processFeature() {
        throw new Error('Local fallback is not supported for this feature. Please start the Python backend.');
    }

    async callPythonBackend() {
        const inputs = this.collectInputData();
        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';
        const controller = new AbortController();
        this._abortController = controller;

        try {
            const response = await fetch(`${backendUrl}/api/process/${this.featureId}/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(inputs),
                signal: controller.signal,
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            if (!response.body) {
                throw new Error('The backend did not provide a response stream.');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalResult = null;
            let backendError = null;

            const handleBlock = (block) => {
                const lines = block.split('\n');
                let eventType = 'message';
                const dataLines = [];

                for (const line of lines) {
                    if (line.startsWith('event:')) {
                        eventType = line.slice(6).trim();
                    } else if (line.startsWith('data:')) {
                        dataLines.push(line.slice(5).trimStart());
                    }
                }

                if (dataLines.length === 0) return;

                const rawData = dataLines.join('\n');
                let eventData;
                try {
                    eventData = JSON.parse(rawData);
                } catch (_) {
                    eventData = { message: rawData };
                }

                if (eventType === 'result') {
                    finalResult = eventData;
                } else if (eventType === 'log') {
                    this.addLog(eventData.message || '', eventData.level || 'info');
                } else if (eventType === 'logs' && Array.isArray(eventData)) {
                    eventData.forEach((entry) => {
                        this.addLog(entry.message || '', entry.level || 'info');
                    });
                } else if (eventType === 'progress') {
                    const progress = Math.max(0, Math.min(1, Number(eventData.progress) || 0));
                    const progressFill = document.getElementById(`progressFill_${this.featureId}`);
                    if (progressFill) progressFill.style.width = `${Math.round(progress * 100)}%`;
                } else if (eventType === 'error') {
                    backendError = eventData.message || 'Unknown backend error';
                }
            };

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
                const blocks = buffer.split('\n\n');
                buffer = blocks.pop() || '';
                blocks.filter(block => block.trim()).forEach(handleBlock);
            }

            buffer += decoder.decode().replace(/\r\n/g, '\n');
            if (buffer.trim()) handleBlock(buffer);

            if (finalResult) return finalResult;
            if (this._cancelled) return { status: 'cancelled' };
            throw new Error(backendError || 'The backend stream ended without a result.');
        } catch (error) {
            if (error.name === 'AbortError' && this._cancelled) {
                return { status: 'cancelled' };
            }
            throw error;
        } finally {
            if (this._abortController === controller) {
                this._abortController = null;
            }
        }
    }

    collectInputData() {
        const inputs = super.collectInputData();

        if (this.pendingFileReads > 0) {
            throw new Error(`Please wait for all CIF files to finish loading (${this.pendingFileReads} remaining)`);
        }

        // Inject uploaded CIF file payloads.
        inputs.cif_files = this.uploadedCifFiles;
        // Keep backward compatibility for backend paths expecting a single CIF.
        inputs.cif_file = this.uploadedCifFiles[0]?.content || '';

        const selectedDbs = Array.from(
            document.querySelectorAll(`#dbCheckboxes_${this.featureId} input[type="checkbox"]:checked`)
        ).map(cb => ({ value: cb.value, name: cb.parentElement.textContent.trim() }));

        const selectedPreds = Array.from(
            document.querySelectorAll(`#predCheckboxes_${this.featureId} input[type="checkbox"]:checked`)
        ).map(cb => ({ value: cb.value, name: cb.parentElement.textContent.trim() }));

        inputs.active_databases = selectedDbs;
        inputs.active_predictors = selectedPreds;

        return inputs;
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results || {};
        const resultsContainer = document.getElementById(`resultsContainer_${this.featureId}`);
        const pendingMsg = document.getElementById(`pendingMessage_${this.featureId}`);
        const batchSummaryEl = document.getElementById(`batchSummary_${this.featureId}`);
        const heatmapEl = document.getElementById(`stabilityHeatmap_${this.featureId}`);
        const downloadEl = document.getElementById(`downloadResultsJson_${this.featureId}`);

        const sourceDisplayNames = {
            materialsproject: 'Materials Project',
            alexandria: 'Alexandria',
            mattersim: 'MatterSim',
            chgnet: 'CHGNet',
            grace: 'GRACE'
        };

        const revokeDownloadUrl = () => {
            if (this._downloadJsonUrl) {
                URL.revokeObjectURL(this._downloadJsonUrl);
                this._downloadJsonUrl = null;
            }
        };

        const renderDownloadLink = (jsonData) => {
            if (!downloadEl) return;
            revokeDownloadUrl();
            downloadEl.innerHTML = '';

            if (!jsonData) {
                downloadEl.textContent = 'Unavailable';
                return;
            }

            const blob = new Blob([jsonData], { type: 'application/json' });
            this._downloadJsonUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = this._downloadJsonUrl;
            link.download = 'stability-analysis-results.json';
            link.textContent = 'Download JSON';
            link.addEventListener('click', () => this.addLog('Results downloaded', 'success'));
            downloadEl.appendChild(link);
        };

        const positiveColor = '#cfe8d3';
        const negativeColor = '#f2cccc';
        const missingColor = '#e1e5e8';

        const toFiniteNumber = (value) => {
            if (value === null || value === undefined) {
                return null;
            }
            if (typeof value === 'string' && value.trim() === '') {
                return null;
            }
            const numeric = Number(value);
            return Number.isFinite(numeric) ? numeric : null;
        };

        const extractFormationEnergyValue = (entry, sourceKey) => {
            const sourceData = (entry.sources || {})[sourceKey] || {};
            if (sourceKey === 'materialsproject' || sourceKey === 'alexandria') {
                return toFiniteNumber(sourceData?.thermodynamic_metrics?.formation_energy_per_atom?.value);
            }
            return toFiniteNumber(sourceData.raw_value);
        };

        const extractHullValue = (entry, sourceKey) => {
            const sourceData = (entry.sources || {})[sourceKey] || {};
            if (sourceKey === 'materialsproject') {
                return toFiniteNumber(sourceData?.thermodynamic_metrics?.energy_above_hull?.value ?? sourceData.raw_value);
            }
            if (sourceKey === 'alexandria') {
                return toFiniteNumber(sourceData?.thermodynamic_metrics?.hull_distance?.value ?? sourceData.raw_value);
            }
            return null;
        };

        const classifyMetricCell = (value, threshold, positiveLabel, negativeLabel) => {
            const numericValue = toFiniteNumber(value);
            if (numericValue === null) {
                return {
                    text: 'NA',
                    color: missingColor,
                    label: 'Missing value'
                };
            }

            const isPositive = numericValue < threshold || Math.abs(numericValue - threshold) < 1e-12;
            return {
                text: numericValue.toFixed(4),
                color: isPositive ? positiveColor : negativeColor,
                label: isPositive ? positiveLabel : negativeLabel
            };
        };

        const renderHeatmap = (cifResults) => {
            if (!heatmapEl) return;
            heatmapEl.innerHTML = '';

            const computeMeanStd = (values) => {
                const finiteValues = values
                    .map(value => toFiniteNumber(value))
                    .filter(value => value !== null);

                if (finiteValues.length === 0) {
                    return { mean: null, stdDev: null, count: 0 };
                }

                const mean = finiteValues.reduce((sum, value) => sum + value, 0) / finiteValues.length;
                const variance = finiteValues.reduce((sum, value) => {
                    const delta = value - mean;
                    return sum + (delta * delta);
                }, 0) / finiteValues.length;

                return {
                    mean,
                    stdDev: Math.sqrt(variance),
                    count: finiteValues.length,
                };
            };

            const extractAggregateStats = (entry, metricKey, fallbackValues) => {
                const aggregateBlock = entry?.thermodynamic_aggregates?.[metricKey];
                const aggregateMean = toFiniteNumber(aggregateBlock?.mean);
                const aggregateStd = toFiniteNumber(aggregateBlock?.std_dev);
                if (aggregateMean !== null || aggregateStd !== null) {
                    return {
                        mean: aggregateMean,
                        stdDev: aggregateStd,
                        count: Number(aggregateBlock?.count) || 0,
                    };
                }
                return computeMeanStd(fallbackValues);
            };

            const metricColumns = [
                {
                    key: 'mp_formation_energy',
                    title: 'MP ΔHf',
                    subtitle: 'eV/atom',
                    sourceLabel: sourceDisplayNames.materialsproject,
                    unit: 'eV/atom',
                    groupLabel: 'Formation energy (ΔHf, eV/atom)',
                    getValue: (entry) => extractFormationEnergyValue(entry, 'materialsproject'),
                    classify: (value) => classifyMetricCell(
                        value,
                        0.0,
                        'Formation-favorable',
                        'Formation-unfavorable'
                    ),
                },
                {
                    key: 'alex_formation_energy',
                    title: 'Alex ΔHf',
                    subtitle: 'eV/atom',
                    sourceLabel: sourceDisplayNames.alexandria,
                    unit: 'eV/atom',
                    groupLabel: 'Formation energy (ΔHf, eV/atom)',
                    getValue: (entry) => extractFormationEnergyValue(entry, 'alexandria'),
                    classify: (value) => classifyMetricCell(
                        value,
                        0.0,
                        'Formation-favorable',
                        'Formation-unfavorable'
                    ),
                },
                {
                    key: 'mattersim_formation_energy',
                    title: 'MatterSim ΔHf',
                    subtitle: 'eV/atom',
                    sourceLabel: sourceDisplayNames.mattersim,
                    unit: 'eV/atom',
                    groupLabel: 'Formation energy (ΔHf, eV/atom)',
                    getValue: (entry) => extractFormationEnergyValue(entry, 'mattersim'),
                    classify: (value) => classifyMetricCell(
                        value,
                        0.0,
                        'Formation-favorable',
                        'Formation-unfavorable'
                    ),
                },
                {
                    key: 'chgnet_formation_energy',
                    title: 'CHGNet ΔHf',
                    subtitle: 'eV/atom',
                    sourceLabel: sourceDisplayNames.chgnet,
                    unit: 'eV/atom',
                    groupLabel: 'Formation energy (ΔHf, eV/atom)',
                    getValue: (entry) => extractFormationEnergyValue(entry, 'chgnet'),
                    classify: (value) => classifyMetricCell(
                        value,
                        0.0,
                        'Formation-favorable',
                        'Formation-unfavorable'
                    ),
                },
                {
                    key: 'grace_formation_energy',
                    title: 'GRACE ΔHf',
                    subtitle: 'eV/atom',
                    sourceLabel: sourceDisplayNames.grace,
                    unit: 'eV/atom',
                    groupLabel: 'Formation energy (ΔHf, eV/atom)',
                    getValue: (entry) => extractFormationEnergyValue(entry, 'grace'),
                    classify: (value) => classifyMetricCell(
                        value,
                        0.0,
                        'Formation-favorable',
                        'Formation-unfavorable'
                    ),
                },
                {
                    key: 'formation_energy_avg',
                    title: 'Avg ΔHf',
                    subtitle: 'eV/atom',
                    sourceLabel: 'All formation sources',
                    unit: 'eV/atom',
                    groupLabel: 'Formation energy (ΔHf, eV/atom)',
                    getValue: (entry) => {
                        const stats = extractAggregateStats(
                            entry,
                            'formation_energy_per_atom',
                            [
                                extractFormationEnergyValue(entry, 'materialsproject'),
                                extractFormationEnergyValue(entry, 'alexandria'),
                                extractFormationEnergyValue(entry, 'mattersim'),
                                extractFormationEnergyValue(entry, 'chgnet'),
                                extractFormationEnergyValue(entry, 'grace'),
                            ],
                        );
                        return stats.mean;
                    },
                    classify: (value) => classifyMetricCell(
                        value,
                        0.0,
                        'Formation-favorable (average)',
                        'Formation-unfavorable (average)'
                    ),
                },
                {
                    key: 'formation_energy_std',
                    title: 'Std ΔHf',
                    subtitle: 'eV/atom',
                    sourceLabel: 'All formation sources',
                    unit: 'eV/atom',
                    groupLabel: 'Formation energy (ΔHf, eV/atom)',
                    getValue: (entry) => {
                        const stats = extractAggregateStats(
                            entry,
                            'formation_energy_per_atom',
                            [
                                extractFormationEnergyValue(entry, 'materialsproject'),
                                extractFormationEnergyValue(entry, 'alexandria'),
                                extractFormationEnergyValue(entry, 'mattersim'),
                                extractFormationEnergyValue(entry, 'chgnet'),
                                extractFormationEnergyValue(entry, 'grace'),
                            ],
                        );
                        return stats.stdDev;
                    },
                    classify: (value) => {
                        const numericValue = toFiniteNumber(value);
                        if (numericValue === null) {
                            return {
                                text: 'NA',
                                color: missingColor,
                                label: 'Missing value'
                            };
                        }
                        return {
                            text: numericValue.toFixed(4),
                            color: '#eef3fb',
                            label: 'Spread across formation sources'
                        };
                    },
                },
                {
                    key: 'mp_hull_energy',
                    title: 'MP E_hull',
                    subtitle: 'eV/atom',
                    sourceLabel: sourceDisplayNames.materialsproject,
                    unit: 'eV/atom',
                    groupLabel: 'Energy above hull (E_hull, eV/atom)',
                    getValue: (entry) => extractHullValue(entry, 'materialsproject'),
                    classify: (value) => classifyMetricCell(
                        value,
                        0.05,
                        'Near/on hull',
                        'Above hull'
                    ),
                },
                {
                    key: 'alex_hull_energy',
                    title: 'Alex E_hull',
                    subtitle: 'eV/atom',
                    sourceLabel: sourceDisplayNames.alexandria,
                    unit: 'eV/atom',
                    groupLabel: 'Energy above hull (E_hull, eV/atom)',
                    getValue: (entry) => extractHullValue(entry, 'alexandria'),
                    classify: (value) => classifyMetricCell(
                        value,
                        0.05,
                        'Near/on hull',
                        'Above hull'
                    ),
                },
                {
                    key: 'hull_energy_avg',
                    title: 'Avg E_hull',
                    subtitle: 'eV/atom',
                    sourceLabel: 'All hull sources',
                    unit: 'eV/atom',
                    groupLabel: 'Energy above hull (E_hull, eV/atom)',
                    getValue: (entry) => {
                        const stats = extractAggregateStats(
                            entry,
                            'energy_above_hull',
                            [
                                extractHullValue(entry, 'materialsproject'),
                                extractHullValue(entry, 'alexandria'),
                            ],
                        );
                        return stats.mean;
                    },
                    classify: (value) => classifyMetricCell(
                        value,
                        0.05,
                        'Near/on hull (average)',
                        'Above hull (average)'
                    ),
                },
                {
                    key: 'hull_energy_std',
                    title: 'Std E_hull',
                    subtitle: 'eV/atom',
                    sourceLabel: 'All hull sources',
                    unit: 'eV/atom',
                    groupLabel: 'Energy above hull (E_hull, eV/atom)',
                    getValue: (entry) => {
                        const stats = extractAggregateStats(
                            entry,
                            'energy_above_hull',
                            [
                                extractHullValue(entry, 'materialsproject'),
                                extractHullValue(entry, 'alexandria'),
                            ],
                        );
                        return stats.stdDev;
                    },
                    classify: (value) => {
                        const numericValue = toFiniteNumber(value);
                        if (numericValue === null) {
                            return {
                                text: 'NA',
                                color: missingColor,
                                label: 'Missing value'
                            };
                        }
                        return {
                            text: numericValue.toFixed(4),
                            color: '#eef3fb',
                            label: 'Spread across hull sources'
                        };
                    },
                },
            ];

            const table = document.createElement('table');
            Object.assign(table.style, {
                borderCollapse: 'separate',
                borderSpacing: '3px',
                tableLayout: 'fixed',
                width: '100%',
                maxWidth: '100%'
            });

            const headerRow = document.createElement('tr');
            const compositionHeader = document.createElement('th');
            compositionHeader.textContent = 'Composition';
            Object.assign(compositionHeader.style, {
                width: '160px',
                paddingRight: '12px',
                textAlign: 'left'
            });
            headerRow.appendChild(compositionHeader);

            const groupRow = document.createElement('tr');
            const blankHeader = document.createElement('th');
            blankHeader.textContent = '';
            Object.assign(blankHeader.style, {
                width: '160px',
                paddingRight: '12px',
                borderBottom: 'none'
            });
            groupRow.appendChild(blankHeader);

            const groupSegments = [
                { label: 'Formation energy (ΔHf, eV/atom)', span: 7 },
                { label: 'Energy above hull (E_hull, eV/atom)', span: 4 },
            ];
            groupSegments.forEach((segment) => {
                const groupHeader = document.createElement('th');
                groupHeader.textContent = segment.label;
                groupHeader.colSpan = segment.span;
                Object.assign(groupHeader.style, {
                    padding: '6px 8px',
                    textAlign: 'center',
                    fontWeight: '700',
                    borderBottom: '1px solid #cfd8e3',
                    background: '#f6f8fb'
                });
                groupRow.appendChild(groupHeader);
            });
            table.appendChild(groupRow);

            metricColumns.forEach((column) => {
                const metricHeader = document.createElement('th');
                metricHeader.innerHTML = `${column.title}<br><span style="font-size:11px; font-weight:500; color:#667085;">${column.subtitle}</span>`;
                metricHeader.title = `${column.sourceLabel} ${column.title} (${column.unit})`;
                Object.assign(metricHeader.style, {
                    padding: '6px 8px',
                    overflow: 'hidden',
                    textAlign: 'center',
                    whiteSpace: 'nowrap',
                    fontWeight: '600',
                    minWidth: '96px'
                });
                headerRow.appendChild(metricHeader);
            });
            table.appendChild(headerRow);

            cifResults.forEach((entry, index) => {
                const row = document.createElement('tr');
                const compositionCell = document.createElement('th');
                const composition = entry.composition || entry.cif_name || `Compound ${index + 1}`;
                compositionCell.textContent = composition;
                compositionCell.title = `${entry.cif_name || composition}`;
                Object.assign(compositionCell.style, {
                    width: '160px',
                    paddingRight: '12px',
                    textAlign: 'left',
                    whiteSpace: 'nowrap'
                });
                row.appendChild(compositionCell);

                metricColumns.forEach((column) => {
                    const metricValue = column.getValue(entry);
                    const classification = column.classify(metricValue);
                    const cell = document.createElement('td');
                    cell.textContent = classification.text;
                    cell.title = `${composition} — ${column.sourceLabel} ${column.title}: ${classification.text || 'Missing'} ${column.unit} (${classification.label})`;
                    cell.setAttribute('aria-label', cell.title);
                    Object.assign(cell.style, {
                        height: '34px',
                        padding: '0 8px',
                        borderRadius: '4px',
                        backgroundColor: classification.color,
                        textAlign: 'center',
                        fontVariantNumeric: 'tabular-nums',
                        color: classification.label === 'Missing value' ? '#6c757d' : '#24303d'
                    });
                    row.appendChild(cell);
                });
                table.appendChild(row);
            });

            heatmapEl.appendChild(table);

            const legend = document.createElement('div');
            legend.innerHTML = `
                <span style="display:inline-flex; align-items:center; gap:5px;"><span style="width:14px; height:14px; border-radius:3px; background:${positiveColor};"></span>Favorable / near hull</span>
                <span style="display:inline-flex; align-items:center; gap:5px;"><span style="width:14px; height:14px; border-radius:3px; background:${negativeColor};"></span>Unfavorable / above hull</span>
                <span style="display:inline-flex; align-items:center; gap:5px;"><span style="width:14px; height:14px; border-radius:3px; background:${missingColor};"></span>Missing</span>
            `;
            Object.assign(legend.style, {
                display: 'flex',
                flexWrap: 'wrap',
                gap: '14px',
                marginTop: '10px',
                fontSize: '12px',
                color: '#5f6b7a'
            });
            heatmapEl.appendChild(legend);

            const note = document.createElement('div');
            note.textContent = 'Each row corresponds to one uploaded compound composition. All values are in eV/atom. Formation columns include per-source values plus average and standard deviation; hull columns include per-source values plus average and standard deviation. Grey cells indicate missing values.';
            Object.assign(note.style, {
                marginTop: '8px',
                fontSize: '12px',
                color: '#5f6b7a'
            });
            heatmapEl.appendChild(note);
        };

        if (finalResults.error) {
            revokeDownloadUrl();
            this.addLog(`Error: ${finalResults.error}`, 'error');
            if (resultsContainer) resultsContainer.style.display = 'none';
            if (pendingMsg) {
                pendingMsg.style.display = 'block';
                pendingMsg.textContent = `Error: ${finalResults.error}`;
            }
            return;
        }

        if (finalResults.status === 'cancelled') {
            revokeDownloadUrl();
            if (resultsContainer) resultsContainer.style.display = 'none';
            if (pendingMsg) {
                pendingMsg.style.display = 'block';
                pendingMsg.textContent = 'Analysis cancelled.';
            }
            return;
        }

        const cifResults = Array.isArray(finalResults.results_per_cif) && finalResults.results_per_cif.length > 0
            ? finalResults.results_per_cif
            : (finalResults.sources ? [finalResults] : []);

        if (cifResults.length === 0) {
            revokeDownloadUrl();
            if (resultsContainer) resultsContainer.style.display = 'none';
            if (pendingMsg) {
                pendingMsg.style.display = 'block';
                pendingMsg.textContent = 'No results available';
            }
            return;
        }

        if (resultsContainer) resultsContainer.style.display = 'block';
        if (pendingMsg) pendingMsg.style.display = 'none';

        const batchSummary = finalResults.batch_summary || {};
        const totalFiles = batchSummary.total_files ?? cifResults.length;
        const processedFiles = batchSummary.processed_files
            ?? cifResults.filter(entry => !entry.error).length;
        const failedFiles = batchSummary.failed_files
            ?? cifResults.filter(entry => entry.error).length;
        if (batchSummaryEl) {
            batchSummaryEl.textContent = `${processedFiles}/${totalFiles} processed, ${failedFiles} failed`;
        }

        renderHeatmap(cifResults);
        renderDownloadLink(finalResults.downloadResultsJson);
        this.addLog('Batch results displayed', 'success');
    }

    async cancelProcessing() {
        if (!this.isProcessing) return;

        this._cancelled = true;

        const cancelBtn = document.getElementById(`cancelBtn_${this.featureId}`);
        if (cancelBtn) {
            cancelBtn.disabled = true;
            cancelBtn.textContent = 'Cancelling...';
        }

        this.addLog('Requesting cancellation...', 'warning');

        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';
        try {
            let response = null;

            // The stream registers the feature before it starts processing. A
            // very fast click can race that registration, so retry 404s briefly.
            for (let attempt = 0; attempt < 5; attempt += 1) {
                response = await fetch(`${backendUrl}/api/process/${this.featureId}/cancel`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });
                if (response.ok || response.status !== 404) break;
                await new Promise(resolve => setTimeout(resolve, 100));
            }

            if (response?.ok) {
                const data = await response.json();
                this.addLog(`Backend: ${data.message || 'cancel acknowledged'}`, 'info');
            } else {
                this.addLog(`Backend cancel returned HTTP ${response?.status || 'unknown'}`, 'warning');
            }
        } catch (err) {
            this.addLog(`Cancel request failed: ${err.message}`, 'error');
        } finally {
            // Stop waiting for the SSE response after the backend has received
            // the cancellation signal. Backend work stops cooperatively.
            if (this._abortController) {
                this._abortController.abort();
                this._abortController = null;
            }
        }
    }
}

window.StabilityConsensusAnalysisFeature = StabilityConsensusAnalysisFeature;
