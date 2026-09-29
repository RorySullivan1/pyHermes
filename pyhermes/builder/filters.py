"""
The Jinja filters, and the escaping contract they implement.

Autoescape is **off**, so escaping is explicit and splits three ways:

* **Plain-text fields** are escaped by the templates through ``escape_html``.
  Pass them raw — pre-escaping double-escapes them.
* **HTML fields** (``TextBlock.content``, ``NumberedItem.body``, ``Card.body``,
  ``Footer.disclaimer``, ``header_disclaimer``) are emitted raw because
  callers deliberately pass markup. **Escaping anything untrusted in them is
  the caller's job** — :func:`escape_html` is exported for that.
* **Attributes** are always escaped by the builder, quotes included, so a
  value can never break out of the attribute it sits in.
"""

import html
import math
import re
from typing import Any

import jinja2

from .exceptions import ValidationError


def validate_hex_color(value: str) -> str:
    """
    Validate that a string is a valid hex color code.

    Returns the value if valid.

    Raises:
        ValidationError: If the value is not a ``#RRGGBB`` string.  This is a
            data-validation failure, not a template failure, so it propagates
            out of a render as-is rather than being wrapped in
            ``TemplateError`` — either way it stays catchable as
            ``EmailBuilderError``, which everything the builder rejects must be.

    Usage in templates:
        {{ color | validate_hex_color }}
    """
    if not isinstance(value, str):
        raise ValidationError(f"hex color must be a string, got {type(value).__name__}: {value!r}")
    if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
        raise ValidationError(f"invalid hex color (expected #RRGGBB), got: {value!r}")
    return value


def escape_html(value: Any) -> str:
    """
    Escape text for safe interpolation into HTML, attributes included.

    Escapes ``&``, ``<``, ``>``, ``"`` and ``'``, so the result is safe both
    in element content and inside a quoted attribute value.

    Use this on any untrusted text destined for an HTML field
    (``TextBlock.content``, ``NumberedItem.body``): those are emitted raw by
    design, so escaping them is the caller's job.  Plain-text fields are
    already escaped by the templates — escaping them again double-escapes.

    Usage in templates::

        {{ section_title | escape_html }}

    Usage from Python::

        from pyhermes.builder.filters import escape_html

        TextBlock(f"<p>{escape_html(untrusted_headline)}</p>")
    """
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def escape_html_ascii(value: Any) -> str:
    """
    :func:`escape_html`, with every non-ASCII character as a numeric reference.

    For text that must survive a client guessing the charset wrong: ``©``
    mis-decoded as latin-1 renders as ``Â©``, an em dash as ``â€"``. The
    footer's default copyright always avoided that by writing ``&copy;`` as
    an entity; a caller cannot, since their entity would escape to literal
    text, so this is the same guarantee for text they supply (#148).

    Scoped to that row, not to every plain-text field. The exposure is the
    same everywhere, but going global is a policy decision with a size cost
    against the 102 KB budget — a reference is 8 bytes where the character
    is 3 — and belongs to its own change.
    """
    return "".join(ch if ch.isascii() else f"&#{ord(ch)};" for ch in escape_html(value))


def css_string(value: Any) -> str:
    """
    Escape text for use inside a quoted CSS string, e.g. ``content: "..."``.

    The running margin boxes are the only place this package writes a fact
    into CSS rather than into markup, and CSS has its own escaping rules:
    a backslash or a double quote ends or corrupts the literal.

    ``<`` is escaped too, and that is the trap rather than the nicety. These
    strings are emitted inside a ``style`` element, where the HTML parser is
    still watching for ``</style>`` — a firm name containing one would close
    the stylesheet and put the rest of the rule on the page as text. A hex
    escape keeps it a string to the CSS parser and invisible to the HTML one.

    A newline becomes ``\\A``, CSS's line break, rather than being dropped.
    """
    text = "" if value is None else str(value)
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("<", "\\3C ")
        .replace("\r", "")
        .replace("\n", "\\A ")
    )


