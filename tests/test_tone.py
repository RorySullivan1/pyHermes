"""
A semantic tone on a cell and a card (#178): the theme decides what negative looks like.

Before this, ``theme.semantic.positive`` and ``negative`` rendered nowhere by
default. They were tokens with no render site, so the only way a figure ever
turned green was a caller copying the hex out of the theme. These tests hold
the three things that change: a tone resolves against the *live* theme, an
explicit colour still wins over it, and a tone is a word, never a hex.
"""

import dataclasses
import math

import pytest

from pyhermes.builder import (
    DEFAULT_THEME,
    SLATE_THEME,
    CardGroup,
    DataTable,
    TemplateEngine,
    Tone,
    ValidationError,
    tone_of,
)
from pyhermes.builder.formats import pct
from pyhermes.builder.models import Card, Cell, KpiItem, TableRow
from pyhermes.builder.theming import SemanticColors


def _table(*cells: Cell) -> DataTable:
    return DataTable(["Factor", "1M"], [TableRow(["Value", cell]) for cell in cells])


def _html(component, theme=DEFAULT_THEME) -> str:
    return component.render(TemplateEngine().bound(theme=theme))


class TestTheVocabulary:
    def test_every_tone_names_a_semantic_token(self):
        """A tone the theme has no token for would fail at render, not at construction."""
        tokens = {spec.name for spec in dataclasses.fields(SemanticColors)}
        assert {tone.value for tone in Tone} == tokens

    @pytest.mark.parametrize("model", [Cell, lambda **kw: Card("S&P 500", "5,234", **kw)])
    @pytest.mark.parametrize("bad", ["#B85450", "Red", "Positive", "up arrow"])
    def test_a_tone_is_a_word_never_a_hex(self, model, bad):
        """
        The boundary that keeps ``tone`` from being a fifth colour exception:
        it carries no colour of its own, so a hex is refused by name.
        """
        with pytest.raises(ValidationError, match="pass a hex as 'color'"):
            model(tone=bad).validate()

    def test_a_kpi_validates_its_tone_too(self):
        with pytest.raises(ValidationError, match="kpi.tone"):
            KpiItem("VIX", "14.32", tone="#4A7C59").validate()


class TestATonedCellFollowsTheTheme:
    @pytest.mark.parametrize("theme", [DEFAULT_THEME, SLATE_THEME], ids=["classic", "slate"])
    @pytest.mark.parametrize("tone", list(Tone))
    def test_the_cell_takes_the_themes_token(self, theme, tone):
        html = _html(_table(Cell("+1.8%", tone=tone)), theme)
        assert f"color: {getattr(theme.semantic, tone)};" in html

    def test_an_explicit_colour_does_not_follow_the_theme(self):
        """Caller data about the figure: the theme is only the fallback behind it."""
        cell = Cell("+1.8%", color="#123456", tone=Tone.NEGATIVE)
        for theme in (DEFAULT_THEME, SLATE_THEME):
            html = _html(_table(cell), theme)
            assert "color: #123456;" in html
            assert theme.semantic.negative not in html

    def test_the_same_table_differs_only_in_the_toned_colour(self):
        toned = _table(Cell("+1.8%", tone=Tone.POSITIVE))
        classic, slate = _html(toned, DEFAULT_THEME), _html(toned, SLATE_THEME)
        assert DEFAULT_THEME.semantic.positive in classic
        assert SLATE_THEME.semantic.positive in slate
        assert SLATE_THEME.semantic.positive not in classic

    def test_a_tone_leaves_the_striping_alone(self):
        """As a cell background does: marking one figure costs no row its tint."""
        table = DataTable(
            ["Factor", "1M"],
            [TableRow(["A", "1"]), TableRow(["B", Cell("2", tone=Tone.NEGATIVE)])],
        )
        second_row = _html(table).split("<tr")[3]
        assert f"background-color: {DEFAULT_THEME.palette.row_alt};" in second_row

    def test_a_subhead_keeps_its_heading_colour(self):
        """A row kind is chrome and outranks a cell's tone, exactly as it outranks a colour."""
        table = DataTable(
            ["Factor", "1M"],
            [TableRow([Cell("Equity", tone=Tone.NEGATIVE)], kind="subhead"), TableRow(["A", "1"])],
        )
        assert DEFAULT_THEME.semantic.negative not in _html(table)

    def test_an_untoned_cell_renders_as_before(self):
        """The default path is byte-identical, which every golden also pins."""
        assert _html(_table(Cell("+1.8%"))) == _html(_table(Cell("+1.8%", tone="")))


