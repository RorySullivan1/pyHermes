"""
The document apparatus (#171): anchors, exhibit numbers, footnotes, contents,
cross-references. Everything here is computed in Python before render, so each
test reads one projection against the other rather than trusting either alone.
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from qa.fixtures import all_paged_fixtures
from svc.builder import (
    ChartBlock,
    Contents,
    DataTable,
    FullWidth,
    ImageBlock,
    TemplateEngine,
    TextBlock,
    ThreeColumn,
    TwoColumn,
    ValidationError,
)
from svc.builder.apparatus import slugify
from svc.builder.email import Email
from svc.builder.models import TableRow
from svc.config import config_override
from svc.document import ContentsPage, EmptyContentsPage, Page, PagedDocument
from svc.pdf import available, render_pdf

requires_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

PAPER_FACTS = {"firm_name": "Hermes", "campaign_name": "Review"}
FACTS = {"email_subject": "Subject", **PAPER_FACTS}


def email(*sections) -> Email:
    built = Email(FACTS)
    for section in sections:
        built.add_section(section)
    return built


def prose(copy: str = "<p>Copy.</p>") -> TextBlock:
    return TextBlock(copy)


class TestSectionAnchors:
    """#183, first commit: every titled section's heading is a destination."""

    @pytest.mark.parametrize(
        ("title", "slug"),
        [
            ("Factor Returns", "factor-returns"),
            ("  Q3: What the curve priced?  ", "q3-what-the-curve-priced"),
            ("Café & Crème", "cafe-creme"),
            ("2026 outlook", "section-2026-outlook"),
            ("★★★", "section"),
        ],
    )
    def test_a_title_slugs_to_a_valid_id(self, title, slug):
        assert slugify(title) == slug

    def test_the_heading_carries_the_slug(self):
        html = email(FullWidth(title="Factor Returns", content=prose())).render()
        assert '<h2 id="factor-returns" ' in html

    def test_a_split_heading_carries_one_too(self):
        html = email(TwoColumn(title="Positioning", left=prose())).render()
        assert '<h2 id="positioning" ' in html

    def test_the_caller_may_override_it(self):
        html = email(FullWidth(title="Factor Returns", anchor="factors", content=prose()))
        assert '<h2 id="factors" ' in html.render()

    def test_an_untitled_section_claims_nothing(self):
        section = FullWidth(anchor="ignored", content=prose())
        assert section.resolved_anchor() == ""
        assert "<h2" not in email(section).render()

    @pytest.mark.parametrize("bad", ["1st", "has space", "a#b", "-lead", 'x"y'])
    def test_a_malformed_override_raises_at_construction(self, bad):
        with pytest.raises(ValidationError, match="container.anchor"):
            FullWidth(title="T", anchor=bad, content=prose())

    def test_two_sections_with_one_slug_raise_when_the_second_is_added(self):
        document = email(FullWidth(title="Factor Returns", content=prose()))
        with pytest.raises(ValidationError, match="'factor-returns' is claimed twice"):
            document.add_section(ThreeColumn(title="Factor returns!", left=prose()))

    def test_the_rejected_section_is_not_kept(self):
        document = email(FullWidth(title="Outlook", content=prose()))
        with pytest.raises(ValidationError):
            document.add_section(FullWidth(title="Outlook", content=prose()))
        assert len(document._sections) == 1
        document.add_section(FullWidth(title="Outlook", anchor="outlook-2", content=prose()))

    def test_a_pages_sections_are_checked_as_the_documents_own(self):
        document = email(FullWidth(title="Method", content=prose()))
        page = Page([FullWidth(title="Method", content=prose())], title="Appendix")
        with pytest.raises(ValidationError, match="'method'"):
            document.add_section(page)

    def test_a_pages_own_title_is_never_rendered_so_claims_no_anchor(self):
        page = Page([FullWidth(content=prose())], title="Appendix")
        assert page.resolved_anchor() == ""
        email(FullWidth(title="Appendix", content=prose()), page)


CHART = "https://cdn.example.com/chart.png"


def table(caption: str = "Factor returns", **kwargs) -> DataTable:
    return DataTable(["Factor", "1M"], [TableRow(["Value", "+1.8%"])], caption=caption, **kwargs)


