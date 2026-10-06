"""
Print typography (#385): a display title, fine print, justified prose and a qualifier.

Each setting on paper, on a slide and in a brochure panel where it reaches
them, and its stated degradation in the email. The PDF read-backs need
``[pdf]`` and ``[qa]`` and skip without either. The house typeface (#391) is
``test_house_typeface.py``'s.
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from pyhermes.brochure import Brochure, Panel
from pyhermes.builder import (
    ChartBlock,
    DataTable,
    EmailBuilder,
    FigureGrid,
    FullWidth,
    Header,
    ImageBlock,
    PullQuote,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import TableRow
from pyhermes.builder.sizing import (
    PRESENTATION_SIZES,
    STANDARD_SIZES,
    fine_print,
    measure_px,
    resolve_size_scheme,
)
from pyhermes.deck import Deck
from pyhermes.document import EmptyBackMatter, EmptyCover, ExhibitsPage, PagedDocument
from pyhermes.pdf import available, render_pdf
from qa.fixtures import _paged, _png, letter_brief

FACTS = {"firm_name": "Hermes Research", "campaign_name": "Brief"}
PNG = _png.solid_png(300, 100, (44, 62, 80))

needs_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='the PDF read-backs need the "[pdf]" and "[qa]" extras',
)


def _email(*sections):
    builder = EmailBuilder().metadata({**FACTS, "email_subject": "Brief"})
    for section in sections:
        builder.section(section)
    return builder.build()


def _paper(*sections, **regions):
    document = PagedDocument(
        _paged.facts(), cover=EmptyCover(), back_matter=EmptyBackMatter(), **regions
    )
    for section in sections:
        document.add_section(section)
    return document


def _h2(html: str, anchor: str) -> str:
    return re.search(rf'<h2 id="{anchor}"[^>]*>', html).group(0)


def _body(copy: str = "<p>Copy.</p>", **options) -> TextBlock:
    return TextBlock(copy, **options)


def _chart(**options) -> ChartBlock:
    return ChartBlock(EmailImage.attached(PNG, alt="Growth", width=300), **options)


class TestADisplayTitle:
    def _masthead(self, **options) -> FullWidth:
        return FullWidth(content=_body(), title="Meridian Fund", title_size="display", **options)

    def test_paper_sets_it_at_the_title_step(self):
        h2 = _h2(_paper(self._masthead()).render(), "meridian-fund")
        assert f"font-size:{STANDARD_SIZES.type.title}px" in h2
        assert "text-transform" not in h2

    def test_upper_case_is_css_and_the_text_part_keeps_the_callers_case(self):
        section = self._masthead(title_case="upper")
        email = _email(section)
        assert "text-transform:uppercase;" in _h2(email.render(), "meridian-fund")
        assert "Meridian Fund" in email.text()
        assert "MERIDIAN FUND" not in email.text()

    def test_an_email_drops_it_to_title_mobile_on_a_phone(self):
        html = _email(self._masthead()).render()
        h2 = _h2(html, "meridian-fund")
        assert 'class="mobile-title"' in h2
        assert f"font-size:{STANDARD_SIZES.type.title}px" in h2
        assert f".mobile-title {{ font-size:{STANDARD_SIZES.type.title_mobile}px" in html

    def test_it_is_still_the_sections_h2_and_contents_entry(self):
        document = _paper(self._masthead())
        assert document.render().count('<h2 id="meridian-fund"') == 1
        assert [anchor for anchor, _ in document._anchors()] == ["meridian-fund"]

    def test_unset_renders_exactly_as_before(self):
        plain = FullWidth(content=_body(), title="Meridian Fund")
        stated = FullWidth(content=_body(), title="Meridian Fund", title_size="section")
        assert _email(plain).render() == _email(stated).render()

    def test_a_slide_sets_it_at_the_presentation_title(self):
        deck = Deck(FACTS).add_slide([self._masthead()], "Statement")
        assert f"font-size:{PRESENTATION_SIZES.type.title}px" in _h2(deck.render(), "meridian-fund")

    def test_a_brochure_panel_sets_it_at_its_density_title(self):
        panels = [Panel([FullWidth(_body(f"<p>Face {n}</p>"))]) for n in range(5)]
        brochure = Brochure(FACTS, [Panel([self._masthead()]), *panels])
        title = resolve_size_scheme(brochure.metadata.size_theme).type.title
        assert f"font-size:{title}px" in _h2(brochure.render(), "meridian-fund")

    @pytest.mark.parametrize(
        ("options", "message"),
        [
            ({"title_size": "huge"}, "title_size"),
            ({"title_case": "lower"}, "title_case"),
        ],
    )
    def test_an_unknown_value_is_refused(self, options, message):
        with pytest.raises(ValidationError, match=message):
            FullWidth(content=_body(), title="T", **options)

    def test_an_untitled_section_cannot_set_how_its_title_looks(self):
        with pytest.raises(ValidationError, match="give the section a title"):
            FullWidth(content=_body(), title_size="display")


class TestFinePrint:
    def _fine(self, **options) -> FullWidth:
        return FullWidth(content=_body(), title="Disclosures", type_size="fine", **options)

    def test_paper_sets_the_copy_at_micro_and_keeps_the_title(self):
        html = _paper(self._fine()).render()
        assert f"font-size: {STANDARD_SIZES.type.micro}px" in html
        assert f"font-size:{STANDARD_SIZES.type.section}px" in _h2(html, "disclosures")

    def test_an_email_ignores_it(self):
        plain = FullWidth(content=_body(), title="Disclosures")
        assert _email(self._fine()).render() == _email(plain).render()

    def test_fine_print_keeps_the_measures_width(self):
        fine = fine_print(STANDARD_SIZES)
        for measure in ("standard", "narrow"):
            assert abs(measure_px(fine, measure) - measure_px(STANDARD_SIZES, measure)) <= 2

    def test_the_text_part_is_unchanged(self):
        plain = FullWidth(content=_body(), title="Disclosures")
        assert _paper(self._fine()).text() == _paper(plain).text()

    def test_an_unknown_size_is_refused(self):
        with pytest.raises(ValidationError, match="type_size"):
            FullWidth(content=_body(), type_size="tiny")

    def test_the_back_matter_stays_at_its_own_size(self):
        """Recorded in `design-axes.md`: a legal sheet is read at ``small``, not ``micro``."""
        html = PagedDocument(_paged.facts(), cover=EmptyCover()).render()
        assert f"font-size:{STANDARD_SIZES.type.small}px; line-height:" in html

    @needs_pdf
    def test_a_fine_print_section_sits_beside_a_reading_size_one(self):
        import pypdfium2

        pdf = pypdfium2.PdfDocument(render_pdf(letter_brief.build()))
        assert len(pdf) == letter_brief.SHEETS
        sheet = pdf[len(pdf) - 1].get_textpage().get_text_range()
        assert "How to read this brief" in sheet
        assert "Important information" in sheet


class TestJustifiedProse:
    def test_paper_justifies_and_hyphenates(self):
        html = _paper(FullWidth(content=_body(align="justify"), align="justify")).render()
        assert 'align="justify"' in html
        assert "text-align:justify; hyphens:auto;" in html

    def test_an_email_renders_it_as_unset(self):
        justified = FullWidth(content=_body(align="justify"), align="justify", title="Note")
        assert (
            _email(justified).render() == _email(FullWidth(content=_body(), title="Note")).render()
        )

    def test_a_split_justifies_each_column_on_paper(self):
        split = TwoColumn(left=_body(), right=_body(), align="justify")
        assert _paper(split).render().count("text-align:justify; hyphens:auto;") >= 2

    def test_a_short_line_refuses_it(self):
        with pytest.raises(ValidationError, match="align"):
            PullQuote("A line", align="justify")
        with pytest.raises(ValidationError, match="align"):
            Header(align="justify")

    @needs_pdf
    def test_the_brief_hyphenates_on_paper(self):
        """A line ends in a hyphen the copy never wrote: the engine broke a word."""
        import pypdfium2

        pdf = pypdfium2.PdfDocument(render_pdf(letter_brief.build()))
        text = "\n".join(page.get_textpage().get_text_range() for page in pdf)
        # The print engine breaks a word with U+2010, the unambiguous hyphen.
        broken = re.findall(r"([a-z]+)[-\u2010]\r?\n([a-z]+)", text)
        assert broken, "no justified line broke a word"


class TestAQualifier:
    def _table(self, **options) -> DataTable:
        return DataTable(["Period", "Fund"], [TableRow(["1 year", "18.2%"])], **options)

    def _image(self, **options) -> ImageBlock:
        return ImageBlock(EmailImage.attached(PNG, alt="Weights", width=300), **options)

    @pytest.mark.parametrize("make", ["_chart", "_table", "_image"])
    def test_it_renders_under_the_subtitle_in_both_media(self, make):
        build = _chart if make == "_chart" else getattr(self, make)
        block = build(subtitle="Growth of 10,000", qualifier="Total return, USD & fees")
        for html in (_email(FullWidth(block)).render(), _paper(FullWidth(block)).render()):
            subtitle = html.index("Growth of 10,000")
            qualifier = html.index("Total return, USD &amp; fees")
            assert subtitle < qualifier
            assert 'class="qualifier"' in html
            assert "font-weight: bold; font-style: italic;" in html

    def test_the_subtitle_closes_up_to_it(self):
        html = _email(FullWidth(_chart(subtitle="S", qualifier="Q"))).render()
        subtitle = re.search(r'<p class="subtitle"[^>]*>', html).group(0)
        assert "margin: 0 0 0 0;" in subtitle

    def test_without_one_nothing_moves(self):
        assert (
            _email(FullWidth(_chart(subtitle="S"))).render()
            == _email(FullWidth(_chart(subtitle="S", qualifier=""))).render()
        )

    def test_the_text_part_prints_it_under_the_subtitle(self):
        text = _email(FullWidth(self._table(subtitle="Returns", qualifier="Net, USD"))).text()
        assert "Returns\nNet, USD" in text

    def test_a_grid_carries_one_and_a_panel_none(self):
        panels = [self._image(subtitle="UK"), self._image(subtitle="US")]
        grid = FigureGrid(panels, subtitle="Weights", qualifier="Percent of assets")
        assert "Percent of assets" in _email(FullWidth(grid)).render()
        with pytest.raises(ValidationError, match="qualifier"):
            FigureGrid([self._image(qualifier="Q"), self._image()])

    def test_markup_is_refused_by_type_and_escaped_as_text(self):
        with pytest.raises(ValidationError, match="plain text"):
            _chart(qualifier=["Q"])
        assert "&lt;b&gt;" in _email(FullWidth(_chart(qualifier="<b>Q</b>"))).render()

    def test_the_list_of_exhibits_takes_none_of_it(self):
        chart = _chart(caption="Growth", label="Exhibit", qualifier="Total return, USD")
        document = _paper(FullWidth(chart, title="Results"), exhibits=ExhibitsPage())
        listing = document.render().split('<h2 id="results"')[0]
        assert "Growth" in listing
        assert "Total return, USD" not in listing

    def test_on_a_slide_it_keeps_the_source_line_and_reaches_the_notes(self):
        chart = _chart(subtitle="Growth", qualifier="Total return, USD", label="Exhibit")
        deck = Deck(FACTS).add_slide(
            [FullWidth(chart)], "Results", source="Fictional data", notes="Say the window."
        )
        html = deck.render()
        assert "Total return, USD" in html
        assert "Fictional data" in html
        notes = deck.notes()
        assert "Say the window." in notes
        assert "Exhibit 1: Total return, USD" in notes
        assert "Total return, USD" in deck.text()

    def test_a_slide_with_no_notes_lists_its_qualified_exhibit(self):
        deck = Deck(FACTS).add_slide([FullWidth(_chart(subtitle="Growth", qualifier="Q"))], "One")
        assert "Growth: Q" in deck.notes()
