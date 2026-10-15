"""
A number nothing can read is refused where it is built (#450).

NaN fails every comparison, so a check written "not positive" lets it through, and
infinity is positive. Each field a template or a computation reads is held here to
refuse NaN, infinity and minus infinity at construction, naming the field. A figure
that deliberately means "missing" (a table cell's NaN) is not one of them, and a test
below holds that.
"""

from __future__ import annotations

import math
from dataclasses import fields
from decimal import Decimal

import pytest

from pyhermes.brochure import FoldFormat
from pyhermes.brochure.fold import LETTER_SHEET
from pyhermes.brochure.panel import Panel
from pyhermes.builder import (
    Banner,
    BarList,
    Columns,
    DataTable,
    Footer,
    FourColumn,
    FullWidth,
    HeatScale,
    Spacing,
    Sparkline,
    TextBlock,
    ThreeColumn,
    TwoColumn,
)
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.finite import is_finite, require_finite
from pyhermes.builder.models import Cell, Column, TableRow
from pyhermes.builder.sizing import (
    COMPACT_SIZES,
    STANDARD_SIZES,
    ComponentScale,
    FrameGeometry,
    PageFormat,
    PageMargin,
    SpacingScale,
    TypeScale,
)
from pyhermes.config import Config
from pyhermes.deck.regions import TitleSlide
from pyhermes.document.regions import Cover
from pyhermes.pdf.exceptions import ProfileError
from pyhermes.pdf.profile import PdfProfile

NON_FINITE = [math.nan, math.inf, -math.inf]
IDS = ["nan", "inf", "-inf"]

LAYERS = [TypeScale, SpacingScale, ComponentScale, FrameGeometry, PageFormat]


def _block() -> TextBlock:
    return TextBlock("<p>a</p>")


def _token_cases() -> list[tuple[type, str]]:
    """Every numeric token of every size layer: read off the dataclasses, never listed."""
    cases = []
    for layer in LAYERS:
        for spec in fields(layer):
            if spec.name != "margin":
                cases.append((layer, spec.name))
    return cases


class TestTheHelper:
    @pytest.mark.parametrize("value", [0, -3, 2.5, 10**400, Decimal("1.5")])
    def test_a_finite_number_passes(self, value):
        assert is_finite(value)
        require_finite(value, "x")

    @pytest.mark.parametrize(
        "value",
        [*NON_FINITE, Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), True, "1", None],
    )
    def test_anything_else_is_refused_by_name(self, value):
        assert not is_finite(value)
        with pytest.raises(ValidationError, match="'column.width' must be a finite number"):
            require_finite(value, "column.width")


class TestEverySizeTokenIsFinite:
    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    @pytest.mark.parametrize(
        ("layer", "token"), _token_cases(), ids=lambda v: getattr(v, "__name__", v)
    )
    def test_a_layer_refuses_it(self, layer, token, bad):
        arguments = {"width": 800} if layer is PageFormat else {}
        arguments[token] = bad
        with pytest.raises(ValidationError, match=f"'[a-z]+\\.{token}' must be a finite number"):
            layer(**arguments)

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    @pytest.mark.parametrize("side", ["top", "right", "bottom", "left"])
    def test_a_page_margin_refuses_it(self, side, bad):
        with pytest.raises(ValidationError, match=f"page.margin.{side}' must be a finite number"):
            PageMargin(**{side: bad})

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    def test_deriving_a_scheme_refuses_it(self, bad):
        with pytest.raises(ValidationError, match="frame.pad_x"):
            STANDARD_SIZES.derive(frame={"pad_x": bad})
        with pytest.raises(ValidationError, match="type.body"):
            COMPACT_SIZES.derive(type={"body": bad})

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    @pytest.mark.parametrize("token", ["content_top", "table_cell_pad", "gutter", "block_gap"])
    def test_a_spacing_override_refuses_it(self, token, bad):
        with pytest.raises(ValidationError, match=f"{token}' must be a finite number"):
            Spacing({token: bad})

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    def test_a_section_never_renders_nan_pixels(self, bad):
        with pytest.raises(ValidationError):
            FullWidth(_block(), spacing=Spacing(content_top=bad))


class TestTheDataAGlanceDraws:
    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    def test_a_bar_list_refuses_it(self, bad):
        with pytest.raises(ValidationError, match="bar_item 'a' must carry a finite number"):
            BarList([("a", bad), ("b", 1.0)])

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    def test_a_sparkline_names_the_value(self, bad):
        with pytest.raises(ValidationError, match="sparkline value 1 must be a finite number"):
            Sparkline([1.0, bad, 2.0])

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    def test_a_table_sparkline_refuses_it(self, bad):
        row = TableRow(["a", Cell("", value=(1.0, bad))])
        with pytest.raises(ValidationError, match="finite number"):
            DataTable(["F", Column("T", kind="sparkline")], [row])


