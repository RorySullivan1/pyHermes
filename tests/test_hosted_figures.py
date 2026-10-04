"""
A chart or an equation floated beside prose on paper (#359).

``ChartBlock(wrap=)`` and ``MathBlock(wrap=)``, hosted by ``TextBlock(figure=)``,
share ``ImageBlock``'s float (#189) and its rules: a width to float at, no
label or note, and in an email the figure sits above the prose by its align.
"""

from __future__ import annotations

import importlib.util

import pytest

from pyhermes.brochure import Brochure, Panel
from pyhermes.builder import ChartBlock, Email, FullWidth, MathBlock, TextBlock, ValidationError
from pyhermes.builder.images import EmailImage
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument
from pyhermes.pdf import available
from qa.fixtures._png import solid_png

requires_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

FACTS = {"firm_name": "F", "campaign_name": "C"}

PROSE = (
    '<p><span id="prose-start"></span>'
    + "The premium rose for a third quarter and explains most of the move. " * 8
    + "</p>"
)


def chart(wrap: str = "right", **kwargs) -> ChartBlock:
    image = EmailImage.attached(solid_png(240, 160, (91, 138, 154)), alt="Premium", width=120)
    return ChartBlock(image, source="Hermes", wrap=wrap, anchor="chart", **kwargs)


def equation(wrap: str = "left", **kwargs) -> MathBlock:
    return MathBlock(
        solid_png(200, 60, (0, 0, 0)), "a+b", width=100, wrap=wrap, anchor="eq", **kwargs
    )


FIGURES = {"ChartBlock": chart, "MathBlock": equation}


def email(*sections) -> Email:
    built = Email({**FACTS, "email_subject": "S"})
    for section in sections:
        built.add_section(section)
    return built


def paged(*sections) -> PagedDocument:
    built = PagedDocument(FACTS, cover=EmptyCover(), back_matter=EmptyBackMatter())
    for section in sections:
        built.add_section(section)
    return built


class TestTheField:
    @pytest.mark.parametrize("name", list(FIGURES))
    def test_both_sides_are_accepted_and_others_refused(self, name):
        assert FIGURES[name]("left").wrap == "left"
        assert FIGURES[name]("right").wrap == "right"
        assert FIGURES[name]("").wrap == ""
        with pytest.raises(ValidationError, match="Unsupported wrap"):
            FIGURES[name]("centre")

    def test_a_wrap_needs_a_width(self):
        with pytest.raises(ValidationError, match="wrapped ChartBlock needs a display width"):
            ChartBlock("https://example.com/c.png", alt_text="C", wrap="left")
        image = EmailImage.attached(solid_png(20, 10, (0, 0, 0)), alt="a+b")
        with pytest.raises(ValidationError, match="wrapped MathBlock needs a display width"):
            MathBlock(image, "a+b", wrap="left")

    @pytest.mark.parametrize("name", list(FIGURES))
    @pytest.mark.parametrize("kwargs", [{"label": "Figure"}, {"notes": ["A note."]}])
    def test_a_hosted_figure_cannot_be_numbered_or_noted(self, name, kwargs):
        if name == "ChartBlock" and "notes" in kwargs:
            kwargs = {"notes": ["A note."], "caption": "Premium[^1]"}
        if name == "MathBlock" and "notes" in kwargs:
            kwargs = {"notes": ["A note."], "caption": "Sum[^1]"}
        with pytest.raises(ValidationError, match="cannot be numbered or carry notes"):
            TextBlock(PROSE, figure=FIGURES[name](**kwargs))

    def test_anything_else_is_refused_naming_all_three(self):
        with pytest.raises(ValidationError, match="ImageBlock, a ChartBlock or a MathBlock"):
            TextBlock(PROSE, figure=TextBlock("<p>x</p>"))  # type: ignore[arg-type]

    @pytest.mark.parametrize("name", list(FIGURES))
    def test_the_figure_reaches_the_manifest(self, name):
        block = TextBlock(PROSE, figure=FIGURES[name]())
        assert block.images() == [block.figure.image]
        [asset] = email(FullWidth(block)).assets()
        assert asset.content_id == block.figure.image.content_id


class TestInAnEmail:
    @pytest.mark.parametrize("name", list(FIGURES))
    def test_it_sits_above_the_prose_byte_for_byte_as_unwrapped(self, name):
        hosted = email(FullWidth(TextBlock(PROSE, figure=FIGURES[name]()))).render()
        # The figure's own markup is what it renders unhosted and unwrapped.
        engine = email(FullWidth(TextBlock("<p>x</p>")))._bound_engine()
        bare = FIGURES[name]("").render(engine)
        assert bare in hosted
        assert hosted.index(bare) < hosted.index('id="prose-start"')
        assert '<div class="wrapped-figure">' in hosted
        assert "wrap-" not in hosted

    @pytest.mark.parametrize("name", list(FIGURES))
    def test_the_text_part_is_the_figure_then_the_prose(self, name):
        figure = FIGURES[name]()
        block = TextBlock(PROSE, figure=figure)
        assert block.text().startswith(figure.text())


class TestOnPaper:
    @pytest.mark.parametrize("name", list(FIGURES))
    def test_it_floats_to_its_side_at_its_width(self, name):
        figure = FIGURES[name]()
        html = paged(FullWidth(TextBlock(PROSE, figure=figure))).render()
        assert (
            f'<div class="wrapped-figure wrap-{figure.wrap}" style="width:{figure.image.width}px;">'
            in html
        )


@requires_pdf
class TestOnTheSheet:
    @staticmethod
    def _beside(document, anchor: str) -> bool:
        """Whether the prose's first line sits level with the figure rather than under it."""
        from pyhermes.pdf import anchor_tops

        landed = anchor_tops(document)
        return abs(landed["prose-start"] - landed[anchor]) < 20

    @pytest.mark.parametrize("name,anchor", [("ChartBlock", "chart"), ("MathBlock", "eq")])
    def test_the_prose_wraps_round_it_in_a_paged_column(self, name, anchor):
        assert self._beside(paged(FullWidth(TextBlock(PROSE, figure=FIGURES[name]()))), anchor)
        assert not self._beside(
            paged(FullWidth(TextBlock(PROSE, figure=FIGURES[name]("")))), anchor
        )

    @pytest.mark.parametrize("name,anchor", [("ChartBlock", "chart"), ("MathBlock", "eq")])
    def test_the_prose_wraps_round_it_in_a_brochure_panel(self, name, anchor):
        def brochure(wrap: str) -> Brochure:
            panels = [Panel([FullWidth(TextBlock(f"<p>Face {n}</p>"))]) for n in range(1, 7)]
            panels[1] = Panel([FullWidth(TextBlock(PROSE, figure=FIGURES[name](wrap)))])
            return Brochure(FACTS, panels)

        assert self._beside(brochure("right" if name == "ChartBlock" else "left"), anchor)
        assert not self._beside(brochure(""), anchor)
