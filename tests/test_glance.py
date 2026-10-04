"""
Data at a glance, drawn without images (#318): the arrow, the bar list, the
sparkline and the hero figure, and the fixtures that carry them (#319–#323).
"""

from __future__ import annotations

import importlib.util
import re
from functools import partial

import pytest

from pyhermes.builder import (
    SIZE_SCHEMES,
    BarItem,
    BarList,
    CardGroup,
    Column,
    DataTable,
    FullWidth,
    HeroStat,
    Sparkline,
    Trend,
    trend_of,
)
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.formats import bps, number, pct
from pyhermes.builder.models import Card, KpiItem, Series, TableRow
from pyhermes.builder.sizing import STANDARD_SIZES, Spacing
from pyhermes.builder.theming import DEFAULT_THEME
from pyhermes.config import config_override
from pyhermes.pdf import available as pdf_available

ENGINE = TemplateEngine()

requires_pdf = pytest.mark.skipif(
    not pdf_available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)


def _render(component) -> str:
    return component.render(ENGINE)


def _markers(html: str) -> list[str]:
    """The arrows drawn for every client but Outlook, in order."""
    return re.findall(r'class="trend trend-(\w+)"', html)


# ----------------------------------------------------------------------
# #319 — a change's direction, drawn as a shape
# ----------------------------------------------------------------------


class TestTheDirectionIsTheNumbers:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [(0.5, Trend.UP), (-0.5, Trend.DOWN), (0, Trend.FLAT), (None, Trend.FLAT)],
    )
    def test_the_sign_decides(self, value, expected):
        assert trend_of(value) is expected

    def test_a_change_written_as_zero_is_flat(self):
        # A move the format rounds away cannot carry an arrow the string contradicts.
        assert trend_of(0.00004, partial(pct, dp=2)) is Trend.FLAT

    def test_a_card_takes_no_direction_from_its_caller(self):
        with pytest.raises(TypeError):
            Card("10Y", "4.21%", arrow="up")  # type: ignore[call-arg]

    def test_from_number_reads_it_off_the_change(self):
        card = KpiItem.from_number("10Y", 0.0421, pct, change=0.0018, change_fmt=bps, arrow=True)
        assert card.arrow == "up"

    def test_the_tone_may_disagree_with_the_direction(self):
        # A rising yield is bad news: the arrow points up, in the negative tone.
        card = KpiItem.from_number(
            "10Y", 0.0421, pct, change=0.0018, change_fmt=bps, good="down", arrow=True
        )
        assert (card.arrow, card.tone) == ("up", "negative")
        html = _render(CardGroup([card, KpiItem("x", "1")]))
        assert f"border-bottom:7px solid {DEFAULT_THEME.semantic.negative}" in html

    def test_an_arrow_needs_a_change(self):
        with pytest.raises(ValidationError, match="marks a change"):
            KpiItem.from_number("10Y", 0.0421, pct, arrow=True)

    def test_unset_draws_nothing(self):
        card = KpiItem.from_number("10Y", 0.0421, pct, change=0.0018, change_fmt=bps)
        assert card.arrow == ""
        assert "trend" not in _render(CardGroup([card, KpiItem("x", "1")]))


def _change_table(**column) -> DataTable:
    return DataTable(
        ["Tenor", Column("Change", format=lambda v: f"{v:+d} bps" if v else "0 bps", **column)],
        [TableRow(["2Y", 9]), TableRow(["5Y", -4]), TableRow(["10Y", 0])],
    )


class TestTheArrowIsDrawnAsAShape:
    def test_each_direction_has_its_shape(self):
        html = _render(_change_table(arrow=True))
        assert _markers(html) == ["up", "down", "flat"]

    def test_outlook_gets_a_vml_shape_and_no_css_triangle(self):
        html = _render(_change_table(arrow=True))
        assert html.count("<!--[if mso]><v:shape") == 2
        assert html.count("<!--[if mso]><v:rect") == 1
        # The CSS triangle sits behind a downlevel-revealed comment the Word engine skips.
        assert html.count('<!--[if !mso]><!--><span class="trend') == 3

    def test_the_triangle_is_sized_by_its_token(self):
        scheme = STANDARD_SIZES.derive(component={"trend_arrow": 10})
        html = _change_table(arrow=True).render(TemplateEngine().bound(size=scheme))
        assert "border-bottom:10px solid" in html
        assert "border-left:6px solid transparent" in html

    def test_it_is_never_a_glyph(self):
        html = _render(_change_table(arrow=True))
        assert not re.search("[←-⇿▲-▽]", html)

    def test_a_flat_marker_is_a_bar(self):
        html = _render(_change_table(arrow=True))
        assert "trend-flat" in html and "border-top:2px solid" in html

    def test_the_plain_text_keeps_the_signed_number_and_draws_nothing(self):
        assert _change_table(arrow=True).text() == _change_table().text()

    def test_a_text_column_refuses_one(self):
        with pytest.raises(ValidationError, match="only figures"):
            DataTable([Column("Desk", kind="text", arrow=True)], [TableRow(["Rates"])])

    def test_a_data_row_needs_a_raw_figure(self):
        with pytest.raises(ValidationError, match="no raw figure"):
            DataTable(["Tenor", Column("Change", arrow=True)], [TableRow(["2Y", "+9"])])

    def test_the_token_is_a_box_not_spacing(self):
        with pytest.raises(ValidationError):
            Spacing(trend_arrow=4)


