"""
Per-exhibit disclosure copy — the field, and its two projections.

The epic's named risk is **projection divergence**: wiring ``context()`` and
forgetting ``text()`` ships a compliance line that a plain-text reader never
sees, which is the failure epic #53 spent four issues preventing. So every
assertion here is made against *both* projections of the same field rather
than against the HTML alone.
"""

import pytest

from svc.builder import ChartBlock, DataTable, ImageBlock, TemplateEngine
from svc.builder.images import EmailImage
from svc.builder.models import TableRow
from svc.builder.textgen import wrap

COPY = "Returns are shown gross of fees. Past performance is not indicative of future results."

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _table(**kwargs):
    return DataTable(headers=["Factor", "1M"], rows=[TableRow(cells=["Value", "+1.8%"])], **kwargs)


def _chart(**kwargs):
    return ChartBlock("https://example.com/chart.png", alt_text="Chart", **kwargs)


def _image(**kwargs):
    return ImageBlock(EmailImage.inline(_PNG, alt="Thumb"), **kwargs)


EXHIBITS = pytest.mark.parametrize(
    "build", [_table, _chart, _image], ids=["table", "chart", "image"]
)


@EXHIBITS
def test_the_disclosure_reaches_both_projections(build):
    """
    One field, both projections — the discipline #116 established.

    The text side is compared against ``wrap(COPY)``, not ``COPY``: the
    projection reflows prose to the plain-text line width, so asserting the
    unbroken sentence would fail on a *correct* projection.
    """
    assert COPY in build(disclosure=COPY).render(TemplateEngine())
    assert wrap(COPY) in build(disclosure=COPY).text()


@EXHIBITS
def test_an_unset_disclosure_renders_nothing_at_all(build):
    """
    Not merely 'renders empty'. The default has to cost **zero bytes**, or
    every pre-existing golden moves the moment the field is added — which is
    the property that let this ship without touching a shipped email.
    """
    assert build(disclosure="").render(TemplateEngine()) == build().render(TemplateEngine())
    assert build(disclosure="").text() == build().text()


@EXHIBITS
def test_the_disclosure_is_escaped_plain_text(build):
    """
    The blessed raw-HTML set stays closed at five (see ``textgen``). A
    caller's angle bracket is copy, not markup, and the template escapes it —
    so this field can never become the sixth surface by accident.
    """
    rendered = build(disclosure="Fees <1% & rising").render(TemplateEngine())
    assert "Fees &lt;1% &amp; rising" in rendered
    assert "Fees <1%" not in rendered


@EXHIBITS
def test_the_disclosure_is_justified(build):
    """
    The one thing that distinguishes it from the attribution line above it:
    a disclosure is a block meant to be read, not a trailing credit.
    """
    assert "text-align: justify" in build(disclosure=COPY).render(TemplateEngine())


@EXHIBITS
def test_the_disclosure_sits_below_the_attribution(build):
    """Ordering is the contract: exhibit, then attribution, then disclosure."""
    rendered = build(disclosure=COPY, **_ATTRIBUTION[build]).render(TemplateEngine())
    assert rendered.index(_ATTRIBUTION_COPY) < rendered.index(COPY)


_ATTRIBUTION_COPY = "Hermes Research"
_ATTRIBUTION = {
    _table: {"source": _ATTRIBUTION_COPY},
    _chart: {"source": _ATTRIBUTION_COPY},
    _image: {"caption": _ATTRIBUTION_COPY},
}


def test_every_exhibit_reads_the_one_shared_partial():
    """
    The partial exists so there is not a fourth hand-written copy of the same
    ``p`` to drift. A template that inlines its own would pass every test
    above and quietly reintroduce the drift, so the inclusion is asserted
    directly.
    """
    from svc.builder.engine import TemplateEngine as Engine

    loader = Engine()._env.loader
    for path in ("analysis/data-table.html", "analysis/chart-block.html", "media/image-block.html"):
        source = loader.get_source(Engine()._env, path)[0]
        assert 'include "common/disclosure.html"' in source, f"{path} does not share the partial"
