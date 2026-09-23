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

from svc.builder.exceptions import ValidationError
from svc.builder.images import EmailImage, pixel_size
from svc.config import get_config

from .fold import FoldFormat
from .imposition import face_name
from .panel import Panel

#: CSS px per inch: every width in the package is px at 96 dpi.
CSS_DPI = 96


def validate_safe_area(fold: FoldFormat, panels: Sequence[Panel]) -> None:
    """
    Every panel keeps its copy at least ``fold.safe`` from its edges.

    Raises:
        ValidationError: Naming the first panel that does not, and both distances.
    """
    for reader, panel in enumerate(panels, start=1):
        inset = fold.inset if panel.inset is None else panel.inset
        if inset < fold.safe:
            named = f" ({panel.title!r})" if panel.title else ""
            raise ValidationError(
                f"the {face_name(fold, reader)}{named} keeps its copy {inset}px from the "
                f"trim, inside the {fold.safe}px safe distance, where a cut can reach it. "
                f"Give it an inset of at least {fold.safe}."
            )


def required_pixels(display_width: int | float, dpi: int | None = None) -> int:
    """Source pixels an image displayed ``display_width`` px wide needs to print at ``dpi``."""
    return math.ceil(display_width * (dpi or get_config().print_dpi) / CSS_DPI)


def validate_image_resolution(images: Sequence[EmailImage]) -> None:
    """
    Every image carries enough pixels to print at ``Config.print_dpi``.

    Below the target prints a warning, as the email's 90 KB threshold does;
    below half of it raises. A hosted image has no bytes to measure, and the
    PDF exporter refuses one anyway.

    Raises:
        ValidationError: Naming the image, its pixel width and the width it needs.
    """
    dpi = get_config().print_dpi
    for image in images:
        size = pixel_size(image.data) if image.data else None
        if size is None:
            continue
        pixels = size[0]
        display = image.width or pixels
        needed = required_pixels(display, dpi)
        if pixels * 2 < needed:
            raise ValidationError(
                f"the image {image.alt or image.filename!r} is {pixels}px wide and displayed "
                f"at {display}px, which prints at {pixels * CSS_DPI / display:.0f} dpi. "
                f"It needs {needed}px to print at {dpi} dpi."
            )
        if pixels < needed:
            print(
                f"WARNING: the image {image.alt or image.filename!r} is {pixels}px wide and "
                f"needs {needed}px to print at {dpi} dpi."
            )
