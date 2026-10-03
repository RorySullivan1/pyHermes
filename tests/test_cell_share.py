"""
A fill-width block sized as a share of its cell (#357).

``DataTable``, ``CardGroup``, ``Callout`` and ``Contents`` take ``width=``,
0.3 to 1.0, and the section's ``align`` places them. The share is a
percentage on both spellings, so Outlook, a browser and the print engine
read one number; where each block lands is measured in a browser and in the
PDF's own layout, because no golden can see it.
"""

from __future__ import annotations

import pytest

from pyhermes.builder import (
    Callout,
    CardGroup,
    Columns,
    Contents,
    DataTable,
    Email,
    FullWidth,
    TextBlock,
    ValidationError,
)
from pyhermes.builder.models import KpiItem, TableRow
from pyhermes.builder.sizing import PHONE_FLOOR
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument
from pyhermes.pdf import available as pdf_available
from qa.screenshots import _launch, _load_playwright, available

requires_browser = pytest.mark.skipif(
    not available(), reason='no browser; screenshots are the optional "[qa]" extra'
)
requires_pdf = pytest.mark.skipif(
    not pdf_available(), reason='laying out a sheet needs the "[pdf]" extra'
)

FACTS = {"firm_name": "F", "campaign_name": "C"}

BLOCKS = {
    "DataTable": lambda w: DataTable(["Tenor", "Yield"], [TableRow(["10Y", "4.21%"])], width=w),
    "CardGroup": lambda w: CardGroup([KpiItem("A", "1"), KpiItem("B", "2")], width=w),
    "Callout": lambda w: Callout(TextBlock("<p>Key point</p>"), width=w),
    "Contents": lambda w: Contents(width=w),
}


def email(*sections) -> Email:
    built = Email({**FACTS, "email_subject": "S"})
    for section in sections:
        built.add_section(section)
    return built


def paged(*sections) -> PagedDocument:
    built = PagedDocument(FACTS, cover=EmptyCover(), back_matter=EmptyBackMatter())
    for section in sections:
        built.add_section(section)
    return built


def table(width=None) -> DataTable:
    return DataTable(
        ["Tenor", "Yield", "Change"],
        [TableRow(["2Y", "3.83%", "+9"]), TableRow(["10Y", "4.21%", "+18"])],
        width=width,
    )


class TestTheField:
    @pytest.mark.parametrize("name", list(BLOCKS))
    def test_a_share_in_range_is_kept_and_one_is_unset(self, name):
        assert BLOCKS[name](0.6).width == 0.6
        assert BLOCKS[name](0.3).width == 0.3
        assert BLOCKS[name](1).width is None
        assert BLOCKS[name](None).width is None

    @pytest.mark.parametrize("name", list(BLOCKS))
    @pytest.mark.parametrize("bad", [0.29, 1.01, 0, -1, True, "60%", 600])
    def test_a_share_out_of_range_is_refused_naming_the_bounds(self, name, bad):
        with pytest.raises(ValidationError, match=r"share of its cell"):
            BLOCKS[name](bad)

    def test_the_bounds_are_named(self):
        with pytest.raises(ValidationError, match=r"from 0\.3 to 1\.0, got: 0\.2"):
            table(0.2)

    def test_unset_and_full_render_the_same_bytes(self):
        assert email(FullWidth(table())).render() == email(FullWidth(table(1.0))).render()

    def test_both_spellings_carry_the_share(self):
        html = email(FullWidth(table(0.6))).render()
        assert 'width="60%"' in html
        assert "width:60%;" in html

    def test_the_section_alignment_places_it(self):
        centred = email(FullWidth(table(0.6), align="center")).render()
        assert '<td align="center" style="padding:0; text-align:center;">' in centred
        assert "margin-left:auto; margin-right:auto;" in centred
        right = email(FullWidth(table(0.6), align="right")).render()
        assert '<td align="right" style="padding:0; text-align:right;">' in right
        left = email(FullWidth(table(0.6))).render()
        assert "margin-left:auto" not in left

    def test_what_is_inside_is_sized_from_the_share(self):
        # A split in a callout is computed from the callout's cell: 616px at the
        # share, less the callout's padding and frame, 308 - 2 * 20 - 2.
        inside = Columns([TextBlock("<p>a</p>"), TextBlock("<p>b</p>")])
        html = email(FullWidth(Callout(inside, width=0.5))).render()
        assert 'width="266" border="0"' in html

    def test_width_projects_to_nothing(self):
        assert email(FullWidth(table(0.6))).text() == email(FullWidth(table())).text()


_SHARE = """() => [...document.querySelectorAll('table.data-table')].map(el => {
  const inner = el.parentElement.closest('table');
  const outer = inner.parentElement.closest('table');
  return [el.getBoundingClientRect().width, inner.getBoundingClientRect().width,
          outer.getBoundingClientRect().width, inner.getBoundingClientRect().x,
          outer.getBoundingClientRect().x];
})"""


@requires_browser
class TestInABrowser:
    @pytest.mark.parametrize("viewport", [1000, PHONE_FLOOR])
    def test_a_centred_table_takes_its_share_and_sits_in_the_middle(self, viewport):
        html = email(FullWidth(table(0.6), align="center")).render()
        with _load_playwright()() as playwright:
            browser = _launch(playwright)
            page = browser.new_page(viewport={"width": viewport, "height": 900})
            page.route("**/*", lambda route: route.abort())
            page.set_content(html)
            [(own, inner, outer, inner_x, outer_x)] = page.evaluate(_SHARE)
            scroll = page.evaluate("() => document.documentElement.scrollWidth")
            browser.close()
        assert inner / outer == pytest.approx(0.6, abs=0.01)
        assert own == pytest.approx(inner, abs=1)
        left_gap = inner_x - outer_x
        assert left_gap == pytest.approx((outer - inner) / 2, abs=1)
        assert scroll <= viewport


def _boxes(document, cls: str):
    from weasyprint.formatting_structure import boxes as wp

    from pyhermes.pdf import layout

    def walk(box):
        yield box
        for child in getattr(box, "children", []):
            yield from walk(child)

    found = []
    for page in layout(document).pages:
        for box in walk(page._page_box):
            element = getattr(box, "element", None)
            if (
                isinstance(box, wp.TableBox)
                and element is not None
                and cls in (element.get("class") or "").split()
            ):
                found.append(box)
    return found


@requires_pdf
class TestOnPaper:
    def test_a_centred_table_takes_its_share_of_the_column(self):
        full = _boxes(paged(FullWidth(table())), "data-table")[0]
        share = _boxes(paged(FullWidth(table(0.6), align="center")), "data-table")[0]
        assert share.width == pytest.approx(full.width * 0.6, abs=1)
        left_gap = share.position_x - full.position_x
        assert left_gap == pytest.approx(full.width * 0.2, abs=1)
