"""
The email's theme offered to matplotlib, so a chart is drawn to match it (#275).

pyHermes still never styles a plot: this hands the author settings to draw
inside, and changes nothing unless called.

    with plt.rc_context(chart_style(email.metadata.theme)):
        fig, ax = plt.subplots()
"""

from __future__ import annotations

from typing import Any

from pyhermes.builder.theming import SERIES_TOKENS as SERIES_TOKENS
from pyhermes.builder.theming import Theme, chart_colors, resolve_theme
from pyhermes.builder.typography import FontTheme, resolve_font_theme

from .charts import _backend

#: Each colour setting and the theme token it reads, as ``(layer, token)``.
RC_TOKENS: dict[str, tuple[str, str]] = {
    "figure.facecolor": ("palette", "surface"),
    "axes.facecolor": ("palette", "surface"),
    "savefig.facecolor": ("palette", "surface"),
    "axes.edgecolor": ("palette", "rule"),
    "grid.color": ("palette", "rule_subtle"),
    "text.color": ("text", "primary"),
    "axes.labelcolor": ("text", "secondary"),
    "axes.titlecolor": ("text", "heading"),
    "xtick.color": ("text", "secondary"),
    "ytick.color": ("text", "secondary"),
}


class ChartStyle(dict[str, Any]):
    """
    matplotlib ``rc`` settings drawn from a theme, with the colours a chart picks by meaning.

    A ``dict``, so ``plt.rc_context(style)`` takes it as it is. ``positive`` and
    ``negative`` colour a bar by its sign, and ``series`` is the colour cycle in
    order, for a chart that sets colours itself.
    """

    positive: str
    negative: str
    series: tuple[str, ...]


def chart_style(
    theme: Theme | str = "classic",
    font_theme: FontTheme | str = "classic",
    *,
    role: str = "label",
) -> ChartStyle:
    """
    The settings to draw a chart in ``theme``'s colours and ``font_theme``'s ``role`` face.

    The font list keeps only the families matplotlib can find, then the
    stack's generic family, so a missing face falls back without a warning.

    Raises:
        BackendMissingError: Without the ``[charts]`` extra.
        ValidationError: For an unknown theme, font theme or role.
    """
    matplotlib = _backend()
    resolved = resolve_theme(theme)
    stack = getattr(resolve_font_theme(font_theme), role)
    series = chart_colors(resolved)
    style = ChartStyle(
        {key: _token(resolved, layer, name) for key, (layer, name) in RC_TOKENS.items()}
    )
    style["axes.prop_cycle"] = matplotlib.cycler(color=list(series))
    style["font.family"] = [*_installed(stack.families[:-1]), stack.families[-1]]
    style.positive = resolved.semantic.positive
    style.negative = resolved.semantic.negative
    style.series = series
    return style


def _token(theme: Theme, layer: str, name: str) -> str:
    value: str = getattr(getattr(theme, layer), name)
    return value


def _installed(families: tuple[str, ...]) -> list[str]:
    """The families matplotlib resolves to a real font, in order."""
    from matplotlib import font_manager

    found = []
    for family in families:
        try:
            font_manager.findfont(
                font_manager.FontProperties(family=family), fallback_to_default=False
            )
        except ValueError:
            continue
        found.append(family)
    return found