# ----------------------------------------------------------------------
# #320 — ranked bars
# ----------------------------------------------------------------------


def _fills(html: str) -> list[int]:
    """Each bar's filled share, read off the markup's coloured cells."""
    return [int(w) for w in re.findall(r'<td width="(\d+)%" style="width: \d+%; background', html)]


class TestABarList:
    ITEMS = [("Apple", 0.08), ("Microsoft", 0.06), ("Nvidia", 0.02)]

    def test_widths_are_proportional_to_the_values(self):
        html = _render(BarList(self.ITEMS, value_format=pct))
        assert _fills(html) == [100, 75, 25]

    def test_ten_items_draw_ten_bars(self):
        items = [(f"Holding {n}", n) for n in range(10, 0, -1)]
        assert _fills(_render(BarList(items))) == [100, 90, 80, 70, 60, 50, 40, 30, 20, 10]

    def test_a_diverging_list_fills_negatives_leftward_from_a_centre_rule(self):
        html = _render(BarList([("Duration", 4), ("Credit", -2)], diverging=True))
        assert _fills(html) == [100, 50]
        credit = html[html.index("Credit") :]
        # The left half fills from the right: its remainder comes first.
        assert re.search(r'<td width="50%" style="width: 50%; height', credit)
        assert "border-left: 1px solid" in html

    def test_a_negative_without_diverging_is_refused(self):
        with pytest.raises(ValidationError, match="diverging=True"):
            BarList([("Credit", -0.01)])

    def test_the_tone_is_the_items_then_the_lists(self):
        html = _render(
            BarList(
                [("Up", 2), ("Down", -1), BarItem("Held", 1, tone="neutral")],
                tone="auto",
                diverging=True,
            )
        )
        semantic = DEFAULT_THEME.semantic
        for colour in (semantic.positive, semantic.negative, semantic.neutral):
            assert f"background-color: {colour}" in html

    def test_untoned_bars_take_the_accent(self):
        assert f"background-color: {DEFAULT_THEME.palette.accent}" in _render(BarList(self.ITEMS))

    @pytest.mark.parametrize("bad", [("Only a label",), ("Label", "1.0"), ("Label", True), 3])
    def test_a_bad_item_is_refused(self, bad):
        with pytest.raises(ValidationError):
            BarList([bad])

    def test_an_empty_list_is_refused(self):
        with pytest.raises(ValidationError, match="at least one"):
            BarList([])

    def test_the_text_is_two_aligned_columns(self):
        text = BarList(self.ITEMS, value_format=partial(pct, dp=1), title="Top three").text()
        assert text == "Top three\n\nApple      8.0%\nMicrosoft  6.0%\nNvidia     2.0%"

    def test_it_is_a_layout_table_kept_on_one_sheet(self):
        html = _render(BarList(self.ITEMS))
        assert 'class="figure bar-list" role="presentation"' in html
        assert "<th" not in html


# ----------------------------------------------------------------------
# #321 — a short series as cell bars
# ----------------------------------------------------------------------


def _bar_heights(html: str) -> list[int]:
    return [int(h) for h in re.findall(r'<td height="(\d+)"', html)]


