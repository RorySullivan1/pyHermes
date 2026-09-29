"""
LaTeX, as a :class:`~pyhermes.builder.MathBlock` painted for a theme (#231).

The picture's pixels are fixed here, so the colour and the size come from the
theme and the density the caller builds the document with: a document under
another theme needs its equations rendered for it. `math.md` records why.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pyhermes.builder import MathBlock, Spacing
from pyhermes.builder.enums import ImageAlign, SizeTheme
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import Footnote
from pyhermes.builder.sizing import SizeScheme, resolve_size_scheme
from pyhermes.builder.theming import Theme, resolve_theme

from .render import check_sources, render_math

#: Computer Modern: what a reader of research expects an equation to look like.
DEFAULT_MATH_FONTSET = "cm"

#: Four pixels per CSS px, which is 384 dpi at 96 px to the inch: over the 300
#: a print needs, so one render serves paper, and a screen PDF downsamples it.
DEFAULT_MATH_SCALE = 4


def image_from_math(
    latex: str = "",
    *,
    theme: Theme | str = "classic",
    size_theme: SizeScheme | SizeTheme | str = SizeTheme.STANDARD,
    fontset: str = DEFAULT_MATH_FONTSET,
    scale: float = DEFAULT_MATH_SCALE,
    lines: Sequence[str] | None = None,
    align_lines: str = "left",
) -> EmailImage:
    """
    Render ``latex`` (or ``lines``) in the theme's primary text colour at its body size.

    Attached by ``cid:``, with the source as alt and the display width the
    pixel width over ``scale``, so the same source twice is attached once.
    """
    rendered = render_math(
        latex,
        font_px=resolve_size_scheme(size_theme).type.body,
        color=resolve_theme(theme).text.primary,
        scale=scale,
        fontset=fontset,
        lines=lines,
        align_lines=align_lines,
    )
    source = "\n".join(check_sources(latex, lines))
    return EmailImage.attached(
        rendered.png, alt=source, width=max(1, round(rendered.width_px / scale))
    )


def math_block(
    latex: str = "",
    *,
    theme: Theme | str = "classic",
    size_theme: SizeScheme | SizeTheme | str = SizeTheme.STANDARD,
    fontset: str = DEFAULT_MATH_FONTSET,
    scale: float = DEFAULT_MATH_SCALE,
    caption: str = "",
    label: str = "",
    anchor: str = "",
    notes: Sequence[Footnote | str] | None = None,
    disclosure: str = "",
    align: str | ImageAlign = ImageAlign.CENTER,
    spacing: Spacing | Mapping[str, int | float] | None = None,
    lines: Sequence[str] | None = None,
    align_lines: str = "left",
) -> MathBlock:
    """
    A :class:`MathBlock` around :func:`image_from_math`, exhibit fields included.

    ``lines`` renders a multi-line display as one image, aligned as a block by
    ``align_lines``; its text part prints one ``$line$`` per line.
    """
    image = image_from_math(
        latex,
        theme=theme,
        size_theme=size_theme,
        fontset=fontset,
        scale=scale,
        lines=lines,
        align_lines=align_lines,
    )
    return MathBlock(
        image,
        latex=latex,
        lines=lines,
        caption=caption,
        label=label,
        anchor=anchor,
        notes=notes,
        disclosure=disclosure,
        align=align,
        spacing=spacing,
    )