def size_kb(value: str) -> float:
    """
    Return the size of a string in kilobytes (UTF-8 encoded).

    Usage in templates:
        {{ content | size_kb }}
    """
    return len(str(value).encode("utf-8")) / 1024


def default_color(value: Any, fallback: str) -> str:
    """
    Return the value if truthy, otherwise the fallback. Validates the result.

    ``fallback`` is required rather than defaulted: the sensible default is
    the active theme's neutral, and a filter must not reach for a theme
    globally — it is handed one, the same way every template is. A literal
    here would be a colour outside the palette by construction.

    Raises:
        ValidationError: If the resolved color is not a ``#RRGGBB`` string.

    Usage in templates::

        {{ card.color | default_color(theme.semantic.neutral) }}
    """
    result = value if value else fallback
    return validate_hex_color(result)


def percent(value: Any) -> str:
    """
    A ratio as a CSS percentage: ``1.72`` -> ``"172%"``.

    Line-heights are stored as ratios in :mod:`pyhermes.builder.sizing`, because a
    ratio is what the design vocabulary means and what a scheme's own tests
    compare. They are *emitted* as percentages because Outlook Classic does
    not support a unitless ``line-height`` at all (#78) — so the conversion
    belongs at the boundary, in a filter, rather than in the token.

    The formatting contract matters as much as the arithmetic: ``1.72 * 100``
    is ``171.99999999999997`` in binary floating point, and ``172.0%`` would
    be as wrong as ``171.99999999999997%``. ``.10g`` rounds to ten
    significant digits and drops the trailing zeros, the same contract
    :meth:`pyhermes.builder.theming.Rgba.css` holds.

    Raises:
        ValidationError: If the value is not a number.

    Usage in templates::

        line-height:{{ size.type.body_line | percent }}
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"percent() needs a number, got: {type(value).__name__} ({value!r})")
    return f"{value * 100:.10g}%"


def heat_color(position: Any, low: str, high: str) -> str:
    """
    The colour ``position`` of the way from ``low`` to ``high``, as ``#RRGGBB``.

    Interpolated per channel in sRGB and rounded half up, so a position pins
    one byte-exact colour. Both ends come from the theme (#227).

    Raises:
        ValidationError: If an end is not ``#RRGGBB`` or the position is not
            a number in ``[0, 1]``.
    """
    ends = [validate_hex_color(low), validate_hex_color(high)]
    if isinstance(position, bool) or not isinstance(position, (int, float)):
        raise ValidationError(f"heat_color() needs a number, got: {position!r}")
    if not 0 <= position <= 1:
        raise ValidationError(f"heat_color() needs a position in [0, 1], got: {position!r}")
    start, end = ([int(hexa[i : i + 2], 16) for i in (1, 3, 5)] for hexa in ends)
    channels = (math.floor(a + (b - a) * position + 0.5) for a, b in zip(start, end, strict=True))
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def readable_on(background: str, dark: str, light: str) -> str:
    """
    Whichever of ``dark`` and ``light`` contrasts more with ``background``.

    WCAG 2.x relative luminance and contrast ratio, so text on a heat tint
    (#227) stays legible at both ends of the scale.
    """
    ratios = {
        colour: _contrast(validate_hex_color(background), validate_hex_color(colour))
        for colour in (dark, light)
    }
    return max((dark, light), key=ratios.__getitem__)


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _luminance(colour: str) -> float:
    def linear(channel: int) -> float:
        c = channel / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(int(colour[i : i + 2], 16)) for i in (1, 3, 5))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def register_all(env: jinja2.Environment) -> None:
    """
    Register all custom filters and tests on a Jinja2 Environment.

    Args:
        env: jinja2.Environment instance
    """
    env.filters["escape_html"] = escape_html
    env.filters["css_string"] = css_string
    env.filters["validate_hex_color"] = validate_hex_color
    env.filters["size_kb"] = size_kb
    env.filters["default_color"] = default_color
    env.filters["percent"] = percent
    env.filters["heat_color"] = heat_color
    env.filters["readable_on"] = readable_on
