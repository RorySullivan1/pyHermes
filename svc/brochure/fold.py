"""
Fold geometry: a sheet, a fold, and the panels the fold makes of it.

A brochure is laid out on panels, not on the sheet. This module turns a sheet
and a fold into panel widths, in px at 96 dpi like every size in the package,
and is the only place those widths are computed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from svc.builder.exceptions import ValidationError
from svc.builder.sizing import PageFormat


class FoldKind(StrEnum):
    """How a sheet is folded, which decides both its panel widths and its imposition."""

    #: One fold down the middle: four faces, two a side.
    BI = "bi"
    #: A letter, or roll, fold: the right third folds in, the left third over
    #: it. Six faces; the panel that folds inside is the narrow one.
    C = "c"
    #: An accordion: two folds in opposite directions, three equal panels.
    Z = "z"
    #: Two flaps fold in from the edges to meet over a double-width centre.
    GATE = "gate"


#: Panels on each side of the sheet, per fold.
PANELS_PER_SIDE: dict[FoldKind, int] = {
    FoldKind.BI: 2,
    FoldKind.C: 3,
    FoldKind.Z: 3,
    FoldKind.GATE: 3,
}

#: The folds whose inner panels must be narrower to close flat. A Z-fold's
#: panels never nest and a bi-fold's two halves meet edge to edge.
_TUCKED = frozenset({FoldKind.C, FoldKind.GATE})


@dataclass(frozen=True)
class FoldFormat:
    """
    A sheet and how it folds: everything panel geometry is computed from.

    **The tuck is a distance, not a ratio.** A panel that folds inside another
    must be a few millimetres narrower or it buckles against the crease, and
    that allowance does not grow with the sheet. So this is not
    :func:`~svc.builder.sizing.column_layout`, which splits a content width by
    weights with gutters between; `brochure.md` has why it was not widened.

    ``panels`` is derived from ``kind``, as ``Medium.slots`` is from its
    regions, so the two cannot disagree. Every width is px at 96 dpi, and an
    ``int`` when whole: the size layers refuse ``356.0``.

    Args:
        sheet: The flat sheet, landscape, with no margin: a panel insets its
               own copy, and a sheet margin would inset the edges twice.
        kind:  The fold.
        tuck:  How much narrower each inside panel is, in px. Zero for a
               bi-fold and a Z-fold, which have no panel that nests.
        inset: How far a panel keeps its copy from its edges unless the
               panel says otherwise, in px. 24px is 1/4in (6.4mm).
    """

    sheet: PageFormat
    kind: FoldKind
    tuck: int | float = 0
    inset: int | float = 24

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "kind", FoldKind(self.kind))
        except ValueError:
            raise ValidationError(
                f"'fold.kind' must be one of {[k.value for k in FoldKind]}, got: {self.kind!r}"
            ) from None
        if self.sheet.height is None:
            raise ValidationError("'fold.sheet' must have a height: a continuous page cannot fold")
        if self.sheet.orientation != "landscape":
            raise ValidationError(
                f"'fold.sheet' must be landscape, got {self.sheet.orientation}: the panels "
                "stand side by side across the sheet's width"
            )
        if any(
            (
                self.sheet.margin.top,
                self.sheet.margin.right,
                self.sheet.margin.bottom,
                self.sheet.margin.left,
            )
        ):
            raise ValidationError(
                "'fold.sheet' must have no margin: a panel insets its own copy, so a sheet "
                "margin would inset the outer panels twice"
            )
        if isinstance(self.tuck, bool) or not isinstance(self.tuck, (int, float)):
            raise ValidationError(f"'fold.tuck' must be a number, got: {type(self.tuck).__name__}")
        if self.tuck < 0:
            raise ValidationError(f"'fold.tuck' must not be negative, got: {self.tuck}")
        if self.tuck and self.kind not in _TUCKED:
            raise ValidationError(
                f"a {self.kind.value}-fold has no panel that folds inside another, so "
                f"'fold.tuck' must be 0, got: {self.tuck}"
            )
        for name in ("inset",):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise ValidationError(f"'fold.{name}' must be a number of px, got: {value!r}")
        if min(self.widths) <= 0:
            raise ValidationError(f"'fold.tuck' ({self.tuck}) leaves a panel with no width")

    @property
    def panels(self) -> int:
        """Panels on each side of the sheet."""
        return PANELS_PER_SIDE[self.kind]

    @property
    def faces(self) -> int:
        """Panels a reader meets, both sides together: what a brochure is given."""
        return 2 * self.panels

    @property
    def width(self) -> int | float:
        """The sheet's width."""
        return self.sheet.width

    @property
    def height(self) -> int | float:
        """The sheet's height, which is every panel's height."""
        assert self.sheet.height is not None  # refused in __post_init__
        return self.sheet.height

    @property
    def widths(self) -> tuple[int | float, ...]:
        """
        Side 1's panel widths, left to right. Sum exactly to the sheet.

        Side 2 is the mirror: a sheet turned over puts side 1's left panel
        behind side 2's right, and a panel is one width on both faces. See
        :meth:`side_widths`.
        """
        width, tuck = self.width, self.tuck
        if self.kind is FoldKind.BI:
            half = _px(width / 2)
            return (half, _px(width - half))
        if self.kind is FoldKind.Z:
            third = _px(width / 3)
            return (third, third, _px(width - 2 * third))
        if self.kind is FoldKind.C:
            # Two full panels and the tuck panel, which is full less the tuck.
            # It sits at side 1's left so it backs side 2's right, the panel
            # that folds in first.
            full = _px((width + tuck) / 3)
            return (_px(width - 2 * full), full, full)
        # GATE: two flaps meeting short of the middle by the tuck, over a
        # centre panel that takes whatever the flaps leave.
        flap = _px((width / 2 - tuck) / 2)
        return (flap, _px(width - 2 * flap), flap)

    def side_widths(self, side: int) -> tuple[int | float, ...]:
        """One side's panel widths, left to right; ``side`` is 1 or 2."""
        if side not in (1, 2):
            raise ValidationError(f"a sheet has sides 1 and 2, got: {side!r}")
        return self.widths if side == 1 else tuple(reversed(self.widths))

    def offsets(self, side: int) -> tuple[int | float, ...]:
        """Each panel's left edge on one side, from the sheet's left edge."""
        edges: list[int | float] = []
        running: int | float = 0
        for width in self.side_widths(side):
            edges.append(_px(running))
            running += width
        return tuple(edges)


