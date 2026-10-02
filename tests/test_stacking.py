"""
How a split stacks on a phone (#362, #363): in source order, reversed, or not at all.

The markup claims are checked here; where each column lands is measured in a
browser at the desktop and the phone floor, because no golden can see it.
"""

from __future__ import annotations

import re

import pytest

from pyhermes.builder import (
    CardGroup,
    Columns,
    Email,
    FourColumn,
    FullWidth,
    TextBlock,
    ThreeColumn,
    TwoColumn,
    ValidationError,
)
from pyhermes.builder.models import KpiItem
from pyhermes.builder.sizing import PHONE_FLOOR, shares
from pyhermes.document import PagedDocument
from qa.screenshots import _launch, _load_playwright, available

requires_browser = pytest.mark.skipif(
    not available(),
    reason='no browser; screenshots are the optional "[qa]" extra',
)

FACTS = {"email_subject": "S", "firm_name": "F", "campaign_name": "C"}


def split(stack="natural", ratio="30-70", **kwargs):
    return TwoColumn(
        ratio,
        TextBlock("<p>LEFTCOPY</p>"),
        TextBlock("<p>RIGHTCOPY</p>"),
        title="Split",
        stack=stack,
        **kwargs,
    )


def email(*sections) -> Email:
    built = Email(FACTS)
    for section in sections:
        built.add_section(section)
    return built


def paper(*sections) -> PagedDocument:
    built = PagedDocument({"firm_name": "F", "campaign_name": "C"})
    for section in sections:
        built.add_section(section)
    return built


class TestTheField:
    def test_it_defaults_to_natural_on_every_split(self):
        left = TextBlock("<p>x</p>")
        assert TwoColumn(left=left).stack == "natural"
        assert ThreeColumn(left=left).stack == "natural"
        assert FourColumn([left, None, None, None]).stack == "natural"
        assert Columns([left, left]).stack == "natural"

    def test_true_reads_as_natural(self):
        assert split(True).stack == "natural"

    @pytest.mark.parametrize("bad", ["reversed", "", None, 1, "left"])
    def test_anything_else_is_refused_naming_the_three(self, bad):
        with pytest.raises(ValidationError, match="'natural', 'reverse' or False"):
            split(bad)

    def test_unset_is_byte_identical_to_natural(self):
        left, right = TextBlock("<p>a</p>"), TextBlock("<p>b</p>")
        assert (
            email(TwoColumn("30-70", left, right)).render()
            == email(TwoColumn("30-70", left, right, stack="natural")).render()
        )


class TestReversed:
    """#362: the columns are written in phone order and laid out right to left."""

    def test_the_right_column_is_written_first(self):
        html = email(split("reverse")).render()
        assert html.index("RIGHTCOPY") < html.index("LEFTCOPY")
        natural = email(split()).render()
        assert natural.index("LEFTCOPY") < natural.index("RIGHTCOPY")

    def test_the_band_and_the_ghost_table_are_rtl_and_each_column_ltr(self):
        html = email(split("reverse")).render()
        assert html.count('dir="rtl"') == 2
        assert html.count('class="stack-column" dir="ltr"') == 2
        assert re.search(r'<!--\[if mso\]>\s*<table dir="rtl"', html)

    def test_the_gutter_faces_the_next_column(self):
        """In a right-to-left row the next column sits to the left, so the margin does too."""
        html = email(split("reverse")).render()
        assert "margin-left:16px" in html and "margin-right:16px" not in html

    def test_the_text_part_keeps_source_order(self):
        assert email(split("reverse")).text() == email(split()).text()

    def test_paper_prints_it_as_written(self):
        """Nothing stacks on a sheet, so the field moves no byte there."""
        assert paper(split("reverse")).render() == paper(split()).render()

    def test_a_nested_columns_reverses_too(self):
        nested = Columns([TextBlock("<p>AAA</p>"), TextBlock("<p>BBB</p>")], stack="reverse")
        html = email(FullWidth(nested)).render()
        assert html.index("BBB") < html.index("AAA")
        assert html.count('dir="rtl"') == 2


