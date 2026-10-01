"""
The email's theme offered to matplotlib (#275): a chart drawn inside it matches the email.
"""

from __future__ import annotations

import warnings

import pytest

pytest.importorskip("matplotlib", reason='chart_style needs "pyhermes[charts]"')

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import to_hex  # noqa: E402

from pyhermes.builder import DEFAULT_THEME, SLATE_THEME, Email  # noqa: E402
from pyhermes.builder.exceptions import ValidationError  # noqa: E402
from pyhermes.data import ChartStyle, chart_style  # noqa: E402
from pyhermes.data.style import RC_TOKENS, SERIES_TOKENS  # noqa: E402


def _token(theme, layer, name):
    return getattr(getattr(theme, layer), name)


def test_a_figure_drawn_inside_takes_the_accent_first():
    with plt.rc_context(chart_style()):
        fig, ax = plt.subplots()
        first, second = ax.plot([1, 2])[0], ax.plot([2, 1])[0]
        bars = ax.bar([0, 1], [1, 2])
    try:
        assert to_hex(first.get_color()) == DEFAULT_THEME.palette.accent.lower()
        assert to_hex(second.get_color()) == DEFAULT_THEME.palette.header_bg.lower()
        assert to_hex(fig.get_facecolor()) == DEFAULT_THEME.palette.surface.lower()
        assert to_hex(ax.spines["left"].get_edgecolor()) == DEFAULT_THEME.palette.rule.lower()
        assert len(bars) == 2
    finally:
        plt.close(fig)


def test_nothing_changes_outside_the_context():
    before = dict(matplotlib.rcParams)
    with plt.rc_context(chart_style("slate")):
        pass
    assert dict(matplotlib.rcParams) == before


@pytest.mark.parametrize("key", list(RC_TOKENS))
def test_slate_differs_from_classic_exactly_where_the_palettes_do(key):
    layer, name = RC_TOKENS[key]
    classic, slate = chart_style("classic")[key], chart_style("slate")[key]
    assert classic == _token(DEFAULT_THEME, layer, name)
    assert slate == _token(SLATE_THEME, layer, name)
    assert (classic != slate) == (
        _token(DEFAULT_THEME, layer, name) != _token(SLATE_THEME, layer, name)
    )


def test_the_series_and_the_signs_come_from_the_theme():
    style = chart_style(SLATE_THEME)
    assert isinstance(style, ChartStyle)
    assert style.series[0] == SLATE_THEME.palette.accent
    assert set(style.series) == {_token(SLATE_THEME, *pair) for pair in SERIES_TOKENS}
    assert (style.positive, style.negative) == (
        SLATE_THEME.semantic.positive,
        SLATE_THEME.semantic.negative,
    )


def test_it_reads_an_emails_own_theme():
    email = Email({"email_subject": "S", "firm_name": "F", "campaign_name": "C", "theme": "slate"})
    assert chart_style(email.metadata.theme).series[0] == SLATE_THEME.palette.accent


@pytest.mark.parametrize(("font_theme", "role"), [("classic", "label"), ("modern", "body")])
def test_the_font_ends_at_the_generic_and_never_warns(font_theme, role):
    from pyhermes.builder.typography import resolve_font_theme

    stack = getattr(resolve_font_theme(font_theme), role)
    family = chart_style(font_theme=font_theme, role=role)["font.family"]
    assert family[-1] == stack.families[-1]
    assert set(family) <= set(stack.families)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with plt.rc_context(chart_style(font_theme=font_theme, role=role)):
            fig, ax = plt.subplots()
            ax.set_title("Factor returns")
            fig.canvas.draw()
            plt.close(fig)


def test_an_unknown_theme_is_refused():
    with pytest.raises(ValidationError):
        chart_style("neon")
