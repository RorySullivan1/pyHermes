"""
Per-column alignment and kind (#117), the first step of the DataTable epic #116.

The claim this file exists to hold: **alignment resolves once, and both
projections read that one resolution.** Before #117 the rule lived as
``loop.first`` in the template and was *re-derived* in
``svc/builder/textgen.py`` so the two would agree — correct, and impossible
to extend. A test that only checked the HTML would let them drift apart.
"""

from __future__ import annotations

import re

import pytest

from svc.builder import DataTable
from svc.builder.engine import TemplateEngine
from svc.builder.enums import ColumnAlign, ColumnKind, RowKind
from svc.builder.exceptions import ValidationError
from svc.builder.models import Cell, Column, TableRow, coerce_cell, coerce_column
from svc.builder.textgen import table as text_table

TEMPLATE = TemplateEngine().template_dir / "analysis" / "data-table.html"


def _html(component: DataTable) -> str:
    return component.render(TemplateEngine())


def _html_aligns(html: str) -> list[str]:
    """The `text-align` of each cell in the first body row."""
    row = html.split("<tr")[2]
    return re.findall(r"text-align: ([a-z]+)", row)


def _text_align_of(column_text: str) -> str:
    """Infer a text column's alignment from where its padding sits."""
    left, right = column_text != column_text.lstrip(), column_text != column_text.rstrip()
    if left and right:
        return "center"
    return "right" if left else "left"


class TestTheResolutionReproducesTheOldConvention:
    """
    Byte-identity is the bar: a table built from plain strings must render
    exactly as it did before this class existed.
    """

    def test_strings_and_columns_render_identically(self):
        rows = [TableRow(["Value", "+1.8%"]), TableRow(["Momentum", "-11.2%"])]
        from_strings = DataTable(["Factor", "1M"], rows)
        from_columns = DataTable([Column("Factor"), Column("1M")], rows)

        assert _html(from_strings) == _html(from_columns)
        assert from_strings.text() == from_columns.text()

    def test_the_position_rule_is_the_old_loop_first(self):
        column = Column("Anything")
        assert column.resolved_kind(0) is ColumnKind.TEXT
        assert column.resolved_kind(1) is ColumnKind.NUMERIC
        assert column.resolved_align(0) is ColumnAlign.LEFT
        assert column.resolved_align(3) is ColumnAlign.RIGHT

    def test_headers_still_reads_back_as_strings(self):
        component = DataTable(["Factor", Column("1M")], [TableRow(["a", "b"])])
        assert component.headers == ["Factor", "1M"]


class TestTheChainRunsThroughKind:
    def test_a_text_column_anywhere_is_left_aligned(self):
        """
        The point of naming the kind: saying `kind="text"` on the third
        column gets left alignment without also having to say so.
        """
        assert Column("Desk", kind="text").resolved_align(2) is ColumnAlign.LEFT

    def test_a_numeric_first_column_is_right_aligned(self):
        assert Column("Rank", kind="numeric").resolved_align(0) is ColumnAlign.RIGHT

    def test_an_explicit_align_wins_over_the_kind(self):
        column = Column("Mid", align="center", kind="numeric")
        assert column.resolved_align(1) is ColumnAlign.CENTER
        assert column.resolved_kind(1) is ColumnKind.NUMERIC


class TestTheCaseThatWasImpossible:
    """Two text columns — unreachable before #117, at any argument."""

    def build(self) -> DataTable:
        return DataTable(
            [Column("Name", kind="text"), Column("Desk", kind="text"), "1M"],
            [TableRow(["Value", "Global Macro", "+1.8%"])],
        )

    def test_both_text_columns_are_left_aligned(self):
        assert _html_aligns(_html(self.build()))[:2] == ["left", "left"]

    def test_only_the_numeric_column_takes_the_numeric_face(self):
        html = _html(self.build())
        row = html.split("<tr")[2]
        assert row.count("Courier") == 2, "one numeric cell, whose stack names Courier twice"

    def test_only_the_numeric_column_is_bold(self):
        row = _html(self.build()).split("<tr")[2]
        assert row.count("font-weight: bold") == 1


