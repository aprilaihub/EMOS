#!/usr/bin/env python3
"""Interactive utility to add/remove predictor IU features.

This script automates the frontend wiring needed for predictor IU features:
- Adds/removes IU feature button rows in index.html
- Adds/removes IU feature module entries in script.js
- Creates/removes IU feature JS implementation files

It assumes predictor IUs and property mappings already exist.
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
PRED_FACTORY_PY = ROOT / "Information_Units" / "Predictors" / "PredictorFactory.py"
PRED_MAPPING_DIR = ROOT / "Information_Units" / "property_mappings" / "sources" / "predictors"
IU_FEATURE_PRED_DIR = ROOT / "Features" / "IU_Features" / "Predictors"


@dataclass
class PredictorStatus:
    pred_id: str
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


def _to_pascal_case(pred_id: str) -> str:
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", pred_id) if p]
    if parts:
        return "".join(p[:1].upper() + p[1:].lower() for p in parts)
    return pred_id[:1].upper() + pred_id[1:].lower()


def _safe_read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _safe_write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _load_predictor_ids_from_factory() -> List[str]:
    src = _safe_read(PRED_FACTORY_PY)
    tree = ast.parse(src)

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "predictor_factory":
                    if isinstance(node.value, ast.Dict):
                        pred_ids: List[str] = []
                        for key_node in node.value.keys:
                            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                                pred_ids.append(key_node.value)
                        return pred_ids

    raise RuntimeError("Could not find predictor_factory in PredictorFactory.py")


def _load_predictor_meta_from_ui_data() -> Dict[str, Tuple[str, str]]:
    payload = json.loads(_safe_read(UI_DATA_JSON))
    pred_map = payload.get("information_units", {}).get("predictors", {})

    by_norm: Dict[str, Tuple[str, str]] = {}
    for display_name, description in pred_map.items():
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


def _extract_predictor_module_block(script_text: str) -> Tuple[int, int, str]:
    try:
        _, pred_open, pred_close = _find_js_object_bounds(script_text, "predictor: {")
        return pred_open, pred_close, script_text[pred_open + 1: pred_close]
    except RuntimeError:
        # If predictor block doesn't exist yet, create virtual bounds for later insertion
        # This allows the script to work in discovery/list mode before any predictors are added
        return -1, -1, ""


def _module_entry_regex(pred_id: str) -> re.Pattern[str]:
    return re.compile(rf"\n\s*{re.escape(pred_id)}\s*:\s*\{{.*?\n\s*\}},", re.S)


def _extract_module_ids(script_text: str) -> List[int]:
    _, _, block = _extract_predictor_module_block(script_text)
    if not block:
        return []
    ids = re.findall(r"\bid\s*:\s*(\d+)\s*,", block)
    return [int(v) for v in ids]


def _has_module_entry(script_text: str, pred_id: str) -> bool:
    _, _, block = _extract_predictor_module_block(script_text)
    if not block:
        return False
    return re.search(rf"\b{re.escape(pred_id)}\s*:\s*\{{", block) is not None


def _upsert_module_entry(script_text: str, pred_id: str, class_name: str, feature_path: str, module_id: int) -> str:
    pred_open, pred_close, block = _extract_predictor_module_block(script_text)
    
    # If the predictor block doesn't exist yet, we need to create it
    if pred_open == -1:
        # Find the generator block to insert the predictor block after it
        try:
            _, gen_open, gen_close = _find_js_object_bounds(script_text, "generator: {")
        except RuntimeError:
            raise RuntimeError("Could not find generator block in script.js to insert predictor block after")
        
        # Create the new predictor block
        entry = (
            f"        {pred_id}: {{\n"
            f"            className: '{class_name}',\n"
            f"            file: '{feature_path}',\n"
            f"            id: {module_id},\n"
            f"        }},"
        )
        new_predictor_block = f"    predictor: {{\n{entry}\n    }},"
        
        # Insert after generator block
        insertion_point = gen_close + 1
        return script_text[:insertion_point] + "\n" + new_predictor_block + script_text[insertion_point:]
    
    # If predictor block exists, update it
    cleaned = _module_entry_regex(pred_id).sub("", block).rstrip()

    entry = (
        f"        {pred_id}: {{\n"
        f"            className: '{class_name}',\n"
        f"            file: '{feature_path}',\n"
        f"            id: {module_id},\n"
        f"        }},"
    )

    if cleaned.strip():
        new_block = cleaned + "\n" + entry + "\n    "
    else:
        new_block = "\n" + entry + "\n    "

    return script_text[: pred_open + 1] + new_block + script_text[pred_close:]


def _remove_module_entry(script_text: str, pred_id: str) -> str:
    pred_open, pred_close, block = _extract_predictor_module_block(script_text)
    
    if pred_open == -1:
        # Block doesn't exist, nothing to remove
        return script_text
    
    updated = _module_entry_regex(pred_id).sub("", block).rstrip()
    if updated.strip():
        new_block = updated + "\n    "
    else:
        new_block = "\n    "
    return script_text[: pred_open + 1] + new_block + script_text[pred_close:]


def _row_block_regex(pred_id: str) -> re.Pattern[str]:
    return re.compile(
        rf"\n\s*<div class=\"iu-option-row\">\s*"
        rf"<label><input type=\"checkbox\" ui-type=\"predictor\" value=\"{re.escape(pred_id)}\">.*?</label>\s*"
        rf"<button[\s\S]*?data-iu-feature=\"{re.escape(pred_id)}\"[\s\S]*?</button>\s*"
        rf"</div>",
        re.S,
    )


def _plain_label_regex(pred_id: str, display_name: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?m)^\s*<label><input type=\"checkbox\" ui-type=\"predictor\" value=\"{re.escape(pred_id)}\">\s*{re.escape(display_name)}\s*</label>\s*$"
    )


def _build_button_row(pred_id: str, display_name: str, description: str) -> str:
    return (
        "                            <div class=\"iu-option-row\">\n"
        f"                                <label><input type=\"checkbox\" ui-type=\"predictor\" value=\"{pred_id}\"> {display_name}</label>\n"
        "                                <button\n"
        "                                    class=\"iu-feature-btn\"\n"
        f"                                    data-iu-feature=\"{pred_id}\"\n"
        "                                    data-iu-type=\"predictor\"\n"
        f"                                    data-iu-name=\"{display_name}\"\n"
        f"                                    data-iu-desc=\"{description}\"\n"
        "                                    title=\"Open IU panel\"\n"
        "                                    aria-label=\"Open IU panel\"\n"
        "                                >&#9654;</button>\n"
        "                            </div>"
    )


def _ensure_button_row(index_text: str, pred_id: str, display_name: str, description: str) -> str:
    row_re = _row_block_regex(pred_id)
    if row_re.search(index_text):
        return index_text

    label_re = _plain_label_regex(pred_id, display_name)
    row = _build_button_row(pred_id, display_name, description)

    if label_re.search(index_text):
        return label_re.sub(row, index_text, count=1)

    anchor = '                            </div>\n                        </div>'
    predictor_header = '<h3>Predictors</h3>'
    start_idx = index_text.find(predictor_header)
    if start_idx < 0:
        raise RuntimeError("Could not find Predictors section in index.html")

    idx = index_text.find(anchor, start_idx)
    if idx < 0:
        raise RuntimeError("Could not find insertion anchor in index.html predictors list")

    return index_text[:idx] + row + "\n" + index_text[idx:]


def _remove_button_row(index_text: str, pred_id: str, display_name: str) -> str:
    row_re = _row_block_regex(pred_id)
    plain_label = f'                            <label><input type="checkbox" ui-type="predictor" value="{pred_id}"> {display_name}</label>'

    if row_re.search(index_text):
        return row_re.sub("\n" + plain_label, index_text, count=1)

    return index_text


def _build_feature_js(class_name: str, pred_id: str, title: str, description: str) -> str:
    return f"""// Auto-generated IU Feature for predictor: {pred_id}
