"""
A solid Callout (#388): a box filled with its tone's full colour, a chip such as a ticker.

The block inside is set on the type that reads on that colour, chosen by the
same rule a section's ground uses (#266), so a dark tone takes the theme's
``on_dark`` ladder and a light one keeps the theme's type.
"""

from __future__ import annotations

import re

import pytest

from pyhermes.brochure import Brochure, Panel
from pyhermes.builder import Callout, DataTable, EmailBuilder, FullWidth, TextBlock
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.models import TableRow
from pyhermes.builder.theming import DEFAULT_THEME, Theme
from pyhermes.deck import Deck
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument
from qa.fixtures import _paged

INK, LEMON, NAVY = "#111111", "#F2D94E", "#1B3A5C"
THEME = DEFAULT_THEME.derive(tones={"ink": INK, "lemon": LEMON})
FACTS = {"firm_name": "Hermes Research", "campaign_name": "Chip", "theme": THEME}
ON_DARK = DEFAULT_THEME.text.on_dark


def _chip(tone: str = "ink", **kwargs) -> Callout:
    return Callout(TextBlock("<p>HRMS</p>"), tone=tone, label="Ticker", fill="solid", **kwargs)


def _email(*sections, theme: Theme = THEME):
    builder = EmailBuilder().metadata({**FACTS, "email_subject": "Chip", "theme": theme})
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


def _box(html: str) -> str:
    """The first callout's markup, from its table to its close."""
    start = html.index('<table class="callout"')
    return html[start : html.index("</table>", start)]


class TestItIsChecked:
    def test_fill_is_tint_or_solid(self):
        with pytest.raises(ValidationError, match="callout.fill"):
            Callout(TextBlock("<p>x</p>"), tone="ink", fill="opaque")

    def test_a_solid_box_needs_a_tone(self):
        with pytest.raises(ValidationError, match="needs a tone"):
            Callout(TextBlock("<p>x</p>"), fill="solid")

    def test_tint_is_the_default(self):
        assert Callout(TextBlock("<p>x</p>")).fill == "tint"


class TestADarkToneTakesTheOnDarkType:
    @pytest.mark.parametrize("build", [_email, _paper], ids=["email", "paper"])
    def test_the_cell_is_filled_and_the_type_is_on_dark(self, build):
        box = _box(build(FullWidth(_chip())).render())
        assert f'bgcolor="{INK}"' in box and f"background-color:{INK};" in box
        assert f"color: {ON_DARK};" in box
        assert DEFAULT_THEME.text.primary not in box

    def test_the_label_is_not_drawn_in_the_colour_it_sits_on(self):
        box = _box(_email(FullWidth(_chip())).render())
        label = re.search(r"<div style=\"[^\"]*\">Ticker</div>", box)
        assert label and f"color: {ON_DARK};" in label.group(0)

    def test_the_block_drops_the_class_dark_mode_would_repaint(self):
        assert "body-text" not in _box(_email(FullWidth(_chip())).render())

    def test_a_table_inside_keeps_its_own_surface(self):
        table = DataTable(["A"], [TableRow(["1"])])
        html = _email(FullWidth(Callout(table, tone="ink", fill="solid"))).render()
        assert f'bgcolor="{DEFAULT_THEME.palette.surface}"' in html

    def test_its_text_part_is_a_tinted_boxes(self):
        assert (
            _email(FullWidth(_chip())).text()
            == _email(
                FullWidth(Callout(TextBlock("<p>HRMS</p>"), tone="ink", label="Ticker"))
            ).text()
        )


class TestALightToneKeepsTheThemesType:
    def test_on_lemon_the_type_stays_dark(self):
        box = _box(_email(FullWidth(_chip("lemon"))).render())
        assert f'bgcolor="{LEMON}"' in box
        assert f"color: {ON_DARK};" not in box
        assert DEFAULT_THEME.text.heading in box


class TestOnADarkSection:
    def test_the_chip_reads_on_a_navy_band(self):
        html = _email(FullWidth(_chip(), background_color=NAVY)).render()
        box = _box(html)
        assert f'bgcolor="{INK}"' in box and f"color: {ON_DARK};" in box

    def test_a_lemon_chip_on_a_navy_band_takes_the_themes_dark_type(self):
        box = _box(_email(FullWidth(_chip("lemon"), background_color=NAVY)).render())
        assert f"color: {ON_DARK};" not in box
        assert DEFAULT_THEME.text.heading in box


class TestInEveryMedium:
    def test_on_a_slide(self):
        box = _box(Deck(FACTS).add_slide([FullWidth(_chip())], "Chip").render())
        assert f'bgcolor="{INK}"' in box and f"color: {ON_DARK};" in box

    def test_in_a_brochure_panel(self):
        panels = [Panel([FullWidth(TextBlock(f"<p>Face {n}</p>"))]) for n in range(5)]
        panels.append(Panel([FullWidth(_chip())]))
        box = _box(Brochure(FACTS, panels).render())
        assert f'bgcolor="{INK}"' in box and f"color: {ON_DARK};" in box

    def test_an_undeclared_tone_is_refused_when_its_section_is_added(self):
        with pytest.raises(ValidationError, match="does not declare"):
            _email(FullWidth(_chip()), theme=DEFAULT_THEME)