class TestBothProjectionsAgree:
    """
    The criterion #117 exists for. Two independent readers, one resolution —
    asserted against the source rather than against each other, so a test
    cannot pass by both being wrong in the same way.
    """

    @staticmethod
    def build() -> DataTable:
        return DataTable(
            [
                Column("Name", kind="text"),
                Column("Middle", align="center"),
                Column("Figure"),
            ],
            [TableRow(["Value", "x", "1"]), TableRow(["Momentum", "wide-value", "-11.2%"])],
        )

    def test_the_html_reads_the_resolved_alignment(self):
        component = self.build()
        expected = [column.align for column in component.resolved_columns()]
        assert _html_aligns(_html(component)) == expected

    def test_the_text_projection_reads_the_same_resolution(self):
        component = self.build()
        expected = [column.align for column in component.resolved_columns()]

        # The short row, sliced back into its columns by the rule's own widths.
        lines = component.text().splitlines()
        widths = [len(part) for part in lines[1].split("  ")]
        short = lines[2]
        observed, at = [], 0
        for width in widths:
            observed.append(_text_align_of(short[at : at + width]))
            at += width + 2

        assert observed == expected

    def test_a_numeric_first_column_moves_in_both(self):
        """
        `textgen.table()` used to assume column zero was the label. A table
        that says otherwise must move in the text part too, not only in the
        markup.
        """
        component = DataTable(
            [Column("Rank", kind="numeric"), Column("Name", kind="text")],
            [TableRow(["1", "Value"]), TableRow(["10", "Momentum"])],
        )
        assert _html_aligns(_html(component)) == ["right", "left"]
        # "Rank" is four wide, so a right-aligned "1" carries three spaces.
        assert component.text().splitlines()[2] == "   1  Value"


class TestTextTableTakesItsAlignments:
    def test_omitted_aligns_keep_the_pre_117_default(self):
        """
        A caller composing a table by hand still gets sensible output, so
        the fallback is the convention rather than an error.
        """
        rendered = text_table(["A", "B"], [["x", "1"], ["longer", "22"]])
        assert rendered.splitlines()[2] == "x        1"

    def test_center_is_honoured(self):
        rendered = text_table(["A"], [["x"], ["wide-cell"]], aligns=["center"])
        assert rendered.splitlines()[2] == "    x"


class TestValidation:
    @pytest.mark.parametrize("bad", ["middle", "justify", "LEFT", "top"])
    def test_an_unknown_align_raises_naming_the_field(self, bad):
        with pytest.raises(ValidationError, match="column.align"):
            coerce_column(Column("H", align=bad))

    @pytest.mark.parametrize("bad", ["number", "string", "TEXT", "money"])
    def test_an_unknown_kind_raises_naming_the_field(self, bad):
        with pytest.raises(ValidationError, match="column.kind"):
            coerce_column(Column("H", kind=bad))

    def test_an_empty_header_raises(self):
        with pytest.raises(ValidationError, match="column.header"):
            coerce_column(Column(""))

    def test_a_non_string_non_column_raises_naming_where_it_came_from(self):
        with pytest.raises(ValidationError, match=r"headers\[1\]"):
            DataTable(["Factor", 7], [TableRow(["a", "b"])])

    def test_the_cell_count_message_still_names_the_row(self):
        with pytest.raises(ValidationError, match="row 0 has 1 cells"):
            DataTable(["A", "B"], [TableRow(["only"])])

    def test_a_bare_string_is_accepted_and_validated(self):
        assert coerce_column("Factor") == Column("Factor")


class TestTheConventionCannotCreepBack:
    def test_the_template_no_longer_decides_from_a_columns_position(self):
        """
        `loop.first` was correct and compact, and it decided four things at
        once. Grep-asserted, because re-introducing it would render correctly
        today and quietly make `Column` unreachable.
        """
        assert "loop.first" not in TEMPLATE.read_text()

    def test_the_template_reads_the_resolved_keys(self):
        source = TEMPLATE.read_text()
        assert "column.align" in source, "the header row reads the resolved column alignment"
        assert "cell.align" in source, "each body cell reads its own resolved alignment (#118)"
        assert "cell.is_text" in source, "the face follows the resolved kind, not a position"