class TestATonedCardFollowsTheTheme:
    @pytest.mark.parametrize("theme", [DEFAULT_THEME, SLATE_THEME], ids=["classic", "slate"])
    @pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
    def test_the_value_takes_the_themes_token(self, theme, orientation):
        cards = [
            KpiItem("UST 10Y", "4.28%", tone=Tone.NEGATIVE),
            KpiItem("Gold", "2,411", tone=Tone.POSITIVE),
        ]
        html = _html(CardGroup(cards, orientation=orientation), theme)
        assert theme.semantic.negative in html
        assert theme.semantic.positive in html

    def test_an_explicit_colour_wins(self):
        html = _html(CardGroup([KpiItem("VIX", "14.32", color="#123456", tone="negative")] * 2))
        assert DEFAULT_THEME.semantic.negative not in html

    def test_an_untoned_card_still_takes_the_neutral(self):
        html = _html(CardGroup([Card("Coverage", "128 names"), Card("Names", "40")]))
        assert f"color: {DEFAULT_THEME.semantic.neutral};" in html


class TestToneOf:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0.0142, Tone.POSITIVE),
            (-0.004, Tone.NEGATIVE),
            (0, Tone.NEUTRAL),
            (-0.0, Tone.NEUTRAL),
            (None, Tone.NEUTRAL),
            (math.nan, Tone.NEUTRAL),
        ],
    )
    def test_the_sign_decides(self, value, expected):
        assert tone_of(value) is expected

    def test_a_figure_shown_as_zero_is_neutral(self):
        """The string and its colour cannot disagree: '0.00%' is never red."""
        assert tone_of(-0.00001) is Tone.NEGATIVE
        assert tone_of(-0.00001, pct) is Tone.NEUTRAL


class TestFromNumber:
    def test_formats_once_and_tones_by_the_sign(self):
        cell = Cell.from_number(-0.004, lambda v: pct(v, 1, sign=True))
        assert (cell.text, cell.tone) == ("-0.4%", Tone.NEGATIVE)

    def test_a_value_that_rounds_to_zero_is_neutral(self):
        cell = Cell.from_number(-0.00001, pct)
        assert (cell.text, cell.tone) == ("0.00%", Tone.NEUTRAL)

    def test_a_stated_tone_overrides_the_sign(self):
        """A falling VIX is good news: the tone is the caller's claim, not the sign's."""
        assert Cell.from_number(-2.18, tone=Tone.POSITIVE).tone is Tone.POSITIVE

    def test_the_default_formatter_is_number(self):
        assert Cell.from_number(5234).text == "5,234"

    def test_an_unknown_tone_raises(self):
        with pytest.raises(ValidationError, match="cell.tone"):
            Cell.from_number(1.0, tone="Up")


class TestThePlainTextProjection:
    def test_a_tone_adds_nothing_to_the_text_part(self):
        """
        The sign already in the formatted string is the tone's projection, so
        a toned table and an untoned one project identically.
        """
        toned = _table(Cell("-0.4%", tone=Tone.NEGATIVE))
        plain = _table(Cell("-0.4%"))
        assert toned.text() == plain.text()


def test_the_semantic_tokens_now_have_a_render_site():
    """
    The gap #170 was filed on: positive and negative rendered nowhere.
    Both templates now read the colour a tone names, through ``theme.tone`` (#387).
    """
    from pathlib import Path

    templates = Path("pyhermes/builder/templates/analysis")
    assert "theme.tone[cell.tone]" in (templates / "data-table.html").read_text(encoding="utf-8")
    assert "theme.tone[card.tone" in (templates / "card-group.html").read_text(encoding="utf-8")
