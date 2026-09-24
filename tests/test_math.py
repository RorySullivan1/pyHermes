"""
The ``[math]`` extra (#230): a deterministic mathtext renderer.

Every test skips without matplotlib, which is what proves the extra optional.
CI's ``data`` job installs it and runs this file. Pixel sizes are asserted
within a tolerance, never as bytes: fonts may differ between machines.
"""

from __future__ import annotations

import struct
import zlib

import pytest

from svc.builder.exceptions import ValidationError

pytest.importorskip("matplotlib", reason='rendering an equation is the "[math]" extra')

from svc.math import FONTSETS, MathError, MathSyntaxError, render_math  # noqa: E402

SOURCE = r"\sigma_p^2 = w^\top \Sigma w"
ARGS = {"font_px": 14, "color": "#3B3B3B", "scale": 3, "fontset": "dejavusans"}


def _render(latex: str = SOURCE, **overrides):
    return render_math(latex, **{**ARGS, **overrides})


def _chunks(png: bytes) -> list[tuple[bytes, bytes]]:
    out, at = [], 8
    while at < len(png):
        (length,) = struct.unpack(">I", png[at : at + 4])
        out.append((png[at + 4 : at + 8], png[at + 8 : at + 8 + length]))
        at += 12 + length
    return out


class TestTheBytesAreDeterministicAndVersionless:
    def test_two_renders_are_equal(self):
        assert _render().png == _render().png

    def test_no_software_chunk(self):
        text = [data for kind, data in _chunks(_render().png) if kind in (b"tEXt", b"iTXt")]
        assert not any(data.startswith(b"Software") for data in text)

    def test_the_size_is_the_headers(self):
        rendered = _render()
        assert (rendered.width_px, rendered.height_px) == struct.unpack(">II", rendered.png[16:24])

    def test_the_width_scales_linearly(self):
        one = _render(scale=1).width_px
        for n in (2, 3, 4):
            assert abs(_render(scale=n).width_px - n * one) <= n

    def test_it_is_transparent(self):
        # IHDR colour type 6 is RGBA; the first pixel of the first row is clear.
        rendered = _render()
        assert rendered.png[25] == 6
        raw = zlib.decompress(b"".join(d for k, d in _chunks(rendered.png) if k == b"IDAT"))
        assert raw[1 + 3] == 0, "the corner pixel's alpha"

    def test_the_five_fontsets_give_five_byte_streams(self):
        assert len({_render(fontset=name).png for name in FONTSETS}) == 5


class TestASourceMathtextRefuses:
    @pytest.mark.parametrize(
        ("latex", "named"),
        [
            (r"\begin{aligned} a \end{aligned}", r"\begin"),
            (r"a \\ b", "Expected end of text"),
            (r"x \le y", r"\le"),
            (r"\displaystyle x", r"\displaystyle"),
        ],
    )
    def test_it_raises_naming_the_symbol_and_the_source(self, latex, named):
        with pytest.raises(MathSyntaxError) as caught:
            _render(latex)
        assert named in str(caught.value) and repr(latex) in str(caught.value)
        assert isinstance(caught.value, MathError) and isinstance(caught.value, ValueError)
        assert isinstance(caught.value.__cause__, ValueError)


class TestTheArgumentsAreValidated:
    @pytest.mark.parametrize("fontset", ["custom", "helvetica"])
    def test_a_fontset_outside_the_five(self, fontset):
        with pytest.raises(ValidationError, match="dejavusans"):
            _render(fontset=fontset)

    @pytest.mark.parametrize(
        ("name", "value"),
        [("color", "black"), ("font_px", 0), ("font_px", -3), ("scale", 0), ("scale", True)],
    )
    def test_a_bad_argument_is_named(self, name, value):
        with pytest.raises(ValidationError, match=name if name != "color" else "black"):
            _render(**{name: value})

    @pytest.mark.parametrize("latex", ["a\nb", "$x$", "a $ b", ""])
    def test_a_bad_source_is_refused_before_any_render(self, latex):
        with pytest.raises(ValidationError, match="latex"):
            _render(latex)

    def test_an_escaped_dollar_is_a_symbol(self):
        assert _render(r"\$5").width_px > 0


