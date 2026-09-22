"""
The finance formatters (#177): every function, table-driven, on its edges.

The edges are the point. Half-up rounding, negative zero, a value that
rounds to zero, a missing figure and each compact threshold are where a
hand-rolled formatter drifts, and each is pinned here by a named case.
"""

import ast
import pathlib
from decimal import Decimal

import pytest

from svc.builder import formats
from svc.builder.formats import bps, compact, delta, displays_zero, money, number, pct


@pytest.mark.parametrize(
    ("value", "kwargs", "expected"),
    [
        (5234, {}, "5,234"),
        (1234567.891, {"dp": 2}, "1,234,567.89"),
        (-1234, {}, "-1,234"),
        (7, {"sign": True}, "+7"),
        (0, {"sign": True}, "0"),
        (-0.0, {}, "0"),
        (-0.004, {"dp": 2}, "0.00"),  # rounds to zero, so unsigned
        (1234567.891, {"dp": 2, "thousands": ".", "decimal": ","}, "1.234.567,89"),
        (1234, {"thousands": ""}, "1234"),
        (Decimal("2.5"), {}, "3"),
    ],
)
def test_number(value, kwargs, expected):
    assert number(value, **kwargs) == expected


@pytest.mark.parametrize(
    ("value", "dp", "expected"),
    [
        (0.125, 2, "0.13"),  # round() gives 0.12
        (2.675, 2, "2.68"),  # the binary float is 2.67499..., round() gives 2.67
        (-0.125, 2, "-0.13"),  # half up means away from zero
        (0.5, 0, "1"),
        (1.5, 0, "2"),
        (2.5, 0, "3"),  # banker's rounding would give 2
    ],
)
def test_rounding_is_half_up(value, dp, expected):
    assert number(value, dp) == expected


@pytest.mark.parametrize(
    ("value", "kwargs", "expected"),
    [
        (0.0142, {}, "1.42%"),
        (0.0142, {"sign": True}, "+1.42%"),
        (-0.004, {"dp": 1, "sign": True}, "-0.4%"),
        (-0.00001, {"sign": True}, "0.00%"),
        (0, {"sign": True}, "0.00%"),
        (12.345, {"dp": 1}, "1,234.5%"),
        (0.125, {"dp": 0}, "13%"),
    ],
)
def test_pct(value, kwargs, expected):
    assert pct(value, **kwargs) == expected


@pytest.mark.parametrize(
    ("value", "kwargs", "expected"),
    [
        (0.0006, {}, "+6 bps"),
        (-0.0025, {}, "-25 bps"),
        (0.0006, {"sign": False}, "6 bps"),
        (0.00005, {"dp": 1}, "+0.5 bps"),
        (0, {}, "0 bps"),
    ],
)
def test_bps(value, kwargs, expected):
    assert bps(value, **kwargs) == expected


@pytest.mark.parametrize(
    ("value", "kwargs", "expected"),
    [
        (5234.0, {}, "$5,234"),
        (-1200, {}, "-$1,200"),  # never "$-1,200"
        (1200, {"sign": True}, "+$1,200"),
        (99.5, {"dp": 2, "currency": "£"}, "£99.50"),
        (1234.5, {"dp": 2, "currency": "EUR ", "thousands": ".", "decimal": ","}, "EUR 1.234,50"),
    ],
)
def test_money(value, kwargs, expected):
    assert money(value, **kwargs) == expected


@pytest.mark.parametrize(
    ("value", "kwargs", "expected"),
    [
        (-2.18, {"unit": "pts"}, "-2.18 pts"),
        (6, {"dp": 0}, "+6"),
        (6, {"dp": 0, "sign": False}, "6"),
        (0, {"unit": "pts"}, "0.00 pts"),
    ],
)
def test_delta(value, kwargs, expected):
    assert delta(value, **kwargs) == expected


@pytest.mark.parametrize(
    ("value", "kwargs", "expected"),
    [
        (1_240_000_000, {}, "1.2bn"),
        (340_000_000, {}, "340m"),  # trailing zero dropped
        (12_400, {}, "12.4k"),
        (0, {}, "0"),
        (12.0, {}, "12"),
        (999, {}, "999"),
        (1000, {}, "1k"),  # exactly on the threshold
        (999_949, {}, "999.9k"),
        (999_950, {}, "1m"),  # rounds to 1,000k, so it moves up a unit
        (999_950_000, {}, "1bn"),
        (-1.24e9, {}, "-1.2bn"),
        (1.24e9, {"sign": True}, "+1.2bn"),
        (5e15, {}, "5,000tn"),  # no unit beyond tn, so it groups
        (1_234_567, {"dp": 2}, "1.23m"),
        (1_500_000, {"dp": 0}, "2m"),
    ],
)
def test_compact(value, kwargs, expected):
    assert compact(value, **kwargs) == expected


class TestAMissingFigure:
    @pytest.mark.parametrize("fmt", [number, pct, bps, delta, money, compact])
    @pytest.mark.parametrize("value", [None, float("nan"), Decimal("NaN")])
    def test_renders_as_the_placeholder(self, fmt, value):
        assert fmt(value) == formats.MISSING

    def test_the_placeholder_is_ascii_and_overridable(self):
        assert formats.MISSING.isascii()
        assert pct(None, missing="n/a") == "n/a"


class TestWhatIsNotAFigure:
    @pytest.mark.parametrize("value", ["1.5", True, [1]])
    def test_a_non_number_raises(self, value):
        with pytest.raises(TypeError):
            number(value)

    def test_infinity_raises(self):
        with pytest.raises(ValueError, match="infinite"):
            pct(float("inf"))

    @pytest.mark.parametrize("dp", [-1, 1.5, True])
    def test_a_bad_dp_raises(self, dp):
        with pytest.raises(ValueError, match="dp"):
            number(1, dp)


class TestTheOutputIsAscii:
    """#148: a non-ASCII character in a plain-text field is a charset risk."""

    @pytest.mark.parametrize("fmt", [number, pct, bps, delta, money, compact])
    def test_every_formatter_emits_ascii_for_a_negative(self, fmt):
        assert fmt(-1234.5).isascii()


@pytest.mark.parametrize(
    ("text", "expected"),
    [("0.00%", True), ("0 bps", True), ("$0", True), ("-0.4%", False), ("1.2bn", False)],
)
def test_displays_zero(text, expected):
    assert displays_zero(text) is expected


def test_it_is_a_pure_module_with_no_builder_imports():
    """
    The formatters are the data layer's floor and must stay stdlib-only, so
    a caller can use them without the render path and they never gain a
    reason to move a golden.
    """
    tree = ast.parse(pathlib.Path(formats.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    relative = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level]
    assert not relative, "formats imports from its own package"
    assert not any(name.startswith("svc") for name in imported), imported
    assert imported <= {"__future__", "numbers", "decimal", "typing"}, imported


def test_it_is_exported_from_the_package():
    import svc.builder

    assert svc.builder.formats is formats
