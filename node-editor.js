/* ═══════════════════════════════════════════════════════════════════
   EMOS Node Editor — Main JS
   Blender-style node graph for wiring Information Units together
   ═══════════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // ── Constants ────────────────────────────────────────────────────
    const PORT_TYPES = { CIF: 'cif', RESULT: 'result', ANY: 'any' };

    // Port compatibility: which output types can connect to which input types
    const PORT_COMPAT = {
        [PORT_TYPES.CIF]:    [PORT_TYPES.CIF, PORT_TYPES.ANY],
        [PORT_TYPES.RESULT]: [PORT_TYPES.RESULT, PORT_TYPES.ANY],
        [PORT_TYPES.ANY]:    [PORT_TYPES.CIF, PORT_TYPES.RESULT, PORT_TYPES.ANY],
    };

    // Node definitions — ports schema per category
    const NODE_SCHEMAS = {
        database:    { inputs: [],                                                                                          outputs: [{ key: 'cif_out',    label: 'CIF',    type: PORT_TYPES.CIF    }] },
        generator:   { inputs: [],                                                                                          outputs: [{ key: 'cif_out',    label: 'CIF',    type: PORT_TYPES.CIF    }] },
        predictor:   { inputs: [{ key: 'cif_in',    label: 'CIF',    type: PORT_TYPES.CIF    }],                           outputs: [{ key: 'result_out', label: 'Result', type: PORT_TYPES.RESULT }] },
        cif_viewer:  { inputs: [{ key: 'cif_in',    label: 'CIF',    type: PORT_TYPES.CIF    }], outputs: [] },
        text_viewer: { inputs: [{ key: 'any_in',    label: 'Input',  type: PORT_TYPES.ANY    }], outputs: [] },
        filter:      { inputs: [{ key: 'cif_in',    label: 'CIF',    type: PORT_TYPES.CIF    }, { key: 'result_in', label: 'Result', type: PORT_TYPES.RESULT }],
                       outputs:[{ key: 'cif_out',   label: 'CIF',    type: PORT_TYPES.CIF    }, { key: 'result_out', label: 'Result', type: PORT_TYPES.RESULT }] },
        lambda:      { inputs: [{ key: 'cif_in',    label: 'CIF',    type: PORT_TYPES.CIF    }, { key: 'result_in', label: 'Result', type: PORT_TYPES.RESULT }],
                       outputs:[{ key: 'cif_out',   label: 'CIF',    type: PORT_TYPES.CIF    }, { key: 'result_out', label: 'Result', type: PORT_TYPES.RESULT }] },
    };

    // ── Factory key mapping ──────────────────────────────────────────
    // These maps are populated at startup from devtools/metadata.json so they
    // stay in sync automatically when new IUs are added.
    let DATABASE_FACTORY_KEYS  = {};  // display_name → factory id
    let GENERATOR_FACTORY_KEYS = {};  // display_name → factory id
    let PREDICTOR_FACTORY_KEYS = {};  // display_name → factory id

    async function loadFactoryKeysFromMetadata() {
        try {
            const meta = await fetch('./devtools/metadata.json').then(r => r.json());
            const ius  = meta.information_units || {};

            for (const entry of (ius.databases  || [])) DATABASE_FACTORY_KEYS[entry.display_name]  = entry.id;
            for (const entry of (ius.generators  || [])) GENERATOR_FACTORY_KEYS[entry.display_name] = entry.id;
            for (const entry of (ius.predictors  || [])) PREDICTOR_FACTORY_KEYS[entry.display_name] = entry.id;
        } catch (e) {
            console.warn('Could not load factory keys from metadata.json:', e);
        }
    }

    // ── State ────────────────────────────────────────────────────────
    let nodes      = {};   // nodeId → nodeObj
    let wires      = [];   // [{ id, fromNode, fromPort, toNode, toPort, type }]
    let nextNodeId = 1;
    let nextWireId = 1;

    // Canvas transform
    let panX = 0, panY = 0, zoom = 1;
    let isPanning = false, panStartX = 0, panStartY = 0;

    // Wiring state
    let wiringFrom = null;  // { nodeId, portKey, portType, isOutput }
    let tempWirePath = null;

    // Dragging state
    let dragNode     = null;
    let dragOffsetX  = 0, dragOffsetY = 0;

    // Resize state
    let resizeNode   = null;
    let resizeStartW = 0, resizeStartH = 0, resizeStartX = 0, resizeStartY = 0;

    // Selection
    let selectedNodeId = null;

    // Pipeline execution
    let isRunning  = false;
    let cancelFlag = false;
    let activeAbortController = null;
    let activeRunId = null;  // Backend run_id for the currently executing node

    // Loaded data
    let uiData            = null;
    let predictorPropsMap = {};  // factoryKey → { runtimePropName: displayLabel }

    // DOM refs
    let canvasContainer, canvas, wiresSvg, processBtn, cancelBtn, statusText, zoomText, contextMenu;

    // ═══════════════════════════════════════════════════════════════
    // INIT
    // ═══════════════════════════════════════════════════════════════
    document.addEventListener('DOMContentLoaded', async () => {
        canvasContainer = document.getElementById('neCanvasContainer');
        canvas          = document.getElementById('neCanvas');
        wiresSvg        = document.getElementById('neWiresSvg');
        processBtn      = document.getElementById('neProcessBtn');
        cancelBtn       = document.getElementById('neCancelBtn');
        statusText      = document.getElementById('neStatusText');
        zoomText        = document.getElementById('neZoomText');
        contextMenu     = document.getElementById('neContextMenu');

        // Load data
        uiData = await fetch('./devtools/ui_data.json').then(r => r.json()).catch(() => null);
        await loadFactoryKeysFromMetadata();
        predictorPropsMap = await loadPredictorProperties();

        populateSidebar();
        bindEvents();
        applyTransform();
    });

    // ═══════════════════════════════════════════════════════════════
    // SIDEBAR
    // ═══════════════════════════════════════════════════════════════
    function populateSidebar() {
        if (!uiData || !uiData.information_units) return;
        const iu = uiData.information_units;

        // Databases
        const dbContainer = document.getElementById('sidebarDatabases');
        for (const [name, desc] of Object.entries(iu.databases || {})) {
            const key = DATABASE_FACTORY_KEYS[name] || deriveKey(name);
            dbContainer.appendChild(makeSidebarItem('database', key, name, desc));
        }

        // Generators
        const genContainer = document.getElementById('sidebarGenerators');
        for (const [name, desc] of Object.entries(iu.generators || {})) {
            const key = GENERATOR_FACTORY_KEYS[name] || deriveKey(name);
            genContainer.appendChild(makeSidebarItem('generator', key, name, desc));
        }

        // Predictors
        const predContainer = document.getElementById('sidebarPredictors');
        for (const [name, desc] of Object.entries(iu.predictors || {})) {
            const key = PREDICTOR_FACTORY_KEYS[name] || deriveKey(name);
            predContainer.appendChild(makeSidebarItem('predictor', key, name, desc));
        }

        // Bind drag events on hardcoded sidebar items (viewers, utility)
        document.querySelectorAll('.ne-sidebar-item[data-node-type="viewer"], .ne-sidebar-item[data-node-type="utility"]').forEach(el => {
            el.addEventListener('dragstart', (e) => {
                const data = {
                    type: el.dataset.nodeType,
                    key:  el.dataset.nodeKey,
                    name: el.textContent.trim(),
                };
                e.dataTransfer.setData('application/emos-node', JSON.stringify(data));
                e.dataTransfer.effectAllowed = 'copy';
            });
        });
    }

    // ── Load predictor property mappings ────────────────────────
    async function loadPredictorProperties() {
        const factoryKeys = [...new Set(Object.values(PREDICTOR_FACTORY_KEYS))];
        const map = {};
        await Promise.all(factoryKeys.map(async (key) => {
            try {
                const r = await fetch(`./Information_Units/property_mappings/sources/predictors/${key}.json`);
                if (!r.ok) return;
                const data = await r.json();
                const props = {};
                for (const [uiKey, cfg] of Object.entries(data.properties || {})) {
                    const runtimeName = cfg.name || uiKey;
                    // Display label: humanise the ui key
                    props[runtimeName] = uiKey.replace(/_/g, ' ');
                }
                map[key] = props;
            } catch { /* silently ignore missing files */ }
        }));
        return map;
    }

    function deriveKey(displayName) {
        return displayName.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
    }

    function makeSidebarItem(type, key, name, desc) {
        const el = document.createElement('div');
        el.className = 'ne-sidebar-item';
        el.draggable = true;
        el.dataset.nodeType = type;
        el.dataset.nodeKey  = key;
        el.textContent = name;
        el.title = desc || name;

        el.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('application/emos-node', JSON.stringify({ type, key, name }));
            e.dataTransfer.effectAllowed = 'copy';
        });
        return el;
    }

    // ═══════════════════════════════════════════════════════════════
    // EVENTS
    // ═══════════════════════════════════════════════════════════════
    function bindEvents() {
        // Drop on canvas
        canvasContainer.addEventListener('dragover', e => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; });
        canvasContainer.addEventListener('drop', onCanvasDrop);

        // Pan & Zoom
        canvasContainer.addEventListener('mousedown', onCanvasMouseDown);
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
        canvasContainer.addEventListener('wheel', onWheel, { passive: false });

        // Context menu
        canvasContainer.addEventListener('contextmenu', onContextMenu);
        document.addEventListener('click', () => contextMenu.style.display = 'none');

        // Keyboard
        document.addEventListener('keydown', onKeyDown);

        // Toolbar
        processBtn.addEventListener('click', runPipeline);
        cancelBtn.addEventListener('click', cancelPipeline);
    }

    async function cancelPipeline() {
        cancelFlag = true;
        const backendUrl = window.EMOS_BACKEND_BASE_URL || 'http://localhost:5001';

        // Tell the backend to cancel the active IU (e.g. send cancel to MatterGen Docker)
        if (activeRunId) {
            try {
                await fetch(`${backendUrl}/api/node/cancel/${activeRunId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });
                console.log(`Cancel sent for run ${activeRunId}`);
            } catch (err) {
                console.warn('Cancel request failed:', err);
            }
        }

        // Also abort the SSE fetch to stop receiving events immediately
        if (activeAbortController) activeAbortController.abort();
    }

    // ── Drop → create node ───────────────────────────────────────
    function onCanvasDrop(e) {
        e.preventDefault();
        const raw = e.dataTransfer.getData('application/emos-node');
        if (!raw) return;
        const { type, key, name } = JSON.parse(raw);

        const rect = canvasContainer.getBoundingClientRect();
        const x = (e.clientX - rect.left - panX) / zoom;
        const y = (e.clientY - rect.top  - panY) / zoom;

        createNode(type, key, name, x, y);
    }

    // ── Pan ──────────────────────────────────────────────────────
    function onCanvasMouseDown(e) {
        // Middle mouse or Shift+Left = pan (always)
        if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
            isPanning = true;
            panStartX = e.clientX - panX;
            panStartY = e.clientY - panY;
            canvasContainer.style.cursor = 'grabbing';
            e.preventDefault();
            return;
        }
        // Left click on empty canvas / background = pan
        if (e.button === 0 && (e.target === canvasContainer || e.target === canvas)) {
            selectNode(null);
            isPanning = true;
            panStartX = e.clientX - panX;
            panStartY = e.clientY - panY;
            canvasContainer.style.cursor = 'grabbing';
            e.preventDefault();
            return;
        }
    }

    function onMouseMove(e) {
        if (isPanning) {
            panX = e.clientX - panStartX;
            panY = e.clientY - panStartY;
            applyTransform();
            return;
        }

        if (dragNode) {
            const x = (e.clientX - canvasContainer.getBoundingClientRect().left - panX) / zoom - dragOffsetX;
            const y = (e.clientY - canvasContainer.getBoundingClientRect().top  - panY) / zoom - dragOffsetY;
            dragNode.x = Math.max(0, x);
            dragNode.y = Math.max(0, y);
            positionNodeEl(dragNode);
            updateWires();
            return;
        }

        if (resizeNode) {
            const dx = (e.clientX - resizeStartX) / zoom;
            const dy = (e.clientY - resizeStartY) / zoom;
            const newW = Math.max(200, resizeStartW + dx);
            const newH = Math.max(100, resizeStartH + dy);
            resizeNode.el.style.width  = newW + 'px';
            resizeNode.el.style.height = newH + 'px';
            resizeNode.width  = newW;
            resizeNode.height = newH;
            // If this is a CIF viewer node, resize the 3Dmol container to fill available space
            if (resizeNode.key === 'cif_viewer') {
                const cifContainer = resizeNode.el.querySelector('.ne-cif-viewer-container');
                if (cifContainer) {
                    // Compute available height: total node height minus header, progress, controls, footer, padding
                    const header = resizeNode.el.querySelector('.ne-node-header');
                    const controls = resizeNode.el.querySelector('.ne-cif-viewer-controls');
                    const footer = resizeNode.el.querySelector('.ne-node-footer');
                    const progress = resizeNode.el.querySelector('.ne-node-progress');
                    const usedH = (header ? header.offsetHeight : 0) +
                                  (progress ? progress.offsetHeight : 0) +
                                  (controls ? controls.offsetHeight + 4 : 0) +
                                  (footer ? footer.offsetHeight : 0) + 24; // padding
                    const viewerH = Math.max(100, newH - usedH);
                    cifContainer.style.height = viewerH + 'px';
                }
            }
            updateWires();
            return;
        }

        if (wiringFrom && tempWirePath) {
            const rect = canvasContainer.getBoundingClientRect();
            const mx = (e.clientX - rect.left - panX) / zoom;
            const my = (e.clientY - rect.top  - panY) / zoom;
            const portPos = getPortWorldPos(wiringFrom.nodeId, wiringFrom.portKey, wiringFrom.isOutput);
            if (wiringFrom.isOutput) {
                tempWirePath.setAttribute('d', bezierPath(portPos.x, portPos.y, mx, my));
            } else {
                tempWirePath.setAttribute('d', bezierPath(mx, my, portPos.x, portPos.y));
            }
        }
    }

    function onMouseUp(e) {
        if (isPanning) {
            isPanning = false;
            canvasContainer.style.cursor = '';
        }
        if (dragNode) {
            dragNode = null;
        }
        if (resizeNode) {
            // If it's a CIF viewer, re-render the 3Dmol viewer at the new size
            if (resizeNode.key === 'cif_viewer') {
                refreshCIFViewer(resizeNode);
            }
            resizeNode = null;
        }
        if (wiringFrom) {
            // If we didn't land on a port, cancel wiring
            cancelWiring();
        }
    }

    // ── Zoom ─────────────────────────────────────────────────────
    function onWheel(e) {
        e.preventDefault();
        const rect = canvasContainer.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        const oldZoom = zoom;
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        zoom = Math.min(3, Math.max(0.2, zoom * delta));

        // Keep the point under cursor fixed
        panX = mx - (mx - panX) * (zoom / oldZoom);
        panY = my - (my - panY) * (zoom / oldZoom);

        applyTransform();
    }

    function applyTransform() {
        canvas.style.transform   = `translate(${panX}px, ${panY}px) scale(${zoom})`;
        wiresSvg.style.transform = `translate(${panX}px, ${panY}px) scale(${zoom})`;
        // Scale dot grid
        const size = 24 * zoom;
        canvasContainer.style.backgroundSize = `${size}px ${size}px`;
        canvasContainer.style.backgroundPosition = `${panX}px ${panY}px`;
        zoomText.textContent = `${Math.round(zoom * 100)}%`;
    }

    // ── Context menu ─────────────────────────────────────────────
    function onContextMenu(e) {
        e.preventDefault();
        const nodeEl = e.target.closest('.ne-node');
        if (!nodeEl) return;
        selectNode(nodeEl.dataset.nodeId);
        contextMenu.style.left = e.clientX + 'px';
        contextMenu.style.top  = e.clientY + 'px';
        contextMenu.style.display = 'block';
        contextMenu.onclick = () => {
            if (selectedNodeId) deleteNode(selectedNodeId);
            contextMenu.style.display = 'none';
        };
    }

    // ── Keyboard ─────────────────────────────────────────────────
    function onKeyDown(e) {
        if (e.key === 'Delete' || e.key === 'Backspace') {
            // Don't delete when typing in inputs
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
            if (selectedNodeId) {
                deleteNode(selectedNodeId);
                e.preventDefault();
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // NODE CREATION
    // ═══════════════════════════════════════════════════════════════
    function createNode(type, key, name, x, y) {
        const id = 'node_' + (nextNodeId++);
        // Determine schema; viewers and utility nodes use their key as schema key
        const schemaKey = (type === 'viewer' || type === 'utility') ? key : type;
        const schema = NODE_SCHEMAS[schemaKey];
        if (!schema) { console.error('Unknown schema:', schemaKey); return; }

        const node = {
            id, type, key, name,
            x, y,
            width: 240,
            height: null, // auto
            inputs: schema.inputs.map(p => ({ ...p })),
            outputs: schema.outputs.map(p => ({ ...p })),
            data: null,   // output data after execution
            el: null,
        };

        nodes[id] = node;
        const el = renderNode(node);
        node.el = el;
        canvas.appendChild(el);
        positionNodeEl(node);
        selectNode(id);
        // Populate property fields async after element is in the DOM
        if (node.type === 'database' || node.type === 'generator') {
            populateNodePropertyFields(node);
        }
        return node;
    }

    function renderNode(node) {
        const el = document.createElement('div');
        el.className = 'ne-node';
        el.dataset.nodeId = node.id;
        el.dataset.type   = node.type;
        el.style.width    = node.width + 'px';

        // Icon
        const iconByKey  = { cif_viewer: '👁️', text_viewer: '📝', filter: '⛗️', lambda: 'λ' };
        const iconByType = { database: '📁', generator: '⚙️', predictor: '🔮', viewer: '👁️', utility: '🔧' };
        const nodeIcon = iconByKey[node.key] || iconByType[node.type] || '📦';

        // Header
        const header = document.createElement('div');
        header.className = 'ne-node-header';
        header.innerHTML = `<span class="ne-node-icon">${nodeIcon}</span><span class="ne-node-title">${node.name}</span>`;
        // X close button
        const closeBtn = document.createElement('span');
        closeBtn.className = 'ne-node-close';
        closeBtn.textContent = '×';
        closeBtn.title = 'Delete node';
        closeBtn.addEventListener('mousedown', (e) => { e.stopPropagation(); });
        closeBtn.addEventListener('click', (e) => { e.stopPropagation(); deleteNode(node.id); });
        header.appendChild(closeBtn);
        header.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;
            e.stopPropagation();
            selectNode(node.id);
            dragNode = node;
            const rect = canvasContainer.getBoundingClientRect();
            dragOffsetX = (e.clientX - rect.left - panX) / zoom - node.x;
            dragOffsetY = (e.clientY - rect.top  - panY) / zoom - node.y;
        });
        el.appendChild(header);

        // Progress bar
        const progress = document.createElement('div');
        progress.className = 'ne-node-progress';
        progress.innerHTML = '<div class="ne-node-progress-bar"></div>';
        el.appendChild(progress);

        // Body — input fields
        const body = document.createElement('div');
        body.className = 'ne-node-body';
        body.innerHTML = buildNodeBodyHTML(node);
        // Stop mousedown propagation on inputs so node isn't dragged
        body.addEventListener('mousedown', e => e.stopPropagation());
        // Handle utility button actions inside the node body
        body.addEventListener('click', e => {
            const action = e.target.dataset && e.target.dataset.action;
            if (!action) return;
            if (action === 'add-filter-rule') {
                addFilterRule(node.id);
            } else if (action === 'remove-filter-rule') {
                e.target.closest('.ne-filter-row').remove();
            }
        });
        el.appendChild(body);

        // Log area
        const log = document.createElement('div');
        log.className = 'ne-node-log';
        log.id = `node-log-${node.id}`;
        body.appendChild(log);

        // Footer (ports)
        const footer = document.createElement('div');
        footer.className = 'ne-node-footer';

        // Input ports (left edge — absolutely positioned)
        for (let i = 0; i < node.inputs.length; i++) {
            const p = node.inputs[i];
            const pw = document.createElement('div');
            pw.className = 'ne-port-wrap ne-port-input';
            pw.style.top = `calc(50% + ${(i - (node.inputs.length - 1) / 2) * 24}px)`;
            const port = document.createElement('div');
            port.className = 'ne-port';
            port.dataset.portKey  = p.key;
            port.dataset.portData = p.type;
            port.dataset.portDir  = 'input';
            port.addEventListener('mousedown', (e) => { e.stopPropagation(); startWiring(node.id, p.key, p.type, false); });
            port.addEventListener('mouseup',   (e) => { e.stopPropagation(); endWiring(node.id, p.key, p.type, false); });
            const label = document.createElement('span');
            label.className = 'ne-port-label ne-port-label-input';
            label.textContent = p.label;
            pw.appendChild(port);
            pw.appendChild(label);
            el.appendChild(pw);
        }

        // Output ports (right edge — absolutely positioned)
        for (let i = 0; i < node.outputs.length; i++) {
            const p = node.outputs[i];
            const pw = document.createElement('div');
            pw.className = 'ne-port-wrap ne-port-output';
            pw.style.top = `calc(50% + ${(i - (node.outputs.length - 1) / 2) * 24}px)`;
            const port = document.createElement('div');
            port.className = 'ne-port';
            port.dataset.portKey  = p.key;
            port.dataset.portData = p.type;
            port.dataset.portDir  = 'output';
            port.addEventListener('mousedown', (e) => { e.stopPropagation(); startWiring(node.id, p.key, p.type, true); });
            port.addEventListener('mouseup',   (e) => { e.stopPropagation(); endWiring(node.id, p.key, p.type, true); });
            const label = document.createElement('span');
            label.className = 'ne-port-label ne-port-label-output';
            label.textContent = p.label;
            pw.appendChild(label);
            pw.appendChild(port);
            el.appendChild(pw);
        }

        // Keep a minimal footer for spacing
        footer.appendChild(document.createTextNode(''));
        el.appendChild(footer);

        // Resize handle
        const rh = document.createElement('div');
        rh.className = 'ne-resize-handle';
        rh.addEventListener('mousedown', (e) => {
            e.stopPropagation();
            resizeNode = node;
            resizeStartX = e.clientX;
            resizeStartY = e.clientY;
            resizeStartW = node.el.offsetWidth;
            resizeStartH = node.el.offsetHeight;
        });
        el.appendChild(rh);

        return el;
    }

    // ── Build body HTML for IU nodes ─────────────────────────────
    function buildNodeBodyHTML(node) {
        if (node.key === 'cif_viewer')  return buildCIFViewerBody(node);
        if (node.key === 'text_viewer') return buildTextViewerBody(node);
        if (node.key === 'filter')      return buildFilterBody(node);
        if (node.key === 'lambda')      return buildLambdaBody(node);

        // For IU nodes, auto-generate fields from property_mappings
        let html = '';

        if (node.type === 'database') {
            html += `<label>Query<input type="text" data-field="target_compositions" placeholder="e.g. Fe, Al2O3"></label>`;
            html += `<label>Batch Size<input type="number" data-field="batch_size" value="10" min="1" max="100"></label>`;
            // Placeholder populated asynchronously after the node is in the DOM
            html += `<div id="prop-fields-${node.id}"><p style="color:#666; font-size:10px;">Loading filters…</p></div>`;
        } else if (node.type === 'generator') {
            html += `<label>Batch Size<input type="number" data-field="batch_size" value="10" min="1" max="1000" step="1"></label>`;
            // Placeholder populated asynchronously after the node is in the DOM
            html += `<div id="prop-fields-${node.id}"></div>`;
        } else if (node.type === 'predictor') {
            // Predictors generally need no user input beyond the CIF from wires
            html += `<p style="color:#888; font-size:10px;">Connect a CIF source to predict properties.</p>`;
        }

        return html;
    }

    // Fetch the per-source property mapping + common definitions and inject fields.
    async function populateNodePropertyFields(node) {
        const container = document.getElementById(`prop-fields-${node.id}`);
        if (!container) return;

        const sourceType = node.type === 'database' ? 'databases' : 'generators';
        const url = `./Information_Units/property_mappings/sources/${sourceType}/${node.key}.json`;

        let sourceMapping, commonProperties;
        try {
            [sourceMapping, commonProperties] = await Promise.all([
                fetch(url).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
                fetch('./Information_Units/property_mappings/common_properties.json').then(r => r.json()).catch(() => ({ properties: {} })),
            ]);
        } catch (e) {
            container.innerHTML = `<p style="color:#666; font-size:10px;">No property filters available.</p>`;
            return;
        }

        const props  = sourceMapping.properties || {};
        const common = commonProperties.properties || {};

        if (node.type === 'database') {
            container.innerHTML = buildPropertyFilterHTML(props, common);
        } else if (node.type === 'generator') {
            container.innerHTML = buildGeneratorPropertyHTML(props, common);
        }
    }

    function buildPropertyFilterHTML(props, common) {
        const defs = Object.entries(props).filter(([, cfg]) => cfg.retrievable !== false);
        if (defs.length === 0) return '';

        let inner = '';
        for (const [uiKey, cfg] of defs) {
            const name     = cfg.name || uiKey;
            const commonDef = common[uiKey] || {};
            const unit     = commonDef.unit        ? ` (${commonDef.unit})`        : '';
            const type     = commonDef.type        || 'string';
            const desc     = commonDef.description || uiKey;
            const label    = uiKey.replace(/_/g, ' ');

            if (cfg.range_support && (type === 'float' || type === 'integer')) {
                inner += `<label title="${desc}">${label}${unit}
                    <span style="display:flex; gap:4px;">
                        <input type="number" data-field="filter_${name}_min" placeholder="min" step="any" style="flex:1;">
                        <input type="number" data-field="filter_${name}_max" placeholder="max" step="any" style="flex:1;">
                    </span>
                </label>`;
            } else {
                inner += `<label title="${desc}">${label}${unit}
                    <input type="text" data-field="filter_${name}" placeholder="${name}">
                </label>`;
            }
        }
        return `<details style="margin-top:6px;">
            <summary style="cursor:pointer; color:#4fc3f7; font-size:10px;">Property Filters</summary>
            <div style="padding-top:4px;">${inner}</div>
        </details>`;
    }

    function buildGeneratorPropertyHTML(props, common) {
        let html = '';
        for (const [uiKey, cfg] of Object.entries(props)) {
            const name     = cfg.name || uiKey;
            const commonDef = common[uiKey] || {};
            const unit     = commonDef.unit        ? ` (${commonDef.unit})`        : '';
            const type     = commonDef.type        || 'float';
            const desc     = commonDef.description || uiKey.replace(/_/g, ' ');

            if (type === 'string') {
                html += `<label title="${desc}">${desc}${unit}
                    <input type="text" data-field="prop_${name}" placeholder="e.g. Si-O">
                </label>`;
            } else if (type === 'integer') {
                html += `<label title="${desc}">${desc}${unit}
                    <input type="number" data-field="prop_${name}" step="1" min="0">
                </label>`;
            } else {
                html += `<label title="${desc}">${desc}${unit}
                    <input type="number" data-field="prop_${name}" step="any">
                </label>`;
            }
        }
        return html;
    }

    function buildCIFViewerBody(node) {
        return `
            <div class="ne-cif-viewer-controls">
                <select class="ne-cif-select" data-field="cif_select"><option value="">No data</option></select>
            </div>
            <div class="ne-cif-viewer-container" id="cif-viewer-${node.id}"></div>
        `;
    }

    function buildTextViewerBody(node) {
        return `<div class="ne-text-viewer-content" id="text-viewer-${node.id}">No data yet.</div>`;
    }

    function buildFilterBody(node) {
        return `
            <div class="ne-filter-rules" id="filter-rules-${node.id}">
                <div class="ne-filter-row">
                    <select class="ne-filter-prop-select"><option value="">— connect predictor —</option></select>
                    <select class="ne-filter-op-select">
                        <option value="=">=</option>
                        <option value="!=">&ne;</option>
                        <option value=">">&gt;</option>
                        <option value="<">&lt;</option>
                        <option value=">=">&ge;</option>
                        <option value="<=">&le;</option>
                    </select>
                    <input type="text" class="ne-filter-value" placeholder="threshold">
                    <button class="ne-filter-remove-btn" data-action="remove-filter-rule" title="Remove">&times;</button>
                </div>
            </div>
            <button class="ne-add-filter-btn" data-action="add-filter-rule" data-node-id="${node.id}">+ Add filter</button>
        `;
    }

    function addFilterRule(nodeId) {
        const node = nodes[nodeId];
        if (!node) return;
        const container = node.el.querySelector(`#filter-rules-${nodeId}`);
        if (!container) return;
        const propOptions = getFilterPropOptions(nodeId);
        const row = document.createElement('div');
        row.className = 'ne-filter-row';
        row.innerHTML = `
            <select class="ne-filter-prop-select">
                ${propOptions.length > 0
                    ? propOptions.map(p => `<option value="${p.name}">${p.label}</option>`).join('')
                    : '<option value="">— connect predictor —</option>'}
            </select>
            <select class="ne-filter-op-select">
                <option value="=">=</option>
                <option value="!=">&ne;</option>
                <option value=">">&gt;</option>
                <option value="<">&lt;</option>
                <option value=">=">&ge;</option>
                <option value="<=">&le;</option>
            </select>
            <input type="text" class="ne-filter-value" placeholder="threshold">
            <button class="ne-filter-remove-btn" data-action="remove-filter-rule" title="Remove">&times;</button>
        `;
        container.appendChild(row);
    }

    function getFilterPropOptions(nodeId) {
        const sourceWire = wires.find(w => w.toNode === nodeId && w.toPort === 'result_in');
        if (!sourceWire) return [];
        const sourceNode = nodes[sourceWire.fromNode];
        if (!sourceNode) return [];
        const props = predictorPropsMap[sourceNode.key] || {};
        return Object.entries(props).map(([name, label]) => ({ name, label: label || name }));
    }

    function refreshFilterNodeDropdowns(nodeId) {
        const node = nodes[nodeId];
        if (!node || node.key !== 'filter') return;
        const propOptions = getFilterPropOptions(nodeId);
        const rows = node.el.querySelectorAll('.ne-filter-row');
        rows.forEach(row => {
            const select = row.querySelector('.ne-filter-prop-select');
            if (!select) return;
            const currentVal = select.value;
            if (propOptions.length > 0) {
                select.innerHTML = propOptions.map(p => `<option value="${p.name}">${p.label}</option>`).join('');
                if (propOptions.find(p => p.name === currentVal)) select.value = currentVal;
            } else {
                select.innerHTML = '<option value="">— connect predictor —</option>';
            }
        });
    }

    function refreshAllFilterNodes() {
        for (const node of Object.values(nodes)) {
            if (node.key === 'filter') refreshFilterNodeDropdowns(node.id);
        }
    }

    function buildLambdaBody(node) {
        const defaultCode =
`# Available variables:
#   cif_list  - list[str] of CIF strings
#   results   - predictor result dict {source, results: [...]}
#
# Set output variables before the script ends:
#   output_cifs    - list[str] of CIF strings to pass forward
#   output_results - results dict to pass forward

output_cifs = cif_list
output_results = results`;
        return `
            <textarea class="ne-lambda-code" data-field="code" spellcheck="false">${defaultCode}</textarea>
            <p class="ne-lambda-warning">⚠ Code runs on the server. Use responsibly.</p>
        `;
    }

    // ── Position helper ──────────────────────────────────────────
    function positionNodeEl(node) {
        node.el.style.left = node.x + 'px';
        node.el.style.top  = node.y + 'px';
    }

    // ── Selection ────────────────────────────────────────────────
    function selectNode(id) {
        if (selectedNodeId && nodes[selectedNodeId]) {
            nodes[selectedNodeId].el.classList.remove('selected');
        }
        selectedNodeId = id;
        if (id && nodes[id]) {
            nodes[id].el.classList.add('selected');
        }
    }

    // ── Delete node ──────────────────────────────────────────────
    function deleteNode(id) {
        const node = nodes[id];
        if (!node) return;
        // Remove connected wires
        wires = wires.filter(w => {
            if (w.fromNode === id || w.toNode === id) {
                removeWireEl(w.id);
                return false;
            }
            return true;
        });
        node.el.remove();
        delete nodes[id];
        if (selectedNodeId === id) selectedNodeId = null;
        updatePortConnectedStates();
        refreshAllFilterNodes();
    }

    // ═══════════════════════════════════════════════════════════════
    // WIRING
    // ═══════════════════════════════════════════════════════════════
    function startWiring(nodeId, portKey, portType, isOutput) {
        wiringFrom = { nodeId, portKey, portType, isOutput };
        // Create temp wire
        tempWirePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        tempWirePath.classList.add('ne-wire-temp');
        wiresSvg.appendChild(tempWirePath);
    }

    function endWiring(nodeId, portKey, portType, isOutput) {
        if (!wiringFrom) return;
        // Must connect output → input (or input → output)
        if (wiringFrom.isOutput === isOutput) { cancelWiring(); return; }
        if (wiringFrom.nodeId === nodeId) { cancelWiring(); return; }

        const fromIsOutput = wiringFrom.isOutput;
        const from = fromIsOutput ? wiringFrom : { nodeId, portKey, portType, isOutput };
        const to   = fromIsOutput ? { nodeId, portKey, portType, isOutput } : wiringFrom;

        // Compatibility check
        const outType = from.portType;
        const inType  = to.portType;
        if (!PORT_COMPAT[outType] || !PORT_COMPAT[outType].includes(inType)) {
            cancelWiring();
            return;
        }

        // Remove existing wire to this input port (replace connection)
        wires = wires.filter(w => {
            if (w.toNode === to.nodeId && w.toPort === to.portKey) {
                removeWireEl(w.id);
                return false;
            }
            return true;
        });

        // Add wire
        const wire = {
            id: 'wire_' + (nextWireId++),
            fromNode: from.nodeId,
            fromPort: from.portKey,
            toNode:   to.nodeId,
            toPort:   to.portKey,
            type:     outType,
        };
        wires.push(wire);

        cancelWiring();
        updateWires();
        updatePortConnectedStates();
    }

    function cancelWiring() {
        wiringFrom = null;
        if (tempWirePath) { tempWirePath.remove(); tempWirePath = null; }
    }

    // ── Wire rendering ───────────────────────────────────────────
    function updateWires() {
        // Remove old rendered wires
        wiresSvg.querySelectorAll('.ne-wire').forEach(el => el.remove());

        for (const w of wires) {
            const fromPos = getPortWorldPos(w.fromNode, w.fromPort, true);
            const toPos   = getPortWorldPos(w.toNode,   w.toPort,   false);
            if (!fromPos || !toPos) continue;

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.classList.add('ne-wire');
            path.dataset.wireId   = w.id;
            path.dataset.wireType = w.type;
            path.setAttribute('d', bezierPath(fromPos.x, fromPos.y, toPos.x, toPos.y));
            path.style.pointerEvents = 'stroke';
            path.addEventListener('click', (e) => {
                e.stopPropagation();
                // Delete wire on click
                wires = wires.filter(ww => ww.id !== w.id);
                updateWires();
                updatePortConnectedStates();
                refreshAllFilterNodes();
            });
            wiresSvg.appendChild(path);
        }
        refreshAllFilterNodes();
    }

    function getPortWorldPos(nodeId, portKey, isOutput) {
        const node = nodes[nodeId];
        if (!node || !node.el) return null;
        const portEl = node.el.querySelector(`.ne-port[data-port-key="${portKey}"][data-port-dir="${isOutput ? 'output' : 'input'}"]`);
        if (!portEl) return null;

        // Calculate position in canvas coordinate space using node position + DOM offsets.
        // This avoids getBoundingClientRect() which includes CSS transform/zoom and
        // would cause double-correction when we divide by zoom.
        const portWrap = portEl.closest('.ne-port-wrap');
        if (portWrap) {
            // Absolutely positioned port wraps: use their offset relative to the node
            const x = node.x + portWrap.offsetLeft + portEl.offsetLeft + portEl.offsetWidth / 2;
            const y = node.y + portWrap.offsetTop  + portEl.offsetTop  + portEl.offsetHeight / 2;
            return { x, y };
        }

        // Fallback: walk up offsetParent chain within the node element
        let offsetX = portEl.offsetWidth / 2;
        let offsetY = portEl.offsetHeight / 2;
        let el = portEl;
        while (el && el !== node.el) {
            offsetX += el.offsetLeft;
            offsetY += el.offsetTop;
            el = el.offsetParent;
        }
        return { x: node.x + offsetX, y: node.y + offsetY };
    }

    function bezierPath(x1, y1, x2, y2) {
        const dx = Math.abs(x2 - x1) * 0.5;
        return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
    }

    function removeWireEl(wireId) {
        const el = wiresSvg.querySelector(`[data-wire-id="${wireId}"]`);
        if (el) el.remove();
    }

    function updatePortConnectedStates() {
        // Reset all ports
        for (const node of Object.values(nodes)) {
            node.el.querySelectorAll('.ne-port').forEach(p => p.classList.remove('connected'));
        }
        // Set connected ports
        for (const w of wires) {
            const fromNode = nodes[w.fromNode];
            const toNode   = nodes[w.toNode];
            if (fromNode) {
                const p = fromNode.el.querySelector(`.ne-port[data-port-key="${w.fromPort}"][data-port-dir="output"]`);
                if (p) p.classList.add('connected');
            }
            if (toNode) {
                const p = toNode.el.querySelector(`.ne-port[data-port-key="${w.toPort}"][data-port-dir="input"]`);
                if (p) p.classList.add('connected');
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // COLLECT NODE INPUTS
    // ═══════════════════════════════════════════════════════════════
    function collectNodeInputs(node) {
        const inputs = {};
        const fields = node.el.querySelectorAll('[data-field]');
        fields.forEach(el => {
            const key = el.dataset.field;
            if (el.type === 'checkbox') {
                inputs[key] = el.checked;
            } else if (el.type === 'number') {
                if (el.value !== '') inputs[key] = parseFloat(el.value);
            } else {
                if (el.value !== '') inputs[key] = el.value;
            }
        });
        return inputs;
    }

    // ═══════════════════════════════════════════════════════════════
    // PIPELINE EXECUTION
    // ═══════════════════════════════════════════════════════════════
    async function runPipeline() {
        if (isRunning) return;

        // Topological sort
        const sorted = topologicalSort();
        if (!sorted) {
            setStatus('Error: cycle detected in graph');
            return;
        }
        if (sorted.length === 0) {
            setStatus('No nodes to process');
            return;
        }

        isRunning  = true;
        cancelFlag = false;
        processBtn.disabled = true;
        cancelBtn.style.display = '';
        setStatus('Running pipeline...');

        // Clear all node states
        for (const n of Object.values(nodes)) {
            setNodeState(n.id, '');
            n.data = null;
            n.portData = null;
            clearNodeLog(n.id);
        }

        // Mark all as waiting
        for (const nid of sorted) {
            setNodeState(nid, 'waiting');
        }

        const backendUrl = window.EMOS_BACKEND_BASE_URL || 'http://localhost:5001';

        for (const nodeId of sorted) {
            if (cancelFlag) {
                setNodeState(nodeId, '');
                setStatus('Cancelled');
                break;
            }

            const node = nodes[nodeId];
            if (!node) continue;

            // Skip nodes with no wire connections at all
            const isConnected = wires.some(w => w.fromNode === nodeId || w.toNode === nodeId);
            if (!isConnected) continue;

            // Viewers don't execute on the backend — they just display data from upstream
            if (node.type === 'viewer') {
                displayViewerData(node);
                setNodeState(nodeId, 'done');
                continue;
            }

            // Filter nodes execute client-side
            if (node.key === 'filter') {
                setNodeState(nodeId, 'running');
                try {
                    executeFilterNode(node);
                    setNodeState(nodeId, 'done');
                    setNodeProgress(nodeId, 100);
                } catch (err) {
                    setNodeState(nodeId, 'error');
                    addNodeLog(nodeId, `Error: ${err.message}`, 'error');
                    setStatus(`Error at ${node.name}: ${err.message}`);
                    break;
                }
                continue;
            }

            setNodeState(nodeId, 'running');
            addNodeLog(nodeId, `Starting ${node.name}...`, 'info');
            setStatus(`Running: ${node.name}`);

            try {
                // Gather upstream data from incoming wires
                const upstreamData = getUpstreamData(nodeId);

                // Collect user inputs from the node's UI fields
                const userInputs = collectNodeInputs(node);

                const payload = {
                    type: node.type,
                    key:  node.key,
                    inputs: userInputs,
                    upstream: upstreamData,
                };

                // Execute via SSE
                const result = await executeNodeSSE(backendUrl, nodeId, payload);

                // Lambda and other multi-output utility nodes return {cif_out, result_out}
                if (node.key === 'lambda') {
                    node.portData = result;
                } else {
                    node.data = result;
                }
                setNodeState(nodeId, 'done');
                addNodeLog(nodeId, 'Done ✓', 'success');
                setNodeProgress(nodeId, 100);

            } catch (err) {
                if (cancelFlag) {
                    setNodeState(nodeId, '');
                    setStatus('Cancelled');
                } else {
                    setNodeState(nodeId, 'error');
                    addNodeLog(nodeId, `Error: ${err.message}`, 'error');
                    setStatus(`Error at ${node.name}: ${err.message}`);
                }
                break; // Stop on first error
            }
        }

        // After pipeline: trigger viewer display for downstream viewers
        for (const nodeId of sorted) {
            const node = nodes[nodeId];
            if (node && node.type === 'viewer' && wires.some(w => w.toNode === nodeId)) {
                displayViewerData(node);
            }
        }

        isRunning = false;
        processBtn.disabled = false;
        cancelBtn.style.display = 'none';
        if (!cancelFlag) setStatus('Pipeline complete');
    }

    function getUpstreamData(nodeId) {
        const data = {};
        for (const w of wires) {
            if (w.toNode === nodeId) {
                const fromNode = nodes[w.fromNode];
                if (fromNode) {
                    // Multi-output nodes store per-port data in portData
                    if (fromNode.portData && w.fromPort in fromNode.portData) {
                        data[w.toPort] = fromNode.portData[w.fromPort];
                    } else if (fromNode.data != null) {
                        data[w.toPort] = fromNode.data;
                    }
                }
            }
        }
        return data;
    }

    function executeNodeSSE(backendUrl, nodeId, payload) {
        return new Promise((resolve, reject) => {
            const ctrl = new AbortController();
            activeAbortController = ctrl;
            activeRunId = null;  // Will be set from the first SSE event

            fetch(`${backendUrl}/api/node/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal: ctrl.signal,
            }).then(response => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let result = null;

                function read() {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            activeAbortController = null;
                            activeRunId = null;
                            if (result != null) resolve(result);
                            else reject(new Error('No result received'));
                            return;
                        }
                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop(); // keep incomplete line

                        let currentEvent = 'log';
                        for (const line of lines) {
                            if (line.startsWith('event: ')) {
                                currentEvent = line.slice(7).trim();
                                continue;
                            }
                            if (line.startsWith('data: ')) {
                                const dataStr = line.slice(6);
                                try {
                                    const data = JSON.parse(dataStr);
                                    if (currentEvent === 'run_id') {
                                        // Capture the backend run_id for cancellation
                                        activeRunId = data.run_id;
                                    } else if (currentEvent === 'log') {
                                        addNodeLog(nodeId, data.message || JSON.stringify(data), data.level || 'info');
                                    } else if (currentEvent === 'progress') {
                                        const pct = Math.round((data.progress || 0) * 100);
                                        setNodeProgress(nodeId, pct);
                                        if (data.message) addNodeLog(nodeId, data.message, 'info');
                                    } else if (currentEvent === 'result') {
                                        result = data;
                                    } else if (currentEvent === 'error') {
                                        reject(new Error(data.message || 'Unknown error'));
                                        reader.cancel();
                                        return;
                                    }
                                } catch (e) {
                                    // non-JSON data line — ignore
                                }
                                currentEvent = 'log'; // reset
                            }
                        }
                        read();
                    }).catch(err => {
                        activeAbortController = null;
                        activeRunId = null;
                        if (err.name === 'AbortError') reject(new Error('Cancelled'));
                        else reject(err);
                    });
                }
                read();
            }).catch(err => {
                activeAbortController = null;
                activeRunId = null;
                reject(err);
            });
        });
    }

    // ═══════════════════════════════════════════════════════════════
    // FILTER NODE (client-side execution)
    // ═══════════════════════════════════════════════════════════════
    function executeFilterNode(node) {
        const upstream  = getUpstreamData(node.id);
        const cifArray  = upstream['cif_in'];
        const resultData = upstream['result_in'];

        const rules       = collectFilterRules(node);
        const cifIn       = Array.isArray(cifArray) ? cifArray : [];
        const resultsList = (resultData && Array.isArray(resultData.results)) ? resultData.results : [];

        const filteredCifs    = [];
        const filteredResults = [];
        const total = Math.max(cifIn.length, resultsList.length);

        for (let i = 0; i < total; i++) {
            const cif  = cifIn[i]  ?? null;
            const res  = resultsList[i] ?? null;
            const props = res ? (res.properties || {}) : {};

            if (rules.length === 0 || rules.every(r => evaluateRule(props, r))) {
                if (cif  !== null) filteredCifs.push(cif);
                if (res  !== null) filteredResults.push({ ...res, index: filteredCifs.length - 1 });
            }
        }

        node.portData = {
            cif_out:    filteredCifs,
            result_out: { source: resultData?.source || 'filter', results: filteredResults },
        };

        const kept = filteredCifs.length;
        addNodeLog(node.id, `Kept ${kept} / ${total} structure(s)`, kept > 0 ? 'success' : 'warning');
    }

    function collectFilterRules(node) {
        const rules = [];
        node.el.querySelectorAll('.ne-filter-row').forEach(row => {
            const prop = row.querySelector('.ne-filter-prop-select')?.value;
            const op   = row.querySelector('.ne-filter-op-select')?.value;
            const val  = row.querySelector('.ne-filter-value')?.value?.trim();
            if (prop && op && val !== '' && val !== undefined) {
                rules.push({ prop, op, val });
            }
        });
        return rules;
    }

    function evaluateRule(properties, rule) {
        const raw = properties[rule.prop];
        if (raw === undefined || raw === null) return false;
        const numVal   = parseFloat(raw);
        const numThresh = parseFloat(rule.val);
        switch (rule.op) {
            case '=':  return (isFinite(numVal) && isFinite(numThresh))
                           ? numVal === numThresh
                           : String(raw) === rule.val;
            case '!=': return (isFinite(numVal) && isFinite(numThresh))
                           ? numVal !== numThresh
                           : String(raw) !== rule.val;
            case '>':  return isFinite(numVal) && isFinite(numThresh) && numVal > numThresh;
            case '<':  return isFinite(numVal) && isFinite(numThresh) && numVal < numThresh;
            case '>=': return isFinite(numVal) && isFinite(numThresh) && numVal >= numThresh;
            case '<=': return isFinite(numVal) && isFinite(numThresh) && numVal <= numThresh;
            default:   return false;
        }
    }

    // ── Topological sort (Kahn's algorithm) ──────────────────────
    function topologicalSort() {
        const nodeIds = Object.keys(nodes);
        const inDegree = {};
        const adj = {};

        for (const id of nodeIds) { inDegree[id] = 0; adj[id] = []; }
        for (const w of wires) {
            if (adj[w.fromNode] && inDegree[w.toNode] !== undefined) {
                adj[w.fromNode].push(w.toNode);
                inDegree[w.toNode]++;
            }
        }

        const queue = nodeIds.filter(id => inDegree[id] === 0);
        const sorted = [];

        while (queue.length > 0) {
            const n = queue.shift();
            sorted.push(n);
            for (const m of (adj[n] || [])) {
                inDegree[m]--;
                if (inDegree[m] === 0) queue.push(m);
            }
        }

        if (sorted.length !== nodeIds.length) return null; // cycle
        return sorted;
    }

    // ── Visual state helpers ─────────────────────────────────────
    function setNodeState(nodeId, state) {
        const node = nodes[nodeId];
        if (!node) return;
        node.el.classList.remove('state-waiting', 'state-running', 'state-done', 'state-error');
        if (state) node.el.classList.add('state-' + state);
    }

    function setNodeProgress(nodeId, pct) {
        const node = nodes[nodeId];
        if (!node) return;
        const bar = node.el.querySelector('.ne-node-progress-bar');
        if (bar) bar.style.width = pct + '%';
    }

    function addNodeLog(nodeId, message, level = 'info') {
        const logEl = document.getElementById(`node-log-${nodeId}`);
        if (!logEl) return;
        logEl.classList.add('visible');
        const entry = document.createElement('div');
        entry.className = `log-${level}`;
        entry.textContent = message;
        logEl.appendChild(entry);
        logEl.scrollTop = logEl.scrollHeight;
    }

    function clearNodeLog(nodeId) {
        const logEl = document.getElementById(`node-log-${nodeId}`);
        if (!logEl) return;
        logEl.innerHTML = '';
        logEl.classList.remove('visible');
        setNodeProgress(nodeId, 0);
    }

    function setStatus(msg) {
        statusText.textContent = msg;
    }

    // ═══════════════════════════════════════════════════════════════
    // VIEWER DISPLAY
    // ═══════════════════════════════════════════════════════════════
    function displayViewerData(node) {
        const upstreamData = getUpstreamData(node.id);
        // Get the first upstream value
        const dataKey = Object.keys(upstreamData)[0];
        const data = upstreamData[dataKey];

        if (data == null) {
            addNodeLog(node.id, 'No upstream data', 'warning');
            return;
        }

        if (node.key === 'cif_viewer') {
            displayCIFViewer(node, data);
        } else if (node.key === 'text_viewer') {
            displayTextViewer(node, data);
        }
        setNodeState(node.id, 'done');
    }

    function displayCIFViewer(node, data) {
        // data should be an array of CIF strings, or a single CIF string
        let cifArray = Array.isArray(data) ? data : [data];
        // Filter to only strings (could be results objects too)
        cifArray = cifArray.filter(d => typeof d === 'string');

        if (cifArray.length === 0) {
            addNodeLog(node.id, 'No CIF data received', 'warning');
            return;
        }

        // Populate dropdown
        const select = node.el.querySelector('.ne-cif-select');
        if (select) {
            select.innerHTML = '';
            cifArray.forEach((_, i) => {
                const opt = document.createElement('option');
                opt.value = i;
                opt.textContent = `Structure ${i + 1}`;
                select.appendChild(opt);
            });
            select.onchange = () => renderCIF(node.id, cifArray[parseInt(select.value)]);
        }

        // Render first structure
        renderCIF(node.id, cifArray[0]);
        addNodeLog(node.id, `Loaded ${cifArray.length} structure(s)`, 'success');
    }

    function renderCIF(nodeId, cifString) {
        const container = document.getElementById(`cif-viewer-${nodeId}`);
        if (!container || !cifString) return;

        // Clear previous viewer
        container.innerHTML = '';
        try {
            const viewer = $3Dmol.createViewer(container, {
                backgroundColor: '#0a0a1e',
                antialias: true,
            });
            viewer.addModel(cifString, 'cif');
            viewer.setStyle({}, { stick: { radius: 0.15 }, sphere: { scale: 0.3 } });
            viewer.addUnitCell();
            viewer.zoomTo();
            viewer.render();
        } catch (err) {
            container.innerHTML = `<p style="color:#e57373; padding:8px; font-size:10px;">3Dmol error: ${err.message}</p>`;
        }
    }

    function refreshCIFViewer(node) {
        // Re-render the current CIF in the viewer at the new container size
        const select = node.el.querySelector('.ne-cif-select');
        const container = document.getElementById(`cif-viewer-${node.id}`);
        if (!container) return;

        // Get the upstream CIF data to find the currently selected structure
        const upstreamData = getUpstreamData(node.id);
        const dataKey = Object.keys(upstreamData)[0];
        const data = upstreamData[dataKey];
        if (!data) return;

        let cifArray = Array.isArray(data) ? data : [data];
        cifArray = cifArray.filter(d => typeof d === 'string');
        if (cifArray.length === 0) return;

        const idx = select ? parseInt(select.value) || 0 : 0;
        const cifString = cifArray[idx] || cifArray[0];
        if (cifString) renderCIF(node.id, cifString);
    }

    function displayTextViewer(node, data) {
        const container = document.getElementById(`text-viewer-${node.id}`);
        if (!container) return;

        let text = '';
        if (typeof data === 'string') {
            text = data;
        } else if (Array.isArray(data)) {
            text = data.map((item, i) => {
                if (typeof item === 'string') return `--- Item ${i + 1} ---\n${item}`;
                return `--- Item ${i + 1} ---\n${JSON.stringify(item, null, 2)}`;
            }).join('\n\n');
        } else {
            text = JSON.stringify(data, null, 2);
        }

        container.textContent = text;
        addNodeLog(node.id, 'Data displayed', 'success');
    }

})();
