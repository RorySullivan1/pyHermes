"""
Single-sheet print pieces (#386): bleed, a pinned foot, separated rows, and a quiet first sheet.

Each feature on paper, in a brochure panel and on a slide where it reaches
them, and its stated degradation in the email. The PDF read-backs need
``[pdf]`` and ``[qa]`` and skip without either.
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from pyhermes.brochure import TRI_FOLD_LETTER, Brochure, Panel
from pyhermes.builder import Callout, Columns, EmailBuilder, FullWidth, TextBlock, TwoColumn
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.sizing import LETTER_PORTRAIT
from pyhermes.deck import SLIDE_16_9, Deck
from pyhermes.document import (
    EmptyBackMatter,
    EmptyCover,
    Page,
    PagedDocument,
    RunningFooter,
    RunningHeader,
    paged_medium,
)
from pyhermes.pdf import available, render_pdf
from qa.fixtures import _paged, letter_product_brief, pitch_16_9, product_brief_layout

NAVY = "#1B2A3A"

needs_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='the PDF read-backs need the "[pdf]" and "[qa]" extras',
)


def _email(*sections):
    builder = EmailBuilder().metadata(
        {"email_subject": "Brief", "firm_name": "Hermes Research", "campaign_name": "Brief"}
    )
    for section in sections:
        builder.section(section)
    return builder.build()


def _paper(*sections, **regions):
    regions = {"cover": EmptyCover(), "back_matter": EmptyBackMatter(), **regions}
    document = PagedDocument(_paged.facts(), medium=paged_medium(LETTER_PORTRAIT), **regions)
    for section in sections:
        document.add_section(section)
    return document


def _band(**options):
    return FullWidth(TextBlock("<p>Band.</p>"), title="Band", background_color=NAVY, **options)


def _box(copy="Box"):
    return Callout(TextBlock(f"<p>{copy}</p>"))


def _bled(html: str) -> list[str]:
    return re.findall(r'<div class="bled" style="([^"]*)"', html)


def _sheets(document):
    import pypdfium2

    return list(pypdfium2.PdfDocument(render_pdf(document)))


class TestABandRunsToTheEdge:
    """#396."""

    def test_bleed_is_true_or_false(self):
        with pytest.raises(ValidationError, match="bleed is True or False"):
            _band(bleed="yes")

    def test_an_email_is_byte_identical_with_and_without_it(self):
        assert _email(_band(bleed=True)).render() == _email(_band()).render()

    def test_paper_runs_the_ground_over_the_margin_and_gives_it_back(self):
        margin = LETTER_PORTRAIT.margin
        (style,) = _bled(_paper(_band(bleed=True)).render())
        assert f"margin:-{margin.top}px -{margin.right}px 0 -{margin.left}px" in style
        assert f"padding:{margin.top}px {margin.right}px 0 {margin.left}px" in style
        assert NAVY in style

    def test_the_top_edge_only_where_the_section_opens_a_sheet(self):
        html = _paper(FullWidth(TextBlock("<p>Lead.</p>")), _band(bleed=True)).render()
        (style,) = _bled(html)
        assert style.startswith("margin:-0px")

    def test_a_break_or_a_page_opens_a_sheet(self):
        top = LETTER_PORTRAIT.margin.top
        lead = FullWidth(TextBlock("<p>Lead.</p>"))
        broken = _paper(lead, _band(bleed=True, break_before=True)).render()
        paged = _paper(lead, Page([_band(bleed=True)])).render()
        for html in (broken, paged):
            assert _bled(html)[0].startswith(f"margin:-{top}px")

    def test_a_split_bleeds_too(self):
        split = TwoColumn(
            left=_box(), right=_box(), title="Split", background_color=NAVY, bleed=True
        )
        assert _bled(_paper(split).render())

    def test_a_brochure_panel_grows_into_the_bleed_on_its_trim_edges(self):
        bleed = TRI_FOLD_LETTER.bleed
        panels = [Panel([_band(bleed=n == 0, anchor=f"b{n}")]) for n in range(6)]
        html = Brochure(_paged.facts(), panels, fold=TRI_FOLD_LETTER).render()
        styles = _bled(html)
        assert len(styles) == 1
        inset = TRI_FOLD_LETTER.inset
        assert styles[0].startswith(f"margin:-{inset + bleed}px")
        assert "overflow:visible" in html

    def test_an_unbled_brochure_is_unchanged(self):
        panels = [Panel([_band(anchor=f"b{n}")]) for n in range(6)]
        html = Brochure(_paged.facts(), panels, fold=TRI_FOLD_LETTER).render()
        assert "overflow:visible" not in html and not _bled(html)

    def test_a_slide_frame_already_spans_its_sheet(self):
        deck = Deck(pitch_16_9.facts(), page=SLIDE_16_9)
        deck.add_slide([_band(bleed=True)], "Slide")
        (style,) = _bled(deck.render())
        assert style.startswith("margin:-0px -0px 0 -0px")

    @needs_pdf
    def test_the_band_reaches_three_edges_of_the_sheet(self):
        image = _sheets(_paper(_band(bleed=True)))[0].render(scale=1).to_pil().convert("RGB")
        width, _ = image.size
        navy = (0x1B, 0x2A, 0x3A)
        for point in ((1, 1), (width - 2, 1), (width // 2, 1)):
            assert image.getpixel(point) == navy, point


class TestASectionPinnedToTheFoot:
    """#397."""

    def test_pin_is_bottom_or_none(self):
        with pytest.raises(ValidationError, match="pin must be one of"):
            _band(pin="top")

    def test_an_email_flows_it_in_place(self):
        assert _email(_band(pin="bottom")).render() == _email(_band()).render()

    def test_paper_floats_it_to_the_footnote_area_and_says_so_in_the_head(self):
        html = _paper(_band(pin="bottom")).render()
        assert '<div class="pinned" style="float:footnote;' in html
        assert ".pinned::footnote-call { content: none; }" in html

    def test_an_unpinned_document_carries_no_rule(self):
        assert ".pinned" not in _paper(_band()).render()

    def test_a_panel_and_a_slide_set_it_on_the_boxs_foot(self):
        panels = [Panel([_band(pin="bottom", anchor=f"b{n}")]) for n in range(6)]
        brochure = Brochure(_paged.facts(), panels, fold=TRI_FOLD_LETTER).render()
        assert f"bottom:{TRI_FOLD_LETTER.inset}px" in brochure
        deck = Deck(pitch_16_9.facts(), page=SLIDE_16_9)
        deck.add_slide([_band(pin="bottom")], "Slide")
        assert "position:absolute; left:0; right:0; bottom:0px;" in deck.render()

    @needs_pdf
    def test_it_sits_at_the_foot_of_its_sheet(self):
        (sheet,) = _sheets(_paper(FullWidth(TextBlock("<p>Lead.</p>")), _band(pin="bottom")))
        image = sheet.render(scale=1).to_pil().convert("RGB")
        width, height = image.size
        rows = [y for y in range(height) if image.getpixel((width // 2, y)) == (0x1B, 0x2A, 0x3A)]
        bottom_margin = LETTER_PORTRAIT.margin.bottom * 0.75
        assert rows and rows[0] > height / 2
        assert abs(rows[-1] - (height - bottom_margin)) < 3

    @needs_pdf
    def test_one_too_tall_for_the_space_left_starts_a_sheet(self):
        filler = FullWidth(TextBlock("<p>" + "Filler copy. " * 520 + "</p>"))
        sheets = _sheets(_paper(filler, _band(pin="bottom")))
        texts = [sheet.get_textpage().get_text_range() for sheet in sheets]
        assert "Band." not in texts[0]
        assert "Band." in texts[-1]


class TestARowWithSeparators:
    """#398, #399."""

    def test_a_row_holds_two_to_six(self):
        Columns([_box() for _ in range(6)])
        with pytest.raises(ValidationError, match="2 to 6"):
            Columns([_box() for _ in range(7)])

    @pytest.mark.parametrize("separator", ["", "   ", "plus", 3])
    def test_a_separator_is_short(self, separator):
        with pytest.raises(ValidationError, match="separator"):
            Columns([_box(), _box()], separator=separator)

    def test_a_reversed_row_refuses_one(self):
        with pytest.raises(ValidationError, match="reversed"):
            Columns([_box(), _box()], separator="+", stack="reverse")

    def test_equal_weights_give_equal_slots_outside_the_separators(self):
        html = _email(FullWidth(Columns([_box(), _box(), _box()], separator="+"))).render()
        shares = re.findall(r'<td class="stack-column" width="([\d.]+)%" valign', html)
        separators = re.findall(r'<td class="stack-column" width="([\d.]+)%" align="center"', html)
        assert len(set(shares)) == 1 and len(shares) == 3
        assert len(separators) == 2
        assert sum(map(float, shares + separators)) <= 100

    def test_the_glyph_is_escaped_and_paper_never_stacks(self):
        row = FullWidth(Columns([_box(), _box()], separator="<"))
        assert "&lt;" in _email(row).render()
        assert "stack-column" not in _paper(row).render().split("<body>")[1]

    def test_an_arrow_draws_the_trend_arrows_shape_with_its_word_twin(self):
        html = _email(FullWidth(Columns([_box(), _box()], separator="arrow"))).render()
        assert 'path="m 0,0 l 2,1 0,2 x e"' in html
        assert "connector connector-right" in html and "connector connector-down" in html
        assert ".connector-across { display:none !important; }" in html

    def test_only_an_arrow_brings_the_phone_rule(self):
        html = _email(FullWidth(Columns([_box(), _box()], separator="+"))).render()
        assert "connector-across" not in html

    def test_an_unstacked_row_draws_only_the_right_arrow(self):
        row = Columns([_box(), _box()], separator="arrow", stack=False)
        html = _email(FullWidth(row)).render()
        assert "connector-right" in html and "connector-down" not in html

    def test_the_text_part_reads_the_slots_in_order(self):
        row = FullWidth(Columns([_box("Left"), _box("Right")], separator="arrow"))
        plain = FullWidth(Columns([_box("Left"), _box("Right")]))
        assert _email(row).text() == _email(plain).text()

    def test_a_panel_and_a_slide_render_one(self):
        row = FullWidth(Columns([_box(), _box()], separator="arrow"), anchor="row")
        panels = [Panel([row] if n == 0 else [_band(anchor=f"b{n}")]) for n in range(6)]
        assert "connector-right" in Brochure(_paged.facts(), panels, fold=TRI_FOLD_LETTER).render()
        deck = Deck(pitch_16_9.facts(), page=SLIDE_16_9)
        deck.add_slide([row], "Slide")
        assert "connector-right" in deck.render()


class TestTheFirstSheetIsQuiet:
    """#400."""

    def test_skip_first_is_true_or_false(self):
        with pytest.raises(ValidationError, match="skip_first"):
            _paper(_band(), running_footer=RunningFooter(skip_first="yes"))

    def test_it_blanks_the_box_under_the_first_page_rule(self):
        html = _paper(_band(), running_footer=RunningFooter(skip_first=True)).render()
        assert "@page :first { @bottom-center { content: none; } }" in html

    @needs_pdf
    def test_sheet_one_has_no_footer_and_sheet_two_reads_two(self):
        filler = FullWidth(TextBlock("<p>" + "Filler copy. " * 600 + "</p>"))
        document = _paper(
            filler,
            running_header=RunningHeader(label="Head", skip_first=True),
            running_footer=RunningFooter(label="Foot", skip_first=True),
        )
        texts = [sheet.get_textpage().get_text_range() for sheet in _sheets(document)]
        assert len(texts) >= 2
        assert "Foot" not in texts[0] and "Head" not in texts[0]
        assert "Foot · 2 / " in texts[1] and "Head" in texts[1]


class TestTheProductBrief:
    """#401."""

    def test_its_email_passes_lint(self):
        from pyhermes.check.lint import Severity, lint_document

        findings = lint_document(product_brief_layout.build())
        assert not [f for f in findings if f.severity is Severity.ERROR]

    def test_it_uses_no_glyph_arrow(self):
        html = product_brief_layout.build().render()
        assert not re.search("[←-⇿▶►]", html)

    @needs_pdf
    def test_it_prints_on_exactly_three_sheets(self):
        sheets = _sheets(letter_product_brief.build())
        assert len(sheets) == letter_product_brief.SHEETS == 3
        texts = [sheet.get_textpage().get_text_range() for sheet in sheets]
        assert letter_product_brief.LABEL not in texts[0]
        assert "· 2 / 3" in texts[1]
