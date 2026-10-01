"""
Section surfaces (#265): a ground whose type stays readable, a border, a boxed block.
"""

from __future__ import annotations

import re

import pytest

from pyhermes.builder import (
    DEFAULT_THEME,
    SLATE_THEME,
    STANDARD_SIZES,
    Button,
    Callout,
    CardGroup,
    DataTable,
    Divider,
    Email,
    FullWidth,
    Stack,
    TextBlock,
    ThreeColumn,
    TwoColumn,
)
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.models import KpiItem, TableRow

FACTS = {"email_subject": "S", "firm_name": "F", "campaign_name": "C"}
NAVY = "#1B2A38"


def _render(*sections, **facts) -> str:
    email = Email({**FACTS, **facts})
    for section in sections:
        email.add_section(section)
    return email.render()


def _heading_color(html: str, title: str) -> str:
    match = re.search(r'color:(#[0-9A-F]{6});[^"]*">\s*' + re.escape(title) + r"\s*</h2>", html)
    assert match, f"no heading {title!r}"
    return match.group(1)


def _prose(html: str, words: str) -> str:
    start = html.index(words)
    return html[html.rindex("<div", 0, start) : start]


class TestADarkGroundKeepsItsTypeReadable:
    """#266: the title and prose on a caller's dark ground take the light ladder."""

    def test_the_title_and_prose_turn_light_by_default(self):
        html = _render(
            FullWidth(TextBlock("<p>Can you read this?</p>"), title="Dark", background_color=NAVY)
        )
        assert _heading_color(html, "Dark") == DEFAULT_THEME.text.on_dark
        assert f"color: {DEFAULT_THEME.text.on_dark};" in _prose(html, "Can you read this?")

    def test_the_dark_mode_class_is_dropped_on_a_ground(self):
        """`.body-text` is forced to the theme's dark type in dark mode, which would undo it."""
        html = _render(
            FullWidth(TextBlock("<p>On navy</p>"), background_color=NAVY),
            FullWidth(TextBlock("<p>On white</p>")),
        )
        assert 'class=""' in _prose(html, "On navy")
        assert 'class="body-text"' in _prose(html, "On white")

    def test_a_caller_text_color_sets_the_whole_ladder(self):
        html = _render(
            FullWidth(
                TextBlock("<p>Gold</p>"), title="Brand", background_color=NAVY, text_color="#F2C14E"
            )
        )
        assert _heading_color(html, "Brand") == "#F2C14E"
        assert "color: #F2C14E;" in _prose(html, "Gold")

    def test_a_light_ground_changes_nothing(self):
        plain = FullWidth(TextBlock("<p>x</p>"), title="T", background_color="#F4F1EC")
        assert DEFAULT_THEME.on_ground("#F4F1EC") is None
        assert _heading_color(_render(plain), "T") == DEFAULT_THEME.text.heading

    def test_it_follows_the_theme(self):
        html = _render(
            FullWidth(TextBlock("<p>x</p>"), title="T", background_color=NAVY), theme="slate"
        )
        assert _heading_color(html, "T") == SLATE_THEME.text.on_dark

    def test_it_reaches_every_column_and_into_a_stack(self):
        section = TwoColumn(
            "50-50",
            TextBlock("<p>Left</p>"),
            Stack([TextBlock("<p>Right</p>")]),
            background_color=NAVY,
        )
        html = _render(section)
        for words in ("Left", "Right"):
            assert f"color: {DEFAULT_THEME.text.on_dark};" in _prose(html, words)

    @pytest.mark.parametrize(
        "block",
        [
            DataTable(["Name", "Value"], [TableRow(["Surface", "1"])]),
            CardGroup([KpiItem("Surface", "1"), KpiItem("b", "2")], orientation="vertical"),
        ],
    )
    def test_a_block_with_its_own_surface_keeps_the_theme_type(self, block):
        html = _render(FullWidth(block, background_color=NAVY))
        cell = html.index('class="mobile-pad"', html.index(NAVY))
        body = html[html.index(">", cell) + 1 : html.index("Surface") + 200]
        light = (DEFAULT_THEME.text.on_dark, DEFAULT_THEME.text.on_dark_secondary)
        assert not re.search(rf"(?<!background-)color: ?({'|'.join(light)})", body)

    def test_a_block_with_its_own_surface_is_set_on_the_themes(self):
        """A table's caption and header sit on whatever is beneath, so they get the surface."""
        table = DataTable(["A"], [TableRow(["1"])], caption="Cap")
        wrapper = (
            f'bgcolor="{DEFAULT_THEME.palette.surface}" '
            f'style="padding:{STANDARD_SIZES.space.caption_gap}px;'
        )
        assert wrapper in _render(FullWidth(table, background_color=NAVY))
        assert wrapper not in _render(FullWidth(table))
        assert wrapper not in _render(FullWidth(TextBlock("<p>x</p>"), background_color=NAVY))

    def test_a_bad_text_color_is_refused(self):
        with pytest.raises(ValidationError, match="container.text_color"):
            FullWidth(TextBlock("<p>x</p>"), text_color="white")


