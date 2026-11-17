"""Focused browser-only viewer checks; follows the node editor's pytest entry point."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_data_viewer_adapter_and_worker():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is needed for executable Data Viewer checks")
    result = subprocess.run(
        [node, str(ROOT / "tests/unit/data_viewer_checks.cjs")],
        cwd=ROOT, text=True, capture_output=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_data_viewer_graph_boundaries_and_local_assets():
    source = (ROOT / "node-editor.js").read_text()
    html = (ROOT / "node-editor.html").read_text()
    branch = source[source.index("function displayViewerData(node)"):]
    assert branch.index("node.dataViewer.load(upstreamData.data_in, upstreamData.labels_in)") < branch.index("Object.keys(upstreamData)[0]")
    assert "label: 'X / Labels (optional)', type: PORT_TYPES.ANY, required: false" in source
    assert "node?.dataViewer?.reset('Upstream input changed." in source
    assert source.count("node.dataViewer?.destroy()") == 3
    assert "configuration.dataViewer = node.dataViewer.configuration()" in source
    for asset in ["data-viewer.js", "vendor/uplot-1.6.32/uPlot.iife.min.js", "vendor/uplot-1.6.32/uPlot.min.css"]:
        assert asset in html
        assert (ROOT / asset).is_file()
    assert html.index('src="data-viewer.js"') < html.index('src="node-editor.js"')
    assert (ROOT / "vendor/uplot-1.6.32/LICENSE").is_file()
    assert "MIT" in (ROOT / "vendor/tsnejs-13ece5d/Readme.md").read_text()
