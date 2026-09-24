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
