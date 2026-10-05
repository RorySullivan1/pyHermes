"""
A status stamp, DRAFT or CONFIDENTIAL, on every sheet (#342).

A fact on ``DocumentMetadata``, so every medium reads it: paper sets it across
each sheet, an email in its header strip, and the text part opens on it.
"""

from __future__ import annotations

import dataclasses
import importlib.util

import pytest

from pyhermes.builder import Email, FullWidth, TextBlock
from pyhermes.builder.document import stamp_type
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.models import STAMP_MAX, DocumentMetadata
from pyhermes.builder.regions import EmptyHeader
from pyhermes.builder.sizing import A4_PORTRAIT, SLIDE_16_9, STANDARD_SIZES
from pyhermes.document import PagedDocument
from pyhermes.pdf import available as pdf_available
from qa.fixtures import all_brochure_fixtures, all_deck_fixtures, all_paged_fixtures

requires_pdf = pytest.mark.skipif(
    not pdf_available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

FACTS = {"firm_name": "F", "campaign_name": "C"}


def _stamped(document, stamp: str):
    """``document`` with its facts restamped, for media whose fixtures carry none."""
    document._metadata = dataclasses.replace(document._metadata, stamp=stamp)
    return document


def _email(stamp: str = "DRAFT", **regions) -> Email:
    email = Email({**FACTS, "email_subject": "S", "stamp": stamp}, **regions)
    return email.add_section(FullWidth(content=TextBlock("<p>Body.</p>")))


class TestTheFact:
    def test_it_is_empty_by_default(self):
        assert DocumentMetadata().stamp == ""

    @pytest.mark.parametrize("stamp", ["DRAFT", "CONFIDENTIAL", "X" * STAMP_MAX, "Draft 2"])
    def test_one_short_line_is_accepted(self, stamp):
        assert DocumentMetadata(stamp=stamp).stamp == stamp

    @pytest.mark.parametrize("stamp", ["X" * (STAMP_MAX + 1), "DRAFT\nTWO", "   ", "\tDRAFT"])
    def test_anything_else_is_refused_at_construction(self, stamp):
        with pytest.raises(ValidationError, match="stamp"):
            DocumentMetadata(stamp=stamp)

    def test_a_non_string_is_refused(self):
        with pytest.raises(ValidationError, match="stamp"):
            DocumentMetadata(stamp=1)  # type: ignore[arg-type]


class TestTheGeometry:
    def test_a_short_word_takes_a_fifth_of_the_short_side(self):
        sized = stamp_type("DRAFT", STANDARD_SIZES.with_page(A4_PORTRAIT).frame)
        assert sized["px"] == round(0.2 * A4_PORTRAIT.width)
        assert sized["angle"] == 55

    def test_a_long_word_shrinks_to_fit_the_diagonal(self):
        frame = STANDARD_SIZES.with_page(SLIDE_16_9).frame
        assert stamp_type("X" * STAMP_MAX, frame)["px"] < stamp_type("DRAFT", frame)["px"]
        assert stamp_type("DRAFT", frame)["angle"] == 29


class TestInAnEmail:
    def test_it_is_the_header_strips_first_line(self):
        email = Email(
            {**FACTS, "email_subject": "S", "stamp": "DRAFT", "header_disclaimer": "Fine print."}
        ).add_section(FullWidth(content=TextBlock("<p>Body.</p>")))
        strip = email.render().split("HEADER: Disclaimer bar", 1)[1]
        assert ">DRAFT</div>" in strip
        assert strip.index(">DRAFT</div>") < strip.index("Fine print.")

    def test_it_is_escaped(self):
        assert "A&lt;B" in _email("A<B").render()

    def test_the_text_part_opens_on_it(self):
        assert _email().text().startswith("[DRAFT]\n")

    def test_an_empty_header_would_drop_it_so_it_is_refused(self):
        with pytest.raises(ValidationError, match="EmptyHeader"):
            _email(header=EmptyHeader()).render()

    def test_unset_neither_part_mentions_it(self):
        email = _email("")
        assert "letter-spacing:2px" not in email.render()
        assert not email.text().startswith("[")

    def test_no_sheet_stamp_reaches_an_email(self):
        assert "sheet-stamp" not in _email().render()


class TestOnPaperMarkup:
    @pytest.mark.parametrize(
        "document",
        [
            lambda: all_paged_fixtures()["a4_wide_appendix"](),
            lambda: _stamped(all_brochure_fixtures()["tri_fold_letter"](), "DRAFT"),
            lambda: _stamped(all_deck_fixtures()["pitch_16_9"](), "DRAFT"),
        ],
        ids=["paged", "brochure", "deck"],
    )
    def test_each_paper_skeleton_sets_it_once_in_the_rule_colour(self, document):
        html = document().render()
        assert html.count('class="sheet-stamp"') == 1
        assert ">DRAFT</div>" in html

    def test_the_text_part_opens_on_it_on_paper_too(self):
        assert all_paged_fixtures()["a4_wide_appendix"]().text().startswith("[DRAFT]\n")

    def test_unset_no_skeleton_carries_it(self):
        html = PagedDocument(FACTS).add_section(FullWidth(content=TextBlock("<p>x</p>"))).render()
        assert "sheet-stamp" not in html


def _sheets(document):
    import pypdfium2

    from pyhermes.pdf import render_pdf

    return [s.get_textpage().get_text_range() for s in pypdfium2.PdfDocument(render_pdf(document))]


@requires_pdf
class TestOnEverySheet:
    @pytest.mark.parametrize(
        "document, stamp",
        [
            (lambda: all_paged_fixtures()["a4_wide_appendix"](), "DRAFT"),
            (lambda: _stamped(all_brochure_fixtures()["tri_fold_letter"](), "DRAFT"), "DRAFT"),
            (lambda: all_deck_fixtures()["pitch_16_9"](), "CONFIDENTIAL"),
        ],
        ids=["paged", "brochure", "deck"],
    )
    def test_every_sheet_carries_it(self, document, stamp):
        sheets = _sheets(document())
        assert len(sheets) > 1
        assert all(stamp in text for text in sheets)

    @pytest.mark.parametrize(
        "document, stamp",
        [
            (lambda: all_paged_fixtures()["a4_wide_appendix"](), "DRAFT"),
            (lambda: all_deck_fixtures()["pitch_16_9"](), "CONFIDENTIAL"),
        ],
        ids=["paged", "deck"],
    )
    def test_it_sits_at_the_centre_of_each_sheet(self, document, stamp):
        # Read off the glyphs' boxes, so a cover, a turned sheet and a slide each count.
        import pypdfium2

        from pyhermes.pdf import render_pdf

        for sheet in pypdfium2.PdfDocument(render_pdf(document())):
            text = sheet.get_textpage()
            found = text.search(stamp).get_next()
            assert found, "the stamp is missing from a sheet"
            start, count = found
            boxes = [text.get_charbox(n) for n in range(start, start + count)]
            centre_x = (min(b[0] for b in boxes) + max(b[2] for b in boxes)) / 2
            centre_y = (min(b[1] for b in boxes) + max(b[3] for b in boxes)) / 2
            width, height = sheet.get_size()
            assert centre_x == pytest.approx(width / 2, abs=6)
            assert centre_y == pytest.approx(height / 2, abs=6)
