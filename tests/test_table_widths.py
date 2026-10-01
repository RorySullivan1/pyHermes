"""
A table column's share of the width (#271).

``Column.width`` is a relative weight, emitted as a percentage ``width``
attribute on each heading cell, because the Word engine honours a cell's width
attribute where it ignores CSS. A table that sets no weight renders byte for
byte as it did before, which leaves the widths to the client.
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from pyhermes.builder import DataTable, FullWidth
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.models import Cell, Column, TableRow
from pyhermes.pdf import available as pdf_available
from qa.screenshots import available as browser_available

#: Weights whose shares do not divide evenly, so the rounding is exercised.
WEIGHTS = (3, 1, 2)
SHARES = (50, 17, 33)

#: One background per column, so a raster can find each column's extent.
GROUNDS = ("#C0392B", "#27AE60", "#2980B9")


def _table(weights=WEIGHTS, grounds=False) -> DataTable:
    headers = [Column(name, width=w) for name, w in zip(("Name", "A", "B"), weights, strict=True)]
    cells = ["Value", "1.0", "2.0"]
    if grounds:
        cells = [Cell(text, background=g) for text, g in zip(cells, GROUNDS, strict=True)]
    return DataTable(headers=headers, rows=[TableRow(cells)])


def _widths(html: str) -> list[str]:
    return re.findall(r'<th scope="col"[^>]*?(?: width="([^"]+)")?\s+style=', html)


class TestTheShares:
    def test_weights_become_percentages_on_the_heading_cells(self):
        assert _widths(_table().render(TemplateEngine())) == [f"{s}%" for s in SHARES]

    @pytest.mark.parametrize(
        "weights",
        [(1, 1, 1), (3, 1, 2), (1, 2, 4), (0.5, 0.25, 7), (5, None, None), (None, 1.5, None)],
    )
    def test_the_shares_sum_to_100(self, weights):
        shares = [int(w.rstrip("%")) for w in _table(weights)._widths()]
        assert sum(shares) == 100

    def test_an_unset_column_weighs_one(self):
        assert _table((3, None, 1))._widths() == ["60%", "20%", "20%"]

    def test_with_no_weight_set_nothing_is_emitted(self):
        plain = DataTable(headers=["Name", "A", "B"], rows=[TableRow(["Value", "1.0", "2.0"])])
        unset = _table((None, None, None))
        html = plain.render(TemplateEngine())
        assert html == unset.render(TemplateEngine())
        assert " width=" not in html.split("<thead>")[1].split("</thead>")[0]

    def test_the_plain_text_projection_is_unchanged(self):
        assert _table().text() == _table((None, None, None)).text()

    @pytest.mark.parametrize("bad", [0, -1, True, "3", float("nan")])
    def test_a_weight_that_is_not_positive_is_refused_at_construction(self, bad):
        with pytest.raises(ValidationError, match="column.width"):
            _table((bad, None, None))


def _measure_in_chromium(table: DataTable) -> tuple[float, list[float]]:
    from qa.screenshots import _launch, _load_playwright

    with _load_playwright()() as playwright:
        browser = _launch(playwright)
        page = browser.new_page(viewport={"width": 1000, "height": 900})
        page.set_content(FullWidth(content=table).render(TemplateEngine()))
        table_width, heads = page.evaluate(
            """() => {
                const t = document.querySelector('table.data-table');
                const heads = [...t.querySelectorAll('th[scope=col]')];
                return [t.getBoundingClientRect().width,
                        heads.map(h => h.getBoundingClientRect().width)];
            }"""
        )
        browser.close()
    return table_width, heads


@pytest.mark.skipif(not browser_available(), reason='no browser; the "[qa]" extra')
def test_in_chromium_the_columns_take_their_shares():
    table_width, heads = _measure_in_chromium(_table())
    for head, share in zip(heads, SHARES, strict=True):
        assert abs(head / table_width * 100 - share) < 1.5, (heads, table_width)


@pytest.mark.skipif(
    not pdf_available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)
def test_on_paper_the_columns_take_their_shares():
    import numpy as np
    import pypdfium2

    from pyhermes.document import (
        EmptyBackMatter,
        EmptyCover,
        EmptyRunningFooter,
        EmptyRunningHeader,
        PagedDocument,
    )
    from pyhermes.pdf import render_pdf

    document = PagedDocument(
        {"firm_name": "F", "campaign_name": "C"},
        cover=EmptyCover(),
        running_header=EmptyRunningHeader(),
        running_footer=EmptyRunningFooter(),
        back_matter=EmptyBackMatter(),
    )
    document.add_section(FullWidth(content=_table(grounds=True)))
    sheet = next(iter(pypdfium2.PdfDocument(render_pdf(document))))
    pixels = np.asarray(sheet.render(scale=96 / 72).to_pil().convert("RGB")).astype(int)
    spans = []
    for ground in GROUNDS:
        rgb = [int(ground[i : i + 2], 16) for i in (1, 3, 5)]
        _, xs = np.where(np.abs(pixels - rgb).max(axis=2) <= 2)
        spans.append(xs.max() - xs.min() + 1)
    total = sum(spans)
    for span, share in zip(spans, SHARES, strict=True):
        assert abs(span / total * 100 - share) < 1.5, spans