class {class_name} extends BaseFeature {{
    constructor(featureId, iuMeta = {{}}) {{
        super(
            featureId,
            iuMeta.iuName ? `${{iuMeta.iuName}} IU Feature` : '{title} IU Feature',
            iuMeta.iuDesc || '{description}'
        );
        this.iuType = iuMeta.iuType || 'predictor';
        this.iuId = iuMeta.iuId || '{pred_id}';
        this._abortController = null;
        this._propertyDefs = [];
        this._propertyUnitByKey = {{}};
        this._downloadUrl = null;
        this._uploadedFiles = [];
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

    _escapeHtml(value) {{
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }}

    _sanitizeDomId(value) {{
        return String(value).replace(/[^a-zA-Z0-9_-]/g, '_');
    }}

    _isLikelyCifText(value) {{
        if (typeof value !== 'string') return false;
        const text = value.trim();
        if (!text) return false;
        return text.startsWith('data_') || text.includes('_cell_') || text.includes('loop_') || text.includes('_atom_site');
    }}

    _isCifProperty(propertyKey, value) {{
        if (typeof value !== 'string') return false;
        return String(propertyKey).toLowerCase().includes('cif') || this._isLikelyCifText(value);
    }}

    createInputsHTML() {{
        return `
            <div class="iu-input-scroll">
                <div class="input-controls">
                    <label>CIF Files
                        <div style="margin-top:6px; padding:12px; background:#f5f5f5; border-radius:4px; border:2px dashed #ccc;">
                            <input type="file" id="cifUpload_${{this.featureId}}" multiple accept=".cif,.zip" style="display:block; margin-bottom:8px;">
                            <small style="color:#666;">Select .cif files or .zip archive. Drag & drop supported.</small>
                            <div id="fileList_${{this.featureId}}" style="margin-top:8px; font-size:12px; color:#333;"></div>
                        </div>
                    </label>
                </div>
            </div>
        `;
    }}

    createOutputsHTML() {{
        return `
            <p>${{this.iuId}} Prediction Results</p>
            <div class="output-display" id="outputDisplay_${{this.featureId}}">
                <div class="output-item" id="iuInputSelectorRow_${{this.featureId}}" style="display:none;">
                    <strong>Input Structure:</strong>
                    <select id="iuInputSelector_${{this.featureId}}"></select>
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

                <div class="output-item" id="iuPropertiesRow_${{this.featureId}}" style="display:none;">
                    <strong>Predicted Properties:</strong>
                    <div id="iuPropertiesDisplay_${{this.featureId}}" style="margin-top:8px;"></div>
                </div>

                <div class="output-item">
                    <strong>Prediction Results (JSON):</strong>
                    <span id="iuPredictionStatus_${{this.featureId}}">Pending...</span>
                    <a id="iuPredictionDownload_${{this.featureId}}" style="display:none; margin-left:10px;" download="${{this.iuId}}_predictions.json">Download</a>
                </div>
            </div>
        `;
    }}

    async initializeUI() {{
        const fileInput = document.getElementById(`cifUpload_${{this.featureId}}`);
        if (!fileInput) return;

        fileInput.addEventListener('change', (e) => this._handleFileSelection(e));

        const dropZone = fileInput.parentElement;
        dropZone.addEventListener('dragover', (e) => {{
            e.preventDefault();
            dropZone.style.background = '#efefef';
        }});
        dropZone.addEventListener('dragleave', () => {{
            dropZone.style.background = '#f5f5f5';
        }});
        dropZone.addEventListener('drop', (e) => {{
            e.preventDefault();
            dropZone.style.background = '#f5f5f5';
            if (e.dataTransfer.files.length > 0) {{
                fileInput.files = e.dataTransfer.files;
                this._handleFileSelection({{}});
            }}
        }});

        await this._renderPropertyDefs();
    }}

    _handleFileSelection(evt) {{
        const fileInput = document.getElementById(`cifUpload_${{this.featureId}}`);
        const listEl = document.getElementById(`fileList_${{this.featureId}}`);
        if (!fileInput || !listEl) return;

        const files = Array.from(fileInput.files);
        this._uploadedFiles = files;

        listEl.textContent = `${{files.length}} file(s) selected`;

        this.addLog(`Loaded ${{files.length}} file(s)`, 'info');
    }}

    async _renderPropertyDefs() {{
        try {{
            const [mappingRes, commonRes] = await Promise.all([
                fetch(`./Information_Units/property_mappings/sources/predictors/${{this.iuId}}.json`),
                fetch('./Information_Units/property_mappings/common_properties.json').catch(() => null),
            ]);
            if (!mappingRes.ok) throw new Error(`${{this.iuId}} mapping HTTP ${{mappingRes.status}}`);

            const mapping = await mappingRes.json();
            const common = commonRes && commonRes.ok ? await commonRes.json() : {{}};
            const properties = mapping?.properties || {{}};
            const commonProperties = common?.properties || {{}};

            const defs = Object.entries(properties)
                .map(([name, cfg]) => ({{
                    uiKey: name,
                    sourceKey: (typeof cfg?.name === 'string' && cfg.name.trim()) ? cfg.name.trim() : name,
                    predictable: !!cfg?.predictable,
                    unit: commonProperties?.[name]?.unit || '',
                }}))
                .filter((p) => p.predictable);

            this._propertyDefs = defs;
            this._propertyUnitByKey = {{}};
            defs.forEach((prop) => {{
                this._propertyUnitByKey[prop.uiKey] = prop.unit || '';
                this._propertyUnitByKey[prop.sourceKey] = prop.unit || '';
            }});
        }} catch (error) {{
            this.addLog(`Failed to load property mappings: ${{error.message}}`, 'error');
            this._propertyDefs = [];
            this._propertyUnitByKey = {{}};
        }}
    }}

    collectInputData() {{
        return {{
            cif_strings: this._uploadedFiles.length > 0 ? 'files_to_be_uploaded' : [],
        }};
    }}

    async callPythonBackend() {{
        if (this._uploadedFiles.length === 0) {{
            throw new Error('No CIF files selected. Please upload .cif files or a .zip archive.');
        }}

        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';

        this._abortController = new AbortController();
        this._cancelled = false;

        this.addLog('Reading CIF files and starting predictions...', 'info');

        try {{
            // Read CIF files as text strings
            const cifStrings = [];
            for (const file of this._uploadedFiles) {{
                if (file.name.endsWith('.cif')) {{
                    const text = await file.text();
                    cifStrings.push(text);
                }} else if (file.name.endsWith('.zip')) {{
                    this.addLog('ZIP files require backend extraction support', 'warning');
                }}
            }}

            if (cifStrings.length === 0) {{
                throw new Error('No valid .cif files found in selection');
            }}

            const payload = {{
                cif_strings: cifStrings
            }};

            const response = await fetch(
                `${{backendUrl}}/api/process/iu/${{this.iuType}}/${{this.iuId}}/stream`,
                {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(payload),
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
                        const numResults = Array.isArray(eventData.results) ? eventData.results.length : 0;
                        this.addLog(`Prediction complete: ${{numResults}} result(s)`, 'success');
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

            return finalResult || {{ status: 'completed', cif_strings: cifStrings, results: [] }};
        }} catch (error) {{
            if (error.name === 'AbortError') {{
                this.addLog('Request cancelled by user', 'warning');
                return {{ status: 'cancelled', cif_strings: [], results: [] }};
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
            cif_strings: [],
            results: [],
            status: 'local_fallback',
        }};
    }}

    updateOutputs(results = null) {{
        const data = results || this.results || {{}};

        if (data.error) {{
            const statusEl = document.getElementById(`iuPredictionStatus_${{this.featureId}}`);
            const downloadEl = document.getElementById(`iuPredictionDownload_${{this.featureId}}`);
            if (statusEl) statusEl.textContent = `Error: ${{data.error}}`;
            if (downloadEl) downloadEl.style.display = 'none';
            return;
        }}

        const statusEl = document.getElementById(`iuPredictionStatus_${{this.featureId}}`);
        const downloadEl = document.getElementById(`iuPredictionDownload_${{this.featureId}}`);

        if (this._downloadUrl) {{
            URL.revokeObjectURL(this._downloadUrl);
            this._downloadUrl = null;
        }}

        if (downloadEl) {{
            const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
            this._downloadUrl = URL.createObjectURL(blob);
            downloadEl.href = this._downloadUrl;
            downloadEl.download = `${{this.iuId}}_predictions_${{Date.now()}}.json`;
            downloadEl.style.display = '';
        }}

        if (statusEl) {{
            statusEl.textContent = 'Ready';
        }}

        const inputCifs = Array.isArray(data.cif_strings) ? data.cif_strings : [];
        const predResults = Array.isArray(data.results) ? data.results : [];
        const selectableResults = predResults
            .filter((r) => r && Number.isInteger(r.index))
            .sort((a, b) => a.index - b.index);

        const inputSelector = document.getElementById(`iuInputSelector_${{this.featureId}}`);
        const inputRow = document.getElementById(`iuInputSelectorRow_${{this.featureId}}`);
        const cifRow = document.getElementById(`iuCifViewerRow_${{this.featureId}}`);
        const viewerContainer = document.getElementById(`iuStructureViewer_${{this.featureId}}`);
        const cifViewer = document.getElementById(`iuCifViewer_${{this.featureId}}`);
        const toggleCifBtn = document.getElementById(`iuToggleCifBtn_${{this.featureId}}`);
        const propertiesRow = document.getElementById(`iuPropertiesRow_${{this.featureId}}`);
        const propertiesDisplay = document.getElementById(`iuPropertiesDisplay_${{this.featureId}}`);

        if (!inputSelector || !inputRow || !cifRow || !viewerContainer || !cifViewer || !propertiesRow || !propertiesDisplay) {{
            return;
        }}

        if (selectableResults.length === 0) {{
            inputRow.style.display = 'none';
            cifRow.style.display = 'none';
            propertiesRow.style.display = 'none';
            return;
        }}

        inputSelector.innerHTML = selectableResults
            .map((result, i) => {{
                const idxLabel = Number.isInteger(result.index) ? `Input ${{result.index + 1}}` : `Result ${{i + 1}}`;
                const statusLabel = result.status === 'error' ? ' (error)' : '';
                return `<option value="${{i}}">${{idxLabel}}${{statusLabel}}</option>`;
            }})
            .join('');
        inputRow.style.display = '';
        cifRow.style.display = '';
        propertiesRow.style.display = '';

        if (this._3dViewer) {{
            viewerContainer.innerHTML = '';
            this._3dViewer = null;
        }}

        const showStructure = (selectedPos) => {{
            const selectedResult = selectableResults[selectedPos];
            if (!selectedResult) return;

            const cifData = (typeof selectedResult.cif_input === 'string' && selectedResult.cif_input.trim())
                ? selectedResult.cif_input
                : (Number.isInteger(selectedResult.index) ? (inputCifs[selectedResult.index] || '') : '');
            cifViewer.textContent = cifData || '(no CIF data available)';

            if (!cifData || typeof $3Dmol === 'undefined') {{
                viewerContainer.innerHTML = '<p style="color:#333;padding:20px;">3D viewer unavailable</p>';
            }} else {{
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
            }}

            this._updateProperties(selectedResult);
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

        const newSelector = inputSelector.cloneNode(true);
        inputSelector.parentNode.replaceChild(newSelector, inputSelector);
        newSelector.addEventListener('change', () => showStructure(parseInt(newSelector.value, 10)));
    }}

    _updateProperties(result) {{
        const propertiesDisplay = document.getElementById(`iuPropertiesDisplay_${{this.featureId}}`);
        if (!propertiesDisplay) return;

        if (!result) {{
            propertiesDisplay.innerHTML = '<p style="color:#999;">No prediction result for this input</p>';
            return;
        }}

        if (result.status === 'error') {{
            const errMsg = result.error ? this._escapeHtml(result.error) : 'Unknown prediction error';
            propertiesDisplay.innerHTML = `<p style="color:#c0392b;">${{errMsg}}</p>`;
            return;
        }}

        const properties = result.properties || {{}};
        const entries = Object.entries(properties);
        if (entries.length === 0) {{
            propertiesDisplay.innerHTML = '<p style="color:#999;">No properties returned for this input</p>';
            return;
        }}

        let html = '<div style="display:grid; gap:8px;">';
        const cifPropertyViews = [];

        entries.forEach(([propKey, value]) => {{
            const unit = this._propertyUnitByKey[propKey] || '';
            const displayLabel = this._formatLabelWithUnit(propKey, unit);

            if (this._isCifProperty(propKey, value)) {{
                const safeId = this._sanitizeDomId(`${{this.featureId}}_${{result.index}}_${{propKey}}`);
                const viewerId = `iuPropStructureViewer_${{safeId}}`;
                const textId = `iuPropCifViewer_${{safeId}}`;
                const toggleId = `iuPropToggleCifBtn_${{safeId}}`;

                html += `
                    <div style="padding:8px; background:#f9f9f9; border-radius:4px;">
                        <strong style="color:#333;">${{this._escapeHtml(displayLabel)}}</strong>
                        <div id="${{viewerId}}" style="width:100%; height:300px; position:relative; background:#ffffff; border-radius:6px; margin-top:6px;"></div>
                        <div style="margin-top:6px; text-align:right;">
                            <button id="${{toggleId}}" class="btn-secondary" style="font-size:11px; padding:4px 10px; cursor:pointer; background:#313244; color:#cdd6f4; border:1px solid #45475a; border-radius:4px;">Show CIF Text</button>
                        </div>
                        <pre id="${{textId}}" class="cif-viewer" style="display:none; max-height:240px; overflow:auto; background:#1e1e2e; color:#cdd6f4; padding:12px; border-radius:6px; font-size:12px; white-space:pre-wrap; margin-top:6px;"></pre>
                    </div>
                `;

                cifPropertyViews.push({{ viewerId, textId, toggleId, cifData: typeof value === 'string' ? value : '' }});
                return;
            }}

            let displayValue = 'N/A';
            if (value !== null && value !== undefined) {{
                if (typeof value === 'object') {{
                    displayValue = JSON.stringify(value);
                }} else {{
                    displayValue = String(value);
                }}
            }}

            const valueColor = displayValue === 'N/A' ? '#999' : '#333';
            html += `
                <div style="display:flex; justify-content:space-between; gap:12px; padding:6px; background:#f9f9f9; border-radius:4px; align-items:flex-start;">
                    <strong style="color:#333;">${{this._escapeHtml(displayLabel)}}</strong>
                    <span style="color:${{valueColor}}; font-family:monospace; text-align:right; white-space:pre-wrap; word-break:break-word;">${{this._escapeHtml(displayValue)}}</span>
                </div>
            `;
        }});

        html += '</div>';
        propertiesDisplay.innerHTML = html;

        cifPropertyViews.forEach((entry) => {{
            const viewerContainer = document.getElementById(entry.viewerId);
            const textEl = document.getElementById(entry.textId);
            const toggleBtn = document.getElementById(entry.toggleId);
            const cifData = entry.cifData || '';

            if (textEl) {{
                textEl.textContent = cifData || '(no CIF data available)';
            }}

            if (!viewerContainer || !cifData || typeof $3Dmol === 'undefined') {{
                if (viewerContainer) {{
                    viewerContainer.innerHTML = '<p style="color:#333;padding:20px;">3D viewer unavailable</p>';
                }}
            }} else {{
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
            }}

            if (toggleBtn && textEl) {{
                const newBtn = toggleBtn.cloneNode(true);
                toggleBtn.parentNode.replaceChild(newBtn, toggleBtn);
                newBtn.addEventListener('click', () => {{
                    const hidden = textEl.style.display === 'none';
                    textEl.style.display = hidden ? 'block' : 'none';
                    newBtn.textContent = hidden ? 'Hide CIF Text' : 'Show CIF Text';
                }});
            }}
        }});
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


def _discover_statuses() -> List[PredictorStatus]:
    pred_ids = _load_predictor_ids_from_factory()
    ui_meta = _load_predictor_meta_from_ui_data()

    index_text = _safe_read(INDEX_HTML)
    script_text = _safe_read(SCRIPT_JS)

    statuses: List[PredictorStatus] = []

    for pred_id in pred_ids:
        norm_id = _normalize_key(pred_id)
        display_name, description = ui_meta.get(norm_id, (pred_id, f"{pred_id} predictor"))
        class_name = f"{_to_pascal_case(pred_id)}IUFeature"
        feature_file = IU_FEATURE_PRED_DIR / f"{class_name}.js"

        statuses.append(
            PredictorStatus(
                pred_id=pred_id,
                display_name=display_name,
                description=description,
                mapping_exists=(PRED_MAPPING_DIR / f"{pred_id}.json").exists(),
                has_button=(f'data-iu-feature="{pred_id}"' in index_text),
                has_module=_has_module_entry(script_text, pred_id),
                has_feature_file=feature_file.exists(),
                feature_file=feature_file,
            )
        )

    return statuses


def _print_statuses(statuses: List[PredictorStatus]) -> None:
    print("\nPredictor IU Feature Status")
    print("=" * 76)
    print(f"{'#':<3} {'Predictor':<32} {'Implemented':<12} {'Button':<8} {'Module':<8} {'JS':<5} {'Mapping':<7}")
    print("-" * 76)

    for idx, s in enumerate(statuses, start=1):
        print(
            f"{idx:<3} {s.pred_id:<32} "
            f"{('yes' if s.is_fully_implemented else 'no'):<12} "
            f"{('yes' if s.has_button else 'no'):<8} "
            f"{('yes' if s.has_module else 'no'):<8} "
            f"{('yes' if s.has_feature_file else 'no'):<5} "
            f"{('yes' if s.mapping_exists else 'no'):<7}"
        )

    print("=" * 76)


def _next_module_id(script_text: str) -> int:
    ids = _extract_module_ids(script_text)
    return (max(ids) + 1) if ids else 2001


def _apply_add(target: PredictorStatus, auto_yes: bool = False) -> None:
    print(f"\nPreparing IU feature creation for: {target.pred_id} ({target.display_name})")

    if target.is_fully_implemented:
        print("IU feature is already fully implemented. No changes made.")
        return

    if not target.mapping_exists:
        print(f"Warning: property mapping file is missing: {PRED_MAPPING_DIR / (target.pred_id + '.json')}")

    if not auto_yes:
        choice = input("Proceed with add/update? [y/N]: ").strip().lower()
        if choice not in {"y", "yes"}:
            print("Cancelled.")
            return

    index_text = _safe_read(INDEX_HTML)
    script_text = _safe_read(SCRIPT_JS)

    class_name = f"{_to_pascal_case(target.pred_id)}IUFeature"
    rel_feature_path = f"./Features/IU_Features/Predictors/{class_name}.js"

    module_id = _next_module_id(script_text)
    index_text = _ensure_button_row(index_text, target.pred_id, target.display_name, target.description)
    script_text = _upsert_module_entry(script_text, target.pred_id, class_name, rel_feature_path, module_id)

    IU_FEATURE_PRED_DIR.mkdir(parents=True, exist_ok=True)
    if not target.feature_file.exists():
        content = _build_feature_js(class_name, target.pred_id, target.display_name, target.description)
        _safe_write(target.feature_file, content)
        print(f"Created JS IU feature: {target.feature_file.relative_to(ROOT)}")
    else:
        print(f"JS IU feature already exists: {target.feature_file.relative_to(ROOT)}")

    _safe_write(INDEX_HTML, index_text)
    _safe_write(SCRIPT_JS, script_text)

    print("Updated index.html and script.js for IU feature wiring.")


def _apply_remove(target: PredictorStatus, auto_yes: bool = False) -> None:
    print(f"\nPreparing IU feature removal for: {target.pred_id} ({target.display_name})")

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

    index_text = _remove_button_row(index_text, target.pred_id, target.display_name)
    script_text = _remove_module_entry(script_text, target.pred_id)

    _safe_write(INDEX_HTML, index_text)
    _safe_write(SCRIPT_JS, script_text)

    if target.feature_file.exists():
        target.feature_file.unlink()
        print(f"Removed JS IU feature: {target.feature_file.relative_to(ROOT)}")

    print("Removed IU feature wiring from index.html and script.js.")


def _select_target(candidates: List[PredictorStatus], prompt_title: str) -> Optional[PredictorStatus]:
    if not candidates:
        print("(none)")
        return None

    print(f"\n{prompt_title}")
    for idx, c in enumerate(candidates, start=1):
        print(f"  {idx}. {c.pred_id} ({c.display_name})")

    while True:
        raw = input("Select predictor number (or press Enter to cancel): ").strip()
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
    print("Predictor IU Feature Manager")
    print("=" * 60)
    print(f"Implemented IU features   : {len(implemented)}")
    print(f"Unimplemented IU features : {len(unimplemented)}")

    print("\nImplemented predictors:")
    if implemented:
        for item in implemented:
            print(f"  - {item.pred_id} ({item.display_name})")
    else:
        print("  (none)")

    print("\nUnimplemented predictors:")
    if unimplemented:
        for item in unimplemented:
            print(f"  - {item.pred_id} ({item.display_name})")
    else:
        print("  (none)")

    action = input("\nChoose action [add/remove/skip]: ").strip().lower()

    if action in {"skip", "", "exit", "quit", "no"}:
        print("No changes made.")
        return

    if action == "add":
        if not unimplemented:
            print("All predictor IU features are already implemented.")
            return
        target = _select_target(unimplemented, "Predictors available for IU feature addition:")
        if target:
            _apply_add(target)
        else:
            print("No selection made. No changes applied.")
        return

    if action == "remove":
        if not implemented:
            print("All predictor IU features are currently unimplemented.")
            return
        target = _select_target(implemented, "Predictors available for IU feature removal:")
        if target:
            _apply_remove(target)
        else:
            print("No selection made. No changes applied.")
        return

    print("Invalid action. No changes made.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage predictor IU feature scaffolding")
    parser.add_argument("--list", action="store_true", help="Only print current IU feature status")
    parser.add_argument("--add", metavar="PRED_ID", help="Add IU feature for a specific predictor id")
    parser.add_argument("--remove", metavar="PRED_ID", help="Remove IU feature for a specific predictor id")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    args = parser.parse_args()

    statuses = _discover_statuses()

    if args.list:
        _print_statuses(statuses)
        return

    if args.add and args.remove:
        raise SystemExit("Use either --add or --remove, not both.")

    if args.add:
        target = next((s for s in statuses if s.pred_id == args.add), None)
        if target is None:
            raise SystemExit(f"Unknown predictor id: {args.add}")
        _apply_add(target, auto_yes=args.yes)
        return

    if args.remove:
        target = next((s for s in statuses if s.pred_id == args.remove), None)
        if target is None:
            raise SystemExit(f"Unknown predictor id: {args.remove}")
        _apply_remove(target, auto_yes=args.yes)
        return

    run_interactive()


if __name__ == "__main__":
    main()