# ----------------------------------------------------------------------
# #231 — math_block, painted for the caller's theme and density
# ----------------------------------------------------------------------

from svc.math import (  # noqa: E402
    DEFAULT_MATH_FONTSET,
    DEFAULT_MATH_SCALE,
    image_from_math,
    math_block,
)


def _darkest(png: bytes) -> tuple[int, int, int]:
    """The darkest fully opaque pixel: the glyph's own colour, free of antialiasing."""
    import io

    from PIL import Image

    image = Image.open(io.BytesIO(png)).convert("RGBA")
    opaque = [px[:3] for px in image.getdata() if px[3] == 255]
    return min(opaque, key=sum)


def _near(rgb: tuple[int, int, int], hexa: str, tolerance: int = 8) -> bool:
    target = [int(hexa[i : i + 2], 16) for i in (1, 3, 5)]
    return all(abs(a - b) <= tolerance for a, b in zip(rgb, target, strict=True))


class TestTheBlockIsPaintedForItsTheme:
    def test_the_default_is_classic_body_text(self):
        from svc.builder.theming import DEFAULT_THEME

        block = math_block(SOURCE, label="Equation")
        assert block.image.src.startswith("cid:") and block.image.alt == SOURCE
        assert _near(_darkest(block.image.data), DEFAULT_THEME.text.primary)

    def test_the_width_is_the_pixel_width_over_the_scale(self):
        rendered = render_math(
            SOURCE, font_px=14, color="#3B3B3B", scale=DEFAULT_MATH_SCALE, fontset="cm"
        )
        image = image_from_math(SOURCE)
        assert image.width == round(rendered.width_px / DEFAULT_MATH_SCALE)

    def test_slate_paints_another_picture(self):
        from svc.builder.theming import SLATE_THEME

        classic, slate = image_from_math(SOURCE), image_from_math(SOURCE, theme="slate")
        assert classic.content_id != slate.content_id
        assert _near(_darkest(slate.data), SLATE_THEME.text.primary)

    def test_a_denser_scheme_draws_smaller_type(self):
        compact = image_from_math(SOURCE, size_theme="compact")
        spacious = image_from_math(SOURCE, size_theme="spacious")
        assert spacious.width > compact.width

    def test_one_source_twice_is_attached_once(self):
        from svc.builder import FullWidth
        from svc.builder.email import Email

        email = Email({"email_subject": "S", "firm_name": "F", "campaign_name": "C"})
        email.add_section(FullWidth(content=math_block(SOURCE, label="Equation")))
        email.add_section(FullWidth(content=math_block(SOURCE, label="Equation")))
        assert len(email.assets()) == 1


class TestTheDefaultsAreDecisions:
    def test_the_fontset_is_computer_modern(self):
        assert DEFAULT_MATH_FONTSET == "cm"

    def test_the_scale_covers_print(self):
        from svc.config import get_config

        assert DEFAULT_MATH_SCALE == 4
        assert DEFAULT_MATH_SCALE * 96 >= get_config().print_dpi

    def test_no_colour_size_or_font_parameter_is_exposed(self):
        import inspect

        banned = {"color", "colour", "font_px", "font_size", "font", "line_height", "size_px"}
        for function in (math_block, image_from_math):
            assert not banned & set(inspect.signature(function).parameters), function.__name__


def test_print_keeps_the_pixels_and_screen_caps_them():
    pytest.importorskip("weasyprint")
    pypdfium2 = pytest.importorskip("pypdfium2")
    import pypdfium2.raw as pdfium_raw

    from svc.builder import FullWidth
    from svc.document import PagedDocument
    from svc.pdf import PRINT, SCREEN, render_pdf

    document = PagedDocument({"firm_name": "F", "campaign_name": "C"})
    block = math_block(r"\hat{\beta} = (X^\top X)^{-1} X^\top y", label="Equation")
    document.add_section(FullWidth(content=block))

    def placed(profile):
        pdf = pypdfium2.PdfDocument(render_pdf(document, profile))
        [image] = [
            obj for page in pdf for obj in page.get_objects(filter=[pdfium_raw.FPDF_PAGEOBJ_IMAGE])
        ]
        left, _, right, _ = image.get_bounds()
        return image.get_px_size(), (right - left) * 96 / 72

    (print_px, _), (screen_px, shown) = placed(PRINT), placed(SCREEN)
    rendered = render_math(
        block.latex, font_px=14, color="#3B3B3B", scale=DEFAULT_MATH_SCALE, fontset="cm"
    )
    assert print_px == (rendered.width_px, rendered.height_px)
    assert screen_px[0] <= round(shown / 96 * 150) + 1 < print_px[0]


