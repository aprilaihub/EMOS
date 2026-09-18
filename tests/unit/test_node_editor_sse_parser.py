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


def test_graph_configuration_and_layout_can_be_saved_and_loaded_without_results():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()
    html = (Path(__file__).parents[2] / "node-editor.html").read_text()

    assert "const GRAPH_FILE_FORMAT = 'emos-node-graph';" in source
    assert "const GRAPH_FILE_VERSION = 1;" in source
    assert "function saveGraph()" in source
    assert "function createGraphFile()" in source
    assert "function serializeGraphNode(node)" in source
    assert "function loadGraphFromFile(event)" in source
    assert "async function loadGraph(graph)" in source
    assert "function validateGraphFile(graph)" in source
    assert "function restoreGraphConnections(connections)" in source
    assert "function clearGraphWithoutConfirmation()" in source
    assert "Runtime results are not restored." in source
    assert "nodes: Object.values(nodes).map(serializeGraphNode)" in source
    assert "connections: wires.map(wire => ({" in source
    assert 'id="neSaveGraphBtn"' in html
    assert 'id="neLoadGraphBtn"' in html
    assert 'id="neLoadGraphInput"' in html


def test_graph_save_load_preserves_dynamic_node_configuration():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    assert "configuration.filterRules = serializeFilterRules(node);" in source
    assert "configuration.treeSelections = [...node.treeSelections];" in source
    assert "configuration.inputs = node.inputs.map(input => ({" in source
    assert "configuration.outputPorts = node.outputs.map(output => ({" in source
    assert "function serializeFilterRules(node)" in source
    assert "function restoreMergerInputs(node, inputs)" in source
    assert "function restoreDynamicOutputPorts(node, outputs)" in source
    assert "function restoreFilterRules(node, rules)" in source
    assert "node.treeSelections = new Set((configuration.treeSelections || [])" in source
    assert "...node.prettyFieldSelections" in source


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


def test_feature_nodes_are_metadata_driven_and_use_existing_feature_api():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()
    html = (Path(__file__).parents[2] / "node-editor.html").read_text()

    assert "let FEATURE_DEFINITIONS = {}" in source
    assert "function populateFeatureSidebar(category, containerId)" in source
    assert "function getFeatureNodeSchema(feature)" in source
    assert "function buildFeatureNodeBody(node)" in source
    assert "async function executeFeatureNode(backendUrl, node)" in source
    assert "${backendUrl}/api/process/${node.key}" in source
    assert 'id="sidebarMaterialsFeatures"' in html
    assert 'id="sidebarElectronicsFeatures"' in html


def test_feature_cif_inputs_and_local_iu_selectors_have_adapters():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    assert "data-feature-field-type=\"iu_checkbox_group\"" in source
    assert "el.dataset.featureFieldType === 'iu_checkbox_group'" in source
    assert "inputs[cifField.name] = cifStrings;" in source
    assert "inputs.labels = cifStrings.map" in source
    assert "outputs: [{ key: 'result_out', label: 'Result', type: PORT_TYPES.RESULT }]" in source
    assert "node.portData = { result_out: result };" in source


def test_splitter_creates_outputs_from_top_level_result_fields_only():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()
    html = (Path(__file__).parents[2] / "node-editor.html").read_text()

    assert "splitter:" in source
    assert "function executeSplitterNode(node)" in source
    assert "function getSplitterOutputDescriptors(value, inputWire)" in source
    assert "function getFeatureSplitterOutputs(feature, value)" in source
    assert "function getRuntimeSplitterOutputs(value)" in source
    assert "function isCifStringList(value)" in source
    assert "sourceNode?.type === 'feature'" in source
    assert "feature?.outputs || []" in source
    assert "[{ key: 'split_cif', label: 'CIF', type: PORT_TYPES.CIF, value }]" in source
    assert "function updateDynamicOutputPorts(node, desiredOutputs)" in source
    assert "function syncSplitterHeight(node)" in source
    assert "const requiredHeight = Math.max(132, 72 + (portCount - 1) * 24);" in source
    assert "function renderOutputPorts(node)" in source
    assert "wrapper.append(label, port);" in source
    assert "Object.keys(item).forEach(key => keys.add(key));" in source
    assert "data-node-key=\"splitter\"" in html


