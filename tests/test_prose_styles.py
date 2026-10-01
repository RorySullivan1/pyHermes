"""
The HTML a prose field carries takes the theme's styles (#280).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pyhermes.builder import (
    DEFAULT_FONTS,
    DEFAULT_THEME,
    STANDARD_SIZES,
    CardGroup,
    Email,
    FontStack,
    FullWidth,
    NumberedList,
    TextBlock,
)
from pyhermes.builder.exceptions import TemplateError, ValidationError
from pyhermes.builder.models import Card, NumberedItem
from pyhermes.builder.prose import STYLED_TAGS, STYLES_TEMPLATE
from pyhermes.check import errors, lint_html
from pyhermes.config import Config

FACTS = {"email_subject": "S", "firm_name": "F", "campaign_name": "C"}

#: One of each styled tag, and nothing else that could carry the same values.
EVERY_TAG = (
    "<h3>Sub</h3><h4>Minor</h4>"
    '<p>See <a href="https://example.com/n">the note</a>.</p>'
    "<ul><li>u</li></ul><ol><li>o</li></ol>"
    "<blockquote>Quoted.</blockquote><hr>"
)


def _render(block, **facts) -> str:
    email = Email({**FACTS, **facts}, config=Config(allow_custom_email_density=True))
    email.add_section(FullWidth(block, title="T"))
    return email.render()


def _style(html: str, tag: str) -> str:
    """The ``style`` of the first ``tag`` in ``html``."""
    found = re.search(rf'<{tag}\b[^>]*\sstyle="([^"]*)"', html)
    assert found, f"no styled <{tag}> in the render"
    return found.group(1)


class TestEachTagTakesTheTheme:
    html = _render(TextBlock(EVERY_TAG))
    size, theme, font = STANDARD_SIZES, DEFAULT_THEME, DEFAULT_FONTS

    def test_a_subheading_is_the_themes_heading(self):
        style = _style(self.html, "h3")
        assert f"font-family: {self.font.heading.css};" in style
        assert f"font-size: {self.size.type.subheading}px;" in style
        assert f"color: {self.theme.text.heading};" in style
        assert f"margin: 0 0 {self.size.component.prose_gap}px 0;" in style

    def test_a_minor_heading_is_body_sized_and_bold(self):
        style = _style(self.html, "h4")
        assert f"font-size: {self.size.type.body}px;" in style
        assert "font-weight: bold;" in style

    @pytest.mark.parametrize("tag", ["ul", "ol"])
    def test_a_list_is_indented_by_margin_not_padding(self, tag):
        # Outlook ignores a list's padding, so the indent is the margin.
        style = _style(self.html, tag)
        assert f"margin: 0 0 {self.size.component.prose_gap}px " in style
        assert f"{self.size.component.prose_indent}px; padding: 0;" in style

    def test_an_item_is_spaced(self):
        assert f"margin: 0 0 {self.size.component.prose_item_gap}px 0;" in _style(self.html, "li")

    def test_a_quotation_is_ruled_in_the_accent(self):
        style = _style(self.html, "blockquote")
        assert f"border-left: 3px solid {self.theme.palette.accent};" in style
        assert f"color: {self.theme.text.secondary};" in style

    def test_a_link_is_the_accent(self):
        assert f"color: {self.theme.palette.accent};" in _style(self.html, "a")

    def test_a_rule_is_the_themes_rule(self):
        assert f"border-top: 1px solid {self.theme.palette.rule};" in _style(self.html, "hr")

    def test_the_render_is_lint_clean(self):
        assert errors(lint_html(self.html)) == []

    def test_the_styles_template_covers_every_tag(self):
        assert set(STYLED_TAGS) == {"h3", "h4", "ul", "ol", "li", "blockquote", "a", "hr"}


class TestTheThreeAxesMoveIt:
    """Standing rules 4–6, per tag: a sentinel value set on each axis reaches the prose."""

    def test_a_sentinel_theme_size_and_font_reach_every_tag(self):
        theme = DEFAULT_THEME.derive(
            palette={"accent": "#0A0B0C", "rule": "#0D0E0F"},
            text={"heading": "#1A1B1C", "secondary": "#1D1E1F"},
        )
        size = STANDARD_SIZES.derive(
            type={"subheading": 31},
            component={"prose_gap": 37, "prose_indent": 41, "prose_item_gap": 43},
        )
        font = DEFAULT_FONTS.derive(heading=FontStack("SentinelHeading", "serif"))
        html = _render(TextBlock(EVERY_TAG), theme=theme, size_theme=size, font_theme=font)
        assert "SentinelHeading" in _style(html, "h3")
        assert "font-size: 31px;" in _style(html, "h3")
        assert "#1A1B1C" in _style(html, "h4")
        assert "37px 41px" in _style(html, "ul")
        assert "43px" in _style(html, "li")
        assert "#0A0B0C" in _style(html, "blockquote") and "#1D1E1F" in _style(html, "blockquote")
        assert "#0A0B0C" in _style(html, "a")
        assert "#0D0E0F" in _style(html, "hr")

    def test_a_spacing_override_moves_the_prose(self):
        html = _render(TextBlock(EVERY_TAG, spacing={"prose_indent": 9}))
        assert "9px; padding: 0;" in _style(html, "ul")


class TestTheAuthorStillDecides:
    def test_an_authors_style_wins(self):
        html = _render(TextBlock('<ul style="margin: 0;"><li style="color: #112233;">x</li></ul>'))
        assert '<ul style="margin: 0;">' in html
        assert '<li style="color: #112233;">' in html

    def test_other_attributes_are_kept(self):
        html = _render(TextBlock('<p><a href="https://example.com/a?x=1&amp;y=2" id="k">a</a></p>'))
        assert '<a href="https://example.com/a?x=1&amp;y=2" id="k" style="' in html

    def test_a_quoted_angle_bracket_does_not_end_the_tag(self):
        html = _render(TextBlock('<p><a href="https://example.com/" title="a > b">a</a></p>'))
        assert 'title="a > b" style="' in html

    def test_a_self_closing_rule_stays_self_closing(self):
        assert re.search(r'<hr style="[^"]*" />', _render(TextBlock("<p>a</p><hr/>")))

    @pytest.mark.parametrize("tag", ["p", "span", "strong", "em", "abbr", "address", "header"])
    def test_a_tag_outside_the_set_is_untouched(self, tag):
        markup = f"<p><{tag}>x</{tag}></p>" if tag != "p" else "<p>x</p>"
        assert markup in _render(TextBlock(markup))

    def test_prose_with_none_of_the_tags_is_byte_identical(self):
        markup = "<p>Plain <b>prose</b>, <i>nothing</i> else.</p>"
        assert f">{markup}</div>" in _render(TextBlock(markup))


class TestTheTopTwoLevelsAreRefused:
    """The section title owns them; a silent demotion would hide that from the author."""

    @pytest.mark.parametrize("tag", ["h1", "h2", "H2"])
    def test_a_text_block(self, tag):
        with pytest.raises(ValidationError, match=r"TextBlock\.content holds an <h[12]>.*<h3>"):
            TextBlock(f"<{tag}>Title</{tag}><p>x</p>")

    def test_a_card_body(self):
        with pytest.raises(ValidationError, match=r"card\.body holds an <h2>"):
            CardGroup([Card("A", "1", body="<h2>x</h2>"), Card("B", "2")])

    def test_a_numbered_item_body(self):
        with pytest.raises(ValidationError, match=r"numbered_item\.body holds an <h1"):
            NumberedList([NumberedItem("1", "One", '<h1 class="x">x</h1>')])

    @pytest.mark.parametrize("markup", ["<h3>x</h3>", "<hr>", "<header>x</header>", "<p>h1</p>"])
    def test_what_is_not_a_top_heading_passes(self, markup):
        TextBlock(markup)


class TestTheOtherProseFields:
    @pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
    def test_a_card_body_is_styled(self, orientation):
        cards = [Card("A", "1", body="<ul><li>x</li></ul>"), Card("B", "2")]
        group = CardGroup(cards, orientation=orientation)
        assert f"{STANDARD_SIZES.component.prose_indent}px; padding: 0;" in _style(
            _render(group), "ul"
        )

    def test_a_numbered_item_body_is_styled(self):
        html = _render(NumberedList([NumberedItem("1", "One", "<p>a <a href='#'>b</a></p>")]))
        assert DEFAULT_THEME.palette.accent in _style(html, "a")

    def test_a_footnote_marker_keeps_its_own_style(self):
        html = _render(TextBlock("<p>Claim.[^1]</p>", notes=["Source."]))
        assert 'style="color: #5B8A9A; text-decoration: none;">1</a>' in html


class TestOnASectionsGround:
    def test_a_link_takes_the_grounds_type(self):
        email = Email(FACTS)
        link = TextBlock('<p><a href="https://example.com/">a</a></p>')
        email.add_section(FullWidth(link, background_color="#1B2A38"))
        style = _style(email.render(), "a")
        assert DEFAULT_THEME.text.on_dark in style
        assert DEFAULT_THEME.palette.accent not in style


class TestAnOverlayRestylesATag:
    def _overlay(self, tmp_path: Path, drop: str | None = None, **restyle: str) -> Path:
        source = (
            Path(__file__).resolve().parent.parent / "pyhermes/builder/templates" / STYLES_TEMPLATE
        ).read_text(encoding="utf-8")
        lines = []
        for line in source.splitlines():
            tag = line.partition(":")[0]
            if tag == drop:
                continue
            lines.append(f"{tag}: {restyle[tag]}" if tag in restyle else line)
        target = tmp_path / STYLES_TEMPLATE
        target.parent.mkdir(parents=True)
        target.write_text("\n".join(lines), encoding="utf-8")
        return tmp_path

    def test_a_house_style_replaces_the_tags(self, tmp_path):
        email = Email(FACTS, template_overlay=self._overlay(tmp_path, h3="letter-spacing: 1px;"))
        email.add_section(FullWidth(TextBlock("<h3>x</h3>")))
        assert '<h3 style="letter-spacing: 1px;">' in email.render()

    def test_an_overlay_that_drops_a_tag_is_refused(self, tmp_path):
        email = Email(FACTS, template_overlay=self._overlay(tmp_path, drop="hr"))
        email.add_section(FullWidth(TextBlock("<hr>")))
        with pytest.raises(TemplateError, match="styles no hr"):
            email.render()