class TestTheCellIsTheUnit:
    """
    #118. Two index-aligned lists held in step by a validator is the shape an
    object replaces — `LinkRow`'s reason: the row has a variable-length part,
    and variable length is what fields cannot express.
    """

    def test_strings_coerce_to_cells(self):
        assert TableRow(["a", "b"]).cells == [Cell(text="a"), Cell(text="b")]

    def test_strings_and_cells_mix_freely(self):
        row = TableRow(["a", Cell("b", color="#00FF00")])
        assert row.cells[0].text == "a"
        assert row.cells[1].color == "#00FF00"

    def test_a_non_string_non_cell_raises_naming_where_it_came_from(self):
        with pytest.raises(ValidationError, match=r"cells\[1\]"):
            TableRow(["a", 7])

    def test_a_bare_string_is_accepted(self):
        assert coerce_cell("x") == Cell(text="x")


class TestTheFlatColorSpelling:
    """
    `colors` is kept because it is the common call path — the same
    flat-keyword pattern `EmailMetadata` uses for its region fields.
    """

    def test_the_two_spellings_converge(self):
        """
        Asserted as *convergence*, not by pinning each separately: two
        spellings pinned apart can drift; two asserted equal cannot.
        """
        flat = DataTable(["A", "B"], [TableRow(["x", "1"], colors=["", "#00FF00"])])
        explicit = DataTable(["A", "B"], [TableRow([Cell("x"), Cell("1", color="#00FF00")])])
        assert _html(flat) == _html(explicit)
        assert flat.text() == explicit.text()

    def test_colors_is_an_initvar_so_the_cell_is_the_single_owner(self):
        """
        Constructor-only: absent from `fields()`, `repr` and `==`, so there is
        no second place a cell's colour can live and go stale.

        Note `getattr(row, "colors")` still answers `None` — an `InitVar`
        with a default leaves that default on the *class*. `EmailMetadata`'s
        flat region keywords behave identically, so this is the established
        shape rather than a wrinkle in this row.
        """
        import dataclasses

        row = TableRow(["a"], colors=["#00FF00"])
        assert "colors" not in {f.name for f in dataclasses.fields(TableRow)}
        assert "colors" not in repr(row)
        assert row == TableRow([Cell("a", color="#00FF00")])

    def test_both_spellings_at_once_raises_rather_than_picking_one(self):
        with pytest.raises(ValidationError, match="both set"):
            TableRow([Cell("x", color="#00FF00")], colors=["#FF0000"])

    def test_a_mismatched_length_still_raises(self):
        with pytest.raises(ValidationError, match="same length"):
            TableRow(["a", "b"], colors=["#00FF00"])

    def test_a_malformed_flat_colour_raises(self):
        with pytest.raises(ValidationError, match="table_row.color"):
            TableRow(["a"], colors=["nope"])


class TestTheChainCompletesAtTheCell:
    def test_a_cell_align_overrides_its_column(self):
        component = DataTable(
            ["Factor", "1M"],
            [TableRow(["Value", Cell("+1.8%", align="left")])],
        )
        assert _html_aligns(_html(component)) == ["left", "left"]

    def test_an_unset_cell_inherits_the_column(self):
        component = DataTable([Column("Mid", align="center"), "1M"], [TableRow(["x", "1"])])
        assert _html_aligns(_html(component))[0] == "center"

    def test_the_override_reaches_the_html_only(self):
        """
        A cell-level override is a property of one cell, so the plain-text
        projection — whose columns are aligned as columns — is unmoved. The
        two parts still agree about the *column*, which is what #117's rule
        is about.
        """
        plain = DataTable(["A", "B"], [TableRow(["x", "1"])])
        nudged = DataTable(["A", "B"], [TableRow(["x", Cell("1", align="left")])])
        assert plain.text() == nudged.text()
        assert _html(plain) != _html(nudged)


