"""
A deck on paper (#218): one slide to a sheet, read back from the PDF, and overflow measured.

Needs ``[pdf]`` and ``[qa]``, and skips without either. Text is read back from
the PDF by pypdfium2, one sheet at a time.
"""

from __future__ import annotations

import importlib.util
import textwrap

import pytest

from pyhermes.builder import DataTable, FullWidth, TextBlock
from pyhermes.builder.models import TableRow
from pyhermes.deck import (
    SLIDE_4_3,
    SLIDE_16_9,
    Deck,
    EmptyClosingSlide,
    EmptyTitleSlide,
    overflowing_slides,
)
from pyhermes.pdf import available, page_count, render_pdf
from qa.fixtures import pitch_16_9

pytestmark = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='the deck PDF tests need the "[pdf]" and "[qa]" extras',
)

FACTS = {
    "firm_name": "Hermes Research",
    "campaign_name": "Quarterly Review",
    "header_disclaimer": "<p>Not investment advice.</p>",
}


def _sheets(document) -> list[str]:
    """Each sheet's text, in order."""
    import pypdfium2

    pdf = pypdfium2.PdfDocument(render_pdf(document))
    return [page.get_textpage().get_text_range() for page in pdf]


def _bare(page=SLIDE_16_9) -> Deck:
    return Deck(FACTS, page=page, title_slide=EmptyTitleSlide(), closing_slide=EmptyClosingSlide())


def _paragraph(marker: str = "One short paragraph") -> list:
    return [FullWidth(content=TextBlock(f"<p>{marker}.</p>"))]


def _long_table() -> list:
    rows = [TableRow([f"Bond {n:02d}", f"{n / 10:.1f}"]) for n in range(1, 41)]
    return [FullWidth(content=DataTable(["Issue", "Weight"], rows))]


class TestOneSlideIsOneSheet:
    @pytest.mark.parametrize("page", [SLIDE_16_9, SLIDE_4_3], ids=["16:9", "4:3"])
    def test_three_slides_are_three_sheets_however_short(self, page):
        deck = _bare(page)
        for title in ("Alpha", "Beta", "Gamma"):
            deck.add_slide(_paragraph("x"), title)
        assert page_count(deck) == 3

    @pytest.mark.parametrize("page", [SLIDE_16_9, SLIDE_4_3], ids=["16:9", "4:3"])
    def test_an_overfull_slide_is_still_one_sheet(self, page):
        deck = _bare(page).add_slide(_long_table(), "Too much").add_slide(_paragraph(), "After")
        assert page_count(deck) == 2

    def test_each_sheet_carries_its_slides_title_and_number(self):
        deck = _bare()
        for title in ("Alpha", "Beta", "Gamma"):
            deck.add_slide(_paragraph(), title)
        for number, (title, sheet) in enumerate(
            zip(("Alpha", "Beta", "Gamma"), _sheets(deck), strict=True), 1
        ):
            assert title in sheet
            assert sheet.rstrip().endswith(str(number)), sheet

    def test_the_fixture_is_one_sheet_a_slide_plus_the_two_regions(self):
        deck = pitch_16_9.build()
        sheets = _sheets(deck)
        assert len(sheets) == len(deck.slides) + 2
        assert "Rates, Projected" in sheets[0]
        assert "Important information" in sheets[-1]
        for slide, sheet in zip(deck.slides, sheets[1:-1], strict=True):
            assert slide.title in sheet
            assert str(deck.number(slide)) in sheet.split()[-1]

    def test_the_notes_never_reach_the_pdf(self):
        assert not any("ZEBRANOTES7" in sheet for sheet in _sheets(pitch_16_9.build()))

    def test_the_agenda_prints_each_entrys_sheet_as_the_footer_counts_it(self):
        deck = pitch_16_9.build()
        agenda = _sheets(deck)[1]
        for slide in deck.slides[1:]:
            if slide.title:
                line = next(line for line in agenda.splitlines() if slide.title in line)
                assert line.rstrip().endswith(str(deck.number(slide))), line


class TestOverflowIsNamed:
    def test_a_forty_row_table_is_named_and_a_paragraph_is_not(self):
        deck = _bare().add_slide(_paragraph(), "Fits").add_slide(_long_table(), "Too much")
        assert overflowing_slides(deck) == ["slide 2: Too much"]

    def test_an_untitled_slide_is_named_by_number(self):
        assert overflowing_slides(_bare().add_slide(_long_table())) == ["slide 1"]

    def test_long_disclosures_are_named_too(self):
        deck = Deck({**FACTS, "header_disclaimer": "<p>Read this.</p>" * 120})
        deck.add_slide(_paragraph(), "Fits")
        assert overflowing_slides(deck) == ["slide 3: Disclosures"]


class TestTheFixtureIsEngineeredRatherThanLucky:
    """The deck fixture fits by design, and a perturbation of one slide is seen."""

    def test_every_slide_fits(self):
        assert overflowing_slides(pitch_16_9.build()) == []

    def test_one_overfull_slide_is_named(self):
        deck = pitch_16_9.build()
        deck.slides[3].sections.append(_long_table()[0])
        assert overflowing_slides(deck) == ["slide 5: Curve by tenor"]


