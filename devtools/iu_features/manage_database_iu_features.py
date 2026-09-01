#!/usr/bin/env python3
"""Interactive utility to add/remove database IU features.

This script automates the frontend wiring needed for database IU features:
- Adds/removes IU feature button rows in index.html
- Adds/removes IU feature module entries in script.js
- Creates/removes IU feature JS implementation files

It assumes database IUs and property mappings already exist.
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
DB_FACTORY_PY = ROOT / "Information_Units" / "Databases" / "DatabaseFactory.py"
DB_MAPPING_DIR = ROOT / "Information_Units" / "property_mappings" / "sources" / "databases"
IU_FEATURE_DB_DIR = ROOT / "Features" / "IU_Features" / "Databases"


@dataclass
class DatabaseStatus:
    db_id: str
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


def _to_pascal_case(db_id: str) -> str:
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", db_id) if p]
    if parts:
        return "".join(p[:1].upper() + p[1:].lower() for p in parts)
    return db_id[:1].upper() + db_id[1:].lower()


def _safe_read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _safe_write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _load_database_ids_from_factory() -> List[str]:
    src = _safe_read(DB_FACTORY_PY)
    tree = ast.parse(src)

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "database_factory":
                    if isinstance(node.value, ast.Dict):
                        db_ids: List[str] = []
                        for key_node in node.value.keys:
                            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                                db_ids.append(key_node.value)
                        return db_ids

    raise RuntimeError("Could not find database_factory in DatabaseFactory.py")


def _load_database_meta_from_ui_data() -> Dict[str, Tuple[str, str]]:
    payload = json.loads(_safe_read(UI_DATA_JSON))
    db_map = payload.get("information_units", {}).get("databases", {})

    by_norm: Dict[str, Tuple[str, str]] = {}
    for display_name, description in db_map.items():
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


def _extract_database_module_block(script_text: str) -> Tuple[int, int, str]:
    _, db_open, db_close = _find_js_object_bounds(script_text, "database: {")
    return db_open, db_close, script_text[db_open + 1: db_close]


def _module_entry_regex(db_id: str) -> re.Pattern[str]:
    return re.compile(rf"\n\s*{re.escape(db_id)}\s*:\s*\{{.*?\n\s*\}},", re.S)


def _extract_module_ids(script_text: str) -> List[int]:
    _, _, block = _extract_database_module_block(script_text)
    ids = re.findall(r"\bid\s*:\s*(\d+)\s*,", block)
    return [int(v) for v in ids]


def _has_module_entry(script_text: str, db_id: str) -> bool:
    _, _, block = _extract_database_module_block(script_text)
    return re.search(rf"\b{re.escape(db_id)}\s*:\s*\{{", block) is not None


def _upsert_module_entry(script_text: str, db_id: str, class_name: str, feature_path: str, module_id: int) -> str:
    db_open, db_close, block = _extract_database_module_block(script_text)
    cleaned = _module_entry_regex(db_id).sub("", block).rstrip()

    entry = (
        f"        {db_id}: {{\n"
        f"            className: '{class_name}',\n"
        f"            file: '{feature_path}',\n"
        f"            id: {module_id},\n"
        f"        }},"
    )

    if cleaned.strip():
        new_block = cleaned + "\n" + entry + "\n    "
    else:
        new_block = "\n" + entry + "\n    "

    return script_text[: db_open + 1] + new_block + script_text[db_close:]


def _remove_module_entry(script_text: str, db_id: str) -> str:
    db_open, db_close, block = _extract_database_module_block(script_text)
    updated = _module_entry_regex(db_id).sub("", block).rstrip()
    if updated.strip():
        new_block = updated + "\n    "
    else:
        new_block = "\n    "
    return script_text[: db_open + 1] + new_block + script_text[db_close:]


def _row_block_regex(db_id: str) -> re.Pattern[str]:
    return re.compile(
        rf"\n\s*<div class=\"iu-option-row\">\s*"
        rf"<span class=\"iu-option-name\">.*?</span>\s*"
        rf"<button\b[^>]*data-iu-feature=\"{re.escape(db_id)}\"[^>]*>[\s\S]*?</button>\s*"
        rf"</div>",
        re.S,
    )


def _plain_label_regex(db_id: str, display_name: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?m)^\s*<span class=\"iu-option-name\">\s*{re.escape(display_name)}\s*</span>\s*$"
    )


def _build_button_row(db_id: str, display_name: str, description: str) -> str:
    return (
        "                            <div class=\"iu-option-row\">\n"
        f"                                <span class=\"iu-option-name\">{display_name}</span>\n"
        "                                <button\n"
        "                                    class=\"iu-feature-btn\"\n"
        f"                                    data-iu-feature=\"{db_id}\"\n"
        "                                    data-iu-type=\"database\"\n"
        f"                                    data-iu-name=\"{display_name}\"\n"
        f"                                    data-iu-desc=\"{description}\"\n"
        "                                    title=\"Open IU panel\"\n"
        "                                    aria-label=\"Open IU panel\"\n"
        "                                >&#9654;</button>\n"
        "                            </div>"
    )


def _ensure_button_row(index_text: str, db_id: str, display_name: str, description: str) -> str:
    row_re = _row_block_regex(db_id)
    if row_re.search(index_text):
        return index_text

    label_re = _plain_label_regex(db_id, display_name)
    row = _build_button_row(db_id, display_name, description)

    if label_re.search(index_text):
        return label_re.sub(row, index_text, count=1)

    anchor = '                            </div>\n                        </div>'
    idx = index_text.find(anchor)
    if idx < 0:
        raise RuntimeError("Could not find insertion anchor in index.html databases list")

    return index_text[:idx] + row + "\n" + index_text[idx:]


def _remove_button_row(index_text: str, db_id: str, display_name: str) -> str:
    row_re = _row_block_regex(db_id)
    plain_label = f'                            <span class="iu-option-name">{display_name}</span>'

    if row_re.search(index_text):
        return row_re.sub("\n" + plain_label, index_text, count=1)

    return index_text


def _build_feature_js(class_name: str, db_id: str, title: str, description: str) -> str:
    return f"""// Auto-generated IU Feature for database: {db_id}