#: Pixel sizes under the defaults at 14px, measured locally (matplotlib 3.11.2,
#: Python 3.11). CI's runners render the same within this tolerance, or the
#: fonts differ between machines and `math.md` must say so.
MEASURED = {
    r"\sigma_p^2 = w^\top \Sigma w": (319, 87),
    r"\hat{\beta} = (X^\top X)^{-1} X^\top y": (496, 85),
    r"\text{VaR}_{99\%} = -q_{0.01}(r)": (480, 71),
}


@pytest.mark.parametrize(("latex", "size"), MEASURED.items())
def test_the_render_size_matches_what_was_measured(latex, size):
    rendered = render_math(
        latex, font_px=14, color="#3B3B3B", scale=DEFAULT_MATH_SCALE, fontset=DEFAULT_MATH_FONTSET
    )
    assert abs(rendered.width_px - size[0]) <= 4 and abs(rendered.height_px - size[1]) <= 4


# ----------------------------------------------------------------------
# #232 — several lines, one image, aligned as a block
# ----------------------------------------------------------------------

LINES = [
    r"\text{VaR}_{99\%} = -q_{0.01}(r)",
    r"\text{ES}_{99\%} = \mathbb{E}[r \mid r \leq q_{0.01}]",
]


class TestTheMultiLineShim:
    def test_two_lines_are_one_block_with_two_source_lines(self):
        block = math_block(lines=LINES, label="Equation", caption="Tail risk")
        assert len(block.images()) == 1
        assert [line for line in block.text().splitlines() if line.startswith("$")] == [
            f"${line}$" for line in LINES
        ]
        assert block.image.alt == "\n".join(LINES)

    def test_two_lines_render_taller_than_one(self):
        one = render_math(LINES[0], **ARGS)
        two = render_math(lines=LINES, **ARGS)
        assert two.height_px > one.height_px * 1.5

    def test_the_block_alignment_changes_the_picture_not_its_size(self):
        left = render_math(lines=LINES, align_lines="left", **ARGS)
        right = render_math(lines=LINES, align_lines="right", **ARGS)
        assert left.png != right.png
        assert abs(left.width_px - right.width_px) <= 2

    @pytest.mark.parametrize(
        ("kwargs", "named"),
        [
            ({"lines": [r"a &= b", "c"]}, "cannot align on a relation"),
            ({"lines": []}, "lines"),
            ({"latex": "x", "lines": LINES}, "not both"),
            ({"lines": LINES, "align_lines": "justify"}, "align_lines"),
        ],
    )
    def test_each_refusal_names_the_argument(self, kwargs, named):
        with pytest.raises(ValidationError, match=named):
            math_block(**kwargs)


def test_twenty_equations_ride_the_manifest_not_the_html():
    """Measured for #232: 280 KB on the wire against a 15 MB warning; math.md records it."""
    from svc.builder import FullWidth
    from svc.builder.email import Email
    from svc.config import get_config
    from svc.delivery import build_message
    from svc.delivery.message import to_wire_bytes

    email = Email({"email_subject": "S", "firm_name": "F", "campaign_name": "C"})
    for i in range(20):
        source = rf"\sigma_{{{i}}}^2 = \sum_j w_j^2 \sigma_j^2 + {i}"
        email.add_section(FullWidth(content=math_block(source, label="Equation")))
    html = email.render()
    wire = to_wire_bytes(build_message(email, sender="a@example.com", to="b@example.com"))
    assert len(email.assets()) == 20
    assert len(wire) < get_config().attachment_warn_kb * 1024
    assert len(html.encode()) < 40 * 1024, "the image bytes leaked into the HTML part"
