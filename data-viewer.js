/* Browser-only Data Viewer: input adaptation, uPlot rendering, worker lifecycle.
 * No graph state, network data, or backend dependencies live in this module. */
(function (root) {
    'use strict';
    const MODES = ['Auto', 'Plot', 'Heatmap', 't-SNE'];
    const MAX_POINTS = 1000;
    const isRecord = value => value !== null && typeof value === 'object' && !Array.isArray(value);
    const entries = data => isRecord(data) && Array.isArray(data.results) ? data.results : data;
    const atPath = (record, path) => path.reduce((value, key) => (
        isRecord(value) && Object.hasOwn(value, key) ? value[key] : undefined
    ), record);

    // JSON-encoded paths distinguish a literal dotted key from a nested field.
    function vectorFields(data) {
        const rows = entries(data);
        if (!Array.isArray(rows) || !rows.length || !rows.every(isRecord)) return [];
        const paths = new Map();
        function walk(value, path) {
            if (Array.isArray(value)) {
                paths.set(JSON.stringify(path), { key: JSON.stringify(path), label: path.map(key => JSON.stringify(key)).join(' → ') });
            } else if (isRecord(value)) {
                Object.keys(value).forEach(key => walk(value[key], [...path, key]));
            }
        }
        rows.forEach(row => walk(row, []));
        return [...paths.values()].sort((a, b) => a.key.localeCompare(b.key));
    }

    function validateMatrix(rows) {
        if (!Array.isArray(rows) || !rows.length || !Array.isArray(rows[0]) || !rows[0].length) {
            throw new Error('Data must contain a non-empty numeric vector or matrix.');
        }
        const width = rows[0].length;
        for (let index = 0; index < rows.length; index++) {
            const row = rows[index];
            if (!Array.isArray(row) || row.length !== width) throw new Error(`Row ${index}: vector lengths must be equal.`);
            for (let column = 0; column < width; column++) {
                if (typeof row[column] !== 'number' || !Number.isFinite(row[column])) {
                    throw new Error(`Row ${index}, column ${column}: expected a finite number.`);
                }
            }
        }
        return width;
    }

    function adapt(data, field = '', materialName = (_, index) => `Row ${index}`) {
        const values = entries(data);
        if (!Array.isArray(values) || !values.length) throw new Error('Data is empty or unsupported; connect a vector, matrix, or record array.');
        let matrix, vector = false, labels, sourceIndices;
        if (values.every(value => typeof value === 'number')) {
            matrix = [values];
            vector = true;
        } else if (values.every(value => Array.isArray(value) && value.length === 2 && typeof value[0] === 'string' && Array.isArray(value[1]))) {
            matrix = values.map(value => value[1]);
            labels = values.map((value, index) => materialName(value[0], index));
        } else if (values.every(isRecord)) {
            const fields = vectorFields(values);
            if (!fields.length) throw new Error('Records have no vector fields. Use a Splitter to select a numeric array.');
            const selected = field || (fields.length === 1 ? fields[0].key : '');
            if (!selected) return { needsField: true, fields };
            if (!fields.some(candidate => candidate.key === selected)) throw new Error('Selected vector field is unavailable; choose a field.');
            const path = JSON.parse(selected);
            matrix = values.map(value => atPath(value, path));
            labels = values.map((value, index) => materialName(value, index));
            sourceIndices = values.map(value => Number.isInteger(value.index) ? value.index : null);
        } else {
            matrix = values;
        }
        const width = validateMatrix(matrix);
        return {
            matrix, vector, width,
            rows: matrix.map((_, index) => ({
                index, sourceIndex: sourceIndices?.[index] ?? null,
                label: String(labels?.[index] ?? `Row ${index}`),
            })),
        };
    }

    function prepare(model, mode, labels) {
        if (!MODES.includes(mode)) throw new Error('Unsupported viewer mode.');
        const kind = mode === 'Auto' ? (model.vector ? 'Plot' : 'Heatmap') : mode;
        if (kind !== 'Plot' && model.vector) throw new Error(`${kind} requires a matrix (one vector per row).`);
        if (kind === 't-SNE' && (model.matrix.length < 2 || model.matrix.length > MAX_POINTS)) {
            throw new Error(`t-SNE requires 2–${MAX_POINTS} points; received ${model.matrix.length}. No sampling is performed.`);
        }
        const expected = kind === 't-SNE' ? model.matrix.length : model.width;
        if (labels !== undefined) {
            if (!Array.isArray(labels) || labels.length !== expected) throw new Error(`X / Labels must contain exactly ${expected} values for ${kind}.`);
            let numeric = true, strings = true;
            for (const value of labels) {
                numeric = numeric && typeof value === 'number' && Number.isFinite(value);
                strings = strings && typeof value === 'string';
            }
            if (!numeric && !strings) throw new Error('X / Labels must be all finite numbers or all strings.');
        }
        return { ...model, kind, labels };
    }

    function extent(values) {
        let min = Infinity, max = -Infinity;
        for (const value of values) { min = Math.min(min, value); max = Math.max(max, value); }
        // uPlot's scales also need finite spans, not just finite individual values.
        if (!Number.isFinite(max - min)) throw new Error('Numeric range is too large to display without rescaling. Rescale explicitly upstream.');
        if (min === max) {
            const pad = Math.max(1, Math.abs(min) * 0.05);
            min -= pad; max += pad;
        }
        if (!Number.isFinite(min) || !Number.isFinite(max)) throw new Error('Numeric range is too large to display. Rescale explicitly upstream.');
        return [min, max];
    }

    const rowText = row => `${row.label} · row ${row.index}${row.sourceIndex === null ? '' : ` · source index ${row.sourceIndex}`}`;
    const color = fraction => `hsl(${240 - 240 * fraction}, 75%, 55%)`;

    // uPlot supplies canvas sizing, scales, axes, and cursor handling for all three
    // displays. A draw hook preserves unsorted/repeated x-values and draws cells.
    function render(host, hover, model, coordinates) {
        const heatmap = model.kind === 'Heatmap';
        const scatter = model.kind === 't-SNE';
        const categorical = !scatter && model.labels?.every(value => typeof value === 'string');
        const xs = scatter ? coordinates.map(point => point[0]) :
            (!heatmap && model.labels && !categorical ? model.labels : Array.from({ length: model.width }, (_, index) => index));
        const ys = scatter ? coordinates.map(point => point[1]) : model.matrix.flat();
        const xRange = heatmap ? [-0.5, model.width - 0.5] : extent(xs);
        const yRange = heatmap ? [-0.5, model.matrix.length - 0.5] : extent(ys);
        let valueMin = Infinity, valueMax = -Infinity;
        if (heatmap) {
            for (const value of ys) { valueMin = Math.min(valueMin, value); valueMax = Math.max(valueMax, value); }
            extent(ys);
        }
        const columnText = index => String(model.labels?.[index] ?? index);
        const defaultHover = heatmap ? `Color: blue ${valueMin} → red ${valueMax}. Hover a cell for row, column and value.` : 'Hover a point for its label and original row index.';
        hover.textContent = defaultHover;
        const axisLabels = (u, ticks) => ticks.map(value => Number.isInteger(value) && value >= 0 && value < model.width ? columnText(value) : '');
        const opts = {
            width: Math.max(220, host.clientWidth), height: Math.max(180, host.clientHeight),
            legend: { show: false }, select: { show: false },
            cursor: { drag: { x: false, y: false }, points: { show: false } },
            scales: { x: { time: false, range: () => xRange }, y: { range: () => yRange } },
            series: [{}, { show: false }],
            axes: [
                { stroke: '#aab5c5', grid: { show: false }, label: scatter ? 't-SNE 1' : 'X / column', ...(heatmap || categorical ? { values: axisLabels } : {}) },
                { stroke: '#aab5c5', grid: { show: false }, label: scatter ? 't-SNE 2' : heatmap ? 'Row (0-based)' : 'Value', ...(heatmap ? { values: (u, ticks) => ticks.map(value => Number.isInteger(value) ? String(value) : '') } : {}) },
            ],
            hooks: {
                draw: [u => {
                    const ctx = u.ctx;
                    ctx.save();
                    ctx.beginPath(); ctx.rect(u.bbox.left, u.bbox.top, u.bbox.width, u.bbox.height); ctx.clip();
                    if (heatmap) {
                        model.matrix.forEach((row, r) => row.forEach((value, c) => {
                            const left = u.valToPos(c - 0.5, 'x', true), right = u.valToPos(c + 0.5, 'x', true);
                            const top = u.valToPos(r + 0.5, 'y', true), bottom = u.valToPos(r - 0.5, 'y', true);
                            ctx.fillStyle = color(valueMax === valueMin ? 0.5 : (value - valueMin) / (valueMax - valueMin));
                            ctx.fillRect(left, top, right - left + 0.5, bottom - top + 0.5);
                        }));
                    } else {
                        const series = scatter ? [ys] : model.matrix;
                        series.forEach((row, r) => {
                            ctx.strokeStyle = ctx.fillStyle = scatter ? '#67c7d1' : color(series.length === 1 ? 0.5 : r / (series.length - 1));
                            ctx.lineWidth = 1.5 * uPlot.pxRatio;
                            if (!scatter) {
                                ctx.beginPath();
                                row.forEach((value, c) => {
                                    const x = u.valToPos(xs[c], 'x', true), y = u.valToPos(value, 'y', true);
                                    if (c) ctx.lineTo(x, y); else ctx.moveTo(x, y);
                                });
                                ctx.stroke();
                            }
                            row.forEach((value, c) => {
                                ctx.beginPath(); ctx.arc(u.valToPos(xs[c], 'x', true), u.valToPos(value, 'y', true), 3 * uPlot.pxRatio, 0, 2 * Math.PI); ctx.fill();
                            });
                        });
                    }
                    ctx.restore();
                }],
                setCursor: [u => {
                    const { left, top } = u.cursor;
                    if (left < 0 || top < 0) { hover.textContent = defaultHover; return; }
                    if (heatmap) {
                        const c = Math.round(u.posToVal(left, 'x')), r = Math.round(u.posToVal(top, 'y'));
                        hover.textContent = model.matrix[r]?.[c] === undefined ? defaultHover : `${rowText(model.rows[r])} · column ${c} (${columnText(c)}) · ${model.matrix[r][c]}`;
                    } else {
                        let nearest = null, distance = 144;
                        (scatter ? [ys] : model.matrix).forEach((row, r) => row.forEach((value, c) => {
                            const d = (left - u.valToPos(xs[c], 'x')) ** 2 + (top - u.valToPos(value, 'y')) ** 2;
                            if (d <= distance) { distance = d; nearest = { r, c, value }; }
                        }));
                        if (!nearest) { hover.textContent = defaultHover; return; }
                        const { r, c, value } = nearest;
                        const row = model.rows[scatter ? c : r];
                        const label = scatter && model.labels ? `${model.labels[c]} · ${rowText(row)}` : rowText(row);
                        hover.textContent = `${label} · ${scatter ? 't-SNE' : `column ${c} (${columnText(c)})`} · x=${xs[c]}, y=${value}`;
                    }
                }],
            },
        };
        // Only endpoints feed uPlot's scale plumbing. The draw hook uses every
        // original point in order; it neither sorts nor merges categories.
        return new uPlot(opts, [[xRange[0], xRange[1]], [yRange[0], yRange[1]]], host);
    }

    function bodyHTML() {
        return `<div class="ne-data-viewer">
            <label>Mode <select class="ne-data-mode" aria-label="Data Viewer mode">${MODES.map(mode => `<option>${mode}</option>`).join('')}</select></label>
            <label class="ne-data-field-label" hidden>Vector field <select class="ne-data-field" aria-label="Vector field"></select></label>
            <div class="ne-data-tsne" hidden>
                <button type="button" class="ne-data-run" disabled>Run t-SNE</button>
                <button type="button" class="ne-data-cancel" disabled>Cancel</button>
                <p>2–1000 points; no sampling or normalization. Seed 42; 500 iterations. Axes have no physical meaning.</p>
            </div>
            <div class="ne-data-status" role="status" aria-live="polite">No data yet.</div>
            <div class="ne-data-plot" aria-label="Data visualization"></div>
            <div class="ne-data-hover"></div>
        </div>`;
    }

    function mount(container, { materialName, onChange = () => {}, workerFactory = () => new Worker('data-viewer-worker.js') } = {}) {
        const select = container.querySelector('.ne-data-mode');
        const field = container.querySelector('.ne-data-field');
        const fieldLabel = container.querySelector('.ne-data-field-label');
        const tsne = container.querySelector('.ne-data-tsne');
        const run = container.querySelector('.ne-data-run');
        const cancel = container.querySelector('.ne-data-cancel');
        const status = container.querySelector('.ne-data-status');
        const host = container.querySelector('.ne-data-plot');
        const hover = container.querySelector('.ne-data-hover');
        let raw, labels, model, plot, worker, generation = 0, selectedField = '', disposed = false;

        function stop() {
            generation++;
            worker?.terminate(); worker = null;
            cancel.disabled = true;
        }
        function clearPlot() { plot?.destroy(); plot = null; host.replaceChildren(); hover.textContent = ''; }
        function refresh(throwErrors = false) {
            stop(); clearPlot(); model = null; run.disabled = true;
            tsne.hidden = select.value !== 't-SNE';
            const fields = vectorFields(raw);
            field.replaceChildren(new Option('Choose a vector field…', ''));
            fields.forEach(candidate => field.add(new Option(candidate.label, candidate.key)));
            if (!selectedField && fields.length === 1) selectedField = fields[0].key;
            field.value = selectedField;
            fieldLabel.hidden = fields.length === 0;
            if (raw === undefined) {
                status.textContent = throwErrors ? 'Required Data input is missing.' : 'No data yet.';
                if (throwErrors) throw new Error(status.textContent);
                return;
            }
            try {
                const adapted = adapt(raw, selectedField, materialName);
                if (adapted.needsField) { status.textContent = 'Choose a vector field; multiple fields are available.'; return; }
                model = prepare(adapted, select.value, labels);
                if (model.kind === 't-SNE') {
                    status.textContent = `${model.matrix.length} points × ${model.width} features. Ready; press Run t-SNE. Perplexity ${Math.min(30, Math.max(1, (model.matrix.length - 1) / 3))}.`;
                    run.disabled = false;
                } else {
                    plot = render(host, hover, model);
                    status.textContent = `${model.kind}: ${model.matrix.length} row(s) × ${model.width} values.`;
                }
            } catch (error) {
                model = null;
                status.textContent = error.message;
                if (throwErrors) throw error;
            }
        }
        select.addEventListener('change', () => { refresh(); onChange(); });
        field.addEventListener('change', () => { selectedField = field.value; refresh(); onChange(); });
        cancel.addEventListener('click', () => {
            stop(); clearPlot(); status.textContent = 'Cancelled. Press Run t-SNE to restart.';
            run.disabled = !model || model.kind !== 't-SNE';
        });
        run.addEventListener('click', () => {
            if (!model || model.kind !== 't-SNE' || disposed) return;
            stop(); clearPlot(); run.disabled = true;
            const token = generation;
            status.textContent = 'Computing affinities…';
            try {
                worker = workerFactory(); cancel.disabled = false;
                const fail = message => {
                    if (disposed || token !== generation) return;
                    stop(); status.textContent = message; run.disabled = false;
                };
                worker.onerror = event => { event.preventDefault(); fail(`t-SNE worker failed: ${event.message || 'cannot load local worker'}`); };
                worker.onmessage = event => {
                    if (disposed || token !== generation || event.data.id !== token) return;
                    const message = event.data;
                    if (message.type === 'progress') status.textContent = `t-SNE ${message.iteration}/500 iterations (${message.percent}%).`;
                    else if (message.type === 'error') fail(message.error);
                    else if (message.type === 'done') {
                        try {
                            if (message.coordinates.length !== model.matrix.length || validateMatrix(message.coordinates) !== 2) throw new Error('Invalid worker coordinates.');
                            plot = render(host, hover, model, message.coordinates);
                            stop(); run.disabled = false;
                            status.textContent = `t-SNE complete (${message.elapsedMs} ms). Axes have no physical meaning.`;
                        } catch (error) { fail(error.message); }
                    }
                };
                worker.postMessage({ id: token, matrix: model.matrix });
            } catch (error) {
                stop(); run.disabled = false; status.textContent = `Cannot start t-SNE: ${error.message}`;
            }
        });
        const observer = new ResizeObserver(() => {
            if (plot && host.clientWidth) plot.setSize({ width: Math.max(220, host.clientWidth), height: Math.max(180, host.clientHeight) });
        });
        observer.observe(host);
        return {
            load(data, xLabels) { raw = data; labels = xLabels; refresh(true); },
            reset(message = 'No data yet.') { raw = undefined; labels = undefined; refresh(); status.textContent = message; },
            configuration() { return { mode: select.value, field: selectedField }; },
            restore(config) {
                select.value = MODES.includes(config?.mode) ? config.mode : 'Auto';
                selectedField = typeof config?.field === 'string' ? config.field : '';
                refresh();
            },
            destroy() { disposed = true; stop(); clearPlot(); observer.disconnect(); raw = labels = model = undefined; },
        };
    }
    root.EMOSDataViewer = { adapt, prepare, vectorFields, validateMatrix, extent, bodyHTML, mount, MAX_POINTS };
    if (typeof module !== 'undefined' && module.exports) module.exports = root.EMOSDataViewer;
})(typeof self !== 'undefined' ? self : globalThis);
