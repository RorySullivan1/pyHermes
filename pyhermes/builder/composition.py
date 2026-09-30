"""
Blocks that hold blocks: several in one cell (#262), or a split inside one (#263).

A container gives each cell one component. These are components too, so they
go wherever one does, and the document walks through them to the blocks they
hold. `.claude/rules/builder-architecture.md` records the walk's contract.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .components import Component, descendants
from .engine import Renderer, cell_width_of, rebind, respaced, scheme_of
from .exceptions import ValidationError
from .images import EmailImage
from .sizing import Spacing, column_layout


def _checked(owner: str, components: Sequence[Component]) -> list[Component]:
    """``components`` as a list, refusing an empty one and anything not a component."""
    if isinstance(components, Component):
        raise ValidationError(
            f"{owner} takes a list of components, got one {type(components).__name__}."
        )
    held = list(components)
    if not held:
        raise ValidationError(f"{owner} needs at least one component.")
    for index, component in enumerate(held):
        if not isinstance(component, Component):
            raise ValidationError(
                f"{owner} item {index} must be a Component, got {type(component).__name__}. "
                "A section goes in an email, not in a block."
            )
    return held


class Stack(Component):
    """
    Several blocks in one cell, one above the next.

    The way to put a paragraph, the table it introduces and a note beneath
    it under one section title, or a figures row over a comment in one
    column, without a section each. The gap between blocks is ``block_gap``,
    which ``spacing=`` moves.

    It has no alignment of its own: each block keeps its own, and inherits the
    section's when it has none. It carries no notes or markup itself, so the
    document numbers the blocks inside it where they sit.

    Args:
        components: The blocks, top to bottom. At least one.
        spacing:    Moves ``block_gap``, the space between them.
    """

    template_path = "common/stack.html"

    SPACING_TOKENS = ("block_gap",)

    def __init__(
        self,
        components: Sequence[Component],
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        self.components = _checked("Stack", components)

    def children(self) -> list[Component]:
        return list(self.components)

    def images(self) -> list[EmailImage]:
        return [image for component in self.components for image in component.images()]

    def text(self) -> str:
        return self._with_subtitle(*(component.text() for component in self.components))

    def context(self) -> dict[str, Any]:
        raise NotImplementedError("Stack renders its blocks first; see render().")

    def render(self, engine: Renderer) -> str:
        engine = respaced(engine, self.spacing, type(self).__name__)
        blocks = [component.render(engine) for component in self.components]
        return engine.render(self.template_path, {"blocks": blocks})


class Columns(Component):
    """
    A split inside a cell: two to four blocks side by side, sized to that cell.

    Where ``TwoColumn`` splits the whole frame, this splits whatever cell it sits
    in: a column of another split, or a place in a ``Stack``. It has no title or
    band of its own, because those belong to the section. The columns are sized
    from the cell's width, with the section's ``gutter`` between them, and stack
    on a phone like any split.

    One level only: a ``Columns`` holding another, even through a ``Stack``,
    raises. There is no minimum column width, because the cell's width is known
    only at render.

    Args:
        components: Two to four blocks, left to right; ``None`` leaves a column empty.
        ratio:      One positive weight per column; equal when unset.
        spacing:    Moves ``gutter`` and ``block_gap``, the gap when stacked.
    """

    template_path = "common/nested-columns.html"

    SPACING_TOKENS = ("gutter", "block_gap")

    COUNTS = range(2, 5)

    def __init__(
        self,
        components: Sequence[Component | None],
        ratio: Sequence[int | float] | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        slots = list(components)
        if len(slots) not in self.COUNTS:
            raise ValidationError(f"Columns takes 2 to 4 components, got {len(slots)}.")
        _checked("Columns", [slot for slot in slots if slot is not None])
        if any(isinstance(inner, Columns) for inner in descendants(self._filled(slots))):
            raise ValidationError(
                "Columns may not hold another Columns: one level of nesting inside a cell."
            )
        weights = tuple(ratio) if ratio is not None else (1,) * len(slots)
        if len(weights) != len(slots) or not all(_positive(weight) for weight in weights):
            raise ValidationError(
                f"Columns takes {len(slots)} positive weights, one per column, got: {ratio!r}"
            )
        self.slots = slots
        self.ratio = weights

    @staticmethod
    def _filled(slots: Sequence[Component | None]) -> list[Component]:
        return [slot for slot in slots if slot is not None]

    def children(self) -> list[Component]:
        return self._filled(self.slots)

    def images(self) -> list[EmailImage]:
        return [image for component in self.children() for image in component.images()]

    def text(self) -> str:
        return self._with_subtitle(*(component.text() for component in self.children()))

    def context(self) -> dict[str, Any]:
        raise NotImplementedError("Columns renders its blocks first; see render().")

    def render(self, engine: Renderer) -> str:
        engine = respaced(engine, self.spacing, type(self).__name__)
        within = cell_width_of(engine)
        geometry = column_layout(self.ratio, scheme_of(engine), within=within)
        columns = [
            {
                "width": column.width,
                "content": slot.render(rebind(engine, cell_width=column.width)) if slot else "",
            }
            for slot, column in zip(self.slots, geometry, strict=True)
        ]
        return engine.render(self.template_path, {"columns": columns, "within": within})


def _positive(value: object) -> bool:
    """A positive int or float, and not a bool."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
