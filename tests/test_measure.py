"""
A prose block's measure (#358): the medium owns the default, written only where it bites.

Two tokens in ``ch``, ``measure_standard`` and ``measure_narrow``, written as
px from the density's body size. Paper, the brochure and the deck default to
``standard`` and an email to none; ``TextBlock(measure=)`` overrides either,
``full`` turning it off. The cap is written only on a cell wider than it.
"""

from __future__ import annotations

import importlib.util
import math

import pytest

from pyhermes.brochure.medium import BROCHURE_MEDIUM
from pyhermes.builder import (
    Email,
    FlowedColumns,
    FullWidth,
    TextBlock,
    TwoColumn,
    ValidationError,
)
from pyhermes.builder.medium import DEFAULT_MEDIUM
from pyhermes.builder.sizing import (
    CH_EM,
    MEASURES,
    PRESENTATION_SIZES,
    STANDARD_SIZES,
    measure_px,
)
from pyhermes.deck.medium import DECK_MEDIUM
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument
from pyhermes.document.medium import PAGED_MEDIUM, paged_medium
from pyhermes.pdf import available

requires_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

FACTS = {"firm_name": "F", "campaign_name": "C"}

COPY = "<p>" + "The curve steepened through the quarter as the front end repriced. " * 12 + "</p>"


def paged(*sections, page=None) -> PagedDocument:
    medium = paged_medium(page) if page is not None else None
    built = PagedDocument(FACTS, cover=EmptyCover(), back_matter=EmptyBackMatter(), medium=medium)
    for section in sections:
        built.add_section(section)
    return built


def email(*sections) -> Email:
    built = Email({**FACTS, "email_subject": "S"})
    for section in sections:
        built.add_section(section)
    return built


def landscape(*sections) -> PagedDocument:
    from pyhermes.builder.sizing import LETTER_LANDSCAPE

    return paged(*sections, page=LETTER_LANDSCAPE)


class TestTheTokens:
    def test_the_two_tokens_are_in_ch_and_convert_from_the_body_size(self):
        assert STANDARD_SIZES.type.measure_standard == 75
        assert STANDARD_SIZES.type.measure_narrow == 60
        assert measure_px(STANDARD_SIZES, "standard") == math.ceil(75 * 14 * CH_EM)
        assert measure_px(PRESENTATION_SIZES, "standard") == math.ceil(75 * 20 * CH_EM)

    def test_a_denser_type_size_narrows_the_px(self):
        assert measure_px(PRESENTATION_SIZES, "narrow") > measure_px(STANDARD_SIZES, "narrow")

    def test_spacing_cannot_move_them(self):
        from pyhermes.builder.sizing import Spacing

        with pytest.raises(ValidationError):
            Spacing(measure_standard=40)


class TestTheMediumOwnsTheDefault:
    def test_paper_the_brochure_and_the_deck_default_to_standard(self):
        for medium in (PAGED_MEDIUM, BROCHURE_MEDIUM, DECK_MEDIUM):
            assert medium.measure == "standard", medium.name

    def test_the_email_and_plain_html_set_none(self):
        from pyhermes.email import EMAIL_MEDIUM

        assert EMAIL_MEDIUM.measure is None
        assert DEFAULT_MEDIUM.measure is None


class TestThePerBlockOverride:
    def test_the_three_and_unset_are_accepted(self):
        for value in (*MEASURES, None):
            assert TextBlock("<p>x</p>", measure=value).measure == value

    def test_anything_else_is_refused(self):
        with pytest.raises(ValidationError, match="'standard', 'narrow', 'full'"):
            TextBlock("<p>x</p>", measure="wide")

    def test_full_turns_it_off_on_paper(self):
        assert "max-width" not in landscape(FullWidth(TextBlock(COPY, measure="full"))).render()

    def test_narrow_narrows_it(self):
        standard = measure_px(STANDARD_SIZES, "standard")
        narrow = measure_px(STANDARD_SIZES, "narrow")
        html = landscape(FullWidth(TextBlock(COPY, measure="narrow"))).render()
        assert f"max-width:{narrow}px;" in html
        assert f"max-width:{standard}px;" not in html

    def test_an_email_block_may_ask_for_one(self):
        narrow = measure_px(STANDARD_SIZES, "narrow")
        assert (
            f"max-width:{narrow}px;" in email(FullWidth(TextBlock(COPY, measure="narrow"))).render()
        )

    def test_position_projects_to_nothing(self):
        assert (
            landscape(FullWidth(TextBlock(COPY))).text()
            == landscape(FullWidth(TextBlock(COPY, measure="full"))).text()
        )


class TestOnlyWhereItBites:
    def test_written_when_the_cell_is_wider_than_the_measure(self):
        cap = measure_px(STANDARD_SIZES, "standard")
        assert f"max-width:{cap}px;" in landscape(FullWidth(TextBlock(COPY))).render()

    def test_omitted_when_the_cell_fits(self):
        # A4 portrait's content is 578px, inside the 630px standard measure.
        assert "max-width" not in paged(FullWidth(TextBlock(COPY))).render()

    def test_the_threshold_is_the_cell_not_the_page(self):
        # A split's column on a landscape sheet already fits.
        html = landscape(TwoColumn(left=TextBlock(COPY), right=TextBlock(COPY))).render()
        assert "max-width" not in html

    def test_a_flowed_column_is_measured_one_column_wide(self):
        assert "max-width" not in landscape(FlowedColumns(TextBlock(COPY), count=2)).render()

    def test_every_email_golden_carries_none(self):
        from qa.fixtures import all_fixtures

        cap = measure_px(STANDARD_SIZES, "standard")
        for name, build in all_fixtures().items():
            assert f"max-width:{cap}px;" not in build().render(), name

    def test_a_centred_block_is_centred_under_its_cap(self):
        html = landscape(FullWidth(TextBlock(COPY), align="center")).render()
        assert "margin-left:auto; margin-right:auto;" in html


@requires_pdf
class TestOnTheSheet:
    def test_a_deck_paragraph_stays_within_the_standard_measure(self):
        """The table slide's lead-in, read back line by line from the deck's PDF."""
        import pypdfium2

        from pyhermes.pdf import render_pdf
        from qa.fixtures import pitch_16_9

        def widest_line(deck) -> float:
            document = pypdfium2.PdfDocument(render_pdf(deck))
            page = document[deck.number(deck.slides[3]) - 1]
            text = page.get_textpage()
            widths = []
            for n in range(text.count_rects()):
                left, _, right, _ = text.get_rect(n)
                widths.append((right - left) * 4 / 3)  # a PDF point is 4/3 of a CSS px
            return max(widths)

        cap = measure_px(PRESENTATION_SIZES, "standard")
        capped = pitch_16_9.build()
        assert "The long end did the work" in capped.slides[3].text()
        widest = widest_line(capped)
        assert cap * 0.85 < widest <= cap + 2, f"a line ran {widest:.0f}px against {cap}px"

        uncapped = pitch_16_9.build()
        uncapped.slides[3].sections[0].content.measure = "full"
        assert widest_line(uncapped) > cap + 2, "the paragraph never needed the cap"