class {class_name} extends BaseFeature {{
    constructor(featureId, iuMeta = {{}}) {{
        super(
            featureId,
            iuMeta.iuName ? `${{iuMeta.iuName}} IU Feature` : '{title} IU Feature',
            iuMeta.iuDesc || '{description}'
        );
        this.iuType = iuMeta.iuType || 'database';
        this.iuId = iuMeta.iuId || '{db_id}';
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
                    <label>Target Compositions
                        <input type="text" id="target_compositions_${{this.featureId}}" placeholder="e.g., Fe, Al2O3, GaAs">
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
                    <strong>Retrieved Dataset (JSON):</strong>
                    <span id="iuDataRetrievedStatus_${{this.featureId}}">Pending...</span>
                    <a id="iuDataRetrievedDownload_${{this.featureId}}" style="display:none; margin-left:10px;" download="${{this.iuId}}_retrieved_dataset.json">Download</a>
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
                fetch(`./Information_Units/property_mappings/sources/databases/${{this.iuId}}.json`),
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
                    retrievable: cfg?.retrievable !== false,
                    unit: commonProperties?.[name]?.unit || '',
                }}))
                .filter((p) => p.retrievable);

            this._propertyDefs = defs;

            if (defs.length === 0) {{
                container.innerHTML = '<p>No retrievable properties found in property mapping.</p>';
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
        const targetEl = document.getElementById(`target_compositions_${{this.featureId}}`);
        const batchEl = document.getElementById(`batch_size_${{this.featureId}}`);

        const inputs = {{
            target_compositions: targetEl?.value?.trim() || '',
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

        const response = await fetch(`${{backendUrl}}/api/process/iu/${{this.iuType}}/${{this.iuId}}`, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(inputs),
            signal: this._abortController.signal,
        }});

        if (!response.ok) {{
            const errBody = await response.text();
            throw new Error(`HTTP ${{response.status}}: ${{errBody}}`);
        }}

        const payload = await response.json();

        if (payload.logs && Array.isArray(payload.logs)) {{
            payload.logs.forEach((log) => this.addLog(log.message, log.level || 'info'));
        }}

        return payload.results || payload;
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
            const statusEl = document.getElementById(`iuDataRetrievedStatus_${{this.featureId}}`);
            const downloadEl = document.getElementById(`iuDataRetrievedDownload_${{this.featureId}}`);
            if (statusEl) statusEl.textContent = `Error: ${{data.error}}`;
            if (downloadEl) downloadEl.style.display = 'none';
            return;
        }}

        const statusEl = document.getElementById(`iuDataRetrievedStatus_${{this.featureId}}`);
        const downloadEl = document.getElementById(`iuDataRetrievedDownload_${{this.featureId}}`);

        if (this._downloadUrl) {{
            URL.revokeObjectURL(this._downloadUrl);
            this._downloadUrl = null;
        }}

        if (downloadEl) {{
            const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
            this._downloadUrl = URL.createObjectURL(blob);
            downloadEl.href = this._downloadUrl;
            downloadEl.download = `${{this.iuId}}_retrieved_dataset_${{Date.now()}}.json`;
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


def _discover_statuses() -> List[DatabaseStatus]:
    db_ids = _load_database_ids_from_factory()
    ui_meta = _load_database_meta_from_ui_data()

    index_text = _safe_read(INDEX_HTML)
    script_text = _safe_read(SCRIPT_JS)

    statuses: List[DatabaseStatus] = []

    for db_id in db_ids:
        norm_id = _normalize_key(db_id)
        display_name, description = ui_meta.get(norm_id, (db_id, f"{db_id} database"))
        class_name = f"{_to_pascal_case(db_id)}IUFeature"
        feature_file = IU_FEATURE_DB_DIR / f"{class_name}.js"

        statuses.append(
            DatabaseStatus(
                db_id=db_id,
                display_name=display_name,
                description=description,
                mapping_exists=(DB_MAPPING_DIR / f"{db_id}.json").exists(),
                has_button=(f'data-iu-feature="{db_id}"' in index_text),
                has_module=_has_module_entry(script_text, db_id),
                has_feature_file=feature_file.exists(),
                feature_file=feature_file,
            )
        )

    return statuses


def _print_statuses(statuses: List[DatabaseStatus]) -> None:
    print("\nDatabase IU Feature Status")
    print("=" * 76)
    print(f"{'#':<3} {'Database':<18} {'Implemented':<12} {'Button':<8} {'Module':<8} {'JS':<5} {'Mapping':<7}")
    print("-" * 76)

    for idx, s in enumerate(statuses, start=1):
        print(
            f"{idx:<3} {s.db_id:<18} "
            f"{('yes' if s.is_fully_implemented else 'no'):<12} "
            f"{('yes' if s.has_button else 'no'):<8} "
            f"{('yes' if s.has_module else 'no'):<8} "
            f"{('yes' if s.has_feature_file else 'no'):<5} "
            f"{('yes' if s.mapping_exists else 'no'):<7}"
        )

    print("=" * 76)


def _next_module_id(script_text: str) -> int:
    ids = _extract_module_ids(script_text)
    return (max(ids) + 1) if ids else 1001


def _apply_add(target: DatabaseStatus, auto_yes: bool = False) -> None:
    print(f"\nPreparing IU feature creation for: {target.db_id} ({target.display_name})")

    if target.is_fully_implemented:
        print("IU feature is already fully implemented. No changes made.")
        return

    if not target.mapping_exists:
        print(f"Warning: property mapping file is missing: {DB_MAPPING_DIR / (target.db_id + '.json')}")

    if not auto_yes:
        choice = input("Proceed with add/update? [y/N]: ").strip().lower()
        if choice not in {"y", "yes"}:
            print("Cancelled.")
            return

    index_text = _safe_read(INDEX_HTML)
    script_text = _safe_read(SCRIPT_JS)

    class_name = f"{_to_pascal_case(target.db_id)}IUFeature"
    rel_feature_path = f"./Features/IU_Features/Databases/{class_name}.js"

    module_id = _next_module_id(script_text)
    index_text = _ensure_button_row(index_text, target.db_id, target.display_name, target.description)
    script_text = _upsert_module_entry(script_text, target.db_id, class_name, rel_feature_path, module_id)

    IU_FEATURE_DB_DIR.mkdir(parents=True, exist_ok=True)
    if not target.feature_file.exists():
        content = _build_feature_js(class_name, target.db_id, target.display_name, target.description)
        _safe_write(target.feature_file, content)
        print(f"Created JS IU feature: {target.feature_file.relative_to(ROOT)}")
    else:
        print(f"JS IU feature already exists: {target.feature_file.relative_to(ROOT)}")

    _safe_write(INDEX_HTML, index_text)
    _safe_write(SCRIPT_JS, script_text)

    print("Updated index.html and script.js for IU feature wiring.")


def _apply_remove(target: DatabaseStatus, auto_yes: bool = False) -> None:
    print(f"\nPreparing IU feature removal for: {target.db_id} ({target.display_name})")

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

    index_text = _remove_button_row(index_text, target.db_id, target.display_name)
    script_text = _remove_module_entry(script_text, target.db_id)

    _safe_write(INDEX_HTML, index_text)
    _safe_write(SCRIPT_JS, script_text)

    if target.feature_file.exists():
        target.feature_file.unlink()
        print(f"Removed JS IU feature: {target.feature_file.relative_to(ROOT)}")

    print("Removed IU feature wiring from index.html and script.js.")


def _select_target(candidates: List[DatabaseStatus], prompt_title: str) -> Optional[DatabaseStatus]:
    if not candidates:
        print("(none)")
        return None

    print(f"\n{prompt_title}")
    for idx, c in enumerate(candidates, start=1):
        print(f"  {idx}. {c.db_id} ({c.display_name})")

    while True:
        raw = input("Select database number (or press Enter to cancel): ").strip()
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
    print("Database IU Feature Manager")
    print("=" * 60)
    print(f"Implemented IU features   : {len(implemented)}")
    print(f"Unimplemented IU features : {len(unimplemented)}")

    print("\nImplemented databases:")
    if implemented:
        for item in implemented:
            print(f"  - {item.db_id} ({item.display_name})")
    else:
        print("  (none)")

    print("\nUnimplemented databases:")
    if unimplemented:
        for item in unimplemented:
            print(f"  - {item.db_id} ({item.display_name})")
    else:
        print("  (none)")

    action = input("\nChoose action [add/remove/skip]: ").strip().lower()

    if action in {"skip", "", "exit", "quit", "no"}:
        print("No changes made.")
        return

    if action == "add":
        if not unimplemented:
            print("All database IU features are already implemented.")
            return
        target = _select_target(unimplemented, "Databases available for IU feature addition:")
        if target:
            _apply_add(target)
        else:
            print("No selection made. No changes applied.")
        return

    if action == "remove":
        if not implemented:
            print("All database IU features are currently unimplemented.")
            return
        target = _select_target(implemented, "Databases available for IU feature removal:")
        if target:
            _apply_remove(target)
        else:
            print("No selection made. No changes applied.")
        return

    print("Invalid action. No changes made.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage database IU feature scaffolding")
    parser.add_argument("--list", action="store_true", help="Only print current IU feature status")
    parser.add_argument("--add", metavar="DB_ID", help="Add IU feature for a specific database id")
    parser.add_argument("--remove", metavar="DB_ID", help="Remove IU feature for a specific database id")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    args = parser.parse_args()

    statuses = _discover_statuses()

    if args.list:
        _print_statuses(statuses)
        return

    if args.add and args.remove:
        raise SystemExit("Use either --add or --remove, not both.")

    if args.add:
        target = next((s for s in statuses if s.db_id == args.add), None)
        if target is None:
            raise SystemExit(f"Unknown database id: {args.add}")
        _apply_add(target, auto_yes=args.yes)
        return

    if args.remove:
        target = next((s for s in statuses if s.db_id == args.remove), None)
        if target is None:
            raise SystemExit(f"Unknown database id: {args.remove}")
        _apply_remove(target, auto_yes=args.yes)
        return

    run_interactive()


if __name__ == "__main__":
    main()
