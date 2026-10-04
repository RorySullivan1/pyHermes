"""
The deck layouts (#346): a slide's source, its pictures, the statement slide, the
divider's agenda, the handout and the footer's counter and mark.

What the markup and the projections can answer runs everywhere; what needs a
layout, or the PDF read back, skips without ``[pdf]`` and ``[qa]``.
"""

from __future__ import annotations

import importlib.util
import warnings

import pytest

from pyhermes.builder import (
    Bibliography,
    Contents,
    DataTable,
    Email,
    FullWidth,
    HeroStat,
    TextBlock,
)
from pyhermes.builder.exceptions import PrintQualityWarning, ValidationError
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import TableRow
from pyhermes.builder.research import Reference
from pyhermes.builder.sizing import A4_PORTRAIT, resolve_size_scheme
from pyhermes.builder.theming import DEFAULT_THEME
from pyhermes.deck import (
    SLIDE_16_9,
    Deck,
    DeckFooter,
    DividerSlide,
    EmptyClosingSlide,
    EmptyTitleSlide,
    Slide,
    SlideBox,
    StatementSlide,
    overflowing_slides,
)
from pyhermes.pdf import available
from qa.fixtures import all_deck_fixtures, pitch_layouts_16_9
from qa.fixtures._png import solid_png

FACTS = {
    "firm_name": "Hermes Research",
    "campaign_name": "Quarterly Review",
    "header_disclaimer": "<p>Not investment advice.</p>",
}
EMAIL_FACTS = {**FACTS, "email_subject": "Quarterly Review"}

needs_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='the deck layout PDF tests need the "[pdf]" and "[qa]" extras',
)

BLEED = solid_png(1280, 720, (28, 42, 58))
HALF = solid_png(640, 720, (91, 138, 154))
REFERENCE = Reference("boe2026", ["Bank of England"], 2026, "Monetary Policy Report")


def _bare(**options) -> Deck:
    """A deck of slides alone, so sheet N is slide N."""
    return Deck(FACTS, title_slide=EmptyTitleSlide(), closing_slide=EmptyClosingSlide(), **options)


def _paragraph(marker: str = "One short paragraph") -> list:
    return [FullWidth(content=TextBlock(f"<p>{marker}.</p>"))]


def _long_table() -> list:
    rows = [TableRow([f"Bond {n:02d}", f"{n / 10:.1f}"]) for n in range(1, 41)]
    return [FullWidth(content=DataTable(["Issue", "Weight"], rows))]


def _sheets(pdf_bytes: bytes) -> list[str]:
    import pypdfium2

    return [page.get_textpage().get_text_range() for page in pypdfium2.PdfDocument(pdf_bytes)]


def _top(pdf_bytes: bytes, sheet: int, text: str) -> float:
    """How far from the foot of ``sheet`` the first ``text`` on it sits, in pt."""
    import pypdfium2

    textpage = pypdfium2.PdfDocument(pdf_bytes)[sheet].get_textpage()
    found = textpage.search(text).get_next()
    assert found, f"{text!r} is not on sheet {sheet + 1}"
    return float(textpage.get_charbox(found[0])[3])


def _deck_sheets(deck: Deck) -> list[str]:
    from pyhermes.pdf import render_pdf

    return _sheets(render_pdf(deck))


# ----------------------------------------------------------------------
# #347 — a slide's source line
# ----------------------------------------------------------------------


