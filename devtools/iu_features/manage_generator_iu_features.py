#!/usr/bin/env python3
"""Interactive utility to add/remove generator IU features.

This script automates the frontend wiring needed for generator IU features:
- Adds/removes IU feature button rows in index.html
- Adds/removes IU feature module entries in script.js
- Creates/removes IU feature JS implementation files

It assumes generator IUs and property mappings already exist.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = ROOT / "index.html"
SCRIPT_JS = ROOT / "script.js"
UI_DATA_JSON = ROOT / "devtools" / "ui_data.json"
GEN_FACTORY_PY = ROOT / "Information_Units" / "Generators" / "GeneratorFactory.py"
GEN_MAPPING_DIR = ROOT / "Information_Units" / "property_mappings" / "sources" / "generators"
IU_FEATURE_GEN_DIR = ROOT / "Features" / "IU_Features" / "Generators"


@dataclass
class GeneratorStatus:
    gen_id: str
    display_name: str
    description: str
    mapping_exists: bool
    has_button: bool
    has_module: bool
    has_feature_file: bool
    feature_file: Path

    @property
    def is_fully_implemented(self) -> bool:
        return self.has_button and self.has_module and self.has_feature_file


def _normalize_key(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _to_pascal_case(gen_id: str) -> str:
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", gen_id) if p]
    if parts:
        return "".join(p[:1].upper() + p[1:].lower() for p in parts)
    return gen_id[:1].upper() + gen_id[1:].lower()


def _safe_read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _safe_write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _load_generator_ids_from_factory() -> List[str]:
    src = _safe_read(GEN_FACTORY_PY)
    tree = ast.parse(src)

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "generator_factory":
                    if isinstance(node.value, ast.Dict):
                        gen_ids: List[str] = []
                        for key_node in node.value.keys:
                            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                                gen_ids.append(key_node.value)
                        return gen_ids

    raise RuntimeError("Could not find generator_factory in GeneratorFactory.py")


def _load_generator_meta_from_ui_data() -> Dict[str, Tuple[str, str]]:
    payload = json.loads(_safe_read(UI_DATA_JSON))
    gen_map = payload.get("information_units", {}).get("generators", {})

    by_norm: Dict[str, Tuple[str, str]] = {}
    for display_name, description in gen_map.items():
        by_norm[_normalize_key(display_name)] = (display_name, description)

    return by_norm


def _find_js_object_bounds(text: str, anchor: str) -> Tuple[int, int, int]:
    anchor_idx = text.find(anchor)
    if anchor_idx < 0:
        raise RuntimeError(f"Could not find anchor: {anchor}")

    open_idx = text.find("{", anchor_idx)
    if open_idx < 0:
        raise RuntimeError(f"Could not find opening brace after anchor: {anchor}")

    depth = 0
    for idx in range(open_idx, len(text)):
        ch = text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return anchor_idx, open_idx, idx

    raise RuntimeError(f"Could not find matching closing brace for anchor: {anchor}")


def _extract_generator_module_block(script_text: str) -> Tuple[int, int, str]:
    _, gen_open, gen_close = _find_js_object_bounds(script_text, "generator: {")
    return gen_open, gen_close, script_text[gen_open + 1: gen_close]


def _module_entry_regex(gen_id: str) -> re.Pattern[str]:
    return re.compile(rf"\n\s*{re.escape(gen_id)}\s*:\s*\{{.*?\n\s*\}},", re.S)


def _extract_module_ids(script_text: str) -> List[int]:
    _, _, block = _extract_generator_module_block(script_text)
    ids = re.findall(r"\bid\s*:\s*(\d+)\s*,", block)
    return [int(v) for v in ids]


def _has_module_entry(script_text: str, gen_id: str) -> bool:
    _, _, block = _extract_generator_module_block(script_text)
    return re.search(rf"\b{re.escape(gen_id)}\s*:\s*\{{", block) is not None


def _upsert_module_entry(script_text: str, gen_id: str, class_name: str, feature_path: str, module_id: int) -> str:
    gen_open, gen_close, block = _extract_generator_module_block(script_text)
    cleaned = _module_entry_regex(gen_id).sub("", block).rstrip()

    entry = (
        f"        {gen_id}: {{\n"
        f"            className: '{class_name}',\n"
        f"            file: '{feature_path}',\n"
        f"            id: {module_id},\n"
        f"        }},"
    )

    if cleaned.strip():
        new_block = cleaned + "\n" + entry + "\n    "
    else:
        new_block = "\n" + entry + "\n    "

    return script_text[: gen_open + 1] + new_block + script_text[gen_close:]


def _remove_module_entry(script_text: str, gen_id: str) -> str:
    gen_open, gen_close, block = _extract_generator_module_block(script_text)
    updated = _module_entry_regex(gen_id).sub("", block).rstrip()
    if updated.strip():
        new_block = updated + "\n    "
    else:
        new_block = "\n    "
    return script_text[: gen_open + 1] + new_block + script_text[gen_close:]


def _row_block_regex(gen_id: str) -> re.Pattern[str]:
    return re.compile(
        rf"\n\s*<div class=\"iu-option-row\">\s*"
        rf"<label><input type=\"checkbox\" ui-type=\"generator\" value=\"{re.escape(gen_id)}\">.*?</label>\s*"
        rf"<button[\s\S]*?data-iu-feature=\"{re.escape(gen_id)}\"[\s\S]*?</button>\s*"
        rf"</div>",
        re.S,
    )


def _plain_label_regex(gen_id: str, display_name: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?m)^\s*<label><input type=\"checkbox\" ui-type=\"generator\" value=\"{re.escape(gen_id)}\">\s*{re.escape(display_name)}\s*</label>\s*$"
    )


def _build_button_row(gen_id: str, display_name: str, description: str) -> str:
    return (
        "                            <div class=\"iu-option-row\">\n"
        f"                                <label><input type=\"checkbox\" ui-type=\"generator\" value=\"{gen_id}\"> {display_name}</label>\n"
        "                                <button\n"
        "                                    class=\"iu-feature-btn\"\n"
        f"                                    data-iu-feature=\"{gen_id}\"\n"
        "                                    data-iu-type=\"generator\"\n"
        f"                                    data-iu-name=\"{display_name}\"\n"
        f"                                    data-iu-desc=\"{description}\"\n"
        "                                    title=\"Open IU panel\"\n"
        "                                    aria-label=\"Open IU panel\"\n"
        "                                >&#9654;</button>\n"
        "                            </div>"
    )


def _ensure_button_row(index_text: str, gen_id: str, display_name: str, description: str) -> str:
    row_re = _row_block_regex(gen_id)
    if row_re.search(index_text):
        return index_text

    label_re = _plain_label_regex(gen_id, display_name)
    row = _build_button_row(gen_id, display_name, description)

    if label_re.search(index_text):
        return label_re.sub(row, index_text, count=1)

    anchor = '                            </div>\n                        </div>'
    generator_header = '<h3>Generators</h3>'
    start_idx = index_text.find(generator_header)
    if start_idx < 0:
        raise RuntimeError("Could not find Generators section in index.html")

    idx = index_text.find(anchor, start_idx)
    if idx < 0:
        raise RuntimeError("Could not find insertion anchor in index.html generators list")

    return index_text[:idx] + row + "\n" + index_text[idx:]


def _remove_button_row(index_text: str, gen_id: str, display_name: str) -> str:
    row_re = _row_block_regex(gen_id)
    plain_label = f'                            <label><input type="checkbox" ui-type="generator" value="{gen_id}"> {display_name}</label>'

    if row_re.search(index_text):
        return row_re.sub("\n" + plain_label, index_text, count=1)

    return index_text


def _build_feature_js(class_name: str, gen_id: str, title: str, description: str) -> str:
    return f"""// Auto-generated IU Feature for generator: {gen_id}
