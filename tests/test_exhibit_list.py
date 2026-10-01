"""
The list of exhibits (#308): the walk's exhibit numbering, read as a contents list.

Every entry is the heading its exhibit already prints, so each test reads the
list against the exhibits rather than trusting either alone.
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from pyhermes.builder import Contents, FullWidth, ValidationError
from pyhermes.builder.email import Email
from pyhermes.document import (
    PAGED_MEDIUM,
    ContentsPage,
    EmptyExhibitsPage,
    ExhibitsPage,
    PagedDocument,
)
from pyhermes.pdf import available, render_pdf
from qa.fixtures import _paged

requires_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

PAPER_FACTS = {"firm_name": "Hermes", "campaign_name": "Review"}
FACTS = {"email_subject": "Subject", **PAPER_FACTS}

ENTRY = re.compile(r'<li class="contents-entry"[^>]*><a href="#([\w-]+)"[^>]*>([^<]+)</a>')


def portrait(**regions) -> PagedDocument:
    """``a4_portrait``'s content, with a list of exhibits on its own sheet."""
    document = _paged.build_on(PAGED_MEDIUM)
    rebuilt = PagedDocument(
        _paged.facts(),
        **{"contents": ContentsPage(heading="In This Review"), **_paged.regions(), **regions},
    )
    for section in document._sections:
        rebuilt.add_section(section)
    return rebuilt


def sheets(document) -> list[list[str]]:
    """Each sheet's lines of text, read back out of the PDF."""
    import pypdfium2

    pdf = pypdfium2.PdfDocument(render_pdf(document))
    return [
        [line.strip() for line in sheet.get_textpage().get_text_range().splitlines()]
        for sheet in pdf
    ]


def headings(document) -> list[tuple[str, str]]:
    """``(anchor, heading)`` for every numbered exhibit, read off the exhibits."""
    document.validate()
    return [
        (component.resolved_anchor(), component.listed())
        for component in document._components()
        if getattr(component, "number", None)
    ]


class TestTheComponent:
    def test_it_lists_every_exhibit_under_its_own_heading(self):
        document = Email(FACTS)
        document.add_section(FullWidth(title="Exhibits", content=Contents(of="exhibits")))
        for section in _paged.build_on(PAGED_MEDIUM)._sections:
            document.add_section(section)
        html = document.render()
        listed = ENTRY.findall(html)
        assert listed == headings(document)
        assert [heading for _, heading in listed] == [
            "Exhibit 1 · Style factor returns",
            "Exhibit 2 · The 2s10s spread",
        ]

    def test_every_entry_lands_on_its_exhibit(self):
        document = portrait()
        document.add_section(FullWidth(content=Contents(of="exhibits")))
        html = document.render()
        for anchor, _ in ENTRY.findall(html.split('class="document-container"')[1]):
            assert f'id="{anchor}"' in html

    def test_a_label_narrows_it_to_that_sequence(self):
        document = portrait()
        document.add_section(FullWidth(content=Contents(of="exhibits", label="Table")))
        assert document._components()[-1].entries == []

    def test_the_text_is_the_headings_one_per_line(self):
        document = portrait()
        document.add_section(FullWidth(content=Contents(of="exhibits", subtitle="Inside")))
        assert "Inside\n\nExhibit 1 · Style factor returns\nExhibit 2 · The 2s10s spread\n" in (
            document.text()
        )

    def test_a_marker_in_a_caption_is_left_out_of_the_entry(self):
        from pyhermes.builder import DataTable
        from pyhermes.builder.models import TableRow

        document = Email(FACTS)
        document.add_section(FullWidth(content=Contents(of="exhibits")))
        document.add_section(
            FullWidth(
                content=DataTable(
                    ["A"],
                    [TableRow(cells=["1"])],
                    caption="Returns[^1]",
                    label="Table",
                    notes=["Gross."],
                )
            )
        )
        assert document._components()[0].entries == [("Table 1 · Returns", "table-1")]

    @pytest.mark.parametrize(
        ("of", "label"), [("figures", None), ("sections", "Table"), ("exhibits", " ")]
    )
    def test_a_listing_it_cannot_make_is_refused(self, of, label):
        with pytest.raises(ValidationError, match="Contents"):
            Contents(of=of, label=label)

    def test_the_default_lists_sections_as_before(self):
        assert Contents().of == "sections"


class TestTheSheet:
    def test_it_is_opt_in(self):
        assert isinstance(PagedDocument(PAPER_FACTS).exhibits, EmptyExhibitsPage)

    def test_it_follows_the_contents_in_both_projections(self):
        document = portrait(exhibits=ExhibitsPage(heading="Exhibits"))
        text = document.text()
        assert (
            text.index("In This Review")
            < text.index("Exhibits\n---")
            < text.index("Market Snapshot\n---")
        )
        html = document.render()
        assert html.index("In This Review") < html.index(">Exhibits</h2>")
        sheet = html[html.index(">Exhibits</h2>") :]
        sheet = sheet[: sheet.index("</table>")]
        assert ENTRY.findall(sheet) == headings(document)

    def test_a_contents_sheet_may_list_exhibits_itself(self):
        document = portrait(contents=ContentsPage(heading="Figures", of="exhibits"))
        assert "Figures\n-------\n\nExhibit 1 · Style factor returns" in document.text()

    def test_an_exhibits_sheet_lists_only_exhibits(self):
        with pytest.raises(ValidationError, match="ContentsPage"):
            ExhibitsPage(of="sections")

    @requires_pdf
    def test_every_entry_cites_the_sheet_its_exhibit_is_on(self):
        document = portrait(exhibits=ExhibitsPage(heading="Exhibits"))
        pages = sheets(document)
        listed = pages[2]
        assert listed[0] == "Exhibits"
        entries = [re.fullmatch(r"(.+?)\s*\.{3,}\s*(\d+)", line) for line in listed[1:]]
        cited = [(m.group(1), int(m.group(2))) for m in entries if m]
        assert [heading for heading, _ in cited] == [
            "Exhibit 1 · Style factor returns",
            "Exhibit 2 · The 2s10s spread",
        ]
        for heading, page in cited:
            on = next(n for n, lines in enumerate(pages[3:], start=4) if heading in lines)
            assert page == on, f"{heading!r} cited as p. {page}, printed on {on}"
