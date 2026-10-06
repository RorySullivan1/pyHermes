"""
Brand tones (#387): a theme declares named tones beyond the semantic three.

A tone is resolved in one place, ``Theme.tone``, so every object that takes a
tone reads a brand tone in every medium; whether a name is declared is asked
once, when its section is added.
"""

from __future__ import annotations

import re

import pytest

from pyhermes.brochure import Brochure, Panel
from pyhermes.builder import (
    Badge,
    BarList,
    Callout,
    Column,
    DataTable,
    EmailBuilder,
    FullWidth,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.exhibits import Legend, LegendEntry
from pyhermes.builder.glance import BarItem
from pyhermes.builder.models import Cell, TableRow
from pyhermes.builder.theming import DEFAULT_THEME, Theme, chart_colors
from pyhermes.deck import Deck
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument
from qa.fixtures import _paged

BRAND, SKY = "#B8860B", "#0077A8"
THEME = DEFAULT_THEME.derive(tones={"brand": BRAND, "sky": SKY})
FACTS = {"firm_name": "Hermes Research", "campaign_name": "Brand", "theme": THEME}


def _email(*sections, theme: Theme = THEME):
    builder = EmailBuilder().metadata({**FACTS, "email_subject": "Brand", "theme": theme})
    for section in sections:
        builder.section(section)
    return builder.build()


def _paper(*sections):
    document = PagedDocument(
        {**_paged.facts(), "theme": THEME}, cover=EmptyCover(), back_matter=EmptyBackMatter()
    )
    for section in sections:
        document.add_section(section)
    return document


def _boxes() -> TwoColumn:
    return TwoColumn(
        left=Callout(TextBlock("<p>Gold.</p>"), tone="brand", label="Facts"),
        right=Callout(TextBlock("<p>Sky.</p>"), tone="sky", label="Suits"),
    )


def _every_reader() -> list[FullWidth]:
    """A Callout, a Badge, a table cell, a status dot and a BarList, each in a brand tone."""
    return [
        FullWidth(
            Callout(TextBlock("<p>Boxed.</p>"), tone="brand"),
            title="Boxed",
            badge=Badge("New", "sky"),
        ),
        FullWidth(
            DataTable(
                ["Holding", Column("Sleeve", kind="status", statuses={"Core": "sky"}), "Weight"],
                [TableRow(["Large cap", "Core", Cell("62%", tone="brand")])],
            )
        ),
        FullWidth(BarList([BarItem("Tech", 31, tone="sky"), BarItem("Banks", 13)], tone="brand")),
    ]


class TestTheThemeDeclaresThem:
    def test_a_brand_tone_resolves_beside_the_semantic_ones(self):
        assert THEME.tone == {
            "positive": DEFAULT_THEME.semantic.positive,
            "negative": DEFAULT_THEME.semantic.negative,
            "neutral": DEFAULT_THEME.semantic.neutral,
            "brand": BRAND,
            "sky": SKY,
        }

    def test_no_semantic_token_is_repainted(self):
        assert THEME.semantic == DEFAULT_THEME.semantic
        assert THEME.palette == DEFAULT_THEME.palette

    def test_derive_adds_to_the_tones_already_declared(self):
        assert THEME.derive(tones={"ink": "#111111"}).tones == {
            "brand": BRAND,
            "sky": SKY,
            "ink": "#111111",
        }

    def test_a_theme_without_tones_resolves_the_semantic_three(self):
        assert list(DEFAULT_THEME.tone) == ["positive", "negative", "neutral"]

    @pytest.mark.parametrize(
        ("tones", "match"),
        [
            ({"positive": "#00AA00"}, "shadows a semantic tone"),
            ({"Brand": BRAND}, "lowercase word"),
            ({"brand": "gold"}, r"theme\.tones\.brand"),
            ({"brand": 0xB8860B}, "hex color string"),
        ],
    )
    def test_a_bad_tone_is_refused_at_construction(self, tones, match):
        with pytest.raises(ValidationError, match=match):
            Theme(tones=tones)

    def test_tones_are_a_mapping(self):
        with pytest.raises(ValidationError, match="maps names"):
            Theme(tones=[("brand", BRAND)])  # type: ignore[arg-type]

    def test_the_theme_owns_its_copy(self):
        given = {"brand": BRAND}
        theme = Theme(tones=given)
        given["brand"] = "#000000"
        assert theme.tone["brand"] == BRAND


class TestACalloutTakesOne:
    @pytest.mark.parametrize("build", [_email, _paper], ids=["email", "paper"])
    def test_each_box_is_framed_in_its_tone_beside_an_untoned_one(self, build):
        html = build(
            _boxes(), FullWidth(Callout(TextBlock("<p>Plain.</p>"), label="Plain"))
        ).render()
        assert f"border:1px solid {BRAND}" in html
        assert f"border:1px solid {SKY}" in html
        assert f"border:1px solid {DEFAULT_THEME.palette.rule}" in html
        assert DEFAULT_THEME.palette.highlight_tint in html

    def test_a_hex_is_still_refused_by_name(self):
        with pytest.raises(ValidationError, match="pass a hex as 'color'"):
            Callout(TextBlock("<p>x</p>"), tone=BRAND)


class TestAnUndeclaredToneIsRefusedWhenItsSectionIsAdded:
    @pytest.mark.parametrize(
        "section",
        [
            FullWidth(Callout(TextBlock("<p>x</p>"), tone="gold")),
            FullWidth(TextBlock("<p>x</p>"), title="T", badge=Badge("New", "gold")),
            FullWidth(DataTable(["A", "B"], [TableRow(["x", Cell("1", tone="gold")])])),
            FullWidth(
                DataTable(
                    ["A", Column("S", kind="status", statuses={"On": "gold"})],
                    [TableRow(["x", "On"])],
                )
            ),
            FullWidth(BarList([BarItem("A", 1, tone="gold")])),
            FullWidth(Legend([LegendEntry("A", tone="gold")])),
        ],
        ids=["callout", "badge", "cell", "status", "bar", "legend"],
    )
    def test_it_names_the_tones_the_theme_declares(self, section):
        email = _email()
        with pytest.raises(
            ValidationError, match=r"'gold'.*\['positive', 'negative', 'neutral', 'brand', 'sky'\]"
        ):
            email.add_section(section)
        assert email.text() == _email().text()

    def test_a_document_on_a_theme_without_it_refuses_a_brand_tone(self):
        with pytest.raises(ValidationError, match="does not declare"):
            _email(_boxes(), theme=DEFAULT_THEME)


class TestEveryReaderTakesOneInEveryMedium:
    def test_in_the_email(self):
        html = _email(*_every_reader()).render()
        assert html.count(BRAND) >= 3 and html.count(SKY) >= 3

    def test_on_a_slide(self):
        deck = Deck(FACTS).add_slide(_every_reader(), "Brand")
        html = deck.render()
        assert html.count(BRAND) >= 3 and html.count(SKY) >= 3

    def test_in_a_brochure_panel(self):
        panels = [Panel([FullWidth(TextBlock(f"<p>Face {n}</p>"))]) for n in range(5)]
        panels.append(Panel(_every_reader()))
        html = Brochure(FACTS, panels).render()
        assert html.count(BRAND) >= 3 and html.count(SKY) >= 3

    def test_a_legend_swatch_takes_the_tone(self):
        html = _email(FullWidth(Legend([LegendEntry("Fund", tone="brand")]))).render()
        assert BRAND in html


class TestAChartsColoursNameABrandTone:
    """#389: the chart cycle ends in the brand tones, so a key and a plot can name one."""

    def test_the_brand_tones_follow_the_series_colours_in_order(self):
        assert chart_colors(THEME) == (*chart_colors(DEFAULT_THEME), BRAND, SKY)

    def test_a_brand_tone_a_series_colour_already_draws_is_kept_once(self):
        accent = DEFAULT_THEME.palette.accent
        theme = DEFAULT_THEME.derive(tones={"house": accent})
        assert chart_colors(theme) == chart_colors(DEFAULT_THEME)

    @pytest.mark.parametrize("build", [_email, _paper], ids=["email", "paper"])
    def test_a_key_in_two_brand_tones_draws_the_plotted_colours(self, build):
        key = Legend([LegendEntry("Gold", tone="brand"), LegendEntry("Sky", tone="sky")])
        html = build(FullWidth(key)).render()
        swatches = re.findall(
            r'class="legend-swatch"[^>]*background-color: (#[0-9A-Fa-f]{6})', html
        )
        assert swatches == list(chart_colors(THEME)[-2:]) == [BRAND, SKY]

    def test_a_series_past_the_tokens_names_a_brand_tone(self):
        first_brand = len(chart_colors(DEFAULT_THEME))
        key = Legend([LegendEntry("Gold", series=first_brand), LegendEntry("Sky", color=SKY)])
        html = _email(FullWidth(key)).render()
        assert BRAND in html and SKY in html

    def test_without_the_tone_the_series_is_refused_naming_colours_and_tones(self):
        key = Legend([LegendEntry("Gold", series=len(chart_colors(DEFAULT_THEME)))])
        with pytest.raises(ValidationError, match=r"chart colours are \[.*\] and its tones \["):
            _email(FullWidth(key), theme=DEFAULT_THEME)

    def test_an_undeclared_tone_is_refused_naming_colours_and_tones(self):
        key = Legend([LegendEntry("Gold", tone="gold")])
        with pytest.raises(
            ValidationError,
            match=r"'gold'.*chart colours are \[.*\] and its tones \['positive', 'negative', "
            r"'neutral', 'brand', 'sky'\]",
        ):
            _email(FullWidth(key))