class {class_name} extends BaseFeature {{
    constructor(featureId, iuMeta = {{}}) {{
        super(
            featureId,
            iuMeta.iuName ? `${{iuMeta.iuName}} IU Feature` : '{title} IU Feature',
            iuMeta.iuDesc || '{description}'
        );
        this.iuType = iuMeta.iuType || 'generator';
        this.iuId = iuMeta.iuId || '{gen_id}';
        this._abortController = null;
        this._propertyDefs = [];
        this._downloadUrl = null;
    }}

    _toDisplayLabel(propertyKey) {{
        const tokenMap = {{
            dos: 'DOS',
            ef: 'EF',
            xc: 'XC',
            id: 'ID',
            scan: 'SCAN',
            dft: 'DFT',
            hhi: 'HHI',
            mp: 'MP',
        }};

        return String(propertyKey)
            .split('_')
            .map((token) => {{
                const lower = token.toLowerCase();
                if (tokenMap[lower]) return tokenMap[lower];
                return token.charAt(0).toUpperCase() + token.slice(1).toLowerCase();
            }})
            .join(' ');
    }}

    _formatLabelWithUnit(propertyName, unit) {{
        const displayName = this._toDisplayLabel(propertyName);
        if (!unit) return displayName;
        return `${{displayName}} (${{unit}})`;
    }}