class TestCellColoursAreSemanticData:
    def test_a_background_renders_on_that_cell_only(self):
        component = DataTable(
            ["A", "B"],
            [TableRow([Cell("x", background="#FFF3CD"), "1"])],
        )
        row = _html(component).split("<tr")[2]
        assert row.count("#FFF3CD") == 1

    def test_a_background_leaves_the_rows_striping_intact(self):
        """
        A caller marking one figure must not have to restate the striping.
        """
        component = DataTable(
            ["A", "B"],
            [TableRow(["x", "1"]), TableRow([Cell("y", background="#FFF3CD"), "2"])],
        )
        alt_row = _html(component).split("<tr")[3]
        assert "#FFF3CD" in alt_row
        # the untouched cell in the same row still takes the alternating tint
        assert alt_row.count("background-color") == 2
        assert "#FFF3CD" not in alt_row.split("<td")[2]

    def test_an_explicit_colour_wins_over_the_kind(self):
        """
        The caller said something about this figure; the theme is only the
        fallback behind it. That holds for a text column too — a colour set
        on a label is not silently discarded.
        """
        component = DataTable(["A", "B"], [TableRow([Cell("x", color="#B85450"), "1"])])
        assert "#B85450" in _html(component).split("<tr")[2]

    def test_an_unset_colour_takes_the_theme(self):
        html = _html(DataTable(["A", "B"], [TableRow(["x", "1"])]))
        assert "#" in html.split("<tr")[2]

    @pytest.mark.parametrize("field", ["color", "background"])
    def test_a_malformed_colour_raises_naming_the_field(self, field):
        with pytest.raises(ValidationError, match=f"cell.{field}"):
            coerce_cell(Cell("x", **{field: "red"}))

    def test_an_unknown_cell_align_raises_naming_the_field(self):
        with pytest.raises(ValidationError, match="cell.align"):
            coerce_cell(Cell("x", align="middle"))

    def test_the_docstring_states_the_boundary(self):
        """
        The fourth bounded exception survives on its *justification*. A
        docstring that stopped saying why would leave a colour parameter with
        no argument behind it — which is how a closed list quietly opens.
        """
        assert Cell.__doc__ is not None
        doc = " ".join(Cell.__doc__.split())
        assert "not control over appearance" in doc
        assert "fourth** bounded exception" in doc
        assert "not**: a styling surface" in doc


class TestThereIsNoStylingSurface:
    @pytest.mark.parametrize("forbidden", ["font", "size", "border", "padding", "weight"])
    def test_the_cell_takes_no_presentation_beyond_the_two_colours(self, forbidden):
        """
        The boundary, enforced rather than promised: colour is admitted as
        data about a figure, and nothing else follows it in.
        """
        import dataclasses

        names = {f.name for f in dataclasses.fields(Cell)}
        assert not [n for n in names if forbidden in n], names


def _rows_html(component: DataTable) -> list[str]:
    return _html(component).split("<tr")[2:]


class TestRowKinds:
    """
    #119. A row's kind is **chrome** — it renders from theme tokens and takes
    no caller colours, unlike a cell's colour, which is data. The two land
    close together and are easy to conflate.
    """

    @staticmethod
    def build() -> DataTable:
        return DataTable(
            ["Sleeve", "1M"],
            [
                TableRow(["Global", "1"]),
                TableRow(["Fixed income"], kind="subhead"),
                TableRow(["Sovereign", "2"]),
                TableRow(["Credit", "3"]),
                TableRow(["Total", "6"], kind=RowKind.TOTAL),
            ],
        )

    def test_a_plain_row_is_unchanged(self):
        """Every pre-existing table renders byte-identically."""
        plain = DataTable(["A", "B"], [TableRow(["x", "1"])])
        explicit = DataTable(["A", "B"], [TableRow(["x", "1"], kind="data")])
        assert _html(plain) == _html(explicit)
        assert plain.text() == explicit.text()

    def test_a_total_is_ruled_off_above(self):
        assert "border-top" in _rows_html(self.build())[4]

    def test_only_the_total_is_ruled(self):
        ruled = [i for i, r in enumerate(_rows_html(self.build())) if "border-top" in r]
        assert ruled == [4]

    def test_a_total_is_bold_across_the_row(self):
        assert _rows_html(self.build())[4].count("font-weight: bold") == 2

    def test_a_total_is_never_striped(self):
        component = DataTable(
            ["A", "B"],
            [TableRow(["x", "1"]), TableRow(["Total", "1"], kind="total")],
        )
        # The total sits where an alternating tint would otherwise fall.
        assert "#F8F7F5" not in _rows_html(component)[1]

    def test_a_subhead_carries_its_label_in_the_label_face(self):
        row = _rows_html(self.build())[1]
        assert "Fixed income" in row
        assert row.count("font-weight: bold") == 2

    def test_a_subhead_takes_the_highlight_tint(self):
        assert "#F8F7F5" in _rows_html(self.build())[1]

    def test_a_subhead_is_padded_to_the_tables_width(self):
        """
        One cell is the honest way to write a heading; the caller should not
        have to spell out the empties for a band that spans the table.
        """
        component = self.build()
        assert len(component.rows[1].cells) == 2
        assert component.rows[1].cells[1].text == ""

    def test_a_subhead_may_still_be_written_out_in_full(self):
        one = DataTable(["A", "B"], [TableRow(["Group"], kind="subhead")])
        full = DataTable(["A", "B"], [TableRow(["Group", ""], kind="subhead")])
        assert _html(one) == _html(full)

    def test_a_wrong_length_row_is_still_a_mistake(self):
        with pytest.raises(ValidationError, match="row 0 has 2 cells"):
            DataTable(["A", "B", "C"], [TableRow(["Group", "stray"], kind="subhead")])

    def test_an_unknown_kind_raises_listing_the_vocabulary(self):
        with pytest.raises(ValidationError, match="table_row.kind"):
            TableRow(["a"], kind="footer")


