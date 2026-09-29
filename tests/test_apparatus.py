"""
The document apparatus (#171): anchors, exhibit numbers, footnotes, contents,
cross-references. Everything here is computed in Python before render, so each
test reads one projection against the other rather than trusting either alone.
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from pyhermes.builder import (
    CardGroup,
    ChartBlock,
    Contents,
    DataTable,
    FullWidth,
    ImageBlock,
    NumberedList,
    TemplateEngine,
    TextBlock,
    ThreeColumn,
    TwoColumn,
    ValidationError,
)
from pyhermes.builder.apparatus import slugify
from pyhermes.builder.email import Email
from pyhermes.builder.models import Card, Footnote, NumberedItem, TableRow
from pyhermes.config import config_override
from pyhermes.document import (
    ContentsPage,
    EmptyBackMatter,
    EmptyContentsPage,
    EmptyCover,
    EmptyRunningFooter,
    Page,
    PagedDocument,
    RunningHeader,
)
from pyhermes.pdf import available, render_pdf
from qa.fixtures import all_paged_fixtures

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


class TestFootnoteMarkers:
    """#182's construction-time half: every marker calls a note and every note is called."""

    @pytest.mark.parametrize(
        "build",
        [
            lambda notes: TextBlock("<p>Returns[^1] rose.</p>", notes=notes),
            lambda notes: table(caption="Returns[^1]", notes=notes),
            lambda notes: chart(caption="", source="Desk[^1]", notes=notes),
            lambda notes: image(caption="Desk[^1]", notes=notes),
            lambda notes: NumberedList([NumberedItem("1", "T", "<p>B[^1]</p>", notes=notes)]),
        ],
        ids=["text", "table", "chart", "image", "list-item"],
    )
    def test_every_component_that_carries_notes_checks_its_markers(self, build):
        build(["Gross of fees."])
        with pytest.raises(ValidationError, match=r"marker \[\^1\] but carries 0 note"):
            build([])
        with pytest.raises(ValidationError, match=r"no marker \[\^2\]"):
            build(["Gross of fees.", "A second note nothing calls."])

    def test_a_note_called_twice_raises(self):
        with pytest.raises(ValidationError, match="twice"):
            TextBlock("<p>A[^1] and B[^1]</p>", notes=["One."])

    def test_a_marker_may_sit_in_either_attribution_field(self):
        both = table(caption="Returns[^2]", source="Desk[^1]", notes=["Desk.", "Returns."])
        assert "Returns[2]" in both.text() and "Desk[1]" in both.text()

    def test_an_empty_note_raises(self):
        with pytest.raises(ValidationError, match="footnote.text"):
            TextBlock("<p>A[^1]</p>", notes=[""])

    def test_a_string_is_a_notes_text(self):
        block = TextBlock(
            "<p>A[^1]</p>",
            notes=[
                "Gross.",
            ][:1],
        )
        assert block.notes == [Footnote("Gross.")]

    def test_rendered_alone_a_marker_keeps_its_local_number(self):
        block = TextBlock("<p>A[^1]</p>", notes=["Gross."])
        assert 'href="#note-1"' in block.render(TemplateEngine())
        assert block.text() == "A[1]"