class TestABorderedSection:
    """#267: a 1px frame, the footer's two fields, and the frame's pixel given back."""

    PAD = STANDARD_SIZES.frame.pad_x

    def test_a_full_width_section_is_framed_in_the_rule(self):
        html = _render(FullWidth(TextBlock("<p>x</p>"), title="Framed", border=True))
        assert f"border:1px solid {DEFAULT_THEME.palette.rule};" in html
        assert f"padding:{STANDARD_SIZES.space.content_top}px {self.PAD - 1}px" in html

    def test_a_split_still_fills_the_frame(self):
        section = ThreeColumn(
            "33-33-33",
            TextBlock("<p>a</p>"),
            TextBlock("<p>b</p>"),
            TextBlock("<p>c</p>"),
            border=True,
            border_color="#5B8A9A",
        )
        html = _render(section)
        assert "border:1px solid #5B8A9A;" in html
        assert f"padding:0 {self.PAD - 1}px; font-size:0" in html
        assert 2 + 2 * (self.PAD - 1) + STANDARD_SIZES.frame.inner == STANDARD_SIZES.frame.width

    def test_a_highlighted_band_gets_all_four_sides(self):
        section = FullWidth(
            TextBlock("<p>x</p>"), highlight=True, border=True, border_color="#5B8A9A"
        )
        html = _render(section)
        for side in ("top", "bottom", "left", "right"):
            assert f"border-{side}:1px solid #5B8A9A;" in html
        assert f"{self.PAD - 2}px" in html

    def test_a_colour_without_a_border_is_refused(self):
        with pytest.raises(ValidationError, match="border=True"):
            FullWidth(TextBlock("<p>x</p>"), border_color="#5B8A9A")

    def test_it_composes_with_a_dark_ground(self):
        section = FullWidth(TextBlock("<p>x</p>"), title="Both", background_color=NAVY, border=True)
        html = _render(section)
        assert f"background-color:{NAVY}; border:1px solid" in html
        assert _heading_color(html, "Both") == DEFAULT_THEME.text.on_dark


