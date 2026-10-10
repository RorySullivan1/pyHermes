"""
Keeping a section together, or starting it on a fresh sheet, without a ``Page`` (#364).

Both are paper's: they land on the section's own row there, and emit nothing
anywhere else. Where a section lands is read back from the PDF, because only
the print engine knows.
"""

from __future__ import annotations

import importlib.util
import re
import warnings

import pytest

from pyhermes.brochure import Panel
from pyhermes.builder import (
    Email,
    FlowedColumns,
    FourColumn,
    FullWidth,
    OnlySections,
    PrintQualityWarning,
    TextBlock,
    ThreeColumn,
    TwoColumn,
    ValidationError,
)
from pyhermes.deck import Slide
from pyhermes.document import EmptyBackMatter, EmptyCover, Page, PagedDocument
from pyhermes.pdf import available, render_pdf

requires_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

FACTS = {"firm_name": "F", "campaign_name": "C"}
LOREM = (
    "The long end did the work this quarter, and the term premium explains most of the move. " * 3
)

#: Lead-in paragraphs that put the kept section across a sheet edge when it is not kept.
STRADDLING = 8


def body(marker: str = "", paragraphs: int = 1) -> TextBlock:
    middle = f"<p>{LOREM}</p>" * paragraphs
    return TextBlock(f"<p>{marker}START</p>{middle}<p>{marker}END</p>")


def paper(*sections) -> PagedDocument:
    document = PagedDocument(FACTS, cover=EmptyCover(), back_matter=EmptyBackMatter())
    for section in sections:
        document.add_section(section)
    return document


def lead_in(paragraphs: int) -> FullWidth:
    return FullWidth(TextBlock(f"<p>{LOREM}</p>" * paragraphs), title="Lead in")


class TestTheFields:
    def test_every_section_container_takes_both(self):
        left = TextBlock("<p>x</p>")
        for section in (
            FullWidth(left, keep_together=True, break_before=True),
            FlowedColumns(left, keep_together=True, break_before=True),
            TwoColumn(left=left, keep_together=True, break_before=True),
            ThreeColumn(left=left, keep_together=True, break_before=True),
            FourColumn([left, None, None, None], keep_together=True, break_before=True),
        ):
            assert section.keep_together and section.break_before

    @pytest.mark.parametrize("name", ["keep_together", "break_before"])
    def test_a_non_bool_is_refused(self, name):
        with pytest.raises(ValidationError, match=name):
            FullWidth(TextBlock("<p>x</p>"), **{name: "yes"})

    def test_on_paper_each_lands_on_the_sections_row_in_both_spellings(self):
        html = paper(
            FullWidth(body("A"), title="Kept", keep_together=True),
            TwoColumn(left=body("B"), break_before=True),
        ).render()
        assert (
            '<tr id="kept-section-1" style="break-inside:avoid; page-break-inside:avoid;">' in html
        )
        assert '<tr style="break-before:page; page-break-before:always;">' in html

    def test_both_together_carry_both(self):
        html = paper(lead_in(1), FullWidth(body(), keep_together=True, break_before=True)).render()
        assert (
            'style="break-before:page; page-break-before:always; '
            'break-inside:avoid; page-break-inside:avoid;"'
        ) in html


class TestNotAByteInAnEmail:
    def test_an_email_is_byte_identical_with_and_without_them(self):
        def email(**placement):
            built = Email({"email_subject": "S", **FACTS})
            built.add_section(FullWidth(body(), title="T", **placement))
            built.add_section(TwoColumn(left=body("L"), **placement))
            return built

        plain = email()
        placed = email(keep_together=True, break_before=True)
        assert placed.render() == plain.render()
        assert placed.text() == plain.text()

    def test_the_text_part_is_unmoved_on_paper(self):
        assert (
            paper(FullWidth(body(), title="T", keep_together=True)).text()
            == paper(FullWidth(body(), title="T")).text()
        )


class TestWhereTheyAreRefused:
    def test_a_panel_refuses_them(self):
        for name in ("keep_together", "break_before"):
            with pytest.raises(ValidationError, match="a panel is one face"):
                Panel([FullWidth(body(), **{name: True})])

    def test_a_slide_refuses_them(self):
        for name in ("keep_together", "break_before"):
            with pytest.raises(ValidationError, match="a slide is already one sheet"):
                Slide([FullWidth(body(), **{name: True})])


