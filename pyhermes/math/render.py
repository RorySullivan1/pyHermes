"""
LaTeX, as the PNG bytes a :class:`~pyhermes.builder.MathBlock` takes (#230).

matplotlib's mathtext is the renderer: a TeX subset with no TeX installation.
It is the ``[math]`` extra, imported only on use, so the core stays Jinja2-only.
"""

from __future__ import annotations

import io
import re
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.filters import validate_hex_color

from .exceptions import BackendMissingError, MathSyntaxError

#: The mathtext fontsets. ``custom`` is refused: it falls back through the
#: caller's rcParams, so the same source would render differently per machine.
FONTSETS = ("cm", "dejavusans", "dejavuserif", "stix", "stixsans")

#: The pixel density one scale step stands for: CSS px are 96 to the inch.
PX_PER_INCH = 96

#: Points per CSS px; mathtext sizes type in points.
_PT_PER_PX = 0.75

_SYMBOL = re.compile(r"Unknown symbol: ([^,\s]+)")
_COLUMN = re.compile(r"col:(\d+)")


@dataclass(frozen=True)
class RenderedMath:
    """A rendered equation: its PNG bytes and their pixel size."""

    png: bytes
    width_px: int
    height_px: int


def available() -> bool:
    """Whether matplotlib is installed, for a caller that wants to skip."""
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return False
    return True


#: How a multi-line display sets its lines: as one block, never on a relation.
LINE_ALIGNMENTS = ("left", "center", "right")


def render_math(
    latex: str = "",
    *,
    font_px: float,
    color: str,
    scale: float,
    fontset: str,
    lines: Sequence[str] | None = None,
    align_lines: str = "left",
) -> RenderedMath:
    """
    Render one expression, or ``lines`` stacked, to a transparent PNG.

    ``scale`` pixels per CSS px. Deterministic and versionless: one source
    under one fontset gives the same bytes every call. A source mathtext cannot
    parse raises :class:`MathSyntaxError` here, at the call. ``lines`` are set
    as one block, aligned by ``align_lines``; mathtext cannot align on ``&``.
    """
    sources = check_sources(latex, lines)
    if align_lines not in LINE_ALIGNMENTS:
        raise ValidationError(
            f"'align_lines' must be one of {list(LINE_ALIGNMENTS)}, got {align_lines!r}"
        )
    _check_positive(font_px, "font_px")
    _check_positive(scale, "scale")
    validate_hex_color(color)
    if fontset not in FONTSETS:
        raise ValidationError(f"'fontset' must be one of {list(FONTSETS)}, got {fontset!r}")
    text = "\n".join(f"${source}$" for source in sources)
    return _render(text, "\n".join(sources), font_px, color, scale, fontset, align_lines)


def check_sources(latex: str, lines: Sequence[str] | None) -> list[str]:
    """The expressions to render: ``latex`` alone, or each of ``lines``."""
    if lines is None:
        _check_source(latex, "latex")
        return [latex]
    if latex:
        raise ValidationError("pass 'latex' or 'lines', not both")
    if isinstance(lines, str) or not lines:
        raise ValidationError(f"'lines' must be a non-empty list of sources, got {lines!r}")
    for line in lines:
        _check_source(line, "lines")
        if "&" in line:
            raise ValidationError(
                f"'lines' holds '&' in {line!r}: mathtext cannot align on a relation, "
                "so the lines align as one block (align_lines=)"
            )
    return list(lines)


def _render(
    text: str, source: str, font_px: float, color: str, scale: float, fontset: str, align: str
) -> RenderedMath:
    """Draw ``text`` on an empty Figure and crop the PNG to it."""
    mpl = _backend()
    figure = mpl.figure.Figure(figsize=(0.01, 0.01))
    figure.text(
        0,
        0,
        text,
        fontsize=font_px * _PT_PER_PX,
        color=color,
        math_fontfamily=fontset,
        multialignment=align,
    )
    buffer = io.BytesIO()
    try:
        figure.savefig(
            buffer,
            format="png",
            dpi=PX_PER_INCH * scale,
            transparent=True,
            bbox_inches="tight",
            pad_inches=0.02,
            metadata={"Software": None},
        )
    except ValueError as exc:
        raise _syntax_error(source, exc) from exc
    png = buffer.getvalue()
    width, height = struct.unpack(">II", png[16:24])
    return RenderedMath(png=png, width_px=width, height_px=height)


def _syntax_error(source: str, exc: ValueError) -> MathSyntaxError:
    last = str(exc).strip().splitlines()[-1]
    symbol = _SYMBOL.search(last)
    column = _COLUMN.search(last)
    what = f"unknown symbol {symbol.group(1)}" if symbol else last.split(":", 1)[-1].strip()
    where = f" at column {column.group(1)}" if column else ""
    return MathSyntaxError(f"mathtext cannot render {source!r}: {what}{where}")


def _check_source(latex: str, name: str) -> None:
    if not isinstance(latex, str) or not latex.strip():
        raise ValidationError(f"'{name}' is required, got {latex!r}")
    if "\n" in latex:
        raise ValidationError(f"'{name}' holds a newline; render several lines with lines=")
    if re.search(r"(?<!\\)\$", latex):
        raise ValidationError(
            f"'{name}' holds a bare '$'; pass the source without delimiters: {latex!r}"
        )


def _check_positive(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise ValidationError(f"{name!r} must be a positive number, got {value!r}")


def _backend() -> Any:
    """Import matplotlib's Figure, or say what to install."""
    try:
        import matplotlib
        import matplotlib.figure  # noqa: F401
    except ImportError as exc:
        raise BackendMissingError(
            "Rendering an equation needs matplotlib, which is an optional extra. "
            'Install it with: pip install "pyhermes[math]"'
        ) from exc
    return matplotlib
