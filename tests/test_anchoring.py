"""
Anchoring copy in a fixed box (#355): a panel, a slide's body, the title slide, a divider.

Each box has a height the print engine is handed, so ``valign`` places the
copy in it. Unset, every box renders as it did; set, the copy and its
overflow sentinel sit in one cell, and an overfull box is still named.
"""

from __future__ import annotations

import importlib.util

import pytest

from pyhermes.brochure import Brochure, Panel, overflowing_panels
from pyhermes.brochure.imposition import impose
from pyhermes.builder import FullWidth, TextBlock, ValidationError, VerticalAlign
from pyhermes.deck import SLIDE_16_9, Deck, DividerSlide, Slide, TitleSlide, overflowing_slides
from pyhermes.deck.regions import EmptyClosingSlide, EmptyTitleSlide
from pyhermes.pdf import available

requires_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

FACTS = {"firm_name": "F", "campaign_name": "C"}


def copy(text: str = "Short copy") -> FullWidth:
    return FullWidth(TextBlock(f"<p>{text}</p>"))


def brochure(valign: str = "top", text: str = "Short copy") -> Brochure:
    panels = [Panel([copy(f"Face {n}")], title=f"P{n}") for n in range(1, 7)]
    panels[0] = Panel([copy(text)], title="Cover", valign=valign)
    return Brochure(FACTS, panels)


def deck(*slides: Slide, title_slide: TitleSlide | None = None) -> Deck:
    built = Deck(
        FACTS,
        page=SLIDE_16_9,
        title_slide=title_slide or EmptyTitleSlide(),
        closing_slide=EmptyClosingSlide(),
    )
    for slide in slides:
        built.add_slide(slide)
    return built


class TestTheField:
    @pytest.mark.parametrize(
        "build",
        [
            lambda v: Panel([copy()], valign=v),
            lambda v: Slide([copy()], valign=v),
            lambda v: DividerSlide("Part", valign=v),
            lambda v: TitleSlide(valign=v).validate(),
        ],
    )
    def test_anything_but_the_three_is_refused(self, build):
        with pytest.raises(ValidationError, match="'top', 'middle', 'bottom'"):
            build("centre")

    def test_the_defaults_keep_every_box_where_it_was(self):
        assert Panel([copy()]).valign == Slide([copy()]).valign == "top"
        assert DividerSlide("Part").valign == TitleSlide().valign == "bottom"

    def test_the_enum_is_accepted(self):
        assert Slide([copy()], valign=VerticalAlign.MIDDLE).valign == "middle"

    def test_unset_and_default_render_the_same_bytes(self):
        assert brochure().render() == brochure("top").render()
        assert (
            deck(Slide([copy()], "T")).render() == deck(Slide([copy()], "T", valign="top")).render()
        )
        assert 'class="anchor"' not in deck(Slide([copy()], "T")).render()

    def test_the_divider_and_title_slide_default_writes_no_anchor_cell(self):
        html = deck(Slide([copy()], "T"), title_slide=TitleSlide()).render()
        assert 'class="anchor"' not in html

    def test_add_slide_and_add_divider_pass_it_on(self):
        built = deck()
        built.add_slide([copy()], "T", valign="bottom")
        built.add_divider("Part", valign="top")
        assert [slide.valign for slide in built.slides] == ["bottom", "top"]

    def test_add_slide_refuses_it_beside_a_built_slide(self):
        with pytest.raises(ValidationError, match="not both"):
            deck().add_slide(Slide([copy()]), valign="middle")

    def test_position_projects_to_nothing(self):
        assert brochure("bottom").text() == brochure().text()
        anchored = deck(Slide([copy()], "T", valign="middle"))
        assert anchored.text() == deck(Slide([copy()], "T")).text()

    def test_a_panel_or_slide_flattened_elsewhere_ignores_it(self):
        from pyhermes.builder import Email

        def email(section):
            built = Email({**FACTS, "email_subject": "S"})
            built.add_section(section)
            return built.render()

        assert email(Panel([copy()], valign="bottom")) == email(Panel([copy()]))
        assert email(Slide([copy()], valign="middle")) == email(Slide([copy()]))


@requires_pdf
class TestOnTheSheet:
    def test_a_bottom_panel_ends_on_its_safe_line(self):
        from pyhermes.pdf import anchor_tops

        built = brochure("bottom")
        box = impose(built.fold)[0]
        safe = box.height - built.inset(built.panels[0])
        assert anchor_tops(built)["panel-1-end"] == pytest.approx(safe, abs=0.5)

    def test_a_middle_panel_sits_between_top_and_bottom(self):
        from pyhermes.pdf import anchor_tops

        top = anchor_tops(brochure("top"))["panel-1-end"]
        middle = anchor_tops(brochure("middle"))["panel-1-end"]
        bottom = anchor_tops(brochure("bottom"))["panel-1-end"]
        assert top < middle < bottom

    def test_a_bottom_slide_ends_at_the_body_foot(self):
        from pyhermes.pdf import anchor_tops

        built = deck(Slide([copy()], "T", valign="bottom"))
        assert anchor_tops(built)["slide-1-end"] == pytest.approx(built.box().body_bottom, abs=0.5)

    def test_a_middle_slide_is_centred_in_its_body(self):
        from pyhermes.pdf import anchor_tops

        built = deck(Slide([copy()], "A"), Slide([copy()], "B", valign="middle"))
        landed = anchor_tops(built)
        box = built.box()
        height = landed["slide-1-end"] - box.body_top
        centre = landed["slide-2-end"] - height / 2
        assert centre == pytest.approx(box.body_top + box.body_height / 2, abs=1)

    def test_each_region_of_a_laid_out_slide_is_anchored(self):
        from pyhermes.pdf import anchor_tops

        built = deck(Slide([copy()], "T", layout="split", side=[copy()], valign="bottom"))
        landed = anchor_tops(built)
        for end in ("slide-1-end", "slide-1-side-end"):
            assert landed[end] == pytest.approx(built.box().body_bottom, abs=0.5)

    @pytest.mark.parametrize("valign", ["middle", "bottom"])
    def test_an_overfull_anchored_panel_is_still_named(self, valign):
        overlong = " ".join(["The curve steepened through the quarter."] * 120)
        assert overflowing_panels(brochure(valign, overlong)) == ["panel 1 (front cover)"]

    @pytest.mark.parametrize("valign", ["middle", "bottom"])
    def test_an_overfull_anchored_slide_is_still_named(self, valign):
        overlong = " ".join(["The curve steepened through the quarter."] * 200)
        built = deck(Slide([copy(overlong)], "Too long", valign=valign))
        assert overflowing_slides(built) == ["slide 1: Too long"]

    @pytest.mark.parametrize("valign", ["top", "middle"])
    def test_a_divider_and_title_slide_anchored_higher_still_fit(self, valign):
        from pyhermes.pdf import anchor_tops

        built = deck(
            Slide([copy()], "T"),
            title_slide=TitleSlide(title="Opening", valign=valign),
        )
        built.add_divider("Part two", valign=valign)
        assert overflowing_slides(built) == []
        assert "part-two" in anchor_tops(built)
