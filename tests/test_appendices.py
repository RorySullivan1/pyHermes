"""
Lettered appendices (#309): one letter level, computed in the walk, in every projection.

The fixture is the issue's own: two body exhibits, then two appendices of two
exhibits each. Each test reads one projection against the expected sequence.
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from pyhermes.builder import (
    Appendices,
    Contents,
    DataTable,
    FullWidth,
    TextBlock,
    ValidationError,
)
from pyhermes.builder.email import Email
from pyhermes.builder.models import TableRow
from pyhermes.config import Config
from pyhermes.document import (
    ContentsPage,
    EmptyBackMatter,
    EmptyCover,
    ExhibitsPage,
    Page,
    PagedDocument,
    RunningHeader,
)
from pyhermes.pdf import available, render_pdf

requires_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

PAPER_FACTS = {"firm_name": "Hermes", "campaign_name": "Review"}
FACTS = {"email_subject": "Subject", **PAPER_FACTS}

EXPECTED = [
    "Exhibit 1",
    "Exhibit 2",
    "Exhibit A.1",
    "Exhibit A.2",
    "Exhibit B.1",
    "Exhibit B.2",
]


def table(caption: str) -> DataTable:
    return DataTable(
        ["Factor", "1M"], [TableRow(cells=["Value", "1.8"])], caption=caption, label="Exhibit"
    )


def build(document):
    """The issue's fixture on ``document``: two body exhibits, two appendices of two."""
    document.add_section(FullWidth(title="Exhibits", content=Contents(of="exhibits")))
    document.add_section(FullWidth(title="Returns", content=table("Returns")))
    document.add_section(FullWidth(title="Risk", content=table("Risk")))
    document.add_section(
        Appendices(
            [
                FullWidth(title="Data sources", content=table("Coverage")),
                FullWidth(content=table("Vendors")),
                FullWidth(
                    title="Robustness",
                    content=TextBlock(
                        '<p>As <a class="xref" href="#exhibit-a-1">Exhibit A.1</a> shows.</p>'
                    ),
                ),
                FullWidth(content=table("Subperiods")),
                FullWidth(content=table("Costs")),
            ]
        )
    )
    return document


def paper(**regions) -> PagedDocument:
    return build(
        PagedDocument(
            PAPER_FACTS,
            **{
                "cover": EmptyCover(),
                "back_matter": EmptyBackMatter(),
                "running_header": RunningHeader(label="Review", follow="section"),
                **regions,
            },
        )
    )


@pytest.fixture(params=["email", "paper"])
def document(request):
    return build(Email(FACTS)) if request.param == "email" else paper()


def headed(html: str) -> list[str]:
    """Every section heading's text, as the markup prints it."""
    return [title.strip() for title in re.findall(r"<h2[^>]*>([^<]+)</h2>", html)]


def numbers(text: str) -> list[str]:
    return re.findall(r"Exhibit (?:[A-Z]\.)?\d+", text)


class TestEveryProjectionAgrees:
    def test_the_markup_numbers_them(self, document):
        html = document.render()
        captions = re.findall(r"<caption[^>]*>(?:<[^>]+>)*([^<]+)", html)
        assert numbers(" ".join(captions)) == EXPECTED

    def test_the_text_numbers_them(self, document):
        text = document.text()
        body = text[text.index("Returns\n---") :]
        # The cross-reference in Appendix B is the fifth mention.
        assert numbers(body) == [*EXPECTED[:4], "Exhibit A.1", *EXPECTED[4:]]

    def test_the_list_of_exhibits_numbers_them(self, document):
        document.validate()
        listing = document._components()[0]
        assert [numbers(heading)[0] for heading, _ in listing.entries] == EXPECTED

    def test_the_anchors_follow_the_numbers(self, document):
        document.validate()
        listing = document._components()[0]
        assert [anchor for _, anchor in listing.entries] == [
            "exhibit-1",
            "exhibit-2",
            "exhibit-a-1",
            "exhibit-a-2",
            "exhibit-b-1",
            "exhibit-b-2",
        ]

    def test_each_appendix_heading_is_lettered_where_it_is_printed(self, document):
        assert headed(document.render())[-2:] == [
            "Appendix A: Data sources",
            "Appendix B: Robustness",
        ]
        assert "Appendix A: Data sources\n------------------------" in document.text()

    def test_a_contents_lists_the_lettered_headings(self):
        document = Email(FACTS)
        document.add_section(FullWidth(content=Contents()))
        build(document)
        document.validate()
        titles = [title for title, _ in document._components()[0].entries]
        assert titles[-2:] == ["Appendix A: Data sources", "Appendix B: Robustness"]

    def test_the_heading_takes_the_house_format(self):
        document = build(Email(FACTS, config=Config(appendix_heading="{letter}. {title}")))
        assert "A. Data sources" in headed(document.render())

    def test_a_reference_to_an_appendix_exhibit_validates(self, document):
        document.validate()
        assert 'id="exhibit-a-1"' in document.render()

    def test_a_reference_to_the_old_numbering_is_named(self):
        document = build(Email(FACTS))
        document.add_section(
            FullWidth(content=TextBlock('<p><a href="#exhibit-3">Exhibit 3</a></p>'))
        )
        with pytest.raises(ValidationError, match="#exhibit-3"):
            document.validate()