class TestStripingCountsDataRows:
    def test_a_subhead_does_not_invert_the_rows_beneath_it(self):
        """
        The bug a naive index-parity implementation ships: everything below
        the first subhead stripes the wrong way.
        """
        component = TestRowKinds.build()
        tinted = ["#F8F7F5" in row for row in _rows_html(component)]
        # data rows are indices 0, 2, 3 → the second data row is the tinted one
        assert tinted[0] is False
        assert tinted[2] is True
        assert tinted[3] is False

    def test_a_total_does_not_consume_a_stripe(self):
        component = DataTable(
            ["A", "B"],
            [
                TableRow(["x", "1"]),
                TableRow(["Sub", "1"], kind="total"),
                TableRow(["y", "2"]),
            ],
        )
        rows = _rows_html(component)
        assert "#F8F7F5" not in rows[0]
        assert "#F8F7F5" in rows[2], "the next data row is still the alternating one"


class TestRowKindsProjectInText:
    """
    The half most likely to be forgotten: a total indistinguishable from a
    data row in the text part is a total only half the readers can find.
    """

    def test_a_total_is_ruled_off_above(self):
        lines = TestRowKinds.build().text().splitlines()
        assert lines[-2].startswith("---")
        assert lines[-1].startswith("Total")

    def test_the_rule_matches_the_headers(self):
        lines = TestRowKinds.build().text().splitlines()
        assert lines[-2] == lines[1]

    def test_a_subhead_is_a_bare_label_on_its_own_line(self):
        """
        Unpadded: plain text has no merged cell, and padding a heading into
        columns would read as a data row with an empty field.
        """
        assert "Fixed income" in TestRowKinds.build().text().splitlines()

    def test_a_subhead_line_carries_no_column_padding(self):
        line = next(
            row for row in TestRowKinds.build().text().splitlines() if "Fixed income" in row
        )
        assert line == "Fixed income"


class TestARowKindIsChromeNotData:
    def test_it_takes_no_caller_colours(self):
        """
        The distinction #118 and #119 are easy to conflate on: a cell's
        colour is the caller's claim about a figure, a row's kind is a
        statement about the row's role — so it renders from theme tokens and
        the vocabulary is a closed set of three words.
        """
        import dataclasses

        assert {k.value for k in RowKind} == {"data", "total", "subhead"}
        names = {f.name for f in dataclasses.fields(TableRow)}
        assert not [n for n in names if "color" in n or "background" in n], names

    def test_a_cell_colour_still_wins_inside_a_total(self):
        """
        The two axes compose: the row says *this is a summary*, the cell says
        *this figure is down*. Neither erases the other.
        """
        component = DataTable(
            ["A", "B"],
            [TableRow(["Total", Cell("-1.2%", color="#B85450")], kind="total")],
        )
        assert "#B85450" in _rows_html(component)[0]
