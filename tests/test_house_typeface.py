"""
A house typeface a printed document embeds (#391), and an email that never sees it.

The face is ``qa/fixtures/fonts``' Specimen Condensed, a renamed DejaVu Sans no
machine has installed. The PDF tests need ``[pdf]`` and ``[qa]``, the chart
test ``[charts]``; each skips without its extra.
"""

from __future__ import annotations

import ctypes
import importlib.util
from pathlib import Path

import pytest

from pyhermes.builder import DEFAULT_FONTS, Email, FontStack, FullWidth, TextBlock
from pyhermes.builder.exceptions import ValidationError
from pyhermes.document import PagedDocument
from pyhermes.pdf import available, render_pdf
from pyhermes.pdf.exporter import render_handout

FONTS = Path(__file__).resolve().parent.parent / "qa" / "fixtures" / "fonts"
REGULAR = FONTS / "SpecimenCondensed-Regular.ttf"
BOLD = FONTS / "SpecimenCondensed-Bold.ttf"
FACTS = {"firm_name": "Hermes Research", "campaign_name": "Quarterly Brief"}

needs_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='the embedding tests need the "[pdf]" and "[qa]" extras',
)


def _house() -> FontStack:
    return FontStack("House Sans", "Arial", "sans-serif", files={"400": REGULAR, "700": BOLD})


def _house_fonts():
    return DEFAULT_FONTS.derive(heading=_house(), label=_house(), body=_house())


def _section() -> FullWidth:
    return FullWidth(content=TextBlock("<p>Set in the house face.</p>"), title="Opening")


def _embedded(pdf: bytes) -> set[str]:
    """Every font name pypdfium2 reads back off a character, subset prefix removed."""
    import pypdfium2
    import pypdfium2.raw as raw

    names = set()
    for page in pypdfium2.PdfDocument(pdf):
        text = page.get_textpage()
        for index in range(text.count_chars()):
            buffer = ctypes.create_string_buffer(256)
            raw.FPDFText_GetFontInfo(text, index, buffer, 256, ctypes.c_int())
            names.add(buffer.value.decode().partition("+")[2])
    return names


class TestTheStack:
    def test_files_are_read_and_keyed_by_weight(self):
        stack = _house()
        assert [(f.weight, f.style) for f in stack.files] == [(400, "normal"), (700, "normal")]
        assert stack.files[0].data == REGULAR.read_bytes()
        assert stack.files[0].format == "truetype"
        assert stack.files[0].content_id.startswith("font-")

    def test_an_italic_is_keyed_with_its_weight(self):
        stack = FontStack("House Sans", "sans-serif", files={"400 italic": REGULAR})
        assert stack.files[0].style == "italic"

    def test_the_css_does_not_change(self):
        assert _house().css == FontStack("House Sans", "Arial", "sans-serif").css

    def test_a_missing_file_raises_at_construction(self, tmp_path):
        with pytest.raises(ValidationError, match="cannot be read"):
            FontStack("House Sans", "sans-serif", files={"400": tmp_path / "absent.ttf"})

    def test_a_file_that_is_not_a_font_raises(self, tmp_path):
        png = tmp_path / "logo.ttf"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(32))
        with pytest.raises(ValidationError, match="is not a TrueType"):
            FontStack("House Sans", "sans-serif", files={"400": png})

    @pytest.mark.parametrize("key", ["regular", "450", "700 oblique", "bold"])
    def test_a_key_that_names_no_weight_raises(self, key):
        with pytest.raises(ValidationError, match="keyed by weight"):
            FontStack("House Sans", "sans-serif", files={key: REGULAR})

    def test_files_must_be_a_mapping(self):
        with pytest.raises(ValidationError, match="map a weight"):
            FontStack("House Sans", "sans-serif", files=[REGULAR])  # type: ignore[arg-type]

    def test_a_theme_declares_each_face_once(self):
        fonts = _house_fonts()
        assert len(fonts.faces) == 2
        assert len(fonts.assets()) == 2
        assert fonts.faces[0].css.startswith("@font-face { font-family: 'House Sans';")


class TestTheEmailNeverSeesIt:
    def _email(self, font_theme) -> Email:
        email = Email({**FACTS, "email_subject": "Brief", "font_theme": font_theme})
        email.add_section(_section())
        return email

    def test_the_html_is_byte_identical_with_and_without_files(self):
        plain = DEFAULT_FONTS.derive(
            heading=FontStack("House Sans", "Arial", "sans-serif"),
            label=FontStack("House Sans", "Arial", "sans-serif"),
            body=FontStack("House Sans", "Arial", "sans-serif"),
        )
        assert self._email(_house_fonts()).render() == self._email(plain).render()

    def test_no_font_rides_the_message(self):
        email = self._email(_house_fonts())
        assert email.assets() == []
        assert email.fonts() == []
        assert "@font-face" not in email.render()


class TestOnPaper:
    def _document(self) -> PagedDocument:
        document = PagedDocument({**FACTS, "font_theme": _house_fonts()})
        document.add_section(_section())
        return document

    def test_the_skeleton_declares_each_face_from_the_manifest(self):
        document = self._document()
        html = document.render()
        for asset in document.fonts():
            assert f"src: url('cid:{asset.content_id}') format('truetype')" in html
        assert html.count("@font-face") == 2

    def test_the_fonts_stay_out_of_the_image_manifest(self):
        document = self._document()
        assert document.assets() == []
        assert [a.mime_type for a in document.fonts()] == ["font/ttf", "font/ttf"]

    @needs_pdf
    def test_a_paged_pdf_embeds_the_face(self):
        assert {"House-Sans", "House-Sans-Bold"} <= _embedded(render_pdf(self._document()))

    @needs_pdf
    def test_a_brochure_pdf_embeds_the_face(self):
        from qa.fixtures import tri_fold_letter

        brochure = tri_fold_letter.build()
        brochure.metadata.font_theme = _house_fonts()
        assert "House-Sans" in _embedded(render_pdf(brochure))

    @needs_pdf
    def test_a_deck_pdf_and_its_handout_embed_the_face(self):
        from qa.fixtures import pitch_16_9

        deck = pitch_16_9.build()
        deck.metadata.font_theme = _house_fonts()
        assert "House-Sans" in _embedded(render_pdf(deck))
        assert "House-Sans" in _embedded(render_handout(deck))


def test_a_chart_drawn_under_chart_style_is_set_in_the_face():
    pytest.importorskip("matplotlib", reason='chart_style needs "pyhermes[charts]"')
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    from pyhermes.data import chart_style

    style = chart_style("classic", _house_fonts())
    assert style["font.family"][0] == "Specimen Condensed"
    with plt.rc_context(style):
        figure, axes = plt.subplots()
        title = axes.set_title("Exhibit 1")
        found = font_manager.findfont(title.get_fontproperties(), fallback_to_default=False)
        plt.close(figure)
    assert Path(found).resolve() == REGULAR.resolve()
