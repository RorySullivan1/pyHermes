"""
Blocks that hold blocks: several in one cell (#262), a split inside one (#263),
or one shown in chosen media only (#365).

A container gives each cell one component. These are components too, so they
go wherever one does, and the document walks through them to the blocks they
hold. `.claude/rules/builder-architecture.md` records the walk's contract.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .apparatus import cited_keys
from .components import Component, Exhibit, descendants
from .engine import Renderer, cell_width_of, rebind, respaced, scheme_of
from .exceptions import ValidationError
from .images import EmailImage
from .medium import check_media, walking_medium
from .models import check_valign
from .sizing import (
    PHONE_FLOOR,
    STANDARD_SIZES,
    Spacing,
    check_unstacked,
    coerce_stack,
    column_layout,
    shares,
)


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
        # An omitted block (#365) leaves no row, so no gap is left behind.
        blocks = [html for component in self.components if (html := component.render(engine))]
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
    raises. Stacking, there is no minimum column width, because the cell's width
    is known only at render; unstacked, the floor is checked against the
    narrowest cell a stacking section gives it on a phone.

    Args:
        components: Two to four blocks, left to right; ``None`` leaves a column empty.
        ratio:      One positive weight per column; equal when unset.
        spacing:    Moves ``gutter`` and ``block_gap``, the gap when stacked.
        stack:      ``"natural"``, ``"reverse"`` to put the last column first on a
                    phone, or ``False`` to keep the columns side by side there.
        valign:     Where each column sits in the row's height, on paper (#356).
    """

    template_path = "common/nested-columns.html"

    SPACING_TOKENS = ("gutter", "block_gap")

    COUNTS = range(2, 5)

    def __init__(
        self,
        components: Sequence[Component | None],
        ratio: Sequence[int | float] | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        stack: str | bool = "natural",
        valign: str = "top",
    ):
        self.spacing = self._coerce_spacing(spacing)
        self.valign = check_valign(valign, "Columns")
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
        self.stack = coerce_stack(stack, "Columns")
        if self.stack is False:
            # The narrowest cell a stacking section gives it at the floor: a stacked
            # split's column, inside the band's inset and the column's phone padding.
            frame, space = STANDARD_SIZES.frame, STANDARD_SIZES.space
            phone = PHONE_FLOOR - 2 * frame.pad_x - 2 * space.mobile_pad_x
            check_unstacked(weights, phone - space.gutter * (len(slots) - 1), "Columns")

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
        gutter_px = scheme_of(engine).space.gutter
        *percent, gutter = shares([c.width for c in geometry], gutter_px, within)
        columns = [
            {
                "width": column.width,
                "share": share,
                "content": slot.render(rebind(engine, cell_width=column.width)) if slot else "",
            }
            for slot, column, share in zip(self.slots, geometry, percent, strict=True)
        ]
        # Nothing stacks on paper, so a reversed or unstacked split prints as written.
        stack = self.stack if not engine.medium.paged else "natural"
        return engine.render(
            self.template_path,
            {
                "columns": columns[::-1] if stack == "reverse" else columns,
                "within": within,
                "stack": "fixed" if stack is False else stack,
                "gutter_share": gutter,
                "valign": self.valign,
            },
        )


def _positive(value: object) -> bool:
    """A positive int or float, and not a bool."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def refuse_numbered(owner: str, components: Sequence[Component]) -> None:
    """
    Refuse a labelled exhibit, a footnote or a citation anywhere in ``components`` (#365).

    Each is numbered across the whole document, so one shown in some media
    only would make "Exhibit 3" or note 7 mean different things in two of them.

    Raises:
        ValidationError: Naming what was found and why.
    """
    for component in descendants(components):
        name = type(component).__name__
        if isinstance(component, Exhibit) and component.label:
            found = f"a {name} labelled {component.label!r}"
        elif component.footnotes():
            found = f"a {name} with footnotes"
        elif any(cited_keys(copy) for copy in component.marked_copy()):
            found = f"a {name} with a citation"
        else:
            continue
        raise ValidationError(
            f"{owner} holds {found}. Notes, citations and labelled exhibits are numbered "
            "across the document, so one shown in some media only would number the rest "
            "differently in each. Keep it outside, or drop the label."
        )


class Only(Component):
    """
    One block shown in the chosen media and omitted, bytes and all, from the rest (#365).

    A "Download the PDF" button for the email, a page note for the report.
    The decision is made in Python, as a ``Page`` flattens, so an omitted
    block emits no markup, carries no image into the manifest and, since a
    document's text part belongs to its medium, projects no text. A block
    numbered across the document (a labelled exhibit, a footnote, a
    citation) is refused, because omitting it would renumber the rest.

    In a cell, an omitted block leaves the cell empty; to drop whole sections,
    use :class:`~pyhermes.builder.containers.OnlySections`.

    Args:
        component: The block.
        media:     The media it shows in: ``"email"``, ``"document"``,
                   ``"brochure"``, ``"deck"`` or ``"html"``.
        spacing:   Accepted for the house signature; a wrapper reads no token,
                   so the block's own ``spacing`` is the one to set.
    """

    def __init__(
        self,
        component: Component,
        media: Sequence[str] | str,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        if not isinstance(component, Component):
            raise ValidationError(
                f"Only takes one Component, got {type(component).__name__}. "
                "For sections, use OnlySections([...])."
            )
        self.media = check_media(media, "Only")
        refuse_numbered("Only", [component])
        self.component = component

    def shown(self) -> bool:
        """Whether the current walk's medium shows the block; outside any document, it does."""
        medium = walking_medium()
        return medium is None or medium in self.media

    def children(self) -> list[Component]:
        return [self.component] if self.shown() else []

    def images(self) -> list[EmailImage]:
        return self.component.images() if self.shown() else []

    def text(self) -> str:
        return self._with_subtitle(self.component.text()) if self.shown() else ""

    def context(self) -> dict[str, Any]:
        raise NotImplementedError("Only renders its block or nothing; see render().")

    def render(self, engine: Renderer) -> str:
        if engine.medium.name not in self.media:
            return ""
        return self.component.render(engine)