    createInputsHTML() {{
        return `
            <div class="iu-input-scroll">
                <div class="input-controls">
                    <label>Batch Size
                        <input type="number" id="batch_size_${{this.featureId}}" min="1" max="1000" step="1">
                    </label>
                </div>
                <div class="input-controls" id="${{this.iuId}}PropertyFilters_${{this.featureId}}">
                    <p>Loading property mappings...</p>
                </div>
            </div>
        `;
    }}

    createOutputsHTML() {{
        return `
            <p>${{this.iuId}} IU outputs</p>
            <div class="output-display" id="outputDisplay_${{this.featureId}}">
                <div class="output-item" id="iuStructSelectorRow_${{this.featureId}}" style="display:none;">
                    <strong>Structure:</strong>
                    <select id="iuStructSelector_${{this.featureId}}"></select>
                </div>

                <div class="output-item" id="iuCifViewerRow_${{this.featureId}}" style="display:none;">
                    <strong>Crystal Structure:</strong>
                    <div id="iuStructureViewer_${{this.featureId}}" style="
                        width:100%; height:400px; position:relative;
                        background:#ffffff; border-radius:6px; margin-top:6px;
                    "></div>
                    <div style="margin-top:6px; text-align:right;">
                        <button id="iuToggleCifBtn_${{this.featureId}}" class="btn-secondary" style="
                            font-size:11px; padding:4px 10px; cursor:pointer;
                            background:#313244; color:#cdd6f4; border:1px solid #45475a;
                            border-radius:4px;
                        ">Show CIF Text</button>
                    </div>
                    <pre id="iuCifViewer_${{this.featureId}}" class="cif-viewer" style="
                        display:none; max-height:300px; overflow:auto; background:#1e1e2e;
                        color:#cdd6f4; padding:12px; border-radius:6px;
                        font-size:12px; white-space:pre-wrap; margin-top:6px;
                    "></pre>
                </div>

                <div class="output-item">
                    <strong>Generated Dataset (JSON):</strong>
                    <span id="iuDataGeneratedStatus_${{this.featureId}}">Pending...</span>
                    <a id="iuDataGeneratedDownload_${{this.featureId}}" style="display:none; margin-left:10px;" download="${{this.iuId}}_generated_dataset.json">Download</a>
                </div>
            </div>
        `;
    }}

    async initializeUI() {{
        const batchInput = document.getElementById(`batch_size_${{this.featureId}}`);
        if (batchInput && !batchInput.value) {{
            batchInput.value = '10';
        }}
        await this._renderPropertyFilters();
    }}