class TestUnstacked:
    """#363: ``stack=False`` keeps a narrow split side by side, if it fits the floor."""

    def test_it_omits_the_stacking_class(self):
        html = email(split(False, ratio="50-50")).render()
        assert 'class="stack-column"' not in html
        assert "LEFTCOPY" in html and "RIGHTCOPY" in html

    def test_its_columns_are_shares_of_the_band(self):
        html = email(split(False, ratio="50-50")).render()
        assert html.count('width="48.7012%"') == 2
        assert 'width="2.5974%"' in html

    def test_the_shares_never_sum_past_the_band(self):
        for widths, gutter, within in (([195, 194, 195], 16, 616), ([300, 300], 16, 616)):
            columns = shares(widths, gutter, within)
            total = sum(float(share) for share in columns[:-1])
            total += float(columns[-1]) * (len(widths) - 1)
            assert total <= 100

    def test_a_split_too_wide_for_the_floor_is_refused_naming_its_narrowest_column(self):
        with pytest.raises(ValidationError, match=r"column 1 is 72px wide at the 375px floor"):
            FourColumn([TextBlock("<p>x</p>")] * 4, stack=False)

    def test_a_thin_weight_is_refused_and_a_balanced_pair_is_not(self):
        with pytest.raises(ValidationError, match="column 1"):
            split(False, ratio=(1, 5))
        assert split(False, ratio="50-50").stack is False
        assert ThreeColumn(left=TextBlock("<p>x</p>"), stack=False).stack is False

    def test_a_nested_pair_is_checked_against_a_stacked_column(self):
        Columns([TextBlock("<p>a</p>"), TextBlock("<p>b</p>")], stack=False)
        with pytest.raises(ValidationError, match="Columns with stack=False"):
            Columns([TextBlock("<p>a</p>")] * 3, stack=False)

    def test_two_unstacked_levels_are_refused(self):
        pair = Columns([TextBlock("<p>a</p>"), TextBlock("<p>b</p>")], stack=False)
        with pytest.raises(ValidationError, match="one of the two must stack"):
            TwoColumn("50-50", pair, TextBlock("<p>c</p>"), stack=False)

    def test_paper_and_text_are_unmoved(self):
        assert paper(split(False, ratio="50-50")).render() == paper(split(ratio="50-50")).render()
        assert email(split(False, ratio="50-50")).text() == email(split(ratio="50-50")).text()

    def test_the_floor_is_the_supported_one(self):
        from qa.screenshots import SUPPORTED_WIDTHS

        assert min(SUPPORTED_WIDTHS) == PHONE_FLOOR


_WHERE = """ids => Object.fromEntries(ids.map(id => {
  const box = document.getElementById(id).getBoundingClientRect();
  return [id, [Math.round(box.x), Math.round(box.y), Math.round(box.width)]];
}))"""


def _placed(html: str, ids: list[str]) -> dict[int, dict]:
    measured = {}
    with _load_playwright()() as playwright:
        browser = _launch(playwright)
        for width in (1000, PHONE_FLOOR):
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.route("**/*", lambda route: route.abort())
            page.set_content(html)
            measured[width] = {
                "at": page.evaluate(_WHERE, ids),
                "scroll": page.evaluate("() => document.documentElement.scrollWidth"),
                "align": page.evaluate(
                    "id => getComputedStyle(document.getElementById(id)).direction", ids[0]
                ),
            }
            page.close()
        browser.close()
    return measured


def _ided(stack, ratio="30-70"):
    return email(
        TwoColumn(
            ratio,
            TextBlock('<p id="L">Left copy</p>'),
            TextBlock('<p id="R">Right copy</p>'),
            stack=stack,
        ),
        FullWidth(
            Columns(
                [
                    CardGroup([KpiItem("Yield", "4.21%")], orientation="vertical"),
                    TextBlock('<p id="B">Beside</p>'),
                ],
                stack=stack,
            )
        ),
    ).render()


@requires_browser
class TestWhereTheColumnsLand:
    @pytest.fixture(scope="class")
    def placed(self):
        ids = ["L", "R", "B"]
        return {
            stack: _placed(_ided(stack, "50-50" if stack is False else "30-70"), ids)
            for stack in ("natural", "reverse", False)
        }

    def test_a_reversed_split_is_the_natural_one_on_a_desktop(self, placed):
        assert placed["reverse"][1000]["at"] == placed["natural"][1000]["at"]

    def test_on_a_phone_the_right_column_comes_first(self, placed):
        natural = placed["natural"][PHONE_FLOOR]["at"]
        reverse = placed["reverse"][PHONE_FLOOR]["at"]
        assert natural["L"][1] < natural["R"][1]
        assert reverse["R"][1] < reverse["L"][1]
        assert reverse["L"][0] == natural["L"][0]

    def test_reversed_copy_still_reads_left_to_right(self, placed):
        assert placed["reverse"][PHONE_FLOOR]["align"] == "ltr"

    def test_an_unstacked_pair_stays_side_by_side_on_a_phone(self, placed):
        at = placed[False][PHONE_FLOOR]["at"]
        assert at["L"][1] == at["R"][1] and at["L"][0] < at["R"][0]

    def test_nothing_overflows_the_floor(self, placed):
        for stack, widths in placed.items():
            assert widths[PHONE_FLOOR]["scroll"] <= PHONE_FLOOR, stack

    def test_unstacked_columns_sit_where_stacking_ones_do_on_a_desktop(self, placed):
        natural = _placed(_ided("natural", "50-50"), ["L", "R"])[1000]["at"]
        unstacked = placed[False][1000]["at"]
        for column in ("L", "R"):
            assert abs(natural[column][0] - unstacked[column][0]) <= 1
            assert abs(natural[column][2] - unstacked[column][2]) <= 1