class TestASparkline:
    def test_heights_are_scaled_to_the_series_own_range(self):
        series = Series((2.0, 3.0, 4.0))
        assert series.heights() == [0.15, 0.575, 1.0]
        # 24px at the standard density: the lowest still shows.
        assert _bar_heights(_render(Sparkline([2.0, 3.0, 4.0]))) == [4, 14, 24]

    def test_a_rising_a_falling_and_a_flat_series_read_as_such(self):
        rising = _bar_heights(_render(Sparkline([1, 2, 3, 4])))
        falling = _bar_heights(_render(Sparkline([4, 3, 2, 1])))
        flat = _bar_heights(_render(Sparkline([2, 2, 2, 2])))
        assert rising == sorted(rising) and rising[0] < rising[-1]
        assert falling == sorted(falling, reverse=True) and falling[0] > falling[-1]
        assert len(set(flat)) == 1

    def test_the_last_bar_takes_the_tone_and_the_rest_the_rule(self):
        html = _render(Sparkline([1, 2, 3], tone="positive"))
        colours = re.findall(r"height: \d+px; background-color: (#[0-9A-F]{6})", html)
        assert colours == [DEFAULT_THEME.palette.rule] * 2 + [DEFAULT_THEME.semantic.positive]

    def test_every_bar_takes_the_tone_when_the_last_is_not_highlighted(self):
        html = _render(Sparkline([1, 2, 3], tone="negative", highlight_last=False))
        assert html.count(f"background-color: {DEFAULT_THEME.semantic.negative}") == 3

    def test_auto_reads_last_against_first(self):
        assert Sparkline([3, 1, 2], tone="auto").resolved_tone() == "negative"

    def test_the_text_reads_min_last_max_in_the_callers_format(self):
        line = Sparkline([3.4, 3.1, 4.2], value_format=partial(number, dp=1)).text()
        assert line == "min 3.1 · last 4.2 · max 4.2"

    def test_a_series_past_the_limit_is_refused_by_name(self):
        with pytest.raises(ValidationError, match=r"2 to 24 values \(Config.sparkline_max\)"):
            Sparkline(list(range(25)))

    def test_the_limit_is_config(self):
        with config_override(sparkline_max=30):
            assert len(Sparkline(list(range(30))).series.values) == 30

    @pytest.mark.parametrize("bad", [[1], [1, "2"], [1, float("nan")], "12"])
    def test_a_bad_series_is_refused(self, bad):
        with pytest.raises(ValidationError):
            Sparkline(bad)

    @pytest.mark.parametrize("token", ["sparkline_height", "sparkline_bar", "sparkline_gap"])
    def test_its_sizes_are_boxes_not_spacing(self, token):
        with pytest.raises(ValidationError):
            Spacing({token: 4})


class TestATrendOnACard:
    def test_a_list_becomes_a_series(self):
        card = KpiItem("10Y", "4.21%", trend=[4.0, 4.1, 4.21])
        assert isinstance(card.trend, Series)

    def test_it_is_drawn_under_the_value_and_read_in_the_text(self):
        trend = Series((4.0, 4.1, 4.2), partial(number, dp=1))
        group = CardGroup([KpiItem("10Y", "4.21%", trend=trend), KpiItem("x", "1")])
        html = _render(group)
        assert html.index("4.21%") < html.index('class="sparkline"') < html.index(">x<")
        assert "min 4.0 · last 4.2 · max 4.2" in group.text()

    def test_from_number_writes_the_summary_in_its_format(self):
        card = KpiItem.from_number("10Y", 0.0421, partial(pct, dp=2), trend=[0.04, 0.0421])
        assert card.trend.summary() == "min 4.00% · last 4.21% · max 4.21%"

    def test_too_long_a_trend_is_refused(self):
        with pytest.raises(ValidationError, match="sparkline_max"):
            KpiItem("10Y", "4.21%", trend=list(range(30)))


def _spark_table(cells, **column) -> DataTable:
    return DataTable(
        ["Tenor", Column("Two years", kind="sparkline", **column)],
        [TableRow(["2Y", cell]) for cell in cells],
    )


class TestASparklineColumn:
    def test_each_row_draws_its_series(self):
        html = _render(_spark_table([[1, 2, 3], [3, 2, 1]]))
        assert html.count('class="sparkline"') == 2

    def test_the_text_is_the_summary(self):
        text = _spark_table([[1, 2, 3]], format=partial(number, dp=1)).text()
        assert "min 1.0 · last 3.0 · max 3.0" in text

    def test_a_list_elsewhere_is_refused(self):
        with pytest.raises(ValidationError, match="kind='sparkline'"):
            DataTable(["Tenor", "Yield"], [TableRow(["2Y", [1, 2]])])

    def test_a_figure_in_a_sparkline_column_is_refused(self):
        with pytest.raises(ValidationError, match="list of figures"):
            _spark_table([4.2])

    def test_a_bar_or_an_arrow_is_refused_on_one(self):
        with pytest.raises(ValidationError, match="only figures"):
            _spark_table([[1, 2]], bar=True)


# ----------------------------------------------------------------------
# #322 — one figure set alone
# ----------------------------------------------------------------------


