"""
A DataFrame becomes a DataTable (#179). Skips cleanly without the ``[data]`` extra.

Every test here asserts against the *resulting table* — headers, resolved
column kinds, cell strings and tones — and not only against the render, so a
change that renders plausibly but adapts wrongly still fails.
"""

import pytest

pd = pytest.importorskip("pandas", reason='the DataFrame adapter needs "pyhermes[data]"')

from pyhermes.builder import TemplateEngine, Tone, ValidationError  # noqa: E402
from pyhermes.builder.enums import ColumnKind, RowKind  # noqa: E402
from pyhermes.builder.formats import money, pct  # noqa: E402
from pyhermes.data import table_from_frame  # noqa: E402

_RET = {"1M": lambda v: pct(v, 1, sign=True)}


def _factors(**columns):
    data = {"1M": [0.018, -0.004, 0.009], **columns}
    return pd.DataFrame(data, index=pd.Index(["Value", "Momentum", "Quality"], name="Factor"))


def _texts(table):
    return [[cell.text for cell in row.cells] for row in table.rows]


class TestTheRoundTrip:
    def test_headers_kinds_strings_and_tones(self):
        table = table_from_frame(_factors(), formats=_RET, tones={"1M": "auto"})
        assert table.headers == ["Factor", "1M"]
        assert [c.kind for c in table.resolved_columns()] == [ColumnKind.TEXT, ColumnKind.NUMERIC]
        assert _texts(table) == [["Value", "+1.8%"], ["Momentum", "-0.4%"], ["Quality", "+0.9%"]]
        assert [row.cells[1].tone for row in table.rows] == [
            Tone.POSITIVE,
            Tone.NEGATIVE,
            Tone.POSITIVE,
        ]

    def test_both_projections_carry_the_formatted_figures(self):
        table = table_from_frame(_factors(), formats=_RET)
        html, text = table.render(TemplateEngine()), table.text()
        for figure in ("+1.8%", "-0.4%", "+0.9%"):
            assert figure in html
            assert figure in text

    def test_the_passthrough_fields_reach_the_table(self):
        table = table_from_frame(
            _factors(),
            source="Hermes Research",
            as_of="24 August 2026",
            subtitle="Long-short",
            caption="Factor returns",
            disclosure="Gross of fees.",
        )
        assert (table.source, table.as_of, table.subtitle) == (
            "Hermes Research",
            "24 August 2026",
            "Long-short",
        )
        assert (table.caption, table.disclosure) == ("Factor returns", "Gross of fees.")


class TestDefaultFormatting:
    def test_an_integer_column_is_whole_and_grouped(self):
        frame = pd.DataFrame({"Names": [1200, 34]}, index=pd.Index(["A", "B"], name="Desk"))
        assert _texts(table_from_frame(frame)) == [["A", "1,200"], ["B", "34"]]

    def test_a_float_column_is_two_places(self):
        frame = pd.DataFrame({"Beta": [1.234, 0.5]}, index=pd.Index(["A", "B"], name="Desk"))
        assert _texts(table_from_frame(frame)) == [["A", "1.23"], ["B", "0.50"]]

    def test_a_bool_column_is_text_not_a_figure(self):
        frame = pd.DataFrame({"Live": [True, False]}, index=pd.Index(["A", "B"], name="Desk"))
        table = table_from_frame(frame)
        assert table.resolved_columns()[1].kind is ColumnKind.TEXT
        assert _texts(table) == [["A", "True"], ["B", "False"]]

    def test_a_formatter_applies_per_column(self):
        frame = _factors(AUM=[1_200_000, 340_000, 12_400])
        table = table_from_frame(frame, formats={**_RET, "AUM": money})
        assert [row[2] for row in _texts(table)] == ["$1,200,000", "$340,000", "$12,400"]


class TestMissingFigures:
    def test_a_missing_figure_renders_as_the_placeholder_and_takes_no_tone(self):
        frame = pd.DataFrame({"1M": [0.018, None]}, index=pd.Index(["A", "B"], name="Desk"))
        table = table_from_frame(frame, formats=_RET, tones={"1M": "auto"})
        assert table.rows[1].cells[1].text == "--"
        assert table.rows[1].cells[1].tone == ""

    def test_a_missing_text_value_renders_as_the_placeholder(self):
        frame = pd.DataFrame({"Desk": ["A", None]})
        assert _texts(table_from_frame(frame, missing="n/a")) == [["A"], ["n/a"]]

    def test_a_formatter_is_never_handed_a_missing_value(self):
        def strict(value):
            assert value == value, "a NaN reached the formatter"
            return str(value)

        frame = pd.DataFrame({"1M": [1.0, float("nan")]}, index=pd.Index(["A", "B"], name="D"))
        table_from_frame(frame, formats={"1M": strict})