    async _renderPropertyFilters() {{
        const container = document.getElementById(`${{this.iuId}}PropertyFilters_${{this.featureId}}`);
        if (!container) return;

        try {{
            const [mappingRes, commonRes] = await Promise.all([
                fetch(`./Information_Units/property_mappings/sources/generators/${{this.iuId}}.json`),
                fetch('./Information_Units/property_mappings/common_properties.json'),
            ]);
            if (!mappingRes.ok) throw new Error(`${{this.iuId}} mapping HTTP ${{mappingRes.status}}`);
            if (!commonRes.ok) throw new Error(`Common properties HTTP ${{commonRes.status}}`);

            const mapping = await mappingRes.json();
            const common = await commonRes.json();
            const properties = mapping?.properties || {{}};
            const commonProperties = common?.properties || {{}};

            const defs = Object.entries(properties)
                .map(([name, cfg]) => ({{
                    uiKey: name,
                    sourceKey: (typeof cfg?.name === 'string' && cfg.name.trim()) ? cfg.name.trim() : name,
                    rangeSupport: !!cfg?.range_support,
                    generatable: cfg?.generatable !== false,
                    unit: commonProperties?.[name]?.unit || '',
                }}))
                .filter((p) => p.generatable);

            this._propertyDefs = defs;

            if (defs.length === 0) {{
                container.innerHTML = '';
                return;
            }}

            let html = '<div class="iu-property-list">';
            defs.forEach((prop) => {{
                const labelWithUnit = this._formatLabelWithUnit(prop.uiKey, prop.unit);
                if (prop.rangeSupport) {{
                    html += `
                        <div class="iu-property-row">
                            <label>${{labelWithUnit}}
                                <div class="iu-range-inputs">
                                    <input type="number" step="any" id="iu_prop_${{prop.uiKey}}_min_${{this.featureId}}" placeholder="Min" title="${{prop.uiKey}}">
                                    <input type="number" step="any" id="iu_prop_${{prop.uiKey}}_max_${{this.featureId}}" placeholder="Max" title="${{prop.uiKey}}">
                                </div>
                            </label>
                        </div>
                    `;
                }} else {{
                    html += `
                        <div class="iu-property-row">
                            <label>${{labelWithUnit}}
                                <input type="text" id="iu_prop_${{prop.uiKey}}_${{this.featureId}}" placeholder="Enter Value" title="${{prop.uiKey}}">
                            </label>
                        </div>
                    `;
                }}
            }});
            html += '</div>';
            container.innerHTML = html;
        }} catch (error) {{
            container.innerHTML = `<p>Failed to load property mappings: ${{error.message}}</p>`;
            this.addLog(`Failed to load property mappings: ${{error.message}}`, 'error');
        }}
    }}

    collectInputData() {{
        const batchEl = document.getElementById(`batch_size_${{this.featureId}}`);

        const inputs = {{
            batch_size: parseInt(batchEl?.value || '10', 10),
        }};

        if (!Number.isFinite(inputs.batch_size) || inputs.batch_size <= 0) {{
            inputs.batch_size = 10;
        }}

        this._propertyDefs.forEach((prop) => {{
            const payloadKey = prop.sourceKey || prop.uiKey;
            if (prop.rangeSupport) {{
                const minEl = document.getElementById(`iu_prop_${{prop.uiKey}}_min_${{this.featureId}}`);
                const maxEl = document.getElementById(`iu_prop_${{prop.uiKey}}_max_${{this.featureId}}`);
                const minRaw = minEl?.value?.trim() || '';
                const maxRaw = maxEl?.value?.trim() || '';

                if (minRaw === '' && maxRaw === '') return;

                if (minRaw !== '' && maxRaw !== '') {{
                    const minVal = parseFloat(minRaw);
                    const maxVal = parseFloat(maxRaw);
                    if (Number.isFinite(minVal) && Number.isFinite(maxVal)) {{
                        inputs[payloadKey] = minVal <= maxVal ? [minVal, maxVal] : [maxVal, minVal];
                    }}
                    return;
                }}

                const exactValRaw = minRaw || maxRaw;
                const exactVal = parseFloat(exactValRaw);
                if (Number.isFinite(exactVal)) {{
                    inputs[payloadKey] = exactVal;
                }}
            }} else {{
                const valEl = document.getElementById(`iu_prop_${{prop.uiKey}}_${{this.featureId}}`);
                const raw = valEl?.value?.trim() || '';
                if (raw !== '') {{
                    inputs[payloadKey] = raw;
                }}
            }}
        }});

        return inputs;
    }}