class TestACallout:
    """#268: one block boxed on a surface the theme owns."""

    def test_it_boxes_its_block_in_a_padded_cell(self):
        html = _render(FullWidth(Callout(TextBlock("<p>Boxed</p>"), label="Key takeaway")))
        box = html[html.index('class="callout"') : html.index("Boxed")]
        pad = STANDARD_SIZES.component
        assert f"padding:{pad.callout_pad_y}px {pad.callout_pad_x}px;" in box
        assert f"background-color:{DEFAULT_THEME.palette.highlight_tint};" in box
        assert f"border:1px solid {DEFAULT_THEME.palette.rule};" in box
        assert ">Key takeaway</div>" in box

    @pytest.mark.parametrize("tone", ["positive", "negative", "neutral"])
    def test_a_tone_takes_its_colour_from_the_theme(self, tone):
        for theme, preset in ((DEFAULT_THEME, "classic"), (SLATE_THEME, "slate")):
            html = _render(FullWidth(Callout(TextBlock("<p>x</p>"), tone=tone)), theme=preset)
            assert f"border:1px solid {getattr(theme.semantic, tone)};" in html

    def test_it_can_go_unframed_and_in_a_column(self):
        section = TwoColumn(
            "30-70", Callout(TextBlock("<p>Left box</p>"), border=False), TextBlock("<p>R</p>")
        )
        html = _render(section)
        box = html[html.index('class="callout"') : html.index("Left box")]
        assert "border:1px" not in box

    def test_its_block_keeps_the_theme_type_on_a_dark_ground(self):
        html = _render(FullWidth(Callout(TextBlock("<p>Inside</p>")), background_color=NAVY))
        assert f"color: {DEFAULT_THEME.text.primary};" in _prose(html, "Inside")

    def test_the_document_numbers_what_it_holds(self):
        email = Email(FACTS)
        email.add_section(
            FullWidth(DataTable(["A"], [TableRow(["1"])], label="Exhibit", caption="First"))
        )
        email.add_section(
            FullWidth(Callout(DataTable(["A"], [TableRow(["1"])], label="Exhibit", caption="Box")))
        )
        assert "Exhibit 2 · Box" in email.render()

    def test_the_text_part_sets_it_off(self):
        email = Email(FACTS)
        email.add_section(FullWidth(Callout(TextBlock("<p>Boxed</p>"), label="Note")))
        text = email.text()
        assert "NOTE\n\nBoxed" in text
        assert text.count("-" * 78) == 2

    @pytest.mark.parametrize(
        ("build", "message"),
        [
            (lambda: Callout("text"), "holds one component"),
            (lambda: Callout(TextBlock("<p>x</p>"), tone="warning"), "tone must be one of"),
        ],
    )
    def test_bad_input_is_refused(self, build, message):
        with pytest.raises(ValidationError, match=message):
            build()


class TestAButtonAndADivider:
    """#269: the contact block's button on its own, and a rule between blocks."""

    def test_a_button_is_the_contact_blocks_markup(self):
        from pyhermes.builder import ContactBlock

        url = "https://example.com/go"
        lone = _render(FullWidth(Button("Go", url)))
        card = _render(FullWidth(ContactBlock(heading="H", cta_label="Go", cta_url=url)))
        start, end = "<!--[if mso]>\n      <v:roundrect", "<!--<![endif]-->"
        assert (
            lone[lone.index(start) : lone.index(end)] == card[card.index(start) : card.index(end)]
        )

    def test_a_button_aligns_and_projects_its_link(self):
        email = Email(FACTS)
        email.add_section(FullWidth(Button("Read it", "https://example.com/r", align="right")))
        assert 'align="right"' in email.render()
        assert "Read it: https://example.com/r" in email.text()

    @pytest.mark.parametrize("url", ["javascript:alert(1)", ""])
    def test_a_button_refuses_a_bad_url(self, url):
        with pytest.raises(ValidationError):
            Button("Go", url)

    def test_a_divider_is_a_rule_in_the_theme(self):
        html = _render(FullWidth(Stack([TextBlock("<p>a</p>"), Divider(), TextBlock("<p>b</p>")])))
        assert f"border-top:1px solid {DEFAULT_THEME.palette.rule};" in html
        assert "<hr" not in html

    def test_both_work_in_a_column(self):
        section = TwoColumn(
            "50-50", Stack([Divider(), Button("Go", "https://example.com")]), TextBlock("<p>R</p>")
        )
        assert "v:roundrect" in _render(section)
