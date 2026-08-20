"""
The escaping contract (#12).

autoescape is OFF, so escaping is explicit and split by field kind:

* plain-text fields are escaped by the builder, in the templates;
* HTML fields (TextBlock.content, NumberedItem.body, the metadata
  disclaimers) are emitted raw — escaping them is the caller's job;
* attributes are always escaped, quotes included, so a value cannot break
  out of the attribute it sits in.

These tests pin both halves: that plain fields *are* escaped, and that HTML
fields are *not* (escaping those would break every caller passing markup).
"""

import pytest

from svc.builder import (
    AuthorBlock,
    CardGroup,
    ChartBlock,
    DataTable,
    Email,
    FullWidth,
    NumberedList,
    TextBlock,
    TwoColumn,
)
from svc.builder.filters import escape_html
from svc.builder.models import KpiItem, NumberedItem, TableRow

NASTY = 'S&P "500" <script>alert(1)</script>'


def _attributes_of(markup: str, tag: str) -> dict:
    """Parse `markup` and return the first `tag` element's attributes.

    Escaping bugs are about document *structure*, so assert on the parsed
    tree rather than on substrings: a payload sitting harmlessly inside an
    attribute value looks identical to an injected attribute in raw text.
    """
    from html.parser import HTMLParser

    class _Collector(HTMLParser):
        found: dict | None = None

        def handle_starttag(self, name, attrs):
            if name == tag and self.found is None:
                self.found = dict(attrs)

    parser = _Collector()
    parser.feed(markup)
    assert parser.found is not None, f"no <{tag}> in rendered output"
    return parser.found


class TestEscapeHtmlHelper:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Research & Strategy", "Research &amp; Strategy"),
            ('say "hi"', "say &quot;hi&quot;"),
            ("it's", "it&#x27;s"),
            ("<script>", "&lt;script&gt;"),
            ("plain text", "plain text"),
        ],
    )
    def test_escapes_the_five_dangerous_characters(self, raw, expected):
        assert escape_html(raw) == expected

    def test_none_becomes_empty_string(self):
        # Optional fields arrive as None; the filter must not print "None".
        assert escape_html(None) == ""

    def test_non_strings_are_coerced(self):
        assert escape_html(42) == "42"

    def test_is_not_idempotent_by_design(self):
        # Documents why callers must NOT pre-escape plain-text fields.
        assert escape_html(escape_html("&")) == "&amp;amp;"

    def test_registered_as_a_jinja_filter(self, engine):
        assert "escape_html" in engine.environment.filters


class TestPlainTextFieldsAreEscaped:
    def test_container_title(self, engine, text_block):
        # The exact symptom reported in #12.
        html = FullWidth(content=text_block, title="Research & Strategy").render(engine)
        assert "Research &amp; Strategy" in html
        assert "Research & Strategy" not in html

    def test_container_title_on_every_container(self, engine, text_block):
        for container in (
            FullWidth(content=text_block, title=NASTY),
            FullWidth(content=text_block, title=NASTY, highlight=True),
            TwoColumn(left=text_block, title=NASTY),
        ):
            html = container.render(engine)
            assert "<script>" not in html, type(container).__name__

    def test_card_label_value_and_sublabel(self, engine):
        html = CardGroup(
            [
                KpiItem(label="S&P 500", value="5,234 & rising", sublabel="+1% & up"),
                KpiItem(label="VIX", value="14"),
            ]
        ).render(engine)
        assert "S&amp;P 500" in html
        assert "5,234 &amp; rising" in html
        assert "+1% &amp; up" in html

    def test_table_headers_and_cells(self, engine):
        html = DataTable(headers=["Asset & Class"], rows=[TableRow(cells=["S&P 500"])]).render(
            engine
        )
        assert "Asset &amp; Class" in html
        assert "S&amp;P 500" in html

    def test_table_source_and_as_of(self, engine):
        html = DataTable(
            headers=["A"],
            rows=[TableRow(cells=["1"])],
            source="Bloomberg & Co",
            as_of="Q1 & Q2",
        ).render(engine)
        assert "Bloomberg &amp; Co" in html
        assert "Q1 &amp; Q2" in html

    def test_subtitle(self, engine):
        html = TextBlock("<p>body</p>", subtitle="Rates & Credit").render(engine)
        assert "Rates &amp; Credit" in html

    def test_author_fields(self, engine):
        html = AuthorBlock(name="Jane & John", job_title="Head of R&D", email="a&b@x.test").render(
            engine
        )
        assert "Jane &amp; John" in html
        assert "Head of R&amp;D" in html
        assert "a&amp;b@x.test" in html

    def test_numbered_item_title_and_number(self, engine):
        html = NumberedList(
            items=[NumberedItem(number="1 & 2", title="Rates & Credit", body="body")]
        ).render(engine)
        assert "Rates &amp; Credit" in html
        assert "1 &amp; 2" in html

    def test_metadata_plain_fields(self, valid_metadata, text_block):
        valid_metadata["email_subject"] = "Weekly Wrap & Review"
        valid_metadata["firm_name"] = "Smith & Co"
        email = Email(metadata=valid_metadata)
        email.add_section(FullWidth(content=text_block))
        html = email.render()
        assert "Weekly Wrap &amp; Review" in html
        assert "Smith &amp; Co" in html


