"""
A table's caption in classic Outlook (#403).

Outlook's Word engine moves a nested table's ``caption`` out of place: when the
captioned table sits in any row but the first of an enclosing layout table,
the caption is drawn at the top of that layout table instead, above the copy
that precedes the table and outside any frame around it. On a dark band it
then reads dark-on-dark. Measured by putting probe drafts into classic Outlook
and reading the paragraphs back through ``Inspector.WordEditor``.

The fix hides the ``caption`` from Outlook (``mso-hide:all``, which the Word
engine honours by dropping the element) and gives Outlook its own copy as a
paragraph directly before the table, inside an ``[if mso]`` block. Every other
client still reads the ``caption`` as the table's accessible name (#120).
"""

from __future__ import annotations

import re

from pyhermes.builder import DataTable, FullWidth, TemplateEngine
from pyhermes.builder.email import Email
from pyhermes.builder.models import TableRow
from qa.lint import SOURCES, lint_html

FACTS = {"email_subject": "Subject", "firm_name": "Hermes", "campaign_name": "Review"}


def table(caption: str = "Treasury yields", **fields) -> DataTable:
    return DataTable(["Tenor", "Yield"], [TableRow(["2Y", "3.91%"])], caption=caption, **fields)


def email_html(component: DataTable) -> str:
    built = Email(FACTS)
    built.add_section(FullWidth(component))
    return built.render()


def outlook_copy(html: str) -> str:
    """The ``[if mso]`` block directly before the data table."""
    before = html.split('<table class="data-table"', 1)[0]
    blocks = re.findall(r"<!--\[if mso\]>(.*?)<!\[endif\]-->", before, re.DOTALL)
    assert blocks, "no [if mso] block precedes the table"
    return blocks[-1]


class TestTheEmailCaption:
    def test_the_caption_is_hidden_from_outlook(self):
        html = email_html(table())
        caption = html.split("<caption", 1)[1].split(">", 1)[0]
        assert "mso-hide:all" in caption

    def test_it_is_still_the_tables_first_child(self):
        """#120's accessible name survives for every client but Outlook."""
        after_table = email_html(table()).split('<table class="data-table"', 1)[1]
        assert after_table.split(">", 1)[1].lstrip().startswith("<caption")

    def test_outlook_gets_its_own_copy_directly_before_the_table(self):
        copy = outlook_copy(email_html(table()))
        assert "<p " in copy and "Treasury yields" in copy

    def test_the_copy_is_styled_as_the_caption_is(self):
        html = email_html(table())
        caption_style = re.search(r'<caption style="([^"]*)"', html).group(1)
        copy_style = re.search(r'<p\b[^>]*\bstyle="([^"]*)"', outlook_copy(html)).group(1)
        for declaration in ("font-weight: bold", "letter-spacing: 0.5px", "text-align: left"):
            assert declaration in caption_style and declaration in copy_style
        assert "caption-side" not in copy_style

    def test_the_copy_is_escaped(self):
        assert "Risk &amp; return" in outlook_copy(email_html(table("Risk & return")))

    def test_a_marker_id_is_written_once(self):
        """The copy links its marker but must not repeat its id."""
        html = email_html(table("Yields[^1]", notes=["Close to close."]))
        assert len(re.findall(r'id="note-ref-1"', html)) == 1
        assert 'href="#note-1"' in outlook_copy(html)

    def test_no_caption_writes_no_copy(self):
        html = email_html(DataTable(["Tenor"], [TableRow(["2Y"])]))
        assert "<caption" not in html
        assert (
            "mso-hide:all" not in html.split('<table class="data-table"', 1)[1].split("</table>")[0]
        )


class TestOtherMediaAreUntouched:
    """Outlook is an email client: a page, a slide or plain HTML renders as before."""

    def test_plain_html_has_no_outlook_copy_and_no_hide(self):
        html = table().render(TemplateEngine())
        assert "mso-hide" not in html
        assert "[if mso]" not in html


HEAD = '<thead><tr><th scope="col">A</th></tr></thead>'


def captioned(caption: str) -> str:
    """A data table whose first child is ``caption``."""
    return f"<table>{caption}{HEAD}</table>"


def caption_rule(html: str, medium: str = "email") -> bool:
    return "outlook-caption" in {f.rule_id for f in lint_html(html, medium)}


class TestOutlookCaptionRule:
    def test_a_caption_outlook_can_see_fires(self):
        nested = captioned("<caption>X</caption>")
        assert caption_rule(f'<table role="presentation"><tr><td>{nested}</td></tr></table>')

    def test_a_hidden_caption_passes(self):
        assert not caption_rule(captioned('<caption style="color:#000; mso-hide:all;">X</caption>'))

    def test_a_caption_inside_a_downlevel_revealed_block_passes(self):
        assert not caption_rule(
            captioned("<!--[if !mso]><!--><caption>X</caption><!--<![endif]-->")
        )

    def test_it_is_an_email_rule_only(self):
        assert not caption_rule(captioned("<caption>X</caption>"), "document")

    def test_the_rule_carries_a_source(self):
        assert SOURCES["outlook-caption"].strip()