    async callPythonBackend() {{
        const inputs = this.collectInputData();
        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';

        this._abortController = new AbortController();
        this._cancelled = false;

        this.addLog('Sending IU request to EMOS backend...', 'info');

        try {{
            const response = await fetch(
                `${{backendUrl}}/api/process/iu/${{this.iuType}}/${{this.iuId}}/stream`,
                {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(inputs),
                    signal: this._abortController.signal,
                }}
            );

            if (!response.ok) {{
                const errBody = await response.text();
                throw new Error(`HTTP ${{response.status}}: ${{errBody}}`);
            }}

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalResult = null;

            while (true) {{
                const {{ done, value }} = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, {{ stream: true }});

                const blocks = buffer.split('\\n\\n');
                buffer = blocks.pop() || '';

                for (const block of blocks) {{
                    if (!block.trim()) continue;

                    const lines = block.split('\\n');
                    let eventType = 'log';
                    let eventData = null;

                    for (const line of lines) {{
                        if (line.startsWith('event:')) {{
                            eventType = line.slice(6).trim();
                        }} else if (line.startsWith('data:')) {{
                            const dataStr = line.slice(5).trim();
                            try {{
                                eventData = JSON.parse(dataStr);
                            }} catch (e) {{
                                eventData = {{ message: dataStr }};
                            }}
                        }}
                    }}

                    if (!eventData) continue;

                    if (eventType === 'log') {{
                        const msg = eventData.message || '';
                        const level = eventData.level || 'info';
                        this.addLog(msg, level);
                    }} else if (eventType === 'progress') {{
                        const raw = Number(eventData.progress);
                        const pct = Number.isFinite(raw)
                            ? Math.round(Math.max(0, Math.min(1, raw)) * 100)
                            : null;
                        const msg = eventData.message || (pct !== null ? `Progress: ${{pct}}%` : 'Progress update');
                        this.addLog(msg, 'info');
                    }} else if (eventType === 'result') {{
                        finalResult = eventData;
                        const numStructs = Array.isArray(eventData.cif_strings) ? eventData.cif_strings.length : 0;
                        this.addLog(`Generation complete: ${{numStructs}} structure(s)`, 'success');
                    }} else if (eventType === 'error') {{
                        this.addLog(eventData.message || 'Unknown error', 'error');
                    }}
                }}
            }}

            if (buffer.trim()) {{
                const lines = buffer.split('\\n');
                let eventType = 'log';
                let eventData = null;

                for (const line of lines) {{
                    if (line.startsWith('event:')) {{
                        eventType = line.slice(6).trim();
                    }} else if (line.startsWith('data:')) {{
                        const dataStr = line.slice(5).trim();
                        try {{
                            eventData = JSON.parse(dataStr);
                        }} catch (e) {{
                            eventData = {{ message: dataStr }};
                        }}
                    }}
                }}

                if (eventData && eventType === 'result') {{
                    finalResult = eventData;
                }}
            }}

            return finalResult || {{ status: 'completed', cif_strings: [] }};
        }} catch (error) {{
            if (error.name === 'AbortError') {{
                this.addLog('Request cancelled by user', 'warning');
                return {{ status: 'cancelled', cif_strings: [] }};
            }}
            throw error;
        }}
    }}

    async cancelProcessing() {{
        if (!this.isProcessing) return;

        this._cancelled = true;
        const cancelBtn = document.getElementById(`cancelBtn_${{this.featureId}}`);
        if (cancelBtn) {{
            cancelBtn.disabled = true;
            cancelBtn.textContent = 'Cancelling...';
        }}

        this.addLog('Cancel requested by user.', 'warning');

        if (this._abortController) {{
            this._abortController.abort();
            this._abortController = null;
        }}
    }}

    async processFeature() {{
        return {{
            source: this.iuId,
            queries: this.collectInputData(),
            cif_strings: [],
            status: 'local_fallback',
        }};
    }}

    updateOutputs(results = null) {{
        const data = results || this.results || {{}};

        if (data.error) {{
            const statusEl = document.getElementById(`iuDataGeneratedStatus_${{this.featureId}}`);
            const downloadEl = document.getElementById(`iuDataGeneratedDownload_${{this.featureId}}`);
            if (statusEl) statusEl.textContent = `Error: ${{data.error}}`;
            if (downloadEl) downloadEl.style.display = 'none';
            return;
        }}

        const statusEl = document.getElementById(`iuDataGeneratedStatus_${{this.featureId}}`);
        const downloadEl = document.getElementById(`iuDataGeneratedDownload_${{this.featureId}}`);

        if (this._downloadUrl) {{
            URL.revokeObjectURL(this._downloadUrl);
            this._downloadUrl = null;
        }}

        if (downloadEl) {{
            const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
            this._downloadUrl = URL.createObjectURL(blob);
            downloadEl.href = this._downloadUrl;
            downloadEl.download = `${{this.iuId}}_generated_dataset_${{Date.now()}}.json`;
            downloadEl.style.display = '';
        }}

        if (statusEl) {{
            statusEl.textContent = 'Ready';
        }}

        const cifList = Array.isArray(data.cif_strings) ? data.cif_strings : [];
        const structRow = document.getElementById(`iuStructSelectorRow_${{this.featureId}}`);
        const structSelector = document.getElementById(`iuStructSelector_${{this.featureId}}`);
        const cifRow = document.getElementById(`iuCifViewerRow_${{this.featureId}}`);
        const viewerContainer = document.getElementById(`iuStructureViewer_${{this.featureId}}`);
        const cifViewer = document.getElementById(`iuCifViewer_${{this.featureId}}`);
        const toggleCifBtn = document.getElementById(`iuToggleCifBtn_${{this.featureId}}`);

        if (!structRow || !structSelector || !cifRow || !viewerContainer || !cifViewer) {{
            return;
        }}

        if (cifList.length === 0) {{
            structRow.style.display = 'none';
            cifRow.style.display = 'none';
            return;
        }}

        structSelector.innerHTML = cifList.map((_, i) => `<option value="${{i}}">Structure ${{i + 1}}</option>`).join('');

        structRow.style.display = '';
        cifRow.style.display = '';

        if (this._3dViewer) {{
            viewerContainer.innerHTML = '';
            this._3dViewer = null;
        }}

        const showStructure = (idx) => {{
            const cifData = cifList[idx];
            cifViewer.textContent = cifData || '(no CIF data available)';

            if (!cifData || typeof $3Dmol === 'undefined') {{
                viewerContainer.innerHTML = '<p style="color:#333;padding:20px;">3D viewer unavailable</p>';
                return;
            }}

            viewerContainer.innerHTML = '';
            const viewer = $3Dmol.createViewer(viewerContainer, {{
                backgroundColor: '#ffffff',
            }});

            viewer.addModel(cifData, 'cif', {{ doAssembly: true, duplicateAssemblyAtoms: true }});
            viewer.setStyle({{}}, {{
                sphere: {{ radius: 0.4, colorscheme: 'Jmol' }},
                stick: {{ radius: 0.15, colorscheme: 'Jmol' }},
            }});
            viewer.addUnitCell();
            viewer.zoomTo();
            viewer.render();

            this._3dViewer = viewer;
        }};

        showStructure(0);

        if (toggleCifBtn) {{
            const newBtn = toggleCifBtn.cloneNode(true);
            toggleCifBtn.parentNode.replaceChild(newBtn, toggleCifBtn);
            newBtn.addEventListener('click', () => {{
                const hidden = cifViewer.style.display === 'none';
                cifViewer.style.display = hidden ? 'block' : 'none';
                newBtn.textContent = hidden ? 'Hide CIF Text' : 'Show CIF Text';
            }});
        }}

        const newSelector = structSelector.cloneNode(true);
        structSelector.parentNode.replaceChild(newSelector, structSelector);
        newSelector.addEventListener('change', () => showStructure(parseInt(newSelector.value, 10)));
    }}

    destroy() {{
        if (this._downloadUrl) {{
            URL.revokeObjectURL(this._downloadUrl);
            this._downloadUrl = null;
        }}
    }}
}}