class TestAttributesCannotBeBrokenOut:
    def test_chart_alt_text_with_a_quote(self, engine):
        # #12's second symptom: a " in alt_text terminated the attribute and
        # emitted stray markup.
        html = ChartBlock(image_url="https://x.test/c.png", alt_text='S&P 500 "YTD" chart').render(
            engine
        )
        assert 'alt="S&amp;P 500 &quot;YTD&quot; chart"' in html

    def test_chart_image_url_with_a_quote(self, engine):
        html = ChartBlock(image_url='https://x.test/c.png?a="b').render(engine)
        assert '"' not in html.split('src="')[1].split('"')[0]

    def test_alt_text_cannot_inject_an_attribute(self, engine):
        # Asserted by parsing, not string matching: the payload text may
        # legitimately appear *inside* the alt value: what must not happen is
        # it becoming an attribute of its own.
        markup = ChartBlock(
            image_url="https://x.test/c.png",
            alt_text='" onerror="alert(1)',
        ).render(engine)
        attrs = _attributes_of(markup, "img")
        assert "onerror" not in attrs
        assert attrs["alt"] == '" onerror="alert(1)'  # intact, as text

    def test_metadata_urls_are_escaped(self, valid_metadata, text_block):
        valid_metadata["logo_url"] = 'https://x.test/l.png?a="b'
        valid_metadata["contact_url"] = "https://x.test/c?a=1&b=2"
        email = Email(metadata=valid_metadata)
        email.add_section(FullWidth(content=text_block))
        html = email.render()
        assert "a=&quot;b" in html
        assert "a=1&amp;b=2" in html


class TestHtmlFieldsStayRaw:
    def test_text_block_content_is_not_escaped(self, engine):
        html = TextBlock("<p>Hello <strong>world</strong></p>").render(engine)
        assert "<strong>world</strong>" in html

    def test_numbered_item_body_is_not_escaped(self, engine):
        html = NumberedList(
            items=[NumberedItem(number="01", title="T", body="<em>emphasis</em>")]
        ).render(engine)
        assert "<em>emphasis</em>" in html

    def test_metadata_disclaimers_are_not_escaped(self, valid_metadata, text_block):
        valid_metadata["footer_disclaimer"] = '<a href="https://x.test">Terms</a>'
        email = Email(metadata=valid_metadata)
        email.add_section(FullWidth(content=text_block))
        assert '<a href="https://x.test">Terms</a>' in email.render()

    def test_rendered_sections_are_not_double_escaped(self, valid_metadata, text_block):
        # Container/component fragments are HTML by the time they reach the
        # skeleton; escaping them would render tags as visible text.
        email = Email(metadata=valid_metadata)
        email.add_section(FullWidth(content=text_block, title="Intro"))
        assert "&lt;table" not in email.render()