class TestASlidesSource:
    def test_the_band_is_one_micro_line_and_the_gap_taken_from_the_body(self):
        scheme = resolve_size_scheme("presentation").with_page(SLIDE_16_9)
        box = SlideBox.of(scheme)
        sourced = box.with_source(scheme)
        assert sourced.source_line > 0
        assert sourced.source_height == sourced.source_line + scheme.space.caption_gap
        assert sourced.body_bottom == box.body_bottom - sourced.source_height
        assert sourced.source_top == sourced.body_bottom
        assert sourced.footer_top == box.footer_top

    def test_it_is_drawn_only_when_set(self):
        deck = _bare().add_slide(_paragraph(), "Plain")
        assert "slide-source-band" not in deck.render()
        deck.add_slide(_paragraph(), "Sourced", source="Hermes Research", as_of="1 May")
        html = deck.render()
        assert html.count("slide-source-band") == 1
        assert "Hermes Research as of 1 May" in html

    def test_a_footnote_is_refused_and_a_date_needs_a_source(self):
        with pytest.raises(ValidationError, match="calls a footnote"):
            Slide(_paragraph(), "T", source="Hermes [^1]")
        with pytest.raises(ValidationError, match="no source to date"):
            Slide(_paragraph(), "T", as_of="1 May")

    def test_a_citation_resolves_against_a_bibliography_on_a_later_slide(self):
        deck = _bare().add_slide(_paragraph(), "Sourced", source="BoE [@boe2026]")
        deck.add_slide([FullWidth(content=Bibliography([REFERENCE]))], "References")
        assert 'href="#ref-boe2026"' in deck.render()
        assert "BoE (Bank of England 2026)" in deck.text()

    def test_a_citation_no_bibliography_lists_names_the_slide(self):
        deck = _bare().add_slide(_paragraph(), "Sourced", source="BoE [@nobody]")
        with pytest.raises(ValidationError, match="the slide titled 'Sourced' cites"):
            deck.render()

    def test_the_text_part_puts_it_under_the_slides_sections(self):
        slide = Slide(_paragraph("Body"), "T", source="Hermes", as_of="1 May")
        assert slide.text().endswith("Body.\n\nHermes as of 1 May")


# ----------------------------------------------------------------------
# #348 — pictures on a slide
# ----------------------------------------------------------------------


class TestAPictureOnASlide:
    def test_a_full_bleed_slide_needs_a_tone_and_an_attached_picture(self):
        with pytest.raises(ValidationError, match="needs ground="):
            Slide(_paragraph(), "T", background_image=EmailImage.attached(BLEED, alt="x"))
        with pytest.raises(ValidationError, match="names a ground but"):
            Slide(_paragraph(), "T", ground="dark")
        hosted = EmailImage.hosted("https://example.com/a.png", alt="x", width=640)
        with pytest.raises(ValidationError, match="fetches nothing"):
            Slide(_paragraph(), "T", image=hosted)

    def test_one_picture_a_slide_and_no_layout_beside_one(self):
        picture = EmailImage.attached(HALF, alt="x")
        with pytest.raises(ValidationError, match="one picture a slide"):
            Slide(
                _paragraph(),
                "T",
                image=picture,
                background_image=EmailImage.attached(BLEED, alt="y"),
                ground="dark",
            )
        with pytest.raises(ValidationError, match="beside a picture"):
            Slide(_paragraph(), "T", image=picture, layout="split", side=_paragraph())
        with pytest.raises(ValidationError, match="image_side"):
            Slide(_paragraph(), "T", image=picture, image_side="top")

    def test_a_picture_too_coarse_for_the_sheet_warns_then_raises(self):
        coarse = EmailImage.attached(solid_png(500, 360, (0, 0, 0)), alt="Coarse")
        with pytest.warns(PrintQualityWarning, match="needs 640px"):
            _bare().add_slide(_paragraph(), "T", image=coarse)
        tiny = EmailImage.attached(solid_png(300, 360, (0, 0, 0)), alt="Tiny")
        deck = _bare()
        with pytest.raises(ValidationError, match="'Tiny' is 300px wide"):
            deck.add_slide(_paragraph(), "T", image=tiny)
        assert deck.slides == []

    def test_a_dark_ground_sets_the_title_light_and_clears_the_sections(self):
        deck = _bare().add_slide(
            _paragraph(),
            "Dark",
            background_image=EmailImage.attached(BLEED, alt="x"),
            ground="dark",
        )
        html = deck.render()
        title = html.split('class="slide-title"')[1].split(">")[0]
        assert f"color:{DEFAULT_THEME.text.on_dark};" in title
        assert "slide-imaged" in html
        assert ".slide-imaged table" in html

    def test_a_picture_beside_the_copy_takes_half_the_sheet(self):
        deck = _bare().add_slide(_paragraph(), "Left", image=EmailImage.attached(HALF, alt="Floor"))
        html = deck.render()
        assert 'alt="Floor" width="640" height="720"' in html
        body = html.split('class="slide-body"')[1].split(">")[0]
        assert "left:640px; width:640px;" in body

    def test_both_pictures_reach_the_manifest_ahead_of_the_sections(self):
        deck = pitch_layouts_16_9.build()
        picture_slides = [s for s in deck.slides if s.own_images()]
        assert len(picture_slides) == 3
        cids = {asset.content_id for asset in deck.assets()}
        for slide in picture_slides:
            assert slide.own_images()[0].asset.content_id in cids

    def test_elsewhere_a_slide_flattens_and_draws_no_picture(self):
        picture = EmailImage.attached(HALF, alt="Floor")
        email = Email(EMAIL_FACTS).add_section(
            Slide(_paragraph("Flat"), "T", image=picture, source="ZEBRASOURCE")
        )
        html = email.render()
        assert "Flat." in html
        assert picture.src not in html
        assert "ZEBRASOURCE" not in html