def chart(caption: str = "Cumulative return", **kwargs) -> ChartBlock:
    return ChartBlock(CHART, alt_text="A chart", caption=caption, **kwargs)


def image(caption: str = "The desk", **kwargs) -> ImageBlock:
    return ImageBlock(CHART, alt_text="A photo", caption=caption, **kwargs)


class TestExhibitNumbering:
    """#181: numbered once, in Python, in reading order, and both projections agree."""

    @pytest.fixture
    def document(self):
        return email(
            FullWidth(title="Returns", content=table(label="Exhibit")),
            TwoColumn(
                title="Split",
                left=chart(label="Exhibit"),
                right=image(label="Exhibit"),
            ),
        )

    def test_the_order_is_reading_order_in_the_markup(self, document):
        html = document.render()
        found = re.findall(r"Exhibit (\d) · (\w+)", html)
        assert found == [("1", "Factor"), ("2", "Cumulative"), ("3", "The")]

    def test_the_order_is_the_same_in_the_text(self, document):
        found = re.findall(r"Exhibit (\d) · (\w+)", document.text())
        assert found == [("1", "Factor"), ("2", "Cumulative"), ("3", "The")]

    def test_each_numbered_exhibit_carries_its_anchor(self, document):
        html = document.render()
        for n in (1, 2, 3):
            assert html.count(f'id="exhibit-{n}"') == 1

    def test_a_page_numbers_its_exhibits_in_place(self):
        document = email(
            FullWidth(content=table(label="Exhibit")),
            Page([FullWidth(content=chart(label="Exhibit"))]),
            FullWidth(content=image(label="Exhibit")),
        )
        assert re.findall(r"Exhibit (\d) ·", document.text()) == ["1", "2", "3"]

    def test_each_label_keeps_its_own_count(self):
        document = email(
            FullWidth(content=table(label="Table")),
            FullWidth(content=chart(label="Figure")),
            FullWidth(content=table(caption="Second", label="Table")),
        )
        text = document.text()
        assert "Table 1 · Factor returns" in text
        assert "Figure 1 · Cumulative return" in text
        assert "Table 2 · Second" in text
        assert 'id="figure-1"' in document.render()

    def test_an_uncaptioned_exhibit_prints_its_number_alone(self):
        document = email(FullWidth(content=chart(caption="", label="Exhibit")))
        assert "Exhibit 1\n" in document.text() + "\n"
        assert "Exhibit 1 ·" not in document.render()

    def test_the_separator_is_house_style_read_at_render(self):
        document = email(FullWidth(content=table(label="Exhibit")))
        with config_override(exhibit_separator=": "):
            assert "Exhibit 1: Factor returns" in document.render()
            assert "Exhibit 1: Factor returns" in document.text()

    def test_the_caller_may_override_the_anchor(self):
        html = email(FullWidth(content=table(label="Exhibit", anchor="returns"))).render()
        assert 'id="returns"' in html and 'id="exhibit-1"' not in html

    def test_an_unlabelled_exhibit_may_still_be_a_destination(self):
        html = email(FullWidth(content=chart(anchor="the-chart"))).render()
        assert 'id="the-chart"' in html and "Exhibit" not in html

    @pytest.mark.parametrize("build", [table, chart, image])
    def test_an_unlabelled_exhibit_renders_byte_identically(self, build):
        engine = TemplateEngine()
        labelled_alone = build(label="Exhibit")
        assert labelled_alone.number is None
        assert labelled_alone.render(engine) == build().render(engine)
        assert labelled_alone.text() == build().text()

    def test_a_shared_exhibit_takes_each_documents_number(self):
        shared = chart(label="Exhibit")
        first = email(FullWidth(content=shared))
        second = email(FullWidth(content=table(label="Exhibit")), FullWidth(content=shared))
        assert "Exhibit 2 · Cumulative" in second.text()
        assert "Exhibit 1 · Cumulative" in first.text()

    def test_a_duplicate_anchor_raises_at_construction(self):
        document = email(FullWidth(content=table(label="Exhibit")))
        with pytest.raises(ValidationError, match="'exhibit-1' is claimed twice"):
            document.add_section(FullWidth(content=chart(anchor="exhibit-1")))

    def test_an_exhibit_and_a_section_may_not_share_an_anchor(self):
        document = email(FullWidth(title="Exhibit 1", content=prose()))
        with pytest.raises(ValidationError, match="Exhibit 1 DataTable"):
            document.add_section(FullWidth(content=table(label="Exhibit")))

    def test_a_blank_label_raises(self):
        with pytest.raises(ValidationError, match="datatable.label"):
            table(label="   ")

    def test_a_malformed_anchor_raises(self):
        with pytest.raises(ValidationError, match="chartblock.anchor"):
            chart(anchor="3rd")


