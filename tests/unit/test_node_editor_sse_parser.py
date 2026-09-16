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