# ----------------------------------------------------------------------
# #349 — the statement slide
# ----------------------------------------------------------------------


STAT = HeroStat("38 bps", "2s10s", "The steepest curve since 2022")


class TestAStatementSlide:
    def test_it_takes_one_hero_stat(self):
        with pytest.raises(ValidationError, match="one HeroStat"):
            StatementSlide(TextBlock("<p>x</p>"))

    def test_it_has_no_title_band_and_centres_the_figure(self):
        deck = _bare().add_statement(STAT, "The lead figure", notes="Pause.")
        html = deck.render()
        assert 'class="slide-title"' not in html
        assert "vertical-align:middle;" in html.split("statement")[1]
        assert 'id="the-lead-figure"' in html

    def test_a_titled_statement_is_listed_by_an_agenda(self):
        deck = _bare().add_slide([FullWidth(content=Contents())], "Agenda")
        deck.add_statement(STAT, "The lead figure")
        assert 'href="#the-lead-figure"' in deck.render()

    def test_the_text_part_prints_the_stats_projection_under_its_title(self):
        deck = _bare().add_statement(STAT, "The lead figure")
        assert "The lead figure\n---------------\n\n" + STAT.text() in deck.text()

    def test_its_number_agrees_with_the_notes(self):
        deck = _bare().add_slide(_paragraph(), "One").add_statement(STAT, "Two", notes="Beat.")
        assert deck.notes().startswith("Slide 2: Two")
        assert 'data-slide="2"' in deck.render().split("statement")[1][:40]

    def test_in_an_email_it_is_the_figure(self):
        html = Email(EMAIL_FACTS).add_section(StatementSlide(STAT, "Lead")).render()
        assert "38 bps" in html


# ----------------------------------------------------------------------
# #350 and #352 — the divider's agenda, and the footer
# ----------------------------------------------------------------------


class TestTheDividersAgenda:
    def test_each_divider_lists_every_part_the_current_one_marked(self):
        deck = _bare(divider_agenda=True)
        deck.add_divider("One").add_slide(_paragraph(), "A").add_divider("Two")
        sheets = deck.render().split('class="sheet ')[1:]
        dividers = [sheet for sheet in sheets if sheet.startswith("slide divider")]
        assert len(dividers) == 2
        light, muted = DEFAULT_THEME.text.on_dark, DEFAULT_THEME.text.on_dark_muted
        for current, sheet in zip(("One", "Two"), dividers, strict=True):
            for part, number in (("One", 1), ("Two", 3)):
                ink = light if part == current else muted
                entry = f'<span style="float:right;">{number}</span>{part}</p>'
                assert f'color:{ink};">{entry}' in sheet

    def test_off_by_default(self):
        assert "divider-agenda" not in _bare().add_divider("One").render()