class TestTheBoundary:
    def test_the_first_appendix_must_be_titled(self):
        with pytest.raises(ValidationError, match="Appendix A"):
            Appendices([FullWidth(content=table("x"))])

    def test_a_page_cannot_sit_inside(self):
        with pytest.raises(ValidationError, match="cannot nest"):
            Appendices([Page([FullWidth(title="A", content=table("x"))])])

    def test_appendices_cannot_sit_on_a_page(self):
        with pytest.raises(ValidationError):
            Page([Appendices([FullWidth(title="A", content=table("x"))])])

    def test_a_document_has_one(self):
        document = build(Email(FACTS))
        with pytest.raises(ValidationError, match="one Appendices"):
            document.add_section(Appendices([FullWidth(title="C", content=table("x"))]))

    def test_an_email_carries_no_wrapper(self):
        email = Email(FACTS)
        email.add_section(Appendices([FullWidth(title="A", content=TextBlock("<p>x</p>"))]))
        alone = Email(FACTS)
        alone.add_section(FullWidth(title="A", content=TextBlock("<p>x</p>")))
        assert email.render().replace("Appendix A: A", "A") == alone.render()

    def test_paper_opens_a_sheet_unless_asked_not_to(self):
        sections = [FullWidth(title="A", content=TextBlock("<p>x</p>"))]
        opened = PagedDocument(PAPER_FACTS).add_section(
            FullWidth(title="Body", content=TextBlock("x"))
        )
        opened.add_section(Appendices(sections))
        assert '<tr style="break-before:page' in opened.render()
        run_on = PagedDocument(PAPER_FACTS).add_section(
            FullWidth(title="Body", content=TextBlock("x"))
        )
        run_on.add_section(Appendices(sections, break_before=False))
        assert '<tr style="break-before:page' not in run_on.render()

    def test_a_format_without_the_letter_is_refused(self):
        with pytest.raises(ValueError, match="letter"):
            Config(appendix_heading="Appendix: {title}")


def sheets(document) -> list[list[str]]:
    import pypdfium2

    pdf = pypdfium2.PdfDocument(render_pdf(document))
    return [
        [line.strip() for line in sheet.get_textpage().get_text_range().splitlines()]
        for sheet in pdf
    ]


@requires_pdf
class TestOnPaper:
    """#171's probes for the running section and ``target-counter``, re-run with letters."""

    @pytest.fixture(scope="class")
    def pages(self):
        return sheets(paper(contents=ContentsPage(), exhibits=ExhibitsPage(heading="Exhibits")))

    def test_the_running_header_names_the_appendix(self, pages):
        appendix = next(n for n, lines in enumerate(pages) if "Appendix A: Data sources" in lines)
        assert pages[appendix][0] == "Appendix A: Data sources"

    def test_a_cross_reference_resolves_to_the_exhibits_sheet(self, pages):
        on = next(n for n, lines in enumerate(pages, 1) if "Exhibit A.1 · Coverage" in lines)
        cited = next(line for lines in pages for line in lines if line.startswith("As Exhibit A.1"))
        assert f"(p. {on})" in cited

    def test_the_list_of_exhibits_cites_each_sheet(self, pages):
        listed = next(lines for lines in pages if lines and lines[0] == "Exhibits")
        entries = [re.fullmatch(r"(.+?)\s*\.{3,}\s*(\d+)", line) for line in listed[1:]]
        cited = [(m.group(1), int(m.group(2))) for m in entries if m]
        assert [numbers(heading)[0] for heading, _ in cited] == EXPECTED
        for heading, page in cited:
            on = next(n for n, lines in enumerate(pages, 1) if heading in lines)
            assert page == on
