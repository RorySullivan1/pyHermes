"""
An aside the prose wraps round on paper, a callout above it in an email (#343).

The second float a ``TextBlock`` hosts, on ``figure``'s terms; `brochure.md`
has its row in the editorial table and the probe it took.
"""

from __future__ import annotations

import importlib.util

import pytest

from pyhermes.builder import Aside, Callout, Email, FullWidth, ImageBlock, TextBlock
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import EmailImage
from pyhermes.document import PagedDocument
from pyhermes.pdf import available as pdf_available
from qa.fixtures import a4_wide_appendix, all_brochure_fixtures, all_paged_fixtures
from qa.fixtures._png import solid_png

requires_pdf = pytest.mark.skipif(
    not pdf_available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

FACTS = {"firm_name": "F", "campaign_name": "C"}
PROSE = "<p>" + "The curve did the work this quarter. " * 10 + "</p>"


def _aside(**kwargs) -> Aside:
    return Aside("Weight less benchmark weight.", title="Active", **kwargs)


def _email(block: TextBlock) -> str:
    email = Email({**FACTS, "email_subject": "S"}).add_section(FullWidth(content=block))
    return email.render()


def _paged(block: TextBlock) -> str:
    return PagedDocument(FACTS).add_section(FullWidth(content=block)).render()


class TestConstruction:
    def test_it_defaults_to_the_right_and_the_highlight_tint(self):
        aside = Aside("Body.")
        assert (aside.side, aside.title, aside.tone) == ("right", None, None)

    @pytest.mark.parametrize("body", ["", "   "])
    def test_it_needs_a_body(self, body):
        with pytest.raises(ValidationError, match="body"):
            Aside(body)

    def test_a_side_is_left_or_right(self):
        with pytest.raises(ValidationError, match="side"):
            Aside("Body.", side="centre")

    def test_a_tone_is_the_callouts(self):
        with pytest.raises(ValidationError, match="tone"):
            Aside("Body.", tone="Loud!")

    @pytest.mark.parametrize("body", ["See the note.[^1]", "As shown [@jt1993]."])
    def test_a_note_or_a_citation_is_refused(self, body):
        with pytest.raises(ValidationError, match="note or cite"):
            Aside(body)

    def test_a_text_block_takes_only_an_aside(self):
        with pytest.raises(ValidationError, match="takes an Aside"):
            TextBlock(PROSE, aside="Body.")  # type: ignore[arg-type]

    def test_a_text_block_hosts_one_float(self):
        figure = ImageBlock(
            EmailImage.attached(solid_png(80, 80, (1, 2, 3)), alt="x", width=80), wrap="left"
        )
        with pytest.raises(ValidationError, match="one float"):
            TextBlock(PROSE, figure=figure, aside=_aside())


class TestInAnEmail:
    def test_it_is_a_callout_above_the_prose(self):
        html = _email(TextBlock(PROSE, aside=_aside()))
        assert html.index('class="wrapped-aside"') < html.index("The curve did the work")
        assert 'class="callout"' in html
        assert "wrap-right" not in html

    def test_it_is_the_callout_byte_for_byte(self):
        boxed = Callout(TextBlock("<p>Weight less benchmark weight.</p>"), label="Active")
        assert boxed.render(_engine()) in _email(TextBlock(PROSE, aside=_aside()))

    def test_its_copy_is_escaped(self):
        html = _email(TextBlock(PROSE, aside=Aside("A <b>bold</b> & claim.")))
        assert "A &lt;b&gt;bold&lt;/b&gt; &amp; claim." in html

    def test_unset_the_block_is_unchanged(self):
        assert "wrapped-aside" not in _email(TextBlock(PROSE))


def _engine():
    from pyhermes.builder.engine import TemplateEngine
    from pyhermes.email import EMAIL_MEDIUM

    return TemplateEngine().bound(medium=EMAIL_MEDIUM)


class TestOnPaper:
    def test_it_floats_to_its_side_at_a_third_of_the_column(self):
        html = _paged(TextBlock(PROSE, aside=_aside(side="left")))
        assert '<div class="wrapped-aside wrap-left" style="width:192px;">' in html

    def test_a_narrow_column_gives_it_up_to_half(self):
        # A tri-fold inside panel, 356px less its 24px inset a side: 308, half is 154.
        html = all_brochure_fixtures()["tri_fold_letter"]().render()
        assert 'class="wrapped-aside wrap-right" style="width:154px;"' in html

    def test_it_precedes_the_prose_so_the_prose_wraps_round_it(self):
        html = _paged(TextBlock(PROSE, aside=_aside()))
        assert html.index("wrapped-aside") < html.index("The curve did the work")


class TestTheText:
    def test_the_prose_then_the_aside_set_off_by_rules(self):
        text = TextBlock(PROSE, aside=_aside()).text()
        prose, rest = text.split("-" * 10, 1)
        assert "The curve did the work" in prose
        assert "ACTIVE" in rest and "Weight less benchmark weight." in rest
        assert text.rstrip().endswith("-" * 10)


def _found(sheet, phrase: str) -> tuple[float, float, float, float]:
    """``(left, bottom, right, top)`` of the first run of ``phrase`` on ``sheet``, in pt."""
    text = sheet.get_textpage()
    found = text.search(phrase).get_next()
    assert found, f"{phrase!r} is not on the sheet"
    start, count = found
    boxes = [text.get_charbox(n) for n in range(start, start + count)]
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def _lines_beside(sheet, aside_phrase: str, side_of_prose: float) -> None:
    """Some prose line sits level with the aside, and ends short of it."""
    left, bottom, _, top = _found(sheet, aside_phrase)
    textpage = sheet.get_textpage()
    rows = [
        textpage.get_charbox(n)
        for n in range(textpage.count_chars())
        if textpage.get_charbox(n)[2] < left and bottom <= textpage.get_charbox(n)[1] <= top
    ]
    assert rows, "no prose sits beside the aside"
    assert max(r[2] for r in rows) < left
    assert min(r[0] for r in rows) == pytest.approx(side_of_prose, abs=40)


@requires_pdf
class TestTheProseWrapsRoundIt:
    def test_in_a_paged_column(self):
        import pypdfium2

        from pyhermes.pdf import render_pdf

        document = all_paged_fixtures()["a4_wide_appendix"]()
        sheet = next(
            s
            for s in pypdfium2.PdfDocument(render_pdf(document))
            if a4_wide_appendix.SUMMARY in s.get_textpage().get_text_range()
        )
        frame_left = 76 * 72 / 96
        _lines_beside(sheet, "The holding", frame_left)

    def test_inside_a_brochure_panels_fixed_box(self):
        import pypdfium2

        from pyhermes.brochure import overflowing_panels
        from pyhermes.pdf import render_pdf

        brochure = all_brochure_fixtures()["tri_fold_letter"]()
        assert overflowing_panels(brochure) == []
        sheet = next(
            s
            for s in pypdfium2.PdfDocument(render_pdf(brochure))
            if "Two-year" in s.get_textpage().get_text_range()
        )
        left, _, _, _ = _found(sheet, "Two-year")
        prose_left, _, prose_right, _ = _found(sheet, "repriced")
        assert prose_right < left
        assert prose_left < left
