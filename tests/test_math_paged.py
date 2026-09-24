"""
An equation on paper (#232): it moves whole, with its caption.

Read back from the PDF through pypdfium2, sheet by sheet, in the shape of
``tests/test_pdf.py``. ``a4_equations`` engineers its second equation at a
sheet's foot, and stripping the ``.figure`` rule must split it, or the tests
above it pass for the wrong reason. Needs ``[pdf]`` and ``[qa]``.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

from qa.fixtures import a4_equations as equations
from svc.pdf import available

pytestmark = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)


def _sheets(strip_figure_rule: bool = False) -> list[tuple[str, list[tuple[int, int]]]]:
    import pypdfium2
    import pypdfium2.raw as pdfium_raw
    import weasyprint

    from svc.pdf.fetcher import build_fetcher

    document = equations.build()
    html = document.render()
    if strip_figure_rule:
        html, removed = re.subn(r"^\s*\.figure \{[^}]*\}\s*$", "", html, flags=re.M)
        assert removed == 1, "the .figure rule is not where the skeleton keeps it"
    pdf = pypdfium2.PdfDocument(
        weasyprint.HTML(string=html, url_fetcher=build_fetcher(document.assets())).write_pdf()
    )
    image = [pdfium_raw.FPDF_PAGEOBJ_IMAGE]
    return [
        (sheet.get_textpage().get_text_range(), [o.get_px_size() for o in sheet.get_objects(image)])
        for sheet in pdf
    ]


def _placed(sheets, index: int) -> tuple[list[int], list[int]]:
    """The sheets carrying equation ``index``'s image, and its caption."""
    _, caption, size = equations.EQUATIONS[index]
    return (
        [n for n, (_, images) in enumerate(sheets) if size in images],
        [n for n, (text, _) in enumerate(sheets) if caption in text],
    )


@pytest.fixture(scope="module")
def sheets():
    return _sheets()


def test_it_lays_out_to_its_sheets(sheets):
    assert len(sheets) == equations.SHEETS == 2


@pytest.mark.parametrize("index", range(len(equations.EQUATIONS)))
def test_each_equation_is_whole_and_keeps_its_caption(sheets, index):
    image_sheets, caption_sheets = _placed(sheets, index)
    assert len(image_sheets) == 1, "an equation image crossed a sheet"
    assert caption_sheets == image_sheets, "the caption left its equation"


def test_the_engineered_equation_splits_without_the_rule():
    image_sheets, caption_sheets = _placed(_sheets(strip_figure_rule=True), equations.ENGINEERED)
    assert image_sheets != caption_sheets


def test_it_is_photographed_one_image_per_sheet(tmp_path: Path):
    from qa.screenshots import capture_pages
    from svc.document import PAGED_MEDIUM

    shots, _ = capture_pages({"a4_equations": equations.build()}, tmp_path)
    assert len(shots) == equations.SHEETS
    page = PAGED_MEDIUM.page_format
    assert {(shot.width, shot.height) for shot in shots} == {(page.width, page.height)}


def test_a_centred_equation_is_centred_on_paper():
    # Found on the first raster: WeasyPrint resolved an auto margin against
    # width:100% before the cap, and every equation sat at the frame's left.
    import pypdfium2
    import pypdfium2.raw as pdfium_raw

    from svc.pdf import render_pdf

    pdf = pypdfium2.PdfDocument(render_pdf(equations.build()))
    for sheet in pdf:
        width, _ = sheet.get_size()
        for image in sheet.get_objects(filter=[pdfium_raw.FPDF_PAGEOBJ_IMAGE]):
            left, _, right, _ = image.get_bounds()
            assert abs((left + right) / 2 - width / 2) < 2, "an equation left the centre line"
