"""
A column's format as a contract (#225), the third child of epic #217.

One string, made once at construction by the column, read by both
projections, with the raw figure kept beside it for the scale that reads it.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from octavo.builder import DataTable
from octavo.builder.engine import TemplateEngine
from octavo.builder.enums import ColumnKind, RowKind, Tone
from octavo.builder.exceptions import ValidationError
from octavo.builder.formats import bps, pct
from octavo.builder.models import Cell, Column, TableRow


def one_year(value: float) -> str:
    return pct(value, 1, sign=True)


def _table(*rows: TableRow, **column) -> DataTable:
    spec = {"format": one_year, "tone": "auto", **column}
    return DataTable(headers=["Fund", Column("1Y", **spec)], rows=list(rows))


class TestTheColumnWritesTheFigure:
    def test_the_issue_example_renders_and_projects_one_string(self):
        table = DataTable(
            headers=[Column("1Y", format=one_year, tone="auto")], rows=[TableRow([0.0142])]
        )
        [[cell]] = [row.cells for row in table.rows]
        assert cell.text == "+1.4%" and cell.tone is Tone.POSITIVE
        html = table.render(TemplateEngine())
        assert f">{cell.text}</td>" in html
        assert table.text().splitlines()[-1].strip() == cell.text

    def test_a_negative_figure_is_toned_from_its_sign(self):
        [cell] = _table(TableRow(["A", -0.02])).rows[0].cells[1:]
        assert cell.text == "-2.0%" and cell.tone is Tone.NEGATIVE

    def test_a_figure_that_renders_as_zero_is_neutral(self):
        [cell] = _table(TableRow(["A", -0.0001])).rows[0].cells[1:]
        assert cell.tone is Tone.NEUTRAL

    def test_a_stated_tone_wins_over_the_sign(self):
        [cell] = _table(TableRow(["A", 0.02]), tone=Tone.NEGATIVE).rows[0].cells[1:]
        assert cell.tone is Tone.NEGATIVE

    def test_a_cells_own_tone_wins_over_its_column(self):
        row = TableRow(["A", Cell(value=0.02, tone=Tone.NEUTRAL)])
        assert _table(row).rows[0].cells[1].tone is Tone.NEUTRAL

    def test_no_tone_leaves_the_cell_untoned(self):
        assert _table(TableRow(["A", 0.02]), tone="").rows[0].cells[1].tone == ""

    @pytest.mark.parametrize("figure", [3, 2.5, Decimal("1.25")])
    def test_a_numeric_column_with_no_format_uses_number(self, figure):
        table = DataTable(["Fund", "Units"], [TableRow(["A", figure])])
        assert table.rows[0].cells[1].text == Cell.from_number(figure).text

    def test_a_cells_colour_and_background_survive_formatting(self):
        row = TableRow(["A", Cell(value=0.02, color="#112233", background="#FBF3E2")])
        cell = _table(row).rows[0].cells[1]
        assert (cell.color, cell.background) == ("#112233", "#FBF3E2")


class TestWhatTheContractRefuses:
    def test_a_raw_figure_in_a_text_column_raises_naming_it(self):
        with pytest.raises(ValidationError, match=r"row 0 .*0\.5.*'Fund'"):
            DataTable(["Fund", "1Y"], [TableRow([0.5, "1%"])])

    def test_a_string_in_a_formatted_column_is_left_as_written(self):
        assert _table(TableRow(["A", "n/a"])).rows[0].cells[1].text == "n/a"

    def test_a_format_that_is_not_callable_raises(self):
        with pytest.raises(ValidationError, match="column.format"):
            Column("1Y", format="pct").validate()  # type: ignore[arg-type]

    def test_a_tone_that_is_not_a_word_raises(self):
        with pytest.raises(ValidationError, match="column.tone"):
            Column("1Y", tone="#B85450").validate()

    def test_a_bool_is_not_a_figure(self):
        with pytest.raises(ValidationError, match="cells"):
            TableRow(["A", True])


class TestATableNeverChangesItsInputs:
    """Each table formats its own copy; a column's format is the contract in every table (#452)."""

    def test_two_tables_over_one_row_list_each_show_their_own_format(self):
        rows = [TableRow(["A", 0.0125]), TableRow(["B", -0.002])]
        first = DataTable(["Fund", Column("Return", format=pct)], rows)
        second = DataTable(["Fund", Column("Return", format=bps)], rows)
        assert [r.cells[1].text for r in first.rows] == ["1.25%", "-0.20%"]
        assert [r.cells[1].text for r in second.rows] == [bps(0.0125), bps(-0.002)]
        assert "1.25%" not in second.text()

    def test_the_callers_rows_and_cells_are_left_as_they_were(self):
        cell = Cell(value=0.0125, tone="negative")
        rows = [TableRow(["A", cell]), TableRow(["B", 0.5])]
        before = [
            (row, list(row.cells), [dataclasses.replace(c) for c in row.cells]) for row in rows
        ]
        DataTable(["Fund", Column("Return", format=pct, tone="auto")], rows)
        for row, cells, snapshot in before:
            assert row.cells == snapshot
            assert all(a is b for a, b in zip(row.cells, cells, strict=True))
        assert (cell.text, cell.tone) == ("", "negative")
        assert rows[1].cells[1].text == "" and rows[1].cells[1].value == 0.5

    def test_the_table_holds_copies_not_the_callers_objects(self):
        rows = [TableRow(["A", "x"])]
        table = DataTable(["Fund", "Note"], rows)
        assert table.rows[0] is not rows[0]
        assert table.rows[0].cells[0] is not rows[0].cells[0]

    def test_a_subhead_row_works_in_tables_of_different_widths(self):
        subhead = TableRow(["Equities"], kind=RowKind.SUBHEAD)
        wide = DataTable(["Name", "1Y", "3Y"], [subhead, TableRow(["A", "1%", "2%"])])
        narrow = DataTable(["Name", "1Y"], [subhead, TableRow(["B", "3%"])])
        assert len(subhead.cells) == 1
        assert [len(row.cells) for row in wide.rows] == [3, 3]
        assert [len(row.cells) for row in narrow.rows] == [2, 2]


class TestTheRawFigureIsKept:
    def test_value_holds_the_figure_after_construction(self):
        assert _table(TableRow(["A", 0.0142])).rows[0].cells[1].value == 0.0142

    def test_a_hand_written_cell_has_none(self):
        assert _table(TableRow(["A", "1.4%"])).rows[0].cells[1].value is None

    def test_cell_gained_exactly_one_field(self):
        # ``badge`` followed it (#325); ``value`` is still the one #225 added.
        names = [spec.name for spec in dataclasses.fields(Cell)]
        assert names == ["text", "align", "color", "background", "tone", "value", "badge"]


class TestAFormatMakesTheColumnNumeric:
    def test_a_formatted_first_column_is_numeric(self):
        assert Column("Rank", format=str).resolved_kind(0) is ColumnKind.NUMERIC

    def test_a_stated_kind_still_wins(self):
        assert Column("Code", kind="text", format=str).resolved_kind(1) is ColumnKind.TEXT

    def test_the_resolution_keeps_the_format(self):
        assert Column("1Y", format=one_year).resolved(1).format is one_year


def test_the_frame_adapter_formats_nothing_itself():
    # The logic moved onto the column; one path means the two cannot differ.
    import pathlib

    assert "from_number" not in pathlib.Path("octavo/data/frames.py").read_text(encoding="utf-8")
