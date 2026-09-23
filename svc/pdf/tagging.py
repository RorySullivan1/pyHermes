"""
Correct the structure tree a tagged render produces, after it is built.

WeasyPrint 70 picks each element's type from the HTML element name alone and
never reads ``role``, so every layout table is announced as a data table
(#202). The markup is already right — the templates mark those tables
``role="presentation"`` and the ``table-role`` lint rule enforces it — so the
correction belongs where the tag is chosen, not in the markup.

A table with no ``th`` carries no header, so nothing in it can be data. That
is the discriminator ``qa/lint.py`` already uses, and one signal for both
keeps the linter and the tagger from disagreeing.

`digital-pdf.md` carries the rest: why a decorative image is fixed in the
template instead, and what the ``~=70.0`` pin is protecting.
"""

from __future__ import annotations

from typing import Any

__all__ = ["retag_layout_tables"]

#: The structure types a table builds, all of which become grouping elements
#: when the table turns out to be layout. ``/TH`` is here for completeness —
#: a table containing one is never retagged, so it is only ever reached
#: through a nested table that was judged separately.
_TABLE_PARTS = frozenset({"/Table", "/THead", "/TBody", "/TFoot", "/TR", "/TD", "/TH"})

#: What a retagged part becomes. ``/Div`` rather than ``/NonStruct``: the rows
#: and cells still group the content visually, and a grouping element says
#: that honestly where ``/NonStruct`` says only "ignore me".
_NEUTRAL = "/Div"

#: The attribute dictionary WeasyPrint attaches to a cell, giving its span in
#: the table's own coordinate space. Meaningless once the cell is a ``/Div``,
#: and a dangling ``/O /Table`` on a non-table element is worse than absent.
_TABLE_ATTRIBUTE_OWNER = "/Table"


def retag_layout_tables(_document: Any, pdf: Any) -> None:
    """
    Retag every layout table in ``pdf`` as a neutral grouping element.

    A WeasyPrint ``finisher``: it takes the rendered document and the pydyf
    PDF, and runs after the structure tree is built and before the file is
    written. Does nothing to a document with no structure tree, so it is
    safe to attach to an untagged render — and an untagged render's bytes
    are unchanged, which is what keeps every existing golden still.

    Each table is judged on its **own** cells: the walk stops at a nested
    table, so a data table inside a layout one keeps its tags and a layout
    table inside a data one loses them. Judging a table by its descendants
    without that boundary would let one nested ``th`` protect every table
    above it.
    """
    elements = _struct_elements(pdf)
    if not elements:
        return

    for element in elements.values():
        if element.get("S") != "/Table":
            continue
        parts = _own_parts(element, elements)
        if any(part.get("S") == "/TH" for part in parts):
            continue  # a header: this is a data table, and correctly tagged
        for part in (element, *parts):
            _neutralise(part)


def _struct_elements(pdf: Any) -> dict[bytes, Any]:
    """Every ``/StructElem`` in the document, keyed by its own reference.

    Keyed by reference because that is what a parent's ``/K`` array holds;
    the alternative, indexing ``pdf.objects`` by position, would depend on
    pydyf numbering objects by list index, which is true today and is not
    something this module should rest on.
    """
    found: dict[bytes, Any] = {}
    for object_ in pdf.objects:
        # A pydyf Dictionary is a dict; anything else in the file is not a
        # structure element, and `.get` on a Stream would raise. The reference
        # is read before narrowing, because it lives on the pydyf object rather
        # than on the mapping it also is.
        reference = getattr(object_, "reference", None)
        if not isinstance(reference, bytes) or not isinstance(object_, dict):
            continue
        if object_.get("Type") == "/StructElem":
            found[reference] = object_
    return found


def _own_parts(table: Any, elements: dict[bytes, Any]) -> list[Any]:
    """
    The table parts belonging to ``table`` itself, nested tables excluded.

    Breadth-first from the table's children. A child that is itself a
    ``/Table`` is not followed and not returned: it is a separate table with
    its own header question, and it is reached on its own pass.
    """
    parts: list[Any] = []
    queue = list(_children(table, elements))
    while queue:
        child = queue.pop()
        if child.get("S") == "/Table":
            continue
        parts.append(child)
        queue.extend(_children(child, elements))
    return parts


def _children(element: Any, elements: dict[bytes, Any]) -> list[Any]:
    """
    The structure elements ``element`` holds.

    ``/K`` mixes two kinds of entry: a reference to a child element, and a
    bare integer marked-content id pointing into the page's content stream.
    Only the first kind is a child here; the integers are the leaves where
    the actual text and images live, and they are left exactly as they are.
    """
    kids = element.get("K")
    if kids is None:
        return []
    if not isinstance(kids, list):
        kids = [kids]
    return [elements[kid] for kid in kids if isinstance(kid, bytes) and kid in elements]


def _neutralise(element: Any) -> None:
    """Turn one table part into a grouping element, attributes included."""
    if element.get("S") not in _TABLE_PARTS:
        return
    element["S"] = _NEUTRAL
    attributes = element.get("A")
    if isinstance(attributes, dict) and attributes.get("O") == _TABLE_ATTRIBUTE_OWNER:
        del element["A"]
