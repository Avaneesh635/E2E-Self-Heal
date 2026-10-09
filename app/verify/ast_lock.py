"""Fail-closed structural lock for generated TypeScript and JavaScript patches."""

from __future__ import annotations

from typing import Final

import tree_sitter_typescript as ts_typescript
from pydantic import BaseModel, ConfigDict, Field
from tree_sitter import Language, Node, Parser, Tree


class AstLockAllowlist(BaseModel):
    """Reviewable data describing the only AST values a patch may change."""

    model_config = ConfigDict(frozen=True)

    locator_methods: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {
                "locator",
                "getByRole",
                "getByText",
                "getByLabel",
                "getByPlaceholder",
                "getByAltText",
                "getByTitle",
                "getByTestId",
            }
        )
    )
    # Page-level actions whose FIRST argument is a selector (``page.click(selector)``). Every
    # other argument (values, keys, options) stays locked. Mirrors the regex scope gate.
    page_selector_methods: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {
                "check",
                "click",
                "dblclick",
                "fill",
                "focus",
                "hover",
                "press",
                "selectOption",
                "setInputFiles",
                "type",
                "uncheck",
                "waitForSelector",
            }
        )
    )
    # Receivers that make ``page_selector_methods`` selector-first. A ``locator.click(x)`` call
    # has no selector argument, so it must not be matched by method name alone.
    page_receivers: frozenset[str] = Field(default_factory=lambda: frozenset({"page"}))
    timeout_keys: frozenset[str] = Field(default_factory=lambda: frozenset({"timeout"}))
    wait_methods: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {
                "waitFor",
                "waitForEvent",
                "waitForFunction",
                "waitForLoadState",
                "waitForRequest",
                "waitForResponse",
                "waitForSelector",
                "waitForTimeout",
                "waitForURL",
            }
        )
    )


class AstLockVerdict(BaseModel):
    """Result of comparing an original file with a generated patch."""

    model_config = ConfigDict(frozen=True)

    allowed: bool
    reason: str
    node_kind: str | None = None
    line: int | None = None


DEFAULT_AST_LOCK_ALLOWLIST: Final = AstLockAllowlist()
_TSX_LANGUAGE: Final = Language(ts_typescript.language_tsx())
_LOCATOR_ARGUMENT_EXECUTION_BOUNDARIES: Final = frozenset(
    {
        "arrow_function",
        "call_expression",
        "function_expression",
        "generator_function",
        "new_expression",
    }
)


def check_ast_lock(
    original_source: str,
    patched_source: str,
    allowlist: AstLockAllowlist = DEFAULT_AST_LOCK_ALLOWLIST,
) -> AstLockVerdict:
    """Allow a patch only when its AST differs at explicitly permitted values."""
    original_bytes = original_source.encode("utf-8")
    patched_bytes = patched_source.encode("utf-8")
    original_tree = _parse(original_bytes)
    patched_tree = _parse(patched_bytes)

    parse_error = _first_parse_error(original_tree.root_node)
    if parse_error is not None:
        return _rejection("original_parse_error", parse_error)
    parse_error = _first_parse_error(patched_tree.root_node)
    if parse_error is not None:
        return _rejection("patched_parse_error", parse_error)

    difference = _first_difference(
        original_tree.root_node,
        patched_tree.root_node,
        original_bytes,
        patched_bytes,
        allowlist,
    )
    if difference is None:
        return AstLockVerdict(allowed=True, reason="structurally_equivalent")
    return _rejection("disallowed_ast_change", difference)


def _parse(source: bytes) -> Tree:
    parser = Parser(_TSX_LANGUAGE)
    return parser.parse(source)


def _first_parse_error(node: Node) -> Node | None:
    if node.is_error or node.is_missing:
        return node
    if not node.has_error:
        return None
    for child in node.children:
        error = _first_parse_error(child)
        if error is not None:
            return error
    return node


def _first_difference(
    original: Node,
    patched: Node,
    original_source: bytes,
    patched_source: bytes,
    allowlist: AstLockAllowlist,
) -> Node | None:
    original_marker = _allowed_marker(original, original_source, allowlist)
    patched_marker = _allowed_marker(patched, patched_source, allowlist)
    if original_marker is not None or patched_marker is not None:
        return None if original_marker == patched_marker else patched

    original_children = _comparable_children(original, original_source, allowlist)
    patched_children = _comparable_children(patched, patched_source, allowlist)
    if original.type != patched.type or len(original_children) != len(patched_children):
        return patched
    if not original.children:
        if _node_text(original, original_source) != _node_text(patched, patched_source):
            return patched
        return None

    for original_child, patched_child in zip(original_children, patched_children, strict=True):
        difference = _first_difference(
            original_child,
            patched_child,
            original_source,
            patched_source,
            allowlist,
        )
        if difference is not None:
            return difference
    return None