class TestTheGeometryOfTheTable:
    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    def test_a_column_weight_refuses_it(self, bad):
        with pytest.raises(ValidationError, match="column.width"):
            DataTable([Column("A", width=bad)], [TableRow(["x"])])

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    @pytest.mark.parametrize("end", ["low", "high", "mid"])
    def test_a_heat_scale_bound_refuses_it(self, end, bad):
        bounds = {"low": 0.0, "high": 1.0, "mid": 0.5}
        bounds[end] = bad
        with pytest.raises(ValidationError, match=f"heat_scale.{end}' must be a finite number"):
            DataTable(["F", Column("A", scale=HeatScale(**bounds))], [TableRow(["x", 0.5])])

    def test_nan_in_a_formatted_column_still_means_missing(self):
        from pyhermes.builder import formats

        table = DataTable(["F", Column("V", format=formats.pct)], [TableRow(["a", math.nan])])
        assert "--" in table.text()

    def test_nan_in_a_scaled_and_barred_column_still_renders_as_missing(self):
        from pyhermes.builder import formats
        from pyhermes.builder.email import Email

        table = DataTable(
            ["F", Column("V", format=formats.pct, scale=HeatScale(0, 0.1), bar=True)],
            [TableRow(["a", math.nan]), TableRow(["b", 0.05])],
        )
        email = Email({"email_subject": "S", "firm_name": "F", "campaign_name": "C"})
        email.add_section(FullWidth(table))
        assert ">--<" in email.render().replace(" ", "").replace("\n", "")


class TestASplitsWeights:
    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    def test_a_two_column_split_refuses_it(self, bad):
        with pytest.raises(ValidationError, match="TwoColumn takes 2 positive weights"):
            TwoColumn((bad, 1), _block(), _block())

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    def test_a_three_column_split_refuses_it(self, bad):
        with pytest.raises(ValidationError, match="ThreeColumn takes 3 positive weights"):
            ThreeColumn((1, bad, 1), _block(), _block(), _block())

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    def test_a_four_column_split_refuses_it(self, bad):
        with pytest.raises(ValidationError, match="FourColumn takes 4 positive weights"):
            FourColumn([_block()] * 4, (1, 1, 1, bad))

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    def test_a_nested_row_refuses_it(self, bad):
        with pytest.raises(ValidationError, match="positive weights"):
            Columns([_block(), _block()], ratio=(1, bad))


class TestARegionsWidths:
    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    @pytest.mark.parametrize(
        ("build", "field"),
        [
            (lambda bad: Banner(logo_width=bad), "banner.logo_width"),
            (lambda bad: Footer(image_width=bad), "footer.image_width"),
            (lambda bad: Cover(logo_width=bad), "cover.logo_width"),
            (lambda bad: TitleSlide(logo_width=bad), "title_slide.logo_width"),
        ],
        ids=["banner", "footer", "cover", "title-slide"],
    )
    def test_a_logo_or_image_width_refuses_it(self, build, field, bad):
        with pytest.raises(ValidationError, match=f"'{field}' must be a finite number"):
            build(bad)


class TestTheFoldAndThePanel:
    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    @pytest.mark.parametrize("name", ["tuck", "inset", "safe", "bleed", "slug"])
    def test_a_fold_distance_refuses_it(self, name, bad):
        arguments = {name: bad}
        if name == "inset":
            arguments["safe"] = 0
        with pytest.raises(ValidationError, match=f"'fold.{name}' must be a finite number"):
            FoldFormat(LETTER_SHEET, "c", **arguments)

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    def test_a_panel_inset_refuses_it(self, bad):
        with pytest.raises(ValidationError, match="inset must be a finite number"):
            Panel([FullWidth(_block())], inset=bad)


class TestTheExporterAndTheRenderer:
    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    def test_a_pdf_profile_dpi_refuses_it(self, bad):
        with pytest.raises(ProfileError, match="dpi must be positive and finite"):
            PdfProfile(name="x", dpi=bad)

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    @pytest.mark.parametrize("name", ["font_px", "scale"])
    def test_an_equation_size_refuses_it(self, name, bad):
        from pyhermes.math.render import render_math

        arguments = {"font_px": 14, "scale": 4, "color": "#000000", "fontset": "stix"}
        arguments[name] = bad
        with pytest.raises(ValidationError, match=f"'{name}' must be a positive, finite number"):
            render_math("x", **arguments)


class TestConfig:
    NUMERIC = [
        spec.name for spec in fields(Config) if spec.type in ("int", "float", "float | None")
    ]

    def test_the_numeric_fields_are_found_by_annotation(self):
        assert {"size_limit_kb", "retry_initial_delay", "request_timeout_seconds"} <= set(
            self.NUMERIC
        )
        assert "allow_custom_email_density" not in self.NUMERIC
        assert "exhibit_separator" not in self.NUMERIC

    @pytest.mark.parametrize("bad", NON_FINITE, ids=IDS)
    @pytest.mark.parametrize("name", NUMERIC)
    def test_every_numeric_field_refuses_it(self, name, bad):
        with pytest.raises(ValueError, match=f"{name} must be finite"):
            Config(**{name: bad})

    def test_no_timeout_is_still_spelt_none(self):
        assert Config(request_timeout_seconds=None).request_timeout_seconds is None

    @pytest.mark.parametrize("text", ["nan", "inf", "-inf"])
    def test_an_environment_override_cannot_smuggle_one_in(self, text, monkeypatch):
        monkeypatch.setenv("PYHERMES_RETRY_BACKOFF_FACTOR", text)
        with pytest.raises(ValueError, match="retry_backoff_factor"):
            Config.from_env()
