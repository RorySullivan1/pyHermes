"""
Two markers side by side (#402): notes 2 and 3 read "2,3", never "23".

The comma sits inside the second superscript and outside its link, so each
number still links to its own note. Asserted in the email and on paper, in
prose and in a table cell, beside a single marker that stays as it was and
two adjacent citations that carry their own brackets.
"""

from __future__ import annotations

import re

import pytest

from pyhermes.builder import Bibliography, DataTable, FullWidth, TextBlock
from pyhermes.builder.email import Email
from pyhermes.builder.models import TableRow
from pyhermes.builder.research import Reference
from pyhermes.document import PagedDocument

PAPER_FACTS = {"firm_name": "Hermes", "campaign_name": "Review"}
FACTS = {"email_subject": "Subject", **PAPER_FACTS}
NOTES = ["One.", "Two.", "Three."]


def _email(*sections) -> Email:
    built = Email(FACTS)
    for section in sections:
        built.add_section(section)
    return built


def _paged(*sections) -> PagedDocument:
    built = PagedDocument(PAPER_FACTS)
    for section in sections:
        built.add_section(section)
    return built


def _prose(copy: str) -> FullWidth:
    return FullWidth(content=TextBlock(f"<p>{copy}</p>", notes=NOTES))


def _sup(number: int, comma: bool = False) -> str:
    return (
        r'<sup class="note-ref" style="line-height: 0;">'
        + ("," if comma else "")
        + rf'<a href="#note-{number}" id="note-ref-{number}"'
    )


MEDIA = pytest.mark.parametrize("build", [_email, _paged], ids=["email", "paged"])


class TestAdjacentNotes:
    @MEDIA
    def test_the_second_marker_opens_on_a_comma(self, build):
        html = build(_prose("Treatment.[^1][^2][^3] Then on.")).render()
        assert re.search(_sup(1), html)
        assert re.search(_sup(2, comma=True), html)
        assert re.search(_sup(3, comma=True), html)

    @MEDIA
    def test_markers_apart_take_no_comma(self, build):
        html = build(_prose("One[^1] and two[^2], then three [^3].")).render()
        for number in (1, 2, 3):
            assert re.search(_sup(number), html)
        assert 'note-ref" style="line-height: 0;">,' not in html

    @MEDIA
    def test_two_markers_in_one_cell(self, build):
        table = DataTable(
            ["Fund", "1Y"], [TableRow(["Accumulation", "4.5%[^1][^2]"])], notes=NOTES[:2]
        )
        html = build(FullWidth(content=table)).render()
        assert re.search(_sup(1), html)
        assert re.search(_sup(2, comma=True), html)

    def test_the_text_part_prints_each_number_bracketed(self):
        text = _email(_prose("Treatment.[^1][^2][^3]")).text()
        assert "Treatment.[1][2][3]" in text


class TestAdjacentCitations:
    """Each citation carries the style's brackets, so two never read as one."""

    @pytest.mark.parametrize(
        ("style", "closing", "opening"), [("numeric", "]", "["), ("author-year", ")", "(")]
    )
    def test_two_side_by_side_stay_apart(self, style, closing, opening):
        references = [
            Reference("a2020", ["Able, Ann"], 2020, "First"),
            Reference("b2021", ["Baker, Ben"], 2021, "Second"),
        ]
        document = _email(
            FullWidth(content=TextBlock("<p>Shown twice.[@a2020][@b2021]</p>")),
            FullWidth(title="References", content=Bibliography(references, style=style)),
        )
        html = document.render()
        assert re.search(rf"</a>{re.escape(closing)}{re.escape(opening)}<a ", html)