class TestAHeroStat:
    @pytest.mark.parametrize("theme", list(SIZE_SCHEMES), ids=str)
    def test_its_value_is_larger_than_a_kpis_in_every_density(self, theme):
        component = SIZE_SCHEMES[theme].component
        assert component.hero_value > component.kpi_value

    def test_the_text_reads_value_label_context(self):
        stat = HeroStat("38 bps", "2s10s", "steepest since 2022")
        assert stat.text() == "38 bps — 2s10s, steepest since 2022"
        assert HeroStat("38 bps", "2s10s").text() == "38 bps — 2s10s"

    def test_it_is_set_at_its_token(self):
        assert "font-size: 44px" in _render(HeroStat("38 bps", "2s10s"))

    def test_from_number_is_untoned_unless_asked(self):
        assert HeroStat.from_number("2s10s", 38).tone == ""
        assert HeroStat.from_number("VIX", 3, tone="auto", good="down").tone == "negative"

    def test_on_a_dark_section_its_type_turns_light(self):
        from pyhermes.builder import Email

        email = Email({"email_subject": "S", "firm_name": "F", "campaign_name": "C"})
        email.add_section(FullWidth(HeroStat("61 bps", "Term premium"), background_color="#22313F"))
        html = email.render()
        hero = html[html.index("hero-stat") :]
        assert f"color: {DEFAULT_THEME.text.on_dark}" in hero[: hero.index("61 bps")]

    def test_on_the_theme_surface_it_takes_the_heading(self):
        assert f"color: {DEFAULT_THEME.text.heading}" in _render(HeroStat("61 bps", "TP"))

    @pytest.mark.parametrize(("value", "label"), [("", "x"), ("1", "")])
    def test_a_value_and_a_label_are_required(self, value, label):
        with pytest.raises(ValidationError):
            HeroStat(value, label)

    def test_a_tone_is_a_word_not_a_hex(self):
        with pytest.raises(ValidationError, match="tone"):
            HeroStat("1", "x", tone="#FF0000")


# ----------------------------------------------------------------------
# #323 — the fixtures
# ----------------------------------------------------------------------


class TestTheGalleryCarriesThem:
    def test_both_media_have_a_glance_fixture(self):
        from qa.fixtures import all_fixtures, all_paged_fixtures

        assert "glance_layout" in all_fixtures()
        assert "a4_glance_layout" in all_paged_fixtures()

    def test_the_deck_and_the_brochure_set_a_hero_figure(self):
        from qa.fixtures import pitch_16_9, tri_fold_letter

        assert "hero-stat" in pitch_16_9.build().render()
        assert "hero-stat" in tri_fold_letter.build().render()

    def test_the_deck_draws_every_direction(self):
        from qa.fixtures import pitch_16_9

        assert set(_markers(pitch_16_9.build().render())) == {"up", "down", "flat"}


def _sheets(document) -> list[str]:
    import pypdfium2

    from pyhermes.pdf import render_pdf

    pdf = pypdfium2.PdfDocument(render_pdf(document))
    return [page.get_textpage().get_text_range() for page in pdf]


@requires_pdf
class TestOnPaper:
    def test_no_glance_object_splits_across_a_sheet(self):
        from qa.fixtures import a4_glance_layout

        sheets = _sheets(a4_glance_layout.build())
        for first, last in [
            ("Top ten holdings", "UK Treasury 1.25% 2051"),
            ("Contribution to return", "Currency"),
            ("Gilt yields and their change", "4.78%"),
            ("38 bps", "steepest since 2022"),
        ]:
            # A title set in capitals by CSS reads back in capitals.
            assert any(first.lower() in sheet.lower() and last in sheet for sheet in sheets), first

    def test_a_bar_prints_at_its_share(self):
        """#320 found the cell bar a width attribute alone, which the print engine ignores."""
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
        tones = ("positive", "negative", "neutral")
        document.add_section(
            FullWidth(BarList([BarItem(t, v, t) for t, v in zip(tones, (8, 4, 2), strict=True)]))
        )
        sheet = next(iter(pypdfium2.PdfDocument(render_pdf(document))))
        pixels = np.asarray(sheet.render(scale=96 / 72).to_pil().convert("RGB")).astype(int)
        spans = []
        for tone in tones:
            hex_ = getattr(DEFAULT_THEME.semantic, tone)
            rgb = [int(hex_[i : i + 2], 16) for i in (1, 3, 5)]
            ys, xs = np.where(np.abs(pixels - rgb).max(axis=2) <= 2)
            row = np.bincount(ys).argmax()  # the bar's row: no glyph is that wide
            on_row = np.sort(xs[ys == row])
            # The longest unbroken run: anti-aliased type can share a grey with a bar.
            runs = np.split(on_row, np.where(np.diff(on_row) > 1)[0] + 1)
            spans.append(max(len(run) for run in runs))
        assert abs(spans[1] / spans[0] - 0.5) < 0.03, spans
        assert abs(spans[2] / spans[0] - 0.25) < 0.03, spans