class TestATitleThatWrapsIsNamed:
    """#316: the title band holds one line, and a second one used to paint over the body."""

    LONG = (
        "A slide title long enough that it cannot possibly fit on one line of a "
        "sixteen by nine slide at the presentation density"
    )

    def test_a_wrapping_title_is_named(self):
        deck = _bare().add_slide(_paragraph(), self.LONG)
        assert overflowing_slides(deck) == [f"slide 1: {self.LONG} (its title wraps)"]

    def test_a_one_line_title_is_not(self):
        assert overflowing_slides(_bare().add_slide(_paragraph(), "Short")) == []

    def test_a_wrapping_title_and_an_overfull_body_are_one_entry(self):
        deck = _bare().add_slide(_long_table(), self.LONG)
        assert overflowing_slides(deck) == [
            f"slide 1: {self.LONG} (its title wraps, and its body overflows)"
        ]

    def test_the_band_clips_the_second_line(self):
        html = _bare().add_slide(_paragraph(), self.LONG).render()
        assert ".slide-title-band { overflow: hidden; }" in html


class TestADeckThatCannotBeLaidOutIsAFinding:
    """#315: any PdfError other than a missing backend escaped the check as a traceback."""

    @staticmethod
    def _hosted_logo_deck() -> Deck:
        from pyhermes.deck import TitleSlide

        deck = Deck(FACTS, title_slide=TitleSlide(logo_url="https://example.com/logo.png"))
        return deck.add_slide(_paragraph(), "One")

    def test_lint_document_reports_it_and_does_not_raise(self):
        from qa.lint import Severity, lint_document

        findings = [
            f for f in lint_document(self._hosted_logo_deck()) if f.rule_id == "slide-overflow"
        ]
        assert [f.severity for f in findings] == [Severity.ERROR]
        assert "not measured" in findings[0].message
        assert "https://example.com/logo.png" in findings[0].message

    def test_the_check_prints_the_finding_and_exits_with_a_lint_code(self, tmp_path, capsys):
        from pyhermes.check.__main__ import EXIT_LINT_ERRORS, main

        draft = tmp_path / "deck.py"
        draft.write_text(
            textwrap.dedent(
                """
                from pyhermes.builder import FullWidth, TextBlock
                from pyhermes.deck import Deck, TitleSlide

                def build():
                    logo = TitleSlide(logo_url="https://example.com/logo.png")
                    deck = Deck({"firm_name": "F", "campaign_name": "C"}, title_slide=logo)
                    return deck.add_slide([FullWidth(content=TextBlock("x"))], "One")
                """
            )
        )
        assert main([f"{draft}:build", "--out", str(tmp_path / "out")]) == EXIT_LINT_ERRORS
        assert "slide-overflow at whole deck" in capsys.readouterr().out

    def test_preview_writes_both_parts_and_skips_the_pdf(self, tmp_path, capsys):
        from qa.preview import EXIT_LINT_ERRORS, main

        draft = tmp_path / "deck.py"
        draft.write_text(
            "from pyhermes.builder import FullWidth, TextBlock\n"
            "from pyhermes.deck import Deck, TitleSlide\n\n"
            "def build():\n"
            '    logo = TitleSlide(logo_url="https://example.com/logo.png")\n'
            '    deck = Deck({"firm_name": "F", "campaign_name": "C"}, title_slide=logo)\n'
            '    return deck.add_slide([FullWidth(content=TextBlock("x"))], "One")\n'
        )
        out = tmp_path / "out"
        assert main([f"{draft}:build", "--lint", "--out", str(out)]) == EXIT_LINT_ERRORS
        assert (out / "deck-build.html").is_file() and (out / "deck-build.txt").is_file()
        assert "pdf skipped" in capsys.readouterr().err


class TestTheCheckExitsOnOverflow:
    def test_an_overflowing_deck_exits_1_and_names_the_slide(self, tmp_path, capsys):
        from pyhermes.check.__main__ import EXIT_LINT_ERRORS, main

        draft = tmp_path / "deck.py"
        draft.write_text(
            textwrap.dedent(
                """
                from pyhermes.builder import DataTable, FullWidth
                from pyhermes.builder.models import TableRow
                from pyhermes.deck import Deck

                def build():
                    rows = [TableRow([str(n), str(n)]) for n in range(40)]
                    deck = Deck({"firm_name": "F", "campaign_name": "C"})
                    return deck.add_slide([FullWidth(content=DataTable(["A", "B"], rows))], "Full")
                """
            )
        )
        assert main([f"{draft}:build", "--out", str(tmp_path / "out")]) == EXIT_LINT_ERRORS
        assert "slide-overflow at slide 2: Full" in capsys.readouterr().out

    def test_a_deck_that_fits_exits_0(self, tmp_path):
        from pyhermes.check.__main__ import EXIT_OK, main

        draft = tmp_path / "deck.py"
        draft.write_text(
            "from qa.fixtures import pitch_16_9\n\ndef build():\n    return pitch_16_9.build()\n"
        )
        assert main([f"{draft}:build", "--out", str(tmp_path / "out")]) == EXIT_OK
