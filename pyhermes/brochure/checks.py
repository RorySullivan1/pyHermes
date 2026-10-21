"""
What a print house rejects, checked before anything renders (#188).

Both checks read facts the brochure already holds at construction: the fold's
arithmetic and each image's own bytes. Neither is on the medium's
``constraints``, because a ``Constraint`` sees only the composed markup, and
neither a panel's inset nor an image's pixel count is in it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from pyhermes.builder.exceptions import PrintQualityWarning, ValidationError, warn_caller
from pyhermes.builder.images import EmailImage, pixel_size
from pyhermes.config import get_config

from .fold import FoldFormat
from .imposition import face_name, impose
from .panel import Panel

#: CSS px per inch: every width in the package is px at 96 dpi.
CSS_DPI = 96


def panel_label(fold: FoldFormat, reader: int, panel: Panel) -> str:
    """How an error names a panel: its face, and its title when it has one."""
    named = f" ({panel.title!r})" if panel.title else ""
    return f"the {face_name(fold, reader)}{named}"


def validate_safe_area(fold: FoldFormat, panels: Sequence[Panel]) -> None:
    """
    Every panel keeps its copy at least ``fold.safe`` from its edges.

    Raises:
        ValidationError: Naming the first panel that does not, and both distances.
    """
    for reader, panel in enumerate(panels, start=1):
        inset = fold.inset if panel.inset is None else panel.inset
        if inset < fold.safe:
            raise ValidationError(
                f"{panel_label(fold, reader, panel)} keeps its copy {inset}px from the "
                f"trim, inside the {fold.safe}px safe distance, where a cut can reach it. "
                f"Give it an inset of at least {fold.safe}."
            )


def validate_inset_room(fold: FoldFormat, panels: Sequence[Panel]) -> None:
    """
    Every panel's inset leaves it a content width and a content height (#460).

    The inset is taken from both edges of each axis, so it must stay under half
    the panel's box. Without this the frame refuses the render, naming neither
    the panel nor the inset.

    Raises:
        ValidationError: Naming the first panel with no room, its inset and its box.
    """
    for panel_box, (reader, panel) in zip(impose(fold), enumerate(panels, start=1), strict=True):
        inset = fold.inset if panel.inset is None else panel.inset
        for axis, length in (("width", panel_box.width), ("height", panel_box.height)):
            if inset * 2 >= length:
                raise ValidationError(
                    f"{panel_label(fold, reader, panel)} has an inset of {inset}px, which leaves "
                    f"no content {axis} inside its {length}px {axis}: an inset is taken from "
                    f"both edges. Give it an inset below {length / 2:g}."
                )


def required_pixels(display_width: int | float, dpi: int | None = None) -> int:
    """Source pixels an image displayed ``display_width`` px wide needs to print at ``dpi``."""
    return math.ceil(display_width * (dpi or get_config().print_dpi) / CSS_DPI)


def validate_image_resolution(
    images: Sequence[
        EmailImage
        | tuple[EmailImage, int | float | None]
        | tuple[EmailImage, int | float | None, str]
    ],
    dpi: int | None = None,
) -> None:
    """
    Every image carries enough pixels to print at ``Config.print_dpi``.

    An entry is an image, displayed at its own ``width`` (or its pixel width
    when it has none), or an ``(image, display width)`` pair for one that
    fills a box instead, such as a panel's ground. Below the target warns with
    a ``PrintQualityWarning``, as the email's 90 KB threshold does; below half of it raises. A
    hosted image has no bytes to measure, and the PDF exporter refuses it.
    ``dpi`` sets another target, as a deck sets a screen's (#348). A third
    element says where the use sits, and the message ends with it (#458).

    Raises:
        ValidationError: Naming the image, its pixel width and the width it needs.
    """
    dpi = dpi or get_config().print_dpi
    for entry in images:
        fills: int | float | None = None
        where: str | None = None
        if isinstance(entry, EmailImage):
            image = entry
        else:
            image, fills, *rest = entry
            where = rest[0] if rest else None
        used = f" It is {where}." if where else ""
        size = pixel_size(image.data) if image.data else None
        if size is None:
            continue
        pixels = size[0]
        display = fills or image.width or pixels
        needed = required_pixels(display, dpi)
        if pixels * 2 < needed:
            raise ValidationError(
                f"the image {image.alt or image.filename!r} is {pixels}px wide and displayed "
                f"at {display}px, which prints at {pixels * CSS_DPI / display:.0f} dpi. "
                f"It needs {needed}px to print at {dpi} dpi.{used}"
            )
        if pixels < needed:
            warn_caller(
                f"the image {image.alt or image.filename!r} is {pixels}px wide and "
                f"needs {needed}px to print at {dpi} dpi.{used}",
                PrintQualityWarning,
            )