class TestTheBodysFirstSection:
    def test_a_break_before_the_first_section_is_dropped_as_a_pages_is(self):
        """The body already opens a sheet, and a forced break there opens a blank one."""
        html = paper(FullWidth(body(), title="First", break_before=True)).render()
        assert "break-before:page" not in html

    def test_the_callers_section_is_not_mutated(self):
        first = FullWidth(body(), title="First", break_before=True)
        paper(first).render()
        assert first.break_before is True


def hidden_then_shown(shown: TextBlock) -> PagedDocument:
    """A kept section only an email shows, then a kept one paper shows (#431)."""
    hidden = FullWidth(body("H"), title="Hidden", keep_together=True)
    return paper(
        OnlySections([hidden], media=["email"]),
        FullWidth(shown, title="Shown", keep_together=True),
    )


class TestTheKeptSectionsAreTheRendersOwn:
    def test_a_section_hidden_on_paper_is_not_counted(self):
        document = hidden_then_shown(body("S"))
        rendered = set(re.findall(r'id="(kept-section-\d+)"', document.render()))
        assert document.kept_sections() == {"kept-section-1": "Shown"}
        assert set(document.kept_sections()) == rendered


def sheets_of(document) -> list[str]:
    import pypdfium2

    pdf = pypdfium2.PdfDocument(render_pdf(document))
    return [sheet.get_textpage().get_text_range() for sheet in pdf]


def sheet_with(sheets: list[str], marker: str) -> int:
    return next(index for index, text in enumerate(sheets) if marker in text)


@requires_pdf
class TestOnPaper:
    def test_unkept_the_section_straddles_a_sheet_edge(self):
        """Guards the next test: the lead-in is engineered, not lucky. Retune STRADDLING."""
        sheets = sheets_of(paper(lead_in(STRADDLING), FullWidth(body("K", 4), title="Kept")))
        assert sheet_with(sheets, "KSTART") + 1 == sheet_with(sheets, "KEND")

    def test_kept_it_moves_whole_to_the_next_sheet(self):
        kept = FullWidth(body("K", 4), title="Kept", keep_together=True)
        sheets = sheets_of(paper(lead_in(STRADDLING), kept))
        assert sheet_with(sheets, "KSTART") == sheet_with(sheets, "KEND") == 1

    def test_break_before_starts_a_fresh_sheet_without_a_page(self):
        sheets = sheets_of(paper(lead_in(1), FullWidth(body("B"), break_before=True)))
        assert sheet_with(sheets, "BSTART") == 1
        assert "Lead in" in sheets[0]

    def test_a_page_and_break_before_agree(self):
        by_page = sheets_of(paper(lead_in(1), Page([FullWidth(body("B"))])))
        by_field = sheets_of(paper(lead_in(1), FullWidth(body("B"), break_before=True)))
        assert len(by_page) == len(by_field)
        assert sheet_with(by_page, "BSTART") == sheet_with(by_field, "BSTART")

    def test_a_kept_section_taller_than_a_sheet_warns_and_names_itself(self):
        tall = paper(lead_in(1), FullWidth(body("T", 40), title="Too tall", keep_together=True))
        with pytest.warns(PrintQualityWarning, match="Too tall is kept together but runs over"):
            render_pdf(tall)

    def test_the_warning_names_the_section_paper_shows(self):
        with pytest.warns(PrintQualityWarning, match="^Shown is kept together"):
            render_pdf(hidden_then_shown(body("S", 40)))

    def test_one_that_fits_does_not(self):
        kept = paper(lead_in(STRADDLING), FullWidth(body("K", 4), title="Kept", keep_together=True))
        with warnings.catch_warnings():
            warnings.simplefilter("error", PrintQualityWarning)
            render_pdf(kept)

    def test_the_layout_warns_too(self):
        from pyhermes.pdf import page_count

        tall = paper(FullWidth(body("T", 40), title="Too tall", keep_together=True))
        with pytest.warns(PrintQualityWarning):
            page_count(tall)