window.{class_name} = {class_name};
"""


def _discover_statuses() -> List[GeneratorStatus]:
    gen_ids = _load_generator_ids_from_factory()
    ui_meta = _load_generator_meta_from_ui_data()

    index_text = _safe_read(INDEX_HTML)
    script_text = _safe_read(SCRIPT_JS)

    statuses: List[GeneratorStatus] = []

    for gen_id in gen_ids:
        norm_id = _normalize_key(gen_id)
        display_name, description = ui_meta.get(norm_id, (gen_id, f"{gen_id} generator"))
        class_name = f"{_to_pascal_case(gen_id)}IUFeature"
        feature_file = IU_FEATURE_GEN_DIR / f"{class_name}.js"

        statuses.append(
            GeneratorStatus(
                gen_id=gen_id,
                display_name=display_name,
                description=description,
                mapping_exists=(GEN_MAPPING_DIR / f"{gen_id}.json").exists(),
                has_button=(f'data-iu-feature="{gen_id}"' in index_text),
                has_module=_has_module_entry(script_text, gen_id),
                has_feature_file=feature_file.exists(),
                feature_file=feature_file,
            )
        )

    return statuses


def _print_statuses(statuses: List[GeneratorStatus]) -> None:
    print("\nGenerator IU Feature Status")
    print("=" * 76)
    print(f"{'#':<3} {'Generator':<32} {'Implemented':<12} {'Button':<8} {'Module':<8} {'JS':<5} {'Mapping':<7}")
    print("-" * 76)

    for idx, s in enumerate(statuses, start=1):
        print(
            f"{idx:<3} {s.gen_id:<32} "
            f"{('yes' if s.is_fully_implemented else 'no'):<12} "
            f"{('yes' if s.has_button else 'no'):<8} "
            f"{('yes' if s.has_module else 'no'):<8} "
            f"{('yes' if s.has_feature_file else 'no'):<5} "
            f"{('yes' if s.mapping_exists else 'no'):<7}"
        )

    print("=" * 76)


def _next_module_id(script_text: str) -> int:
    ids = _extract_module_ids(script_text)
    return (max(ids) + 1) if ids else 1101


def _apply_add(target: GeneratorStatus, auto_yes: bool = False) -> None:
    print(f"\nPreparing IU feature creation for: {target.gen_id} ({target.display_name})")

    if target.is_fully_implemented:
        print("IU feature is already fully implemented. No changes made.")
        return

    if not target.mapping_exists:
        print(f"Warning: property mapping file is missing: {GEN_MAPPING_DIR / (target.gen_id + '.json')}")

    if not auto_yes:
        choice = input("Proceed with add/update? [y/N]: ").strip().lower()
        if choice not in {"y", "yes"}:
            print("Cancelled.")
            return

    index_text = _safe_read(INDEX_HTML)
    script_text = _safe_read(SCRIPT_JS)

    class_name = f"{_to_pascal_case(target.gen_id)}IUFeature"
    rel_feature_path = f"./Features/IU_Features/Generators/{class_name}.js"

    module_id = _next_module_id(script_text)
    index_text = _ensure_button_row(index_text, target.gen_id, target.display_name, target.description)
    script_text = _upsert_module_entry(script_text, target.gen_id, class_name, rel_feature_path, module_id)

    IU_FEATURE_GEN_DIR.mkdir(parents=True, exist_ok=True)
    if not target.feature_file.exists():
        content = _build_feature_js(class_name, target.gen_id, target.display_name, target.description)
        _safe_write(target.feature_file, content)
        print(f"Created JS IU feature: {target.feature_file.relative_to(ROOT)}")
    else:
        print(f"JS IU feature already exists: {target.feature_file.relative_to(ROOT)}")

    _safe_write(INDEX_HTML, index_text)
    _safe_write(SCRIPT_JS, script_text)

    print("Updated index.html and script.js for IU feature wiring.")


def _apply_remove(target: GeneratorStatus, auto_yes: bool = False) -> None:
    print(f"\nPreparing IU feature removal for: {target.gen_id} ({target.display_name})")

    if not (target.has_button or target.has_module or target.has_feature_file):
        print("IU feature is not implemented. No changes made.")
        return

    if not auto_yes:
        choice = input("Proceed with removal? [y/N]: ").strip().lower()
        if choice not in {"y", "yes"}:
            print("Cancelled.")
            return

    index_text = _safe_read(INDEX_HTML)
    script_text = _safe_read(SCRIPT_JS)

    index_text = _remove_button_row(index_text, target.gen_id, target.display_name)
    script_text = _remove_module_entry(script_text, target.gen_id)

    _safe_write(INDEX_HTML, index_text)
    _safe_write(SCRIPT_JS, script_text)

    if target.feature_file.exists():
        target.feature_file.unlink()
        print(f"Removed JS IU feature: {target.feature_file.relative_to(ROOT)}")

    print("Removed IU feature wiring from index.html and script.js.")


def _select_target(candidates: List[GeneratorStatus], prompt_title: str) -> Optional[GeneratorStatus]:
    if not candidates:
        print("(none)")
        return None

    print(f"\n{prompt_title}")
    for idx, c in enumerate(candidates, start=1):
        print(f"  {idx}. {c.gen_id} ({c.display_name})")

    while True:
        raw = input("Select generator number (or press Enter to cancel): ").strip()
        if raw == "":
            return None
        if raw.isdigit():
            picked = int(raw)
            if 1 <= picked <= len(candidates):
                return candidates[picked - 1]
        print("Invalid selection. Try again.")


def run_interactive() -> None:
    statuses = _discover_statuses()
    implemented = [s for s in statuses if s.is_fully_implemented]
    unimplemented = [s for s in statuses if not s.is_fully_implemented]

    print("\n" + "=" * 60)
    print("Generator IU Feature Manager")
    print("=" * 60)
    print(f"Implemented IU features   : {len(implemented)}")
    print(f"Unimplemented IU features : {len(unimplemented)}")

    print("\nImplemented generators:")
    if implemented:
        for item in implemented:
            print(f"  - {item.gen_id} ({item.display_name})")
    else:
        print("  (none)")

    print("\nUnimplemented generators:")
    if unimplemented:
        for item in unimplemented:
            print(f"  - {item.gen_id} ({item.display_name})")
    else:
        print("  (none)")

    action = input("\nChoose action [add/remove/skip]: ").strip().lower()

    if action in {"skip", "", "exit", "quit", "no"}:
        print("No changes made.")
        return

    if action == "add":
        if not unimplemented:
            print("All generator IU features are already implemented.")
            return
        target = _select_target(unimplemented, "Generators available for IU feature addition:")
        if target:
            _apply_add(target)
        else:
            print("No selection made. No changes applied.")
        return

    if action == "remove":
        if not implemented:
            print("All generator IU features are currently unimplemented.")
            return
        target = _select_target(implemented, "Generators available for IU feature removal:")
        if target:
            _apply_remove(target)
        else:
            print("No selection made. No changes applied.")
        return

    print("Invalid action. No changes made.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage generator IU feature scaffolding")
    parser.add_argument("--list", action="store_true", help="Only print current IU feature status")
    parser.add_argument("--add", metavar="GEN_ID", help="Add IU feature for a specific generator id")
    parser.add_argument("--remove", metavar="GEN_ID", help="Remove IU feature for a specific generator id")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    args = parser.parse_args()

    statuses = _discover_statuses()

    if args.list:
        _print_statuses(statuses)
        return

    if args.add and args.remove:
        raise SystemExit("Use either --add or --remove, not both.")

    if args.add:
        target = next((s for s in statuses if s.gen_id == args.add), None)
        if target is None:
            raise SystemExit(f"Unknown generator id: {args.add}")
        _apply_add(target, auto_yes=args.yes)
        return

    if args.remove:
        target = next((s for s in statuses if s.gen_id == args.remove), None)
        if target is None:
            raise SystemExit(f"Unknown generator id: {args.remove}")
        _apply_remove(target, auto_yes=args.yes)
        return

    run_interactive()


if __name__ == "__main__":
    main()
