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