def _comparable_children(node: Node, source: bytes, allowlist: AstLockAllowlist) -> list[Node]:
    """Children to compare, without a trailing timeout-only options object on an action or wait.

    ``click(sel)`` and ``click(sel, { timeout: 10_000 })`` wait differently but do the same
    thing, so adding or removing ``{ timeout: <number> }`` is a wait-condition edit. Any other
    key, a computed value, or a call outside the action/wait methods stays locked.
    """
    children = list(node.children)
    call = node.parent
    if node.type != "arguments" or call is None or call.type != "call_expression":
        return children
    if _call_name(call, source) not in allowlist.page_selector_methods | allowlist.wait_methods:
        return children
    last = next((c for c in reversed(node.named_children) if c.type != "comment"), None)
    if last is None or not _is_timeout_only_object(last, source, allowlist):
        return children
    index = next(i for i, child in enumerate(children) if child.id == last.id)
    start = index - 1 if index > 0 and children[index - 1].type == "," else index
    return children[:start] + children[index + 1 :]


def _is_timeout_only_object(node: Node, source: bytes, allowlist: AstLockAllowlist) -> bool:
    pairs = [child for child in node.named_children if child.type != "comment"]
    if node.type != "object" or len(pairs) != 1 or pairs[0].type != "pair":
        return False
    value = pairs[0].child_by_field_name("value")
    return (
        value is not None and value.type == "number" and _is_timeout_value(value, source, allowlist)
    )


def _allowed_marker(
    node: Node,
    source: bytes,
    allowlist: AstLockAllowlist,
) -> str | None:
    if node.type == "string" and _inside_locator_arguments(node, source, allowlist):
        return "locator_literal"
    if node.type == "string_fragment" and _inside_locator_arguments(node, source, allowlist):
        return "locator_template_fragment"
    if node.type == "number" and _is_timeout_value(node, source, allowlist):
        return "timeout_number"
    if _is_wait_method_name(node, source, allowlist):
        return "wait_method"
    return None


def _inside_locator_arguments(
    node: Node,
    source: bytes,
    allowlist: AstLockAllowlist,
) -> bool:
    current: Node | None = node
    while current is not None and current.parent is not None:
        parent = current.parent
        if parent.type in _LOCATOR_ARGUMENT_EXECUTION_BOUNDARIES:
            return False
        if parent.type == "arguments" and parent.parent is not None:
            call = parent.parent
            if call.type == "call_expression":
                name = _call_name(call, source)
                if name in allowlist.locator_methods:
                    return True
                return (
                    name in allowlist.page_selector_methods
                    and _has_page_receiver(call, source, allowlist)
                    and _is_first_argument(parent, current)
                )
        current = parent
    return False


def _has_page_receiver(call: Node, source: bytes, allowlist: AstLockAllowlist) -> bool:
    function = call.child_by_field_name("function")
    if function is None or function.type != "member_expression":
        return False
    receiver = function.child_by_field_name("object")
    return (
        receiver is not None
        and receiver.type == "identifier"
        and _node_text(receiver, source) in allowlist.page_receivers
    )


def _is_first_argument(arguments: Node, argument: Node) -> bool:
    # Comments are extras and appear among named children; they are not arguments.
    first = next((child for child in arguments.named_children if child.type != "comment"), None)
    return first is not None and first.id == argument.id


def _is_timeout_value(node: Node, source: bytes, allowlist: AstLockAllowlist) -> bool:
    pair = node.parent
    if pair is None or pair.type != "pair":
        return False
    key = pair.child_by_field_name("key")
    value = pair.child_by_field_name("value")
    if key is None or value is None or value.id != node.id:
        return False
    return _node_text(key, source).strip("'\"") in allowlist.timeout_keys


def _is_wait_method_name(node: Node, source: bytes, allowlist: AstLockAllowlist) -> bool:
    if node.type == "identifier" and node.parent is not None:
        call = node.parent
        if call.type == "call_expression" and call.child_by_field_name("function") is not None:
            function = call.child_by_field_name("function")
            return (
                function is not None
                and function.id == node.id
                and _node_text(node, source) in allowlist.wait_methods
            )

    if node.type not in {"property_identifier", "private_property_identifier"}:
        return False
    member = node.parent
    if member is None or member.type != "member_expression" or member.parent is None:
        return False
    call = member.parent
    function = call.child_by_field_name("function") if call.type == "call_expression" else None
    if function is None or function.id != member.id:
        return False
    return _node_text(node, source) in allowlist.wait_methods


def _call_name(call: Node, source: bytes) -> str | None:
    function = call.child_by_field_name("function")
    if function is None:
        return None
    if function.type == "identifier":
        return _node_text(function, source)
    if function.type == "member_expression":
        property_node = function.child_by_field_name("property")
        if property_node is not None:
            return _node_text(property_node, source)
    return None


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="strict")


def _rejection(reason: str, node: Node) -> AstLockVerdict:
    return AstLockVerdict(
        allowed=False,
        reason=reason,
        node_kind=node.type,
        line=node.start_point.row + 1,
    )
