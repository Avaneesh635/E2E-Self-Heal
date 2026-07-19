from app.preprocess.jsx_chunker import chunk_for_line, extract_error_line


def test_extracts_failing_line_from_error_log():
    assert extract_error_line("Error\nat tests/login.spec.ts:12") == 12


def test_returns_smallest_nested_jsx_element_with_margin():
    source = """export function App() {
  return (
    <section>
      <form>
        <button id="save">
          Save
        </button>
      </form>
    </section>
  )
}
"""

    chunk = chunk_for_line(source, 5, margin=1)

    assert chunk.is_fallback is False
    assert chunk.start_line == 4
    assert chunk.end_line == 8
    assert '<button id="save">' in chunk.source
    assert "</button>" in chunk.source
    assert "<section>" not in chunk.source


def test_returns_self_closing_jsx_element_slice():
    source = """export function IconButton() {
  return (
    <Toolbar>
      <IconButton aria-label="Save" />
    </Toolbar>
  )
}
"""

    chunk = chunk_for_line(source, 4, margin=0)

    assert chunk.is_fallback is False
    assert chunk.start_line == 4
    assert chunk.end_line == 4
    assert chunk.source.strip() == '<IconButton aria-label="Save" />'


def test_returns_fragment_slice_when_fragment_is_smallest_parent():
    source = """export function EmptyState() {
  return (
    <>
      Plain text
    </>
  )
}
"""

    chunk = chunk_for_line(source, 4, margin=0)

    assert chunk.is_fallback is False
    assert chunk.start_line == 3
    assert chunk.end_line == 5
    assert "<>" in chunk.source
    assert "</>" in chunk.source


def test_falls_back_to_whole_file_when_no_jsx_parent():
    source = """const label = "Save";
const timeout = 5000;
"""

    chunk = chunk_for_line(source, 1, margin=1)

    assert chunk.is_fallback is True
    assert chunk.start_line == 1
    assert chunk.end_line == 2
    assert chunk.source == source


def test_falls_back_to_whole_file_when_line_missing():
    source = "<button>Save</button>\n"

    chunk = chunk_for_line(source, None)

    assert chunk.is_fallback is True
    assert chunk.source == source
