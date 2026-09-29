"""
Imposition: the order a reader meets the panels, laid onto the sheet a printer prints.

The caller composes panels in reader order and never names a printer position.
This module owns the mapping, one small table per fold, and turns it into a
:class:`~pyhermes.brochure.panel.PanelBox` for every panel.
"""

from __future__ import annotations

from .fold import FoldFormat, FoldKind
from .panel import PanelBox

#: Each side's panels, left to right, as reader indices from 1.
#:
#: A sheet turned over on its long edge puts side 1's left panel behind side
#: 2's right, so the two faces of one physical panel sit at mirrored
#: positions; ``FoldFormat.side_widths`` mirrors the widths the same way, and
#: a test holds every table to it by checking the narrow panel's faces.
#:
#: C-fold: the outside carries the flap, the back and the front cover; the
#: inside is the three-panel spread, its narrow right panel folding in first.
#: Z-fold: the front cover is side 2's right, and side 1 is the spread the
#: accordion opens onto. Gate: the front is two flaps meeting in the middle,
#: so the cover is two reader panels, and the back is the centre's outside.
IMPOSITION: dict[FoldKind, tuple[tuple[int, ...], tuple[int, ...]]] = {
    FoldKind.BI: ((4, 1), (2, 3)),
    FoldKind.C: ((6, 5, 1), (2, 3, 4)),
    FoldKind.Z: ((2, 3, 4), (5, 6, 1)),
    FoldKind.GATE: ((2, 6, 1), (3, 4, 5)),
}

#: What a reader calls each panel, in reader order. Used in errors and in the
#: proof's margin labels, so a designer checks a name rather than a number.
FACE_NAMES: dict[FoldKind, tuple[str, ...]] = {
    FoldKind.BI: ("front cover", "inside left", "inside right", "back cover"),
    FoldKind.C: (
        "front cover",
        "inside left",
        "inside centre",
        "inside right",
        "back cover",
        "inside flap",
    ),
    FoldKind.Z: (
        "front cover",
        "inside left",
        "inside centre",
        "inside right",
        "outside left",
        "outside centre",
    ),
    FoldKind.GATE: (
        "cover, left flap",
        "cover, right flap",
        "inside left flap",
        "inside centre",
        "inside right flap",
        "back cover",
    ),
}


def impose(fold: FoldFormat) -> tuple[PanelBox, ...]:
    """Every panel's place on the sheet, in reader order."""
    placed: dict[int, PanelBox] = {}
    for side, readers in enumerate(IMPOSITION[fold.kind], start=1):
        for position, (reader, left, width) in enumerate(
            zip(readers, fold.offsets(side), fold.side_widths(side), strict=True), start=1
        ):
            placed[reader] = PanelBox(
                reader=reader,
                side=side,
                position=position,
                left=left,
                width=width,
                height=fold.height,
            )
    return tuple(placed[reader] for reader in sorted(placed))


def sides(fold: FoldFormat) -> tuple[tuple[int, ...], ...]:
    """Each side's reader indices, left to right: the printer's order."""
    return IMPOSITION[fold.kind]


def face_name(fold: FoldFormat, reader: int) -> str:
    """What a reader calls panel ``reader`` of this fold."""
    return FACE_NAMES[fold.kind][reader - 1]
