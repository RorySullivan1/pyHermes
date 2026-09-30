"""
Blocks that hold blocks: several in one cell, top to bottom (#262).

A container gives each cell one component. These are components too, so they
go wherever one does, and the document walks through them to the blocks they
hold. `.claude/rules/builder-architecture.md` records the walk's contract.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .components import Component
from .engine import Renderer, respaced
from .exceptions import ValidationError
from .images import EmailImage
from .sizing import Spacing


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