def sheets(document) -> list[list[str]]:
    """Each sheet's lines of text, read back out of the PDF."""
    import pypdfium2

    pdf = pypdfium2.PdfDocument(render_pdf(document))
    return [
        [line.strip() for line in sheet.get_textpage().get_text_range().splitlines()]
        for sheet in pdf
    ]


class TestTheContentsComponent:
    """#183 in an email: a linked list, no page numbers, filled by the document."""

    @pytest.fixture
    def document(self):
        return email(
            FullWidth(title="In This Issue", content=Contents(subtitle="Inside")),
            FullWidth(title="Factor Returns", content=prose()),
            Page([FullWidth(title="Method", anchor="how", content=prose())], title="Appendix"),
        )

    def test_it_links_every_other_titled_section_in_reading_order(self, document):
        html = document.render()
        links = re.findall(
            r'<li class="contents-entry"[^>]*><a href="#([\w-]+)"[^>]*>([^<]+)</a>', html
        )
        assert links == [("factor-returns", "Factor Returns"), ("how", "Method")]

    def test_every_link_lands_on_a_heading(self, document):
        html = document.render()
        for anchor in re.findall(r'<li class="contents-entry"[^>]*><a href="#([\w-]+)"', html):
            assert f'<h2 id="{anchor}"' in html

    def test_an_email_carries_no_page_numbers(self, document):
        assert "target-counter" not in document.render()

    def test_the_text_is_the_titles_one_per_line(self, document):
        assert "Inside\n\nFactor Returns\nMethod\n" in document.text()

    def test_an_untitled_section_is_not_listed(self):
        document = email(
            FullWidth(content=Contents()),
            FullWidth(content=prose()),
            FullWidth(title="T", content=prose()),
        )
        assert document._components()[0].entries == [("T", "t")]


class TestTheContentsSheet:
    """#183 on paper: a region after the cover, the page numbers the print engine's."""

    def test_it_is_opt_in(self):
        assert isinstance(PagedDocument(PAPER_FACTS).contents, EmptyContentsPage)

    def test_it_follows_the_cover_in_both_projections(self):
        document = all_paged_fixtures()["a4_portrait"]()
        text = document.text()
        assert (
            text.index("Quarterly Review")
            < text.index("In This Review")
            < text.index("Market Snapshot\n---")
        )
        html = document.render()
        assert (
            html.index("page: cover")
            < html.index("In This Review")
            < html.index('class="document-container"')
        )

    def test_its_heading_is_not_a_section_title(self):
        html = PagedDocument(PAPER_FACTS, contents=ContentsPage()).render()
        heading = html[: html.index(">Contents</h2>")]
        assert "section-title" not in heading[heading.rindex("<table") :]

    def test_the_page_number_is_the_print_engines(self):
        html = all_paged_fixtures()["a4_portrait"]().render()
        assert "target-counter(attr(href), page)" in html

    @requires_pdf
    @pytest.mark.parametrize("name", ["a4_portrait", "slide_16_9"])
    def test_every_entry_cites_the_sheet_its_section_starts_on(self, name):
        pages = sheets(all_paged_fixtures()[name]())
        contents = pages[1]
        assert contents[0] == "In This Review"
        entries = [re.fullmatch(r"(.+?)\s*\.{3,}\s*(\d+)", line) for line in contents[1:]]
        cited = [(m.group(1), int(m.group(2))) for m in entries if m]
        assert [title for title, _ in cited] == [
            "Market Snapshot",
            "Narrative",
            "Factor Returns",
            "Positioning",
            "Methodology",
        ]
        for title, page in cited:
            starts = next(n for n, lines in enumerate(pages[2:], start=3) if title in lines)
            assert page == starts, f"{title!r} cited as p. {page}, starts on {starts}"
