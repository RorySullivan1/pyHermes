"""
The MathBlock component (#229), the first child of epic #221.

An equation is an image plus the LaTeX it was rendered from. The source is
its alt text and its text projection, and it is an exhibit in full. Every
test runs on ``solid_png`` bytes: the component never imports the extra.
"""

from __future__ import annotations

import re

import pytest

from pyhermes.builder import ChartBlock, DataTable, FullWidth, MathBlock, TextBlock
from pyhermes.builder.email import Email
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import TableRow
from qa.fixtures import kitchen_sink
from qa.fixtures._png import solid_png

PNG = solid_png(120, 30, (59, 59, 59))
SOURCE = r"\sigma^2"
FACTS = {"email_subject": "S", "firm_name": "F", "campaign_name": "C"}


def _block(**overrides) -> MathBlock:
    return MathBlock(**{"image": PNG, "latex": SOURCE, "width": 40, **overrides})


class TestItConstructsWithNoExtra:
    def test_bytes_become_an_attached_image_whose_alt_is_the_source(self):
        block = _block()
        assert block.image.src.startswith("cid:")
        assert block.image.alt == block.latex == SOURCE

    def test_an_image_that_already_says_the_source_is_kept(self):
        image = EmailImage.attached(PNG, alt=SOURCE, width=40)
        assert _block(image=image).image is image

    def test_text_prints_the_source_on_its_own_line(self):
        assert f"${SOURCE}$" in _block().text().splitlines()

    def test_images_reaches_the_manifest(self):
        email = Email(FACTS)
        block = _block()
        email.add_section(FullWidth(content=block))
        assert [a.content_id for a in email.assets()] == [block.image.content_id]


class TestItRefusesByName:
    @pytest.mark.parametrize("latex", ["", "   "])
    def test_a_blank_source(self, latex):
        with pytest.raises(ValidationError, match="math_block.latex"):
            _block(latex=latex)

    def test_a_newline_points_at_lines(self):
        with pytest.raises(ValidationError, match="lines="):
            _block(latex="a\nb")

    def test_an_alt_that_is_not_the_source(self):
        image = EmailImage.attached(PNG, alt="Variance", width=40)
        with pytest.raises(ValidationError, match="math_block.image"):
            _block(image=image)

    def test_a_decorative_image(self):
        image = EmailImage.attached(PNG, decorative=True, width=40)
        with pytest.raises(ValidationError, match="never decorative"):
            _block(image=image)

    def test_a_bad_alignment(self):
        with pytest.raises(ValidationError, match="math_block.align"):
            _block(align="justify")


class TestTheSourceSurvivesEveryProjection:
    def test_the_alt_is_escaped_as_an_attribute(self):
        block = _block(latex=r'a < b & "c"')
        html = block.render(TemplateEngine())
        assert 'alt="a &lt; b &amp; &quot;c&quot;"' in html
        assert block.latex in block.text()

    def test_the_context_carries_the_source(self):
        assert _block().context()["image_alt"] == SOURCE


class TestItIsAnExhibitInFull:
    @pytest.fixture
    def email(self) -> Email:
        email = Email(FACTS)
        chart = ChartBlock(
            EmailImage.attached(solid_png(60, 20, (1, 2, 3)), alt="Chart", width=60),
            label="Figure",
        )
        table = DataTable(["A", "B"], [TableRow(["x", "1"])], label="Table")
        email.add_section(FullWidth(content=chart))
        email.add_section(FullWidth(content=_block(label="Equation", caption="Variance")))
        email.add_section(FullWidth(content=table))
        email.add_section(
            FullWidth(content=_block(latex="x", label="Equation", caption="Mean[^1]", notes=["N."]))
        )
        email.add_section(
            FullWidth(content=TextBlock('<p>See <a href="#equation-2">Equation 2</a>.</p>'))
        )
        return email

    def test_equations_number_separately_and_carry_ids(self, email):
        html = email.render()
        assert 'id="equation-1"' in html and 'id="equation-2"' in html
        assert "Equation 1 · Variance" in html and "Figure 1" in html and "Table 1" in html

    def test_a_reference_resolves_in_both_projections(self, email):
        email.validate()
        assert 'href="#equation-2"' in email.render()
        assert "Equation 2" in email.text()

    def test_a_caption_marker_joins_the_endnotes(self, email):
        html = email.render()
        assert re.search(r'Mean<sup class="note-ref"', html)
        assert 'class="notes-heading"' in html and "N." in email.text()

    def test_a_marker_without_a_note_raises(self):
        with pytest.raises(ValidationError, match=r"\[\^1\]"):
            _block(caption="Mean[^1]")

    def test_unlabelled_it_carries_no_number(self):
        html = _block(caption="Variance").render(TemplateEngine())
        assert "Equation" not in html and ' id="' not in html


class TestTheGalleryHoldsIt:
    def test_kitchen_sink_sets_every_field(self):
        [block] = [
            c
            for section in kitchen_sink.build()._sections
            for c in section.components()
            if isinstance(c, MathBlock) and c.label
        ]
        assert block.caption and block.label and block.anchor and block.notes
        assert block.disclosure and block.align != "center" and block.spacing is not None
        assert block.image.width


def test_the_builder_imports_no_optional_backend():
    import ast
    import pathlib

    tree = ast.parse(pathlib.Path("pyhermes/builder/components.py").read_text(encoding="utf-8"))
    modules = [
        getattr(node, "module", None) or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    ]
    assert not [
        m for m in modules if m and (m.startswith("matplotlib") or m.startswith("pyhermes.math"))
    ]


class TestLines:
    def test_the_component_takes_lines_without_the_extra(self):
        block = MathBlock(PNG, lines=["a = b", "c = d"], width=40)
        assert block.image.alt == "a = b\nc = d"
        assert "$a = b$\n$c = d$" in block.text()

    @pytest.mark.parametrize("lines", [[], ["a", ""], ["a\nb"]])
    def test_bad_lines_raise(self, lines):
        with pytest.raises(ValidationError, match="math_block"):
            MathBlock(PNG, lines=lines, width=40)

    def test_latex_and_lines_together_raise(self):
        with pytest.raises(ValidationError, match="not both"):
            MathBlock(PNG, latex="x", lines=["y"], width=40)
