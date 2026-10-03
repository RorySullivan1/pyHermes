"""
A split's columns aligned on the cross axis (#356): paper honours it, an email refuses it.

The field sits on every split and on ``Columns``, one value per split. On
paper the inline columns take ``vertical-align`` and the ghost table's cells
the ``valign`` attribute; an email refuses anything but ``top`` when the
section is added, until an Outlook check lifts it.
"""

from __future__ import annotations

import importlib.util

import pytest

from pyhermes.builder import (
    Columns,
    Email,
    FourColumn,
    FullWidth,
    Stack,
    TextBlock,
    ThreeColumn,
    TwoColumn,
    ValidationError,
)
from pyhermes.deck import SLIDE_16_9, Deck, Slide
from pyhermes.deck.regions import EmptyClosingSlide, EmptyTitleSlide
from pyhermes.document import EmptyBackMatter, EmptyCover, Page, PagedDocument
from pyhermes.pdf import available

requires_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

FACTS = {"firm_name": "F", "campaign_name": "C"}

TALL = "<p>" + "<br>".join(f"Line {n}" for n in range(12)) + '<span id="tall-end"></span></p>'


def short(marker: str = "short") -> TextBlock:
    return TextBlock(
        f'<p><span id="{marker}-start"></span>Short<span id="{marker}-end"></span></p>'
    )


def split(valign: str = "top") -> TwoColumn:
    return TwoColumn(left=short(), right=TextBlock(TALL), valign=valign)


def paged(*sections) -> PagedDocument:
    document = PagedDocument(FACTS, cover=EmptyCover(), back_matter=EmptyBackMatter())
    for section in sections:
        document.add_section(section)
    return document


def email(*sections) -> Email:
    built = Email({**FACTS, "email_subject": "S"})
    for section in sections:
        built.add_section(section)
    return built


class TestTheField:
    @pytest.mark.parametrize(
        "build",
        [
            lambda v: TwoColumn(left=short(), valign=v),
            lambda v: ThreeColumn(left=short(), valign=v),
            lambda v: FourColumn([short(), None, None, None], valign=v),
            lambda v: Columns([short(), short("b")], valign=v),
        ],
    )
    def test_every_split_takes_the_three_and_refuses_the_rest(self, build):
        for value in ("top", "middle", "bottom"):
            assert build(value).valign == value
        with pytest.raises(ValidationError, match="'top', 'middle', 'bottom'"):
            build("baseline")

    def test_top_is_the_default_and_byte_identical(self):
        assert paged(split()).render() == paged(split("top")).render()
        assert email(split()).render() == email(split("top")).render()

    def test_paper_writes_it_on_both_spellings(self):
        html = paged(split("middle")).render()
        assert "vertical-align:middle;" in html
        assert 'valign="middle"' in html

    def test_a_nested_columns_takes_its_own_value(self):
        inner = Columns([short("a"), TextBlock(TALL)], valign="bottom")
        html = paged(TwoColumn(left=Stack([inner]), right=short("b"), valign="middle")).render()
        assert "vertical-align:bottom;" in html
        assert "vertical-align:middle;" in html

    def test_position_projects_to_nothing(self):
        assert paged(split("bottom")).text() == paged(split()).text()


class TestAnEmailRefusesIt:
    @pytest.mark.parametrize("valign", ["middle", "bottom"])
    def test_a_split_off_the_top_is_refused_naming_the_outlook_gate(self, valign):
        with pytest.raises(ValidationError, match=r"Outlook check.*#356"):
            email(split(valign))

    def test_a_nested_columns_is_refused_too(self):
        nested = Columns([short("a"), short("b")], valign="middle")
        with pytest.raises(ValidationError, match="Columns sets valign='middle'"):
            email(FullWidth(Stack([nested])))

    def test_a_split_inside_a_page_is_refused(self):
        with pytest.raises(ValidationError, match="TwoColumn sets valign='bottom'"):
            email(Page([split("bottom")]))

    def test_the_refused_section_is_not_added(self):
        built = email(split())
        with pytest.raises(ValidationError):
            built.add_section(split("middle"))
        assert built.render() == email(split()).render()

    def test_top_is_accepted(self):
        assert "vertical-align:top;" in email(split("top")).render()


@requires_pdf
class TestOnTheSheet:
    @staticmethod
    def _landed(document) -> dict[str, float]:
        from pyhermes.pdf import anchor_tops

        return anchor_tops(document)

    def test_paged_middle_and_bottom_place_the_short_column(self):
        top = self._landed(paged(split()))
        middle = self._landed(paged(split("middle")))
        bottom = self._landed(paged(split("bottom")))
        assert top["short-start"] < middle["short-start"] < bottom["short-start"]
        # Bottom: the short column's last line shares the tall one's last line.
        assert bottom["short-end"] == pytest.approx(bottom["tall-end"], abs=1)
        # Middle: the short column's centre is the tall one's.
        tall_top = top["short-start"]
        tall_centre = (tall_top + bottom["tall-end"]) / 2
        middle_centre = (middle["short-start"] + middle["short-end"]) / 2
        assert middle_centre == pytest.approx(tall_centre, abs=12)

    def test_a_deck_split_honours_it(self):
        def deck(valign: str) -> Deck:
            built = Deck(
                FACTS,
                page=SLIDE_16_9,
                title_slide=EmptyTitleSlide(),
                closing_slide=EmptyClosingSlide(),
            )
            built.add_slide(Slide([split(valign)], "Split"))
            return built

        top = self._landed(deck("top"))
        bottom = self._landed(deck("bottom"))
        assert top["short-start"] < bottom["short-start"]
        assert bottom["short-end"] == pytest.approx(bottom["tall-end"], abs=1)
