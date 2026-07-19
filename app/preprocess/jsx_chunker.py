"""Semantic JSX chunking for bounded LLM context."""

import importlib.util
import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

_HAS_TREE_SITTER = (
    importlib.util.find_spec("tree_sitter") is not None
    and importlib.util.find_spec("tree_sitter_typescript") is not None
)
_LOCATION_LINE_RE = re.compile(r"\bat\s+[\w./\\-]+\.(?:spec|test)\.[jt]sx?:(\d+)\b")
_JSX_NODE_TYPES = {"jsx_element", "jsx_self_closing_element", "jsx_fragment"}


@dataclass(frozen=True)
class CodeChunk:
    """Source slice selected for LLM context."""

    source: str
    start_line: int
    end_line: int
    is_fallback: bool = False


def extract_error_line(error_log: str) -> int | None:
    """Extract the failing source line from the normalized Playwright error log."""
    match = _LOCATION_LINE_RE.search(error_log)
    if not match:
        return None
    return int(match.group(1))


def chunk_for_line(source: str, line: int | None, margin: int = 1) -> CodeChunk:
    """Return the smallest enclosing JSX node around ``line``, or the whole file."""
    lines = source.splitlines()
    if not source or line is None or line < 1 or line > max(len(lines), 1):
        return _whole_file_chunk(source)
    if not _HAS_TREE_SITTER:
        return _whole_file_chunk(source)

    try:
        chunk = _chunk_for_line_tree_sitter(source, line, margin)
    except Exception as exc:
        logger.warning("jsx_chunk_tree_sitter_failed_falling_back", error=str(exc))
        return _whole_file_chunk(source)
    return chunk or _whole_file_chunk(source)


def _chunk_for_line_tree_sitter(source: str, line: int, margin: int) -> CodeChunk | None:
    import tree_sitter_typescript as ts_typescript
    from tree_sitter import Language, Parser

    code_bytes = source.encode("utf-8")
    tsx_language = Language(ts_typescript.language_tsx())
    parser = Parser(tsx_language)
    tree = parser.parse(code_bytes)
    target_row = line - 1
    best = None

    def walk(node) -> None:
        nonlocal best
        start_row = node.start_point[0]
        end_row = node.end_point[0]
        if start_row <= target_row <= end_row and node.type in _JSX_NODE_TYPES:
            if best is None or _line_span(node) < _line_span(best):
                best = node
        for child in node.children:
            if child.start_point[0] <= target_row <= child.end_point[0]:
                walk(child)

    walk(tree.root_node)
    if best is None:
        return None

    lines = source.splitlines(keepends=True)
    start_line = max(1, best.start_point[0] + 1 - max(margin, 0))
    end_line = min(len(lines), best.end_point[0] + 1 + max(margin, 0))
    return CodeChunk(
        source="".join(lines[start_line - 1 : end_line]),
        start_line=start_line,
        end_line=end_line,
    )


def _line_span(node) -> int:
    return node.end_point[0] - node.start_point[0]


def _whole_file_chunk(source: str) -> CodeChunk:
    line_count = len(source.splitlines()) or 1
    return CodeChunk(source=source, start_line=1, end_line=line_count, is_fallback=True)