class TestTheFooter:
    def test_the_counter_and_the_mark_are_validated(self):
        with pytest.raises(ValidationError, match="counter"):
            DeckFooter(counter="roman")
        with pytest.raises(ValidationError, match="DeckFooter"):
            Deck(FACTS, footer={"counter": "total"})

    def test_the_default_prints_the_bare_number(self):
        assert DeckFooter().count(4, 12) == "4"
        assert DeckFooter(counter="total").count(4, 12) == "4 / 12"

    def test_the_mark_is_on_every_banded_sheet_and_never_the_title_slide(self):
        deck = Deck(FACTS, footer=DeckFooter(counter="total", label="Private"))
        deck.add_slide(_paragraph(), "One").add_divider("Part").add_statement(STAT)
        html = deck.render()
        assert html.count("slide-footer-mark") == 4
        assert "Private" not in html.split('class="sheet slide')[0]
        for number in range(2, 6):
            assert f'"float:right;">{number} / 5</span>' in html


# ----------------------------------------------------------------------
# #353 — the fixture
# ----------------------------------------------------------------------


class TestTheLayoutsFixture:
    def test_it_is_a_deck_fixture(self):
        assert "pitch_layouts_16_9" in all_deck_fixtures()

    def test_every_new_field_is_set_away_from_its_default(self):
        deck = pitch_layouts_16_9.build()
        slides = deck.slides
        for name in ("source", "as_of", "background_image", "ground", "image"):
            assert any(getattr(slide, name, None) for slide in slides), name
        assert {s.image_side for s in slides if s.image} == {"left", "right"}
        assert any(isinstance(s, StatementSlide) for s in slides)
        assert deck.divider_agenda
        assert deck.footer == DeckFooter(counter="total", label=pitch_layouts_16_9.MARK)
        assert sum(isinstance(s, DividerSlide) for s in slides) == 2

    def test_the_notes_sentinel_is_in_the_notes_alone(self):
        deck = pitch_layouts_16_9.build()
        assert "ZEBRANOTES7" in deck.notes()
        assert "ZEBRANOTES7" not in deck.render()
        assert "ZEBRANOTES7" not in deck.text()


# ----------------------------------------------------------------------
# On paper
# ----------------------------------------------------------------------