class TestTheIndex:
    def test_a_default_range_index_is_left_out(self):
        frame = pd.DataFrame({"Desk": ["A", "B"], "Names": [3, 4]})
        assert table_from_frame(frame).headers == ["Desk", "Names"]

    def test_a_named_index_heads_the_first_column(self):
        assert table_from_frame(_factors()).headers[0] == "Factor"

    def test_an_unnamed_index_needs_a_label(self):
        frame = pd.DataFrame({"1M": [0.1]}, index=["Value"])
        with pytest.raises(ValidationError, match="index_label"):
            table_from_frame(frame)
        assert table_from_frame(frame, index_label="Factor").headers[0] == "Factor"

    def test_the_index_can_be_forced_either_way(self):
        assert table_from_frame(_factors(), index=False).headers == ["1M"]
        frame = pd.DataFrame({"Names": [3]})
        assert table_from_frame(frame, index=True, index_label="#").headers == ["#", "Names"]


class TestRowKinds:
    def test_the_last_row_can_be_a_total(self):
        table = table_from_frame(_factors(), total_row=True)
        assert [row.kind for row in table.rows] == [RowKind.DATA, RowKind.DATA, RowKind.TOTAL]

    def test_a_subhead_is_inserted_before_its_row(self):
        table = table_from_frame(_factors(), subheads={"Momentum": "Style"})
        assert [row.kind for row in table.rows] == [
            RowKind.DATA,
            RowKind.SUBHEAD,
            RowKind.DATA,
            RowKind.DATA,
        ]
        assert table.rows[1].cells[0].text == "Style"


class TestTones:
    def test_a_stated_tone_applies_to_the_whole_column(self):
        table = table_from_frame(_factors(), tones={"1M": Tone.NEGATIVE})
        assert {row.cells[1].tone for row in table.rows} == {Tone.NEGATIVE}

    def test_a_figure_that_rounds_to_zero_is_neutral(self):
        frame = pd.DataFrame({"1M": [-0.00001]}, index=pd.Index(["A"], name="D"))
        cell = table_from_frame(frame, formats=_RET, tones={"1M": "auto"}).rows[0].cells[1]
        assert (cell.text, cell.tone) == ("0.0%", Tone.NEUTRAL)

    def test_the_adapter_never_colours_by_hex(self):
        table = table_from_frame(_factors(), tones={"1M": "auto"})
        assert not any(cell.color for row in table.rows for cell in row.cells)


class TestNumpyScalars:
    def test_numpy_values_are_formatted_as_python_numbers(self):
        frame = pd.DataFrame(
            {"Int": pd.Series([5234], dtype="int64"), "Float": pd.Series([1.5], dtype="float32")}
        )
        assert _texts(table_from_frame(frame)) == [["5,234", "1.50"]]


class TestWhatItRefuses:
    @pytest.mark.parametrize(
        ("kwargs", "match"),
        [
            ({"formats": {"1m": pct}}, "formats names columns"),
            ({"tones": {"YTD": "auto"}}, "tones names columns"),
            ({"subheads": {"Carry": "Style"}}, "subheads names rows"),
            ({"tones": {"1M": "Up"}}, r"tones\['1M'\]"),
        ],
    )
    def test_a_mapping_naming_nothing_raises_by_name(self, kwargs, match):
        with pytest.raises(ValidationError, match=match):
            table_from_frame(_factors(), **kwargs)

    def test_auto_on_a_text_column_raises(self):
        frame = pd.DataFrame({"Desk": ["A"]})
        with pytest.raises(ValidationError, match="not numeric"):
            table_from_frame(frame, tones={"Desk": "auto"})

    def test_an_empty_frame_raises_through_the_tables_own_check(self):
        with pytest.raises(ValidationError, match="at least one row"):
            table_from_frame(pd.DataFrame({"1M": []}))

    def test_a_multi_index_raises(self):
        frame = pd.DataFrame(
            {"1M": [0.1]}, index=pd.MultiIndex.from_tuples([("Eq", "Value")], names=["A", "B"])
        )
        with pytest.raises(ValidationError, match="flat"):
            table_from_frame(frame)

    def test_duplicate_column_names_raise_by_name(self):
        # #434: both "a" columns used to fall back to text, silently.
        frame = pd.DataFrame([[1.0, "x", 2.0]], columns=["a", "b", "a"])
        with pytest.raises(ValidationError, match=r"unique column names; repeated: \['a'\]"):
            table_from_frame(frame)

    def test_a_non_frame_raises(self):
        with pytest.raises(ValidationError, match="DataFrame"):
            table_from_frame({"1M": [0.1]})