def test_output_labels_are_inside_nodes_before_right_edge_pins():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()
    css = (Path(__file__).parents[2] / "node-editor.css").read_text()

    assert "width: type === 'feature' ? 360 : 320" in source
    assert "wrapper.append(label, port);" in source
    assert "min-width: 300px;" in css
    assert "right: -6px;" in css
    assert "justify-content: flex-end;" in css
    assert "padding: 8px 28px;" in css


def test_splitter_logs_raw_input_before_its_done_log():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()

    splitter = source[source.index("function executeSplitterNode(node)") : source.index("function getSplitterInputWire", source.index("function executeSplitterNode(node)"))]
    assert "clearNodeLog(node.id);" in splitter
    assert "addNodeLog(node.id, formatSplitterInput(input), 'raw');" in splitter
    assert "function formatSplitterInput(input)" in source


def test_tree_splitter_and_merger_are_registered_local_utilities():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()
    html = (Path(__file__).parents[2] / "node-editor.html").read_text()

    assert "tree_splitter:" in source
    assert "merger:" in source
    assert "function executeTreeSplitterNode(node)" in source
    assert "function updateTreeSplitterOutputs(node)" in source
    assert "function removeTreeSplitterOutput(node, output)" not in source
    assert "ne-dynamic-output-remove" not in source
    assert "function executeMergerNode(node)" in source
    assert "function addMergerInput(node)" in source
    assert "function refreshMergerInputLabels(nodeId)" in source
    assert "function renderInputPorts(node, container = node.el)" in source
    assert "function getMergerInputs(node)" in source
    assert "function getMergerInputConnections(node)" in source
    assert "getMergerInputConnections(node).length >= 2" in source
    assert "origin?.key === 'tree_splitter' && originOutput?.label" in source
    assert ": origin?.name || input.defaultLabel || input.label;" in source
    assert "originOutput.label.replace(/\\s*>\\s*/g, ' - ')" in source
    assert "Merge pairs requires all connected lists to have the same length." in source
    assert "result = connectedInputs.flatMap(input => input.value);" in source
    assert "Object.fromEntries(connectedInputs.map(input => [input.name, input.value[index]]))" in source
    assert "const outputType = splitterPortType(null, result);" in source
    assert "label: outputType === PORT_TYPES.CIF ? 'CIF' : 'Result'" in source
    assert "<label><span>Merge pairs</span><input type=\"radio\"" in source
    assert "data-node-key=\"tree_splitter\"" in html
    assert "data-node-key=\"merger\"" in html


def test_processing_status_has_an_animated_indicator():
    source = (Path(__file__).parents[2] / "node-editor.js").read_text()
    css = (Path(__file__).parents[2] / "node-editor.css").read_text()

    assert "statusText.classList.toggle('ne-status-processing', active);" in source
    assert ".ne-status-processing::after" in css
    assert "@keyframes ne-processing-dots" in css


def test_tree_splitter_and_merger_controls_override_shared_input_sizing():
    css = (Path(__file__).parents[2] / "node-editor.css").read_text()

    assert ".ne-node-body .ne-tree-splitter-entry input" in css
    assert ".ne-node-body .ne-merger-mode input" in css
    assert "min-width: 14px;" in css
    assert "justify-content: space-between;" in css


def test_pretty_labels_wrap_and_merger_options_stay_close_to_radios():
    css = (Path(__file__).parents[2] / "node-editor.css").read_text()

    assert "grid-template-columns: repeat(2, max-content);" in css
    assert "justify-content: flex-start;" in css
    assert "grid-template-columns: minmax(0, 1fr);" in css
    assert "white-space: normal;" in css
    assert "overflow-wrap: anywhere;" in css


def test_running_nodes_show_the_provided_spinner_next_to_their_titles():
    project_root = Path(__file__).parents[2]
    source = (project_root / "node-editor.js").read_text()
    css = (project_root / "node-editor.css").read_text()
    spinner = (project_root / "images" / "ball-triangle.svg").read_text()

    assert "ne-node-title-wrap" in source
    assert 'src="images/ball-triangle.svg"' in source
    assert ".ne-node.state-running .ne-node-spinner" in css
    assert "<animate" in spinner


def test_feature_metadata_matches_current_runtime_names():
    metadata = (Path(__file__).parents[2] / "devtools/ui_data.json").read_text()

    assert '"name": "active_databases"' in metadata
    assert '"name": "active_predictors"' in metadata
    assert '"name": "cif_strings"' in metadata
    assert '"name": "numberOfGatePoints"' in metadata
    assert '"name": "channelWidthNm"' not in metadata
    assert '"name": "cifFiles"' not in metadata
