"""
The quantitative-table fixture (#228), the proof epic #217 closes on.

A Letter portrait table using every word the epic added, crossing a sheet:
its tiered head read back from the PDF on every sheet it occupies, its sheet
count asserted, and each sheet photographed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from pyhermes.builder.components import DataTable
from pyhermes.builder.sizing import LETTER_PORTRAIT
from pyhermes.pdf import available
from qa.fixtures import all_paged_fixtures
from qa.fixtures import letter_quant_table as quant

requires_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)


def _table() -> DataTable:
    [table] = [
        component
        for section in quant.build()._sections
        for component in section.components()
        if isinstance(component, DataTable)
    ]
    return table


class TestItUsesEveryWord:
    def test_it_is_in_the_paged_gallery_at_letter_portrait(self):
        document = all_paged_fixtures()["letter_quant_table"]()
        assert document.medium.page_format == LETTER_PORTRAIT

    def test_every_column_word_is_set(self):
        columns = _table().columns
        for name in ("format", "tone", "align_decimal", "unit", "scale", "bar"):
            assert any(getattr(column, name) for column in columns), name

    def test_the_table_carries_groups_a_marker_and_raw_figures(self):
        table = _table()
        assert table.groups and table.notes
        assert any("[^1]" in cell.text for row in table.rows for cell in row.cells)
        assert any(cell.value is not None for row in table.rows for cell in row.cells)


@requires_pdf
class TestOnPaper:
    @pytest.fixture(scope="class")
    def sheets(self):
        import pypdfium2
        import weasyprint

        from pyhermes.pdf.fetcher import build_fetcher

        document = quant.build()
        pdf = pypdfium2.PdfDocument(
            weasyprint.HTML(
                string=document.render(), url_fetcher=build_fetcher(document.assets())
            ).write_pdf()
        )
        return [sheet.get_textpage().get_text_range() for sheet in pdf]

    def test_it_lays_out_to_its_sheets(self, sheets):
        assert len(sheets) == quant.SHEETS == 2

    def test_the_table_crosses_a_sheet(self, sheets):
        occupied = [text for text in sheets if any(name in text for name in quant.STRATEGIES)]
        assert len(occupied) == 2

    def test_every_sheet_of_the_table_carries_its_whole_head(self, sheets):
        heads = [g.label.upper() for g in quant.GROUPS] + ["WEIGHT", *quant.UNITS]
        for index, text in enumerate(sheets):
            if any(name in text for name in quant.STRATEGIES):
                missing = [head for head in heads if head not in text]
                assert not missing, f"sheet {index + 1} lost {missing}"

    def test_the_marked_figures_note_sits_on_its_sheet(self, sheets):
        [first] = [text for text in sheets if quant.STRATEGIES[0] in text]
        assert "no ten-year record" in first

    def test_it_is_photographed_one_image_per_sheet(self, tmp_path: Path):
        from qa.screenshots import capture_pages

        shots, _ = capture_pages({"letter_quant_table": quant.build()}, tmp_path)
        assert len(shots) == quant.SHEETS
        for shot in shots:
            assert (shot.width, shot.height) == (LETTER_PORTRAIT.width, LETTER_PORTRAIT.height)