def _px(value: int | float) -> int | float:
    """A width as an ``int`` when whole, so it never prints as ``356.0px``."""
    return int(value) if float(value).is_integer() else value


#: The flat sheets, landscape, in px at 96 dpi. Letter is 11 x 8.5in; A4 is
#: 297 x 210mm. No margin: see ``FoldFormat.sheet``.
LETTER_SHEET = PageFormat(width=1056, height=816)
A4_SHEET = PageFormat(width=1123, height=794)

#: The shipped folds. Every preset's widths are pinned by a test.
#:
#: The C-fold's tuck is 12px, 1/8in (3.2mm): 356 + 356 + 344. The gate's is
#: 7.5px, 2mm, which leaves each flap a whole 277px over a 569px centre.
BI_FOLD_LETTER = FoldFormat(sheet=LETTER_SHEET, kind=FoldKind.BI)
TRI_FOLD_LETTER = FoldFormat(sheet=LETTER_SHEET, kind=FoldKind.C, tuck=12)
Z_FOLD_LETTER = FoldFormat(sheet=LETTER_SHEET, kind=FoldKind.Z)
GATE_FOLD_A4 = FoldFormat(sheet=A4_SHEET, kind=FoldKind.GATE, tuck=7.5)

#: Every shipped fold by name, as ``PAGE_FORMATS`` names every page.
FOLD_FORMATS: dict[str, FoldFormat] = {
    "bi_fold_letter": BI_FOLD_LETTER,
    "tri_fold_letter": TRI_FOLD_LETTER,
    "z_fold_letter": Z_FOLD_LETTER,
    "gate_fold_a4": GATE_FOLD_A4,
}
