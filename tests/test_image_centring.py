"""
An aligned image is where its alignment says, in the PDF and in a browser.

A block image ignores ``text-align``, and WeasyPrint resolves ``margin: auto``
against ``width: 100%`` before the ``max-width`` cap, so a centred ``ImageBlock``
and an aligned ``ChartBlock`` sat at the left edge everywhere but Outlook. The
image is now inline in a zero-leading line box (`math.md` has the measurements).
"""

from __future__ import annotations

import importlib.util

import pytest

from qa.fixtures._png import solid_png
from qa.screenshots import available as browser_available
from svc.builder import ChartBlock, FullWidth, ImageBlock
from svc.builder.images import EmailImage
from svc.pdf import available as pdf_available

requires_pdf = pytest.mark.skipif(
    not pdf_available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

#: Each block, the side it should sit on, and a pixel size no other block shares.
CASES = {
    "centred image": (lambda: ImageBlock(_image(400, 100, "a"), caption="C"), "center"),
    "right image": (lambda: ImageBlock(_image(240, 60, "b"), align="right"), "right"),
    "left image": (lambda: ImageBlock(_image(220, 60, "c"), align="left"), "left"),
    "linked image": (
        lambda: ImageBlock(_image(260, 60, "d"), link_url="https://example.com"),
        "center",
    ),
    "centred chart": (lambda: ChartBlock(_image(600, 200, "e"), align="center"), "center"),
    "right chart": (lambda: ChartBlock(_image(580, 200, "f"), align="right"), "right"),
    "unaligned chart": (lambda: ChartBlock(_image(560, 200, "g")), "left"),
}


def _image(width: int, height: int, alt: str) -> EmailImage:
    return EmailImage.attached(solid_png(width, height, (40, 40, 40)), alt=alt, width=width // 2)


def _content_box() -> tuple[float, float]:
    """A full-width section's content column on paper: the sheet less margin and padding."""
    from svc.builder.sizing import STANDARD_SIZES
    from svc.document import PAGED_MEDIUM

    page, pad = PAGED_MEDIUM.page_format, STANDARD_SIZES.frame.pad_x
    return page.margin.left + pad, page.width - page.margin.right - pad


def _expected(side: str, left: float, right: float, width: float) -> float:
    """Where the image's centre should be, in a frame from ``left`` to ``right``."""
    if side == "center":
        return (left + right) / 2
    return left + width / 2 if side == "left" else right - width / 2


@requires_pdf
@pytest.mark.parametrize("name", list(CASES))
def test_on_paper_each_image_sits_where_its_alignment_says(name):
    import pypdfium2
    import pypdfium2.raw as pdfium_raw

    from svc.document import PagedDocument
    from svc.pdf import render_pdf

    build, side = CASES[name]
    document = PagedDocument({"firm_name": "F", "campaign_name": "C"})
    document.add_section(FullWidth(content=build()))
    [sheet] = [
        s
        for s in pypdfium2.PdfDocument(render_pdf(document))
        if list(s.get_objects(filter=[pdfium_raw.FPDF_PAGEOBJ_IMAGE]))
    ][:1]
    [image] = sheet.get_objects(filter=[pdfium_raw.FPDF_PAGEOBJ_IMAGE])
    left, _, right, _ = (v * 96 / 72 for v in image.get_bounds())
    frame_left, frame_right = _content_box()
    centre = (left + right) / 2
    assert abs(centre - _expected(side, frame_left, frame_right, right - left)) < 2


@requires_pdf
@pytest.mark.parametrize("align", ["left", "center", "right"])
def test_on_paper_a_decorative_image_follows_its_alignment(align):
    # Drawn as a CSS background on paper (#202), so it is found in the raster.
    import numpy as np
    import pypdfium2

    from svc.document import (
        EmptyBackMatter,
        EmptyCover,
        EmptyRunningFooter,
        EmptyRunningHeader,
        PagedDocument,
    )
    from svc.pdf import render_pdf

    image = EmailImage.attached(solid_png(160, 40, (10, 10, 10)), decorative=True, width=80)
    document = PagedDocument(
        {"firm_name": "F", "campaign_name": "C"},
        cover=EmptyCover(),
        running_header=EmptyRunningHeader(),
        running_footer=EmptyRunningFooter(),
        back_matter=EmptyBackMatter(),
    )
    document.add_section(FullWidth(content=ImageBlock(image, align=align)))
    sheet = next(iter(pypdfium2.PdfDocument(render_pdf(document))))
    pixels = np.asarray(sheet.render(scale=96 / 72).to_pil().convert("L"))
    _, xs = np.where(pixels < 40)
    expected = _expected(align, *_content_box(), 80)
    assert abs((xs.min() + xs.max() + 1) / 2 - expected) < 2


@pytest.mark.skipif(not browser_available(), reason='no browser; the "[qa]" extra')
def test_in_a_browser_each_image_sits_where_its_alignment_says():
    from qa.screenshots import _launch, _load_playwright, inline_cid_images
    from svc.builder.email import Email

    email = Email({"email_subject": "S", "firm_name": "F", "campaign_name": "C"})
    for build, _ in CASES.values():
        email.add_section(FullWidth(content=build()))
    html = inline_cid_images(email.render(), email)
    with _load_playwright()() as playwright:
        browser = _launch(playwright)
        page = browser.new_page(viewport={"width": 1000, "height": 900})
        page.set_content(html)
        placed = page.eval_on_selector_all(
            "td img[alt]",
            """els => els.map(e => {
                const i = e.getBoundingClientRect(), c = e.closest('td').getBoundingClientRect();
                return [e.alt, i.left, i.right, c.left, c.right];
            })""",
        )
        browser.close()
    by_alt = {alt: rest for alt, *rest in placed}
    for name, (build, side) in CASES.items():
        left, right, cell_left, cell_right = by_alt[build().image.alt]
        expected = _expected(side, cell_left, cell_right, right - left)
        assert abs((left + right) / 2 - expected) < 2, name
