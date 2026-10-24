"""Ambiguous Target Check: did the element the test used become several look-alikes?

When a diff removes the element a failing locator named and adds two or more elements of the
same kind in its place (one ``Submit`` button becomes ``Save draft`` and ``Publish``), any of
them can make the test pass, and picking one is a guess about what the test author meant. A
model asked to repair it picks one anyway, and the repair reads as a success. This check
recognizes the situation from the abstracted DOM diff alone, so the graph can refuse it as
``ambiguous_target`` before any model call.

It is deliberately narrow. It fires only when all of these hold:

* the failing locator names an identifying attribute (``id``, a class, ``data-testid`` or
  ``name``) of an element the diff removes;
* the same file gains at least two elements with that element's tag and ``type`` that do not
  carry the old name;
* no ``--selector-hint`` was given, because a hint is a person's answer to the question.

A locator that names an element only by role or text never matches, so such tests are left to
the repair loop.
"""

import structlog

from app.preprocess.selector_diff_check import failing_locator, locator_terms

logger = structlog.get_logger(__name__)

# Attributes whose values a CSS-style locator names an element by. ``type`` is left out on
# purpose: ``type="submit"`` is shared by every submit button, so it identifies none of them.
_IDENTIFYING = ("id", "className", "class", "data-testid", "name")
_MIN_LOOK_ALIKES = 2


def _names(element: dict) -> set[str]:
    """Every identifying token of an element: ids, test ids, names, and each class."""
    attributes = element.get("attributes", {})
    tokens: set[str] = set()
    for key in _IDENTIFYING:
        value = str(attributes.get(key, "")).strip()
        if not value:
            continue
        tokens.update(value.split() if key in ("className", "class") else [value])
    return tokens


def _kind(element: dict) -> tuple[str, str]:
    return element.get("tag", ""), str(element.get("attributes", {}).get("type", ""))


def _selector_for(element: dict, line: int) -> str:
    """A selector a person could pass back as ``--selector-hint`` to choose this element."""
    attributes = element.get("attributes", {})
    if attributes.get("id"):
        return f"#{attributes['id']}"
    if attributes.get("data-testid"):
        return f'[data-testid="{attributes["data-testid"]}"]'
    if attributes.get("name"):
        return f'[name="{attributes["name"]}"]'
    classes = str(attributes.get("className") or attributes.get("class") or "").split()
    if classes:
        return "." + ".".join(classes)
    return f"<{element.get('tag', '')}> at line {line}"


def ambiguous_replacements(raw_log: str, dom_diff_context: list[dict]) -> list[str]:
    """Selectors of the look-alikes that replaced the failing element, or ``[]``.

    A non-empty result means the test cannot say which of them it meant, so a repair would be
    a guess. ``[]`` covers every case the check cannot decide.
    """
    if any(entry.get("type") == "selector_hint" for entry in dom_diff_context):
        return []
    terms = locator_terms(failing_locator(raw_log))
    if not terms:
        return []
    for removed in dom_diff_context:
        previous, current = removed.get("previous") or {}, removed.get("current") or {}
        matched = _names(previous) & terms
        if not previous or not matched or matched & _names(current):
            continue
        look_alikes = [
            (entry.get("current") or {}, int(entry.get("line", 0)))
            for entry in dom_diff_context
            if entry.get("file") == removed.get("file")
            and (entry is removed or not entry.get("previous"))
        ]
        candidates = [
            _selector_for(element, line)
            for element, line in look_alikes
            if element and _kind(element) == _kind(previous) and not _names(element) & matched
        ]
        if len(candidates) >= _MIN_LOOK_ALIKES:
            logger.info(
                "ambiguous_target_detected",
                removed=sorted(matched),
                candidates=candidates,
                file=removed.get("file"),
            )
            return candidates
    return []
