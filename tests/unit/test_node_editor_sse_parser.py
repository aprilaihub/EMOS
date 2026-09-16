from pathlib import Path


def test_sse_event_type_survives_stream_chunk_boundaries():
    """Large result data can arrive in later reads than its event header."""
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    event_declaration = source.index("let currentEvent = 'log';")
    read_function = source.index("function read()", event_declaration)

    assert event_declaration < read_function
    assert "let currentEvent = 'log';" not in source[
        read_function : source.index("read();", read_function)
    ]


def test_execution_controls_use_a_persisted_sequential_scheduler():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    assert "const executionState = {" in source
    assert "async function startExecution(runMode)" in source
    assert "while (executionState.status === 'running')" in source
    assert "function getNextEligibleNode()" in source
    assert "if (runMode === 'step')" in source


def test_breakpoints_pause_after_their_node_completes():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    completion = source.index("completeNode(node, result);")
    breakpoint = source.index("if (node.breakpointEnabled)", completion)

    assert completion < breakpoint
    assert "pauseExecution('breakpoint'" in source[breakpoint : breakpoint + 300]


def test_cancellation_preserves_prior_results_and_retries_active_node():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    cancellation = source.index("function requestCancellation()")
    active_cancel = source[cancellation : source.index("async function sendBackendCancel", cancellation)]

    assert "if (!executionState.activeNodeCanCancel)" in active_cancel
    assert "executionState.status = 'finishing_after_cancel';" in active_cancel
    assert "clearNodeOutput(node);" in active_cancel
    assert "setNodeState(node.id, 'pending');" in active_cancel
    assert "activeSseCancel" in source


def test_runtime_and_canvas_clears_require_confirmation():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()
    html = (Path(__file__).parents[2] / "node-editor.html").read_text()

    assert "async function clearOutputsWithConfirmation()" in source
    assert "async function clearCanvasWithConfirmation()" in source
    assert "showConfirmation(" in source
    assert 'id="neConfirmDialog"' in html
    assert 'id="neClearCanvasBtn"' in html


def test_completed_results_enable_node_and_aggregate_downloads():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()
    html = (Path(__file__).parents[2] / "node-editor.html").read_text()

    assert "function createNodeResultRecord(node)" in source
    assert "function downloadNodeResult(node)" in source
    assert "function downloadAllResults()" in source
    assert "function downloadJson(filename, value)" in source
    assert "node.resultRecord = createNodeResultRecord(node);" in source
    assert "downloadAllBtn.disabled = !hasCompletedResult();" in source
    assert 'id="neDownloadAllBtn"' in html


def test_resized_nodes_resize_their_log_and_viewer_content():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    assert "function resizeNodeContent(node, nodeHeight)" in source
    assert "log.style.height" in source
    assert "log.style.maxHeight" in source
    assert "textContent.style.maxHeight" in source
    assert "cifContainer.style.height" in source


def test_filter_rules_compare_true_and_false_values():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    assert "function parseBoolean(value)" in source
    assert "const booleanValue = parseBoolean(raw);" in source
    assert "const booleanThreshold = parseBoolean(rule.val);" in source


def test_cif_viewer_uses_compositions_and_renders_an_atom_legend():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    assert "function getCifComposition(cifString, index)" in source
    assert "opt.textContent = getCifComposition(cif, i);" in source
    assert "function renderCIFLegend(nodeId, elements)" in source
    assert "colorscheme: 'Jmol'" in source


def test_clearing_cif_viewer_output_also_removes_its_legend():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    reset = source[source.index("function resetViewerDisplay(node)") : source.index("function resetExecutionState", source.index("function resetViewerDisplay(node)"))]

    assert "cif-legend-${node.id}" in reset
    assert "legend.innerHTML = '';" in reset
    assert "legend.hidden = true;" in reset


def test_filter_requires_results_but_not_cif_input():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    assert "label: 'CIF (optional)'" in source
    assert "required: false" in source
    assert "function getRequiredInputs(node)" in source
    assert "Filter requires result data from a predictor." in source
    assert "res?.cif_input" in source


def test_pretty_text_viewer_exposes_selectable_result_fields():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    assert "ne-text-pretty-toggle" in source
    assert "function getPrettyFields(entries)" in source
    assert "function collectPrettyFields(value, prefix, fields)" in source
    assert "function renderPrettyFieldToggles(container, fields, node, data)" in source
    assert "function needsPrettyFieldRender(container, fields)" in source
    assert "function getMaterialName(entry, index)" in source
    assert "field.replace('.', ' - ')" in source