@needs_pdf
class TestOnPaper:
    def test_every_layout_fits(self):
        assert overflowing_slides(pitch_layouts_16_9.build()) == []

    def test_a_body_running_into_the_source_band_is_named(self):
        deck = pitch_layouts_16_9.build()
        sourced = next(slide for slide in deck.slides if slide.source)
        sourced.sections.append(_long_table()[0])
        assert overflowing_slides(deck) == [f"slide {deck.number(sourced)}: Sourced figures"]

    def test_a_body_overflowing_beside_a_picture_is_named(self):
        deck = _bare().add_slide(_long_table(), "Beside", image=EmailImage.attached(HALF, alt="x"))
        assert overflowing_slides(deck) == ["slide 1: Beside"]

    def test_a_source_that_wraps_is_named(self):
        deck = _bare().add_slide(_paragraph(), "Long", source="A source. " * 40)
        assert overflowing_slides(deck) == ["slide 1: Long (its source wraps)"]

    def test_the_source_sits_between_the_body_and_the_footer_band(self):
        from pyhermes.pdf import anchor_tops

        deck = _bare().add_slide(_paragraph(), "Sourced", source="Hermes Research")
        box = deck.slide_box(deck.slides[0])
        top = anchor_tops(deck)["slide-1-source-end"]
        assert box.body_bottom <= top < box.footer_top
        assert "Hermes Research" in _deck_sheets(deck)[0]

    def test_each_footer_reads_n_of_the_total_and_carries_the_mark(self):
        deck = pitch_layouts_16_9.build()
        sheets = _deck_sheets(deck)
        total = len(sheets)
        assert total == deck.sheet_count() == len(deck.slides) + 2
        assert pitch_layouts_16_9.MARK not in sheets[0]
        for number, sheet in enumerate(sheets[1:], start=2):
            assert sheet.rstrip().endswith(f"{number} / {total}"), sheet
            assert pitch_layouts_16_9.MARK in sheet

    def test_every_divider_lists_every_part_at_its_first_sheet(self):
        from pyhermes.pdf import render_pdf

        deck = pitch_layouts_16_9.build()
        pdf = render_pdf(deck)
        sheets = _sheets(pdf)
        dividers = [slide for slide in deck.slides if isinstance(slide, DividerSlide)]
        for divider in dividers:
            index = deck.number(divider) - 1
            lines = sheets[index].splitlines()
            # The number floats right, so it is extracted before its part; each
            # pair is read back by the height it is set at instead.
            for part in dividers:
                assert lines.count(part.title) >= 1 and str(deck.number(part)) in lines
            heights = [_top(pdf, index, str(deck.number(part))) for part in dividers]
            assert heights == sorted(heights, reverse=True)

    def test_the_statement_slide_prints_its_figure_and_not_its_title(self):
        deck = pitch_layouts_16_9.build()
        statement = next(s for s in deck.slides if isinstance(s, StatementSlide))
        sheet = _deck_sheets(deck)[deck.number(statement) - 1]
        assert "38 bps" in sheet
        assert "The lead figure" not in sheet


@needs_pdf
class TestTheHandout:
    def _handout(self, deck: Deck, **kwargs) -> bytes:
        from pyhermes.pdf import render_handout

        return render_handout(deck, **kwargs)

    def test_one_sheet_a_slide_and_region_each_with_its_slides_notes(self):
        deck = pitch_layouts_16_9.build()
        pdf = self._handout(deck)
        pages = _sheets(pdf)
        assert len(pages) == deck.sheet_count()
        for slide in deck.slides:
            index = deck.number(slide) - 1
            if slide.title and slide.TITLE_BAND:
                assert slide.title in pages[index]
            for paragraph in filter(None, slide.notes.split("\n\n")):
                assert paragraph in " ".join(pages[index].split())

    def test_the_slide_sits_above_its_notes(self):
        deck = pitch_layouts_16_9.build()
        pdf = self._handout(deck)
        statement = next(s for s in deck.slides if isinstance(s, StatementSlide))
        index = deck.number(statement) - 1
        assert _top(pdf, index, STAT.value) > _top(pdf, index, "Let the number sit")

    def test_the_notes_sentinel_reaches_the_handout(self):
        pages = _sheets(self._handout(pitch_layouts_16_9.build()))
        assert any("ZEBRANOTES7" in page for page in pages)

    def test_a_sheet_is_laid_out_exactly_as_the_slide(self):
        deck = pitch_layouts_16_9.build()
        handout = deck.handout()
        assert all(sheet in handout for sheet in deck._sheets(deck._bound_engine()))
        width = A4_PORTRAIT.width - A4_PORTRAIT.margin.left - A4_PORTRAIT.margin.right
        assert f"transform:scale({round(width / 1280, 6)})" in handout

    def test_a_handout_page_needs_a_height(self):
        from pyhermes.builder.sizing import DEFAULT_PAGE

        with pytest.raises(ValidationError, match="give its page a height"):
            pitch_layouts_16_9.build().handout(DEFAULT_PAGE)

    def test_two_handouts_of_one_deck_are_byte_identical(self):
        # Needs HarfBuzz-Subset, as every determinism test does: CI's pdf job has it.
        deck = pitch_layouts_16_9.build()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert self._handout(deck) == self._handout(deck)