class TestFootnotesAcrossTheDocument:
    """#182's projections: one number per note, placed where each medium can put it."""

    @pytest.fixture
    def sections(self):
        return (
            FullWidth(
                title="A", content=TextBlock("<p>Rates repriced.[^1]</p>", notes=["Two-year."])
            ),
            TwoColumn(
                title="B",
                left=table(source="Desk[^1]", notes=["Close to close."]),
                right=chart(caption="Spread[^1]", notes=["In bps."]),
            ),
        )

    def test_notes_number_in_reading_order_in_both_projections(self, sections):
        document = email(*sections)
        assert re.findall(r'id="note-ref-(\d)"', document.render()) == ["1", "2", "3"]
        assert re.findall(r"\[(\d)\]", document.text()) == ["1", "2", "3", "1", "2", "3"]

    def test_a_marker_sits_at_the_same_place_in_both_projections(self, sections):
        document = email(*sections)
        assert re.search(
            r'repriced\.<sup class="note-ref"[^>]*><a href="#note-1"', document.render()
        )
        assert "Rates repriced.[1]" in document.text()

    def test_each_note_is_said_once_per_projection_in_an_email(self, sections):
        document = email(*sections)
        for note in ("Two-year.", "Close to close.", "In bps."):
            assert document.render().count(note) == 1
            assert document.text().count(note) == 1

    def test_an_email_gathers_them_as_endnotes_linked_both_ways(self, sections):
        html = email(*sections).render()
        assert 'class="notes-heading"' in html and 'class="footnote"' not in html
        assert re.search(
            r'<li id="note-2"[^>]*><a href="#note-ref-2"[^>]*>2\.</a> Close to close\.', html
        )

    def test_a_page_floats_each_note_at_its_marker_and_gathers_none(self, sections):
        document = PagedDocument(PAPER_FACTS)
        for section in sections:
            document.add_section(section)
        html = document.render()
        assert 'class="notes-heading"' not in html
        assert re.search(
            r'</sup><span class="footnote" id="note-3" data-note="3">In bps\.</span>', html
        )
        for note in ("Two-year.", "Close to close.", "In bps."):
            assert html.count(note) == 1
        assert "[1] Two-year." in document.text()

    def test_a_document_without_notes_has_no_notes_block(self):
        document = email(FullWidth(content=prose()))
        assert "notes-heading" not in document.render()
        assert "Notes\n-----" not in document.text()

    def test_a_note_anchor_cannot_be_claimed_by_a_section(self, sections):
        document = email(*sections)
        with pytest.raises(ValidationError, match="'note-2' is claimed twice"):
            document.add_section(FullWidth(title="Anything", anchor="note-2", content=prose()))

    @requires_pdf
    def test_each_note_is_at_the_foot_of_the_sheet_its_marker_is_on(self):
        pages = sheets(all_paged_fixtures()["a4_portrait"]())
        called_from = {
            "1. The front end is the two-year gilt.": "The curve steepened through the quarter",
            "2. Factor definitions follow the methodology in the appendix.": "Exhibit 1",
            "3. Measured close to close.": "Exhibit 2",
        }
        for note, marker_context in called_from.items():
            holding = [n for n, lines in enumerate(pages) if note in lines]
            assert len(holding) == 1, f"{note!r} is on sheets {holding}"
            assert any(marker_context in line for line in pages[holding[0]]), (
                f"{note!r} is not on the sheet its marker is on"
            )
            # At the foot: below everything but the running footer.
            lines = pages[holding[0]]
            assert lines.index(note) > max(
                i for i, line in enumerate(lines) if marker_context in line
            )


XREF = '<p>See <a class="xref" href="#exhibit-1">Exhibit 1</a>.</p>'


class TestCrossReferences:
    """#184: a class hook, one CSS rule, one degrader rule and one validator."""

    def test_an_email_renders_the_link_as_written(self):
        html = email(
            FullWidth(content=table(label="Exhibit")), FullWidth(content=prose(XREF))
        ).render()
        assert '<a class="xref" href="#exhibit-1">Exhibit 1</a>' in html
        assert "target-counter" not in html

    def test_the_text_part_says_the_reference_alone(self):
        document = email(FullWidth(content=table(label="Exhibit")), FullWidth(content=prose(XREF)))
        assert "See Exhibit 1." in document.text()

    def test_paper_asks_the_print_engine_for_the_page(self):
        html = all_paged_fixtures()["a4_portrait"]().render()
        assert re.search(r'a\.xref::after \{\s*content: " \(p\. " target-counter', html)

    def test_a_forward_reference_is_legal(self):
        document = email(FullWidth(content=prose(XREF)), FullWidth(content=table(label="Exhibit")))
        assert "See Exhibit 1." in document.text()

    def test_a_dangling_reference_raises_by_name_before_any_template(self):
        document = email(FullWidth(content=prose(XREF)))
        for project in (document.render, document.text, document.validate):
            with pytest.raises(ValidationError, match="TextBlock links to #exhibit-1"):
                project()

    def test_renumbering_is_what_it_catches(self):
        document = email(FullWidth(content=table(label="Table")), FullWidth(content=prose(XREF)))
        with pytest.raises(ValidationError, match="#exhibit-1"):
            document.render()

    @pytest.mark.parametrize(
        "section",
        [
            lambda: FullWidth(content=CardGroup([Card("A", body=XREF)], orientation="vertical")),
            lambda: FullWidth(content=NumberedList([NumberedItem("1", "T", XREF)])),
        ],
        ids=["card-body", "numbered-item-body"],
    )
    def test_every_raw_html_field_is_checked(self, section):
        with pytest.raises(ValidationError, match="#exhibit-1"):
            email(section()).render()

    def test_the_document_facts_and_the_footer_are_checked_too(self):
        from pyhermes.builder import Footer

        with pytest.raises(ValidationError, match="header_disclaimer links to #nowhere"):
            Email({**FACTS, "header_disclaimer": '<a href="#nowhere">x</a>'}).render()
        with pytest.raises(ValidationError, match="Footer links to #nowhere"):
            Email(FACTS, footer=Footer(disclaimer='<a href="#nowhere">x</a>')).render()

    def test_a_link_to_a_section_or_a_note_resolves(self):
        copy = '<p><a href="#outlook">Outlook</a>, and <a href="#note-1">note 1</a>[^1].</p>'
        document = email(
            FullWidth(title="Outlook", content=TextBlock(copy, notes=["A note."])),
        )
        document.validate()

    @requires_pdf
    def test_on_paper_the_page_is_the_sheet_the_target_is_on(self):
        pages = sheets(all_paged_fixtures()["a4_portrait"]())
        cited = [
            (n, int(match.group(1)))
            for n, lines in enumerate(pages, start=1)
            for line in lines
            if (match := re.search(r"Exhibit 1 \(p\. (\d+)\)", line))
        ]
        assert len(cited) == 1, cited
        citing, page = cited[0]
        target = next(
            n
            for n, lines in enumerate(pages, start=1)
            if any("Exhibit 1 ·" in line for line in lines)
        )
        assert page == target and citing != target


