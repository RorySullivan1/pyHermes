"""
A page's sheets laid landscape inside a portrait document (#341).

A named page applies to a block in the body's flow and never to a table row,
so a turned page is a body table of its own; the run after it breaks back onto
the medium's sheet. `media.md` records the WeasyPrint 70 probe.
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from pyhermes.builder import Email, FullWidth, TextBlock
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.sizing import (
    A4_LANDSCAPE,
    A4_PORTRAIT,
    LETTER_LANDSCAPE,
    SLIDE_16_9,
    STANDARD_SIZES,
)
from pyhermes.document import (
    PAGED_MEDIUM,
    EmptyCover,
    Page,
    PagedDocument,
    paged_medium,
)
from pyhermes.pdf import available as pdf_available
from qa.fixtures import a4_wide_appendix, all_paged_fixtures

requires_pdf = pytest.mark.skipif(
    not pdf_available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

FACTS = {"firm_name": "F", "campaign_name": "C"}


def _section(title: str = "Wide") -> FullWidth:
    return FullWidth(title=title, content=TextBlock(f"<p>{title} copy.</p>"))


class TestTheField:
    def test_it_takes_portrait_or_landscape(self):
        assert Page([_section()], orientation="landscape").orientation == "landscape"
        assert Page([_section()], orientation="portrait").orientation == "portrait"
        assert Page([_section()]).orientation is None

    @pytest.mark.parametrize("bad", ["Landscape", "sideways", ""])
    def test_anything_else_is_refused_at_construction(self, bad):
        with pytest.raises(ValidationError, match="orientation"):
            Page([_section()], orientation=bad)

    def test_add_page_passes_it_on(self):
        document = PagedDocument(FACTS).add_page([_section()], orientation="landscape")
        [page] = document._sections
        assert page.orientation == "landscape"


class TestWhichSheetTurns:
    def test_a_landscape_page_turns_a_portrait_sheet(self):
        turned = Page([_section()], orientation="landscape").turned_sheet(PAGED_MEDIUM)
        assert (turned.width, turned.height) == (A4_LANDSCAPE.width, A4_LANDSCAPE.height)
        assert turned.margin == A4_PORTRAIT.margin

    def test_a_portrait_page_turns_a_landscape_sheet(self):
        medium = paged_medium(LETTER_LANDSCAPE)
        turned = Page([_section()], orientation="portrait").turned_sheet(medium)
        assert (turned.width, turned.height) == (LETTER_LANDSCAPE.height, LETTER_LANDSCAPE.width)

    @pytest.mark.parametrize(
        "orientation, page",
        [(None, A4_PORTRAIT), ("portrait", A4_PORTRAIT), ("landscape", SLIDE_16_9)],
    )
    def test_a_page_already_that_way_up_does_not_turn(self, orientation, page):
        assert Page([_section()], orientation=orientation).turned_sheet(paged_medium(page)) is None


class TestTheMarkup:
    @pytest.fixture()
    def html(self) -> str:
        return all_paged_fixtures()["a4_wide_appendix"]().render()

    def test_the_skeleton_declares_the_turned_sheet(self, html):
        assert "@page landscape { size: 1123px 794px; }" in html

    def test_the_turned_run_is_a_body_table_as_wide_as_its_frame(self, html):
        width = A4_LANDSCAPE.frame_width
        assert re.search(
            rf'class="document-container" role="presentation" width="{width}"[^>]*'
            rf'style="width:{width}px; [^"]*page: landscape;"',
            html,
        )

    def test_the_run_after_it_breaks_back_onto_the_mediums_sheet(self, html):
        width = A4_PORTRAIT.frame_width
        assert re.search(
            rf'width="{width}"[^>]*style="width:{width}px; [^"]*break-before: page;', html
        )

    def test_the_sections_render_against_the_wider_frame(self, html):
        # page.html's own table, inside the run, is the landscape frame's.
        assert f'style="width:{A4_LANDSCAPE.frame_width}px; background-color:' in html

    def test_an_email_flattens_the_page_byte_for_byte(self):
        def email(section) -> str:
            return (
                Email({**FACTS, "email_subject": "S"})
                .add_section(_section("Before"))
                .add_section(section)
            ).render()

        turned = Page([_section()], orientation="landscape")
        assert email(turned) == email(_section())

    def test_the_text_part_flattens_too(self):
        turned = PagedDocument(FACTS).add_page([_section()], orientation="landscape")
        plain = PagedDocument(FACTS).add_page([_section()])
        assert turned.text() == plain.text()

    def test_unset_the_skeleton_names_no_turned_page(self):
        html = PagedDocument(FACTS).add_page([_section()]).render()
        assert "page: landscape" not in html
        assert "@page landscape" not in html


def _sheets(document) -> list[tuple[int, int, str]]:
    import pypdfium2

    from pyhermes.pdf import render_pdf

    return [
        (
            round(sheet.get_width() * 96 / 72),
            round(sheet.get_height() * 96 / 72),
            sheet.get_textpage().get_text_range(),
        )
        for sheet in pypdfium2.PdfDocument(render_pdf(document))
    ]


PORTRAIT = (A4_PORTRAIT.width, A4_PORTRAIT.height)
LANDSCAPE = (A4_LANDSCAPE.width, A4_LANDSCAPE.height)


@requires_pdf
class TestOnPaper:
    @pytest.fixture(scope="class")
    def sheets(self) -> list[tuple[int, int, str]]:
        return _sheets(all_paged_fixtures()["a4_wide_appendix"]())

    def test_the_sheets_are_the_right_sizes_in_order(self, sheets):
        sizes = [(w, h) for w, h, _ in sheets]
        first = next(
            n for n, (_, _, text) in enumerate(sheets) if a4_wide_appendix.APPENDIX in text
        )
        last = next(n for n, (_, _, text) in enumerate(sheets) if a4_wide_appendix.METHOD in text)
        assert sizes[:first] == [PORTRAIT] * first
        assert sizes[first:last] == [LANDSCAPE] * (last - first)
        assert sizes[last:] == [PORTRAIT] * (len(sheets) - last)
        assert last - first >= 2, "the table should cross a landscape sheet"

    def test_the_table_head_repeats_on_every_landscape_sheet(self, sheets):
        for width, _, text in sheets:
            if width == LANDSCAPE[0]:
                assert all(h.upper() in text for h in a4_wide_appendix.HEADERS)

    def test_the_running_boxes_follow_onto_the_landscape_sheets(self, sheets):
        for number, (width, _, text) in enumerate(sheets, start=1):
            if width == LANDSCAPE[0]:
                assert f"{number} / {len(sheets)}" in text or f"{number}/{len(sheets)}" in text

    def test_the_cross_references_name_the_sheets_their_targets_start_on(self, sheets):
        appendix = next(
            n for n, (_, _, t) in enumerate(sheets, 1) if a4_wide_appendix.APPENDIX in t
        )
        method = next(n for n, (_, _, t) in enumerate(sheets, 1) if a4_wide_appendix.METHOD in t)
        summary = next(t for _, _, t in sheets if a4_wide_appendix.SUMMARY in t)
        assert f"The appendix (p. {appendix})" in summary
        assert f"the method (p. {method})" in summary.replace("\r\n", " ")

    def test_a_table_on_the_landscape_sheet_is_as_wide_as_its_frame(self):
        from tests.test_cell_share import _boxes

        [table, *_] = _boxes(all_paged_fixtures()["a4_wide_appendix"](), "data-table")
        inner = A4_LANDSCAPE.frame_width - 2 * STANDARD_SIZES.frame.pad_x
        assert table.width == pytest.approx(inner, abs=2)

    def test_a_body_that_opens_landscape_wastes_no_sheet(self):
        document = PagedDocument(FACTS, cover=EmptyCover())
        document.add_page([_section("Wide")], orientation="landscape").add_section(_section("Tall"))
        sizes = [(w, h, "Wide" in t, "Tall" in t) for w, h, t in _sheets(document)]
        assert sizes[0] == (*LANDSCAPE, True, False)
        assert sizes[1][:2] == PORTRAIT and sizes[1][3]

    def test_two_turned_pages_in_a_row_each_start_a_sheet(self):
        document = PagedDocument(FACTS, cover=EmptyCover())
        document.add_section(_section("Tall"))
        document.add_page([_section("Alpha")], orientation="landscape")
        document.add_page([_section("Beta")], orientation="landscape")
        document.add_section(_section("Omega"))
        rows = [(w, h) for w, h, _ in _sheets(document)[:4]]
        assert rows == [PORTRAIT, LANDSCAPE, LANDSCAPE, PORTRAIT]
