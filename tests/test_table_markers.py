"""
A footnote marker in a cell or a column head (#224), the second child of #217.

The marker in the text is the apparatus's one spelling for "a note is called
here", so a cell's marker is numbered, rendered and gathered exactly like a
caption's. Each site is asserted in each medium.
"""

from __future__ import annotations

import re

import pytest

from pyhermes.builder import DataTable, FullWidth, TextBlock
from pyhermes.builder.email import Email
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.models import TableRow
from pyhermes.document import PagedDocument

PAPER_FACTS = {"firm_name": "Hermes", "campaign_name": "Review"}
FACTS = {"email_subject": "Subject", **PAPER_FACTS}
LEAD = FullWidth(content=TextBlock("<p>Rates repriced.[^1]</p>", notes=["Two-year."]))


def _table(**overrides) -> DataTable:
    arguments = {
        "headers": ["Fund", "1Y", "Since launch[^1]"],
        "rows": [
            TableRow(["Accumulation", "4.5%", "7.2%[^2]"]),
            TableRow(["Income", "4.1%", "6.8%"]),
        ],
        "notes": ["Launched 3 March 2014.", "Annualised; the class is under ten years old."],
    }
    return DataTable(**{**arguments, **overrides})


def _email(table: DataTable) -> Email:
    built = Email(FACTS)
    built.add_section(LEAD)
    built.add_section(FullWidth(content=table))
    return built


def _paged(table: DataTable) -> PagedDocument:
    built = PagedDocument(PAPER_FACTS)
    built.add_section(LEAD)
    built.add_section(FullWidth(content=table))
    return built


def _sup(number: int) -> str:
    return rf'<sup class="note-ref"[^>]*><a href="#note-{number}" id="note-ref-{number}"'


class TestEachSiteIsAMarker:
    @pytest.mark.parametrize("build", [_email, _paged], ids=["email", "paged"])
    def test_a_head_and_a_cell_render_the_captions_superscript(self, build):
        html = build(_table()).render()
        assert re.search(r"Since launch" + _sup(2), html), "the head's marker"
        assert re.search(r"7\.2%" + _sup(3), html), "the cell's marker"

    def test_an_email_gathers_them_among_the_endnotes(self):
        html = _email(_table()).render()
        assert 'class="footnote"' not in html
        for number, note in ((2, "Launched 3 March"), (3, "Annualised; the class")):
            assert re.search(rf'<li id="note-{number}"[^>]*>.*?{number}\.</a> {note}', html)

    def test_a_page_floats_each_note_from_its_marker(self):
        html = _paged(_table()).render()
        assert 'class="notes-heading"' not in html
        assert re.search(r'</sup><span class="footnote" id="note-3" data-note="3">Annualised', html)

    def test_rendered_alone_the_markers_keep_their_local_numbers(self):
        html = _table().render(TemplateEngine())
        assert 'href="#note-1"' in html and 'href="#note-2"' in html


class TestTheTextPartSpellsTheDocumentsNumber:
    def test_a_head_and_a_cell_print_the_number_where_the_marker_was(self):
        text = _email(_table()).text()
        assert "Since launch[2]" in text and "7.2%[3]" in text
        assert "[^" not in text

    def test_the_column_is_measured_with_the_marker_spelled(self):
        head, rule, *rows = _table().text().splitlines()
        assert len(rule.split("  ")[2]) == len("Since launch[1]")
        assert head.endswith("Since launch[1]")
        assert rows[0].endswith("7.2%[2]") and len(rows[0]) == len(head)


class TestTheMarkerCheckReachesTheCells:
    def test_a_marker_in_a_cell_with_no_note_raises(self):
        with pytest.raises(ValidationError, match=r"\[\^3\]"):
            _table(rows=[TableRow(["A", "1%[^3]", "2%[^2]"])])

    def test_a_note_with_no_marker_raises(self):
        with pytest.raises(ValidationError, match="no marker"):
            _table(rows=[TableRow(["A", "1%", "2%"])])

    def test_a_marker_called_twice_from_a_cell_raises(self):
        with pytest.raises(ValidationError, match="twice"):
            _table(rows=[TableRow(["A", "1%[^1]", "2%[^2]"])])


class TestNoMarkerIsByteIdentical:
    def test_a_table_without_markers_renders_as_before(self):
        plain = DataTable(["Fund", "1Y"], [TableRow(["A", "4.5%"])])
        html = plain.render(TemplateEngine())
        assert ">FUND<" not in html and ">Fund</th>" in html and ">4.5%</td>" in html
        assert "note-ref" not in html
