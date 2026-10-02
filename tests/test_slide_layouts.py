"""
A slide body's named layout (#366): full, split or sidebar.

Each region renders against its own frame, computed like a split's columns,
and carries its own overflow sentinel. Anywhere but its own sheet a laid-out
slide is its regions' sections in reading order, main first.
"""

from __future__ import annotations

import importlib.util

import pytest

from pyhermes.builder import DataTable, Email, FullWidth, TextBlock, ValidationError
from pyhermes.builder.models import TableRow
from pyhermes.builder.sizing import resolve_size_scheme
from pyhermes.deck import SLIDE_16_9, Deck, Slide
from pyhermes.deck.regions import EmptyClosingSlide, EmptyTitleSlide
from pyhermes.deck.slide import SlideBox
from pyhermes.pdf import available

requires_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

FACTS = {"firm_name": "F", "campaign_name": "C"}


def copy(marker: str) -> FullWidth:
    return FullWidth(TextBlock(f"<p>{marker} copy</p>"), title=marker.title())


def deck(*slides: Slide) -> Deck:
    built = Deck(
        FACTS, page=SLIDE_16_9, title_slide=EmptyTitleSlide(), closing_slide=EmptyClosingSlide()
    )
    for slide in slides:
        built.add_slide(slide)
    return built


def sidebar(side=None) -> Slide:
    return Slide([copy("MAIN")], "Laid out", layout="sidebar", side=side or [copy("SIDE")])


class TestTheField:
    def test_full_is_the_default_and_byte_identical(self):
        assert Slide([copy("A")]).layout == "full"
        plain = deck(Slide([copy("A")], "T")).render()
        assert deck(Slide([copy("A")], "T", layout="full")).render() == plain

    def test_an_unknown_layout_is_refused(self):
        with pytest.raises(ValidationError, match="'full', 'split', 'sidebar'"):
            Slide([copy("A")], layout="grid", side=[copy("B")])

    def test_a_laid_out_body_needs_a_side_and_a_full_one_refuses_it(self):
        with pytest.raises(ValidationError, match=r"give side=\[...\]"):
            Slide([copy("A")], layout="split")
        with pytest.raises(ValidationError, match="a full body has no side region"):
            Slide([copy("A")], side=[copy("B")])

    def test_the_side_is_checked_like_the_main(self):
        with pytest.raises(ValidationError, match="holds containers"):
            Slide([copy("A")], layout="split", side=[TextBlock("<p>x</p>")])

    def test_add_slide_takes_them(self):
        built = deck().add_slide([copy("A")], "T", layout="split", side=[copy("B")])
        assert built.slides[0].layout == "split"
        assert [s.title for s in built.slides[0].side] == ["B"]


class TestTheRegions:
    @pytest.fixture
    def box(self):
        scheme = resolve_size_scheme("presentation").with_page(SLIDE_16_9)
        return SlideBox.of(scheme), scheme.space.gutter

    def test_a_full_body_is_one_region_across_the_sheet(self, box):
        slide_box, gutter = box
        (region,) = slide_box.regions("full", gutter)
        assert (region.left, region.width, region.inset) == (0, slide_box.width, slide_box.inset)

    @pytest.mark.parametrize("layout, share", [("split", 1 / 2), ("sidebar", 1 / 3)])
    def test_the_copy_widths_split_by_weight_with_a_gutter_between(self, box, layout, share):
        slide_box, gutter = box
        main, side = slide_box.regions(layout, gutter)
        copy_main, copy_side = main.width - gutter, side.width - gutter
        assert copy_main + gutter + copy_side == slide_box.width - 2 * slide_box.inset
        assert abs(copy_side - (copy_main + copy_side) * share) <= 1

    def test_the_copy_sits_level_with_the_title_and_the_frames_meet(self, box):
        slide_box, gutter = box
        main, side = slide_box.regions("sidebar", gutter)
        assert main.left + main.inset == slide_box.inset
        assert main.left + main.width == side.left
        assert side.left + side.width - side.inset == slide_box.width - slide_box.inset

    def test_each_region_is_written_with_its_own_sentinel(self):
        html = deck(sidebar()).render()
        assert 'id="slide-1-end"' in html and 'id="slide-1-side-end"' in html
        assert html.index("MAIN copy") < html.index("SIDE copy")


class TestElsewhere:
    def test_in_an_email_it_is_its_sections_main_first(self):
        def email(*sections):
            built = Email({"email_subject": "S", **FACTS})
            for section in sections:
                built.add_section(section)
            return built

        untitled = Slide([copy("MAIN")], layout="sidebar", side=[copy("SIDE")])
        laid_out = email(untitled)
        flat = email(copy("MAIN"), copy("SIDE"))
        assert laid_out.render() == flat.render()
        # A slide's text joins its sections as a page's does, one blank line apart.
        assert (
            laid_out.text()
            == Email({"email_subject": "S", **FACTS})
            .add_section(Slide([copy("MAIN"), copy("SIDE")]))
            .text()
        )

    def test_the_text_part_reads_main_then_side(self):
        text = deck(sidebar()).text()
        assert text.index("MAIN copy") < text.index("SIDE copy")


def long_table() -> FullWidth:
    return FullWidth(DataTable(["A", "B"], [TableRow([str(n), str(n)]) for n in range(40)]))


@requires_pdf
class TestOnTheSheet:
    def test_an_overflowing_sidebar_names_its_slide(self):
        from pyhermes.deck import overflowing_slides

        assert overflowing_slides(deck(sidebar())) == []
        assert overflowing_slides(deck(sidebar([long_table()]))) == ["slide 1: Laid out"]

    def test_an_overflowing_main_region_names_it_too(self):
        from pyhermes.deck import overflowing_slides

        main = Slide([long_table()], "Main spills", layout="split", side=[copy("SIDE")])
        assert overflowing_slides(deck(main)) == ["slide 1: Main spills"]

    def test_the_two_regions_print_side_by_side_on_one_sheet(self):
        import pypdfium2

        from pyhermes.pdf import render_pdf

        pdf = pypdfium2.PdfDocument(render_pdf(deck(sidebar())))
        assert len(pdf) == 1
        page = pdf[0].get_textpage()
        boxes = {}
        for marker in ("MAIN", "SIDE"):
            index = page.get_text_range().index(f"{marker} copy")
            boxes[marker] = page.get_charbox(index)
        main_left, main_bottom = boxes["MAIN"][0], boxes["MAIN"][1]
        side_left, side_bottom = boxes["SIDE"][0], boxes["SIDE"][1]
        assert side_left > main_left + 300
        assert abs(main_bottom - side_bottom) < 2