def header_lines(pages: list[list[str]], folio: str = " / ") -> list[str]:
    """Each sheet's top-margin line, the one carrying the folio; "" where none."""
    return [next((line for line in lines if folio in line), "") for lines in pages]


def following_lines(document, pages: list[list[str]]) -> list[str]:
    """
    What the following margin box says on each sheet after the cover.

    ``a4_portrait``'s header follows and carries the folio; ``a4_long_table``'s
    footer follows and carries none, and is the last line pdfium reads off a sheet.
    """
    body = pages[1:]
    if document.running_header.follow:
        return [line.split(" · ")[0] for line in header_lines(body)]
    return [lines[-1] for lines in body]


class TestTheRunningHeaderFollowsTheSection:
    """#185: the page's own knowledge of what it holds, through the print engine."""

    def test_only_a_known_thing_may_be_followed(self):
        with pytest.raises(ValidationError, match="running_header.follow"):
            RunningHeader(follow="chapter")

    def test_a_following_box_prints_the_named_string(self):
        html = all_paged_fixtures()["a4_portrait"]().render()
        assert "string(running-header-fallback, last) string(running-header, first)" in html
        assert '.running-header-start { string-set: running-header-fallback "Hermes' in html

    def test_a_box_that_does_not_follow_prints_its_label_as_before(self):
        html = all_paged_fixtures()["a4_portrait"]().render()
        assert 'content: "Confidential";' in html
        assert "running-footer-start {" not in html

    def test_the_text_projection_is_still_empty_by_decision(self):
        assert RunningHeader(follow="section").text({"campaign_name": "C"}) == ""

    def test_the_section_titles_set_the_strings_only_on_paper(self):
        paged = all_paged_fixtures()["a4_portrait"]().render()
        assert ".section-title h2 {" in paged
        emailed = email(FullWidth(title="T", content=prose())).render()
        assert "string-set" not in emailed and "running-header-start" not in emailed

    @requires_pdf
    @pytest.mark.parametrize("name", ["a4_portrait", "a4_long_table", "slide_16_9"])
    def test_each_sheet_is_headed_by_a_section_begun_on_or_before_it(self, name):
        document = all_paged_fixtures()[name]()
        box = document.running_header if document.running_header.follow else document.running_footer
        pages = sheets(document)
        titles = [section.title for section in document._flat_sections() if section.title]
        begun: list[str] = []
        shown_by_sheet = following_lines(document, pages)
        for n, (lines, shown) in enumerate(zip(pages[1:], shown_by_sheet, strict=True), start=2):
            begun += [title for title in titles if title in lines and title not in begun]
            if begun:
                assert shown in begun, f"sheet {n} is headed {shown!r}, begun: {begun}"
            else:
                assert shown == box.label, f"sheet {n}: {shown!r}"

    @requires_pdf
    @pytest.mark.parametrize("name", ["a4_portrait", "a4_long_table"])
    def test_the_line_changes_between_sections(self, name):
        document = all_paged_fixtures()[name]()
        shown = set(following_lines(document, sheets(document)))
        assert len(shown & {s.title for s in document._flat_sections()}) >= 2, shown

    def test_the_two_boxes_may_differ(self):
        document = all_paged_fixtures()["a4_long_table"]()
        assert document.running_footer.follow and not document.running_header.follow
        html = document.render()
        assert "string(running-footer-fallback, last) string(running-footer, first)" in html
        assert 'content: "Hermes Research — Quarterly Review" " · "' in html

    @requires_pdf
    def test_with_no_titled_section_the_label_is_the_fallback(self):
        document = PagedDocument(
            PAPER_FACTS,
            cover=EmptyCover(),
            running_header=RunningHeader(
                label="The Label", follow="section", show_page_number=True
            ),
            running_footer=EmptyRunningFooter(),
            back_matter=EmptyBackMatter(),
        )
        document.add_section(FullWidth(content=prose("<p>Untitled.</p>" * 3)))
        assert header_lines(sheets(document)) == ["The Label · 1 / 1"]
