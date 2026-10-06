"""
Epic #335: exhibits that group.

#336 is ``FigureGrid``, lettered panels in one numbered exhibit; #337 is
``Legend``, a chart's key stated in markup; #338 is a section's own source
line; #339 the fixtures that carry all three through both media.
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from pyhermes.builder import (
    Appendices,
    ChartBlock,
    Contents,
    DataTable,
    Email,
    FigureGrid,
    FourColumn,
    FullWidth,
    ImageBlock,
    Legend,
    LegendEntry,
    MathBlock,
    Only,
    Stack,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import TableRow
from pyhermes.builder.theming import DEFAULT_THEME, SLATE_THEME, chart_colors
from pyhermes.deck import Deck, EmptyClosingSlide, EmptyTitleSlide, overflowing_slides
from pyhermes.document import PagedDocument
from pyhermes.pdf import available as pdf_available
from qa.fixtures import a4_research_note, research_note
from qa.fixtures._png import solid_png
from qa.fixtures._research import EXHIBITS, PANELS

FACTS = {"email_subject": "S", "firm_name": "Hermes", "campaign_name": "Grouped"}
PAPER = {"firm_name": "Hermes", "campaign_name": "Grouped"}

requires_pdf = pytest.mark.skipif(
    not pdf_available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)


def email(*sections, **facts) -> Email:
    built = Email({**FACTS, **facts})
    for section in sections:
        built.add_section(section)
    return built


def paper(*sections) -> PagedDocument:
    built = PagedDocument(PAPER)
    for section in sections:
        built.add_section(section)
    return built


def _sheets(document) -> list[str]:
    import pypdfium2

    from pyhermes.pdf import render_pdf

    pdf = pypdfium2.PdfDocument(render_pdf(document))
    return [page.get_textpage().get_text_range() for page in pdf]


def _image(alt: str = "Chart", rgb: tuple[int, int, int] = (42, 61, 84)) -> EmailImage:
    return EmailImage.attached(solid_png(300, 120, rgb), alt=alt, width=300)


def chart(caption: str = "", label: str = "", **kwargs) -> ChartBlock:
    return ChartBlock(_image(caption or "Chart"), caption=caption, label=label, **kwargs)


def grid(caption: str = "Term premium", count: int = 2, **kwargs) -> FigureGrid:
    names = ["UK", "US", "Euro area", "Japan"][:count]
    panels = [
        ChartBlock(_image(f"{n} premium", (40 + i, 61, 84)), subtitle=n)
        for i, n in enumerate(names)
    ]
    return FigureGrid(panels, caption=caption, **kwargs)


# ----------------------------------------------------------------------
# #336 — FigureGrid
# ----------------------------------------------------------------------


class TestTheGridIsOneExhibit:
    @pytest.fixture
    def document(self):
        return email(
            FullWidth(content=chart("First", label="Exhibit")),
            FullWidth(content=grid()),
            FullWidth(content=chart("Third", label="Exhibit")),
        )

    def test_the_walk_numbers_it_once_between_two_singles(self, document):
        found = re.findall(r"Exhibit (\d) · (\w+)", document.render())
        assert found == [("1", "First"), ("2", "Term"), ("3", "Third")]
        assert re.findall(r"Exhibit (\d) · (\w+)", document.text()) == found

    def test_its_panels_anchor_beneath_its_anchor(self, document):
        html = document.render()
        assert 'id="exhibit-2"' in html
        assert html.count('id="exhibit-2-a"') == 1 and html.count('id="exhibit-2-b"') == 1

    def test_each_panel_prints_its_letter_and_title(self, document):
        html = document.render()
        assert "(a) UK" in html and "(b) US" in html

    def test_a_cross_reference_to_a_panel_validates(self, document):
        document.add_section(
            FullWidth(content=TextBlock('<p><a class="xref" href="#exhibit-2-b">2(b)</a></p>'))
        )
        document.validate()

    def test_a_panel_the_grid_lacks_is_named(self, document):
        document.add_section(FullWidth(content=TextBlock('<p><a href="#exhibit-2-c">c</a></p>')))
        with pytest.raises(ValidationError, match="#exhibit-2-c"):
            document.validate()

    def test_a_list_of_exhibits_lists_the_grid_once(self, document):
        listing = Contents(of="exhibits")
        document.add_section(FullWidth(content=listing))
        document.validate()
        assert [title for title, _ in listing.entries] == [
            "Exhibit 1 · First",
            "Exhibit 2 · Term premium",
            "Exhibit 3 · Third",
        ]

    def test_in_an_appendix_it_numbers_by_letter(self):
        document = email(Appendices([FullWidth(title="Data", content=grid())]))
        html = document.render()
        assert "Exhibit A.1 · Term premium" in html
        assert 'id="exhibit-a-1-a"' in html and 'id="exhibit-a-1-b"' in html

    def test_an_unlabelled_grid_has_no_panel_anchors(self):
        html = email(FullWidth(content=grid(label=""))).render()
        assert "exhibit-" not in html and "(a) UK" in html

    def test_an_anchor_of_its_own_carries_the_panels_too(self):
        html = email(FullWidth(content=grid(anchor="premia"))).render()
        assert 'id="premia"' in html and 'id="premia-b"' in html

    def test_a_panel_anchor_that_collides_is_refused(self):
        document = email(FullWidth(content=grid(anchor="premia")))
        with pytest.raises(ValidationError, match="'premia-a' is claimed twice"):
            document.add_section(FullWidth(title="Premia A", content=TextBlock("<p>x</p>")))


class TestItsProjections:
    def test_the_text_prints_the_heading_once_then_each_letter_and_alt(self):
        text = email(FullWidth(content=grid(source="Source: BoE"))).text()
        heading, *rest = text[text.index("Exhibit 1") :].split("\n\n")[:4]
        assert heading == "Exhibit 1 · Term premium"
        assert rest == ["(a) UK [UK premium]", "(b) US [US premium]", "Source: BoE"]
        assert text.count("Exhibit 1") == 1

    def test_the_shared_copy_sits_beneath_every_panel_once(self):
        html = email(
            FullWidth(content=grid(source="Source: BoE", disclosure="Model estimates."))
        ).render()
        assert html.count("Source: BoE") == 1 and html.count("Model estimates.") == 1
        assert html.index("(b) US") < html.index("Source: BoE") < html.index("Model estimates.")

    def test_a_marker_in_its_source_is_numbered(self):
        document = email(FullWidth(content=grid(source="BoE[^1]", notes=["Daily."])))
        assert "BoE[1]" in document.text() and 'id="note-ref-1"' in document.render()

    def test_its_images_reach_the_manifest_through_its_panels(self):
        document = email(FullWidth(content=grid(count=4)))
        assert len(document.images()) == 4 and len(document.assets()) == 4

    def test_a_chart_panel_keeps_its_border_and_a_picture_none(self):
        mixed = FigureGrid(
            [ChartBlock(_image("A"), subtitle="A"), ImageBlock(_image("B"), subtitle="B")]
        )
        html = mixed.render(TemplateEngine().bound())
        borders = re.findall(r'<img [^>]*border: ([^;"]+)', html)
        assert borders == [f"1px solid {DEFAULT_THEME.palette.rule}", "0"]

    def test_a_linked_picture_panel_links(self):
        linked = ImageBlock(_image("B"), subtitle="B", link_url="https://example.com/b")
        html = FigureGrid([ChartBlock(_image("A")), linked]).render(TemplateEngine().bound())
        assert '<a href="https://example.com/b"' in html


class TestItsLayout:
    def test_two_panels_sit_two_across_and_stack_on_a_phone(self):
        html = grid().render(TemplateEngine().bound())
        assert html.count('class="figure-grid"') == 1
        assert html.count('class="stack-column"') == 3, "two panels and the gutter between"

    def test_a_short_last_row_keeps_its_panels_the_rows_width(self):
        html = grid(count=3).render(TemplateEngine().bound())
        rows = html.split('class="figure-grid"')[1:]
        assert len(rows) == 2
        assert rows[0].count('width="48.7%"') == rows[1].count('width="48.7%"') == 2

    def test_four_panels_in_one_row(self):
        html = grid(count=4, columns=4).render(TemplateEngine().bound())
        assert html.count('class="figure-grid"') == 1

    def test_a_panels_image_is_sized_to_its_cell(self):
        wide = FigureGrid(
            [ChartBlock(EmailImage.attached(solid_png(600, 90, (1, 2, 3)), alt="A", width=600))] * 2
        )
        assert re.findall(r'<img [^>]*width="(\d+)"', wide.render(TemplateEngine().bound())) == [
            "300",
            "300",
        ]

    def test_on_paper_only_a_row_has_a_gap_under_it(self):
        html = paper(FullWidth(content=grid(count=4))).render()
        gaps = re.findall(r'id="exhibit-1-[a-d]"[^>]*padding: ([^;]+);', html)
        assert gaps == ["0 0 16px 0", "0 0 16px 0", "0", "0"]

    def test_in_an_email_every_panel_but_the_last_has_one(self):
        html = email(FullWidth(content=grid(count=4))).render()
        gaps = re.findall(r'id="exhibit-1-[a-d]"[^>]*padding: ([^;]+);', html)
        assert gaps == ["0 0 16px 0", "0 0 16px 0", "0 0 16px 0", "0"]

    def test_one_figure_table_holds_every_panel(self):
        html = email(FullWidth(content=grid(count=3))).render()
        assert html.count('class="figure"') == 1
        figure = html[html.index('class="figure"') :]
        assert all(f'id="exhibit-1-{letter}"' in figure for letter in "abc")


class TestARefusal:
    @pytest.mark.parametrize(
        "field", ["label", "anchor", "caption", "source", "disclosure", "wrap"]
    )
    def test_a_panel_may_not_carry_what_the_grid_carries(self, field):
        value = {"label": "Exhibit", "anchor": "own", "wrap": "left"}.get(field, "Copy.")
        panel = ChartBlock(_image(), **{field: value})
        with pytest.raises(ValidationError, match=f"panels\\[0\\] sets {field}="):
            FigureGrid([panel, chart()])

    def test_a_panel_may_not_carry_notes(self):
        panel = ChartBlock(_image(), source="Src[^1]", notes=["n"])
        with pytest.raises(ValidationError, match="sets source="):
            FigureGrid([panel, chart()])

    def test_a_table_is_its_own_exhibit(self):
        table = DataTable(["A"], [TableRow(["1"])])
        with pytest.raises(ValidationError, match="A table is its own exhibit"):
            FigureGrid([chart(), table])  # type: ignore[list-item]

    def test_a_decorative_panel_is_refused(self):
        panel = ImageBlock("https://example.com/x.png", decorative=True, width=200)
        with pytest.raises(ValidationError, match="decorative"):
            FigureGrid([chart(), panel])

    @pytest.mark.parametrize("count", [0, 1, 5])
    def test_two_to_four_panels(self, count):
        with pytest.raises(ValidationError, match="2 to 4 panels"):
            FigureGrid([chart() for _ in range(count)])

    @pytest.mark.parametrize("columns", [0, 3, True, "2"])
    def test_columns_run_one_to_the_panels(self, columns):
        with pytest.raises(ValidationError, match="columns run 1 to its 2 panels"):
            FigureGrid([chart(), chart()], columns=columns)

    def test_no_nested_grid(self):
        with pytest.raises(ValidationError, match="ChartBlock or an ImageBlock"):
            FigureGrid([grid(), chart()])  # type: ignore[list-item]

    def test_an_equation_is_not_a_panel(self):
        equation = MathBlock(solid_png(40, 12, (0, 0, 0)), latex="x")
        with pytest.raises(ValidationError, match="ChartBlock or an ImageBlock"):
            FigureGrid([equation, chart()])  # type: ignore[list-item]

    def test_a_labelled_grid_is_refused_in_one_medium_only(self):
        with pytest.raises(ValidationError, match="labelled 'Exhibit'"):
            Only(grid(), "email")


class TestInEveryMedium:
    def test_a_grid_renders_on_a_slide(self):
        deck = Deck(PAPER, title_slide=EmptyTitleSlide(), closing_slide=EmptyClosingSlide())
        deck.add_slide([FullWidth(content=grid())], title="Premia")
        html = deck.render()
        assert 'id="exhibit-1-b"' in html

    @requires_pdf
    def test_two_and_four_panels_fit_a_slide(self):
        deck = Deck(PAPER, title_slide=EmptyTitleSlide(), closing_slide=EmptyClosingSlide())
        deck.add_slide([FullWidth(content=grid())], title="Two")
        deck.add_slide([FullWidth(content=grid(count=4, columns=4))], title="Four")
        assert overflowing_slides(deck) == []

    @requires_pdf
    def test_a_cross_reference_to_a_panel_reads_its_page_on_paper(self):
        lead = "".join(f"<p>Lead-in line {n}.</p>" for n in range(70))
        see = '<p>See <a class="xref" href="#exhibit-1-b">1(b)</a>.</p>'
        document = paper(
            FullWidth(content=TextBlock(see)),
            FullWidth(content=TextBlock(lead)),
            FullWidth(content=grid()),
        )
        sheets = _sheets(document)
        on = next(n for n, text in enumerate(sheets, 1) if "(b) US" in text)
        cited = next(n for n, text in enumerate(sheets, 1) if "See 1(b)" in text)
        assert on > cited, "the grid did not move off the citing sheet"
        assert f"1(b) (p. {on})" in sheets[cited - 1]

    @requires_pdf
    def test_on_paper_the_grid_keeps_to_one_sheet(self):
        landed = set()
        for lead in range(36, 48):
            sheets = _sheets(
                paper(
                    FullWidth(TextBlock("".join(f"<p>Line {n}.</p>" for n in range(lead)))),
                    FullWidth(content=grid(count=4, source="Source: probe")),
                )
            )
            [(at, sheet)] = [(i, t) for i, t in enumerate(sheets) if "(a) UK" in t]
            assert all(f"({letter})" in sheet for letter in "abcd"), f"split at {lead} lines"
            landed.add(at)
        assert len(landed) > 1, "the sweep never moved the grid across a sheet"


# ----------------------------------------------------------------------
# #337 — Legend
# ----------------------------------------------------------------------


class TestALegend:
    def test_bare_labels_take_the_chart_colours_in_order(self):
        key = Legend(["10Y gilt", "2Y gilt"])
        assert [e.series for e in key.entries] == [0, 1]
        html = key.render(TemplateEngine().bound())
        fills = re.findall(r"legend-swatch[^>]*background-color: (#\w+)", html)
        assert fills == list(chart_colors(DEFAULT_THEME)[:2])

    def test_a_series_recolours_with_the_theme(self):
        key = Legend(["10Y gilt"])
        html = email(FullWidth(content=key), theme="slate").render()
        assert f"background-color: {chart_colors(SLATE_THEME)[0]}" in html

    def test_a_tone_is_the_themes_semantic_colour(self):
        html = Legend([LegendEntry("Down", tone="negative")]).render(TemplateEngine().bound())
        assert f"background-color: {DEFAULT_THEME.semantic.negative}" in html

    def test_it_draws_no_image(self):
        html = Legend(["A", "B", "C", "D"]).render(TemplateEngine().bound())
        assert "<img" not in html and html.count("legend-swatch") == 4

    def test_the_text_states_the_key(self):
        assert Legend(["10Y gilt", "2Y gilt"]).text() == "Key: 10Y gilt, 2Y gilt"

    def test_a_column_puts_one_entry_a_line(self):
        html = Legend(["A", "B"], layout="column").render(TemplateEngine().bound())
        assert html.count('<div style="margin: 0;">') == 2

    def test_under_a_chart_it_sits_between_the_picture_and_the_source(self):
        block = ChartBlock(_image(), source="Source: BoE", legend=Legend(["10Y", "2Y"]))
        html = email(FullWidth(content=block)).render()
        assert html.index("<img") < html.index('class="legend"') < html.index("Source: BoE")
        text = email(FullWidth(content=block)).text()
        assert "[Chart]\n\nKey: 10Y, 2Y\n\nSource: BoE" in text

    def test_a_chart_takes_only_a_legend(self):
        with pytest.raises(ValidationError, match="legend is a Legend"):
            ChartBlock(_image(), legend=TextBlock("<p>x</p>"))  # type: ignore[arg-type]

    def test_a_chart_with_a_key_is_still_one_exhibit(self):
        block = chart("Rates", label="Exhibit", legend=Legend(["A"]))
        document = email(FullWidth(content=Stack([block, chart("Next", label="Exhibit")])))
        assert re.findall(r"Exhibit (\d) · (\w+)", document.text()) == [
            ("1", "Rates"),
            ("2", "Next"),
        ]


class TestALegendRefusal:
    def test_a_colour_outside_the_themes_chart_colours_is_refused(self):
        key = Legend([LegendEntry("Odd", color="#123456")])
        with pytest.raises(ValidationError, match="not one of this theme's chart colours"):
            email(FullWidth(content=key))

    def test_a_chart_colour_of_another_theme_is_refused(self):
        classic = chart_colors(DEFAULT_THEME)[0]
        key = Legend([LegendEntry("Classic", color=classic)])
        with pytest.raises(ValidationError, match="chart colours"):
            email(FullWidth(content=ChartBlock(_image(), legend=key)), theme="slate")

    def test_a_chart_colour_of_the_theme_is_accepted(self):
        key = Legend([LegendEntry("Accent", color=chart_colors(DEFAULT_THEME)[0].lower())])
        email(FullWidth(content=key))

    def test_a_refused_legend_in_a_grid_panel_is_found(self):
        key = Legend([LegendEntry("Odd", color="#123456")])
        panel = ChartBlock(_image(), legend=key)
        with pytest.raises(ValidationError, match="chart colours"):
            email(FullWidth(content=FigureGrid([panel, chart()])))

    @pytest.mark.parametrize(
        ("entry", "message"),
        [
            (LegendEntry("A"), "one way"),
            (LegendEntry("A", tone="positive", series=0), "one way"),
            (LegendEntry("A", tone="Up"), "tone' must be one of"),
            (LegendEntry("A", color="teal"), "hex color"),
            (LegendEntry("A", series=-1), "series indexes"),
            (LegendEntry("A", series=True), "series indexes"),
            (LegendEntry(" ", series=0), "needs a label"),
        ],
    )
    def test_an_entry_names_one_colour_one_way(self, entry, message):
        with pytest.raises(ValidationError, match=message):
            Legend([entry])

    @pytest.mark.parametrize("entries", [[], ["x"] * 13, "abc"])
    def test_one_to_twelve_entries(self, entries):
        with pytest.raises(ValidationError, match="1 to 12 entries"):
            Legend(entries)

    def test_a_layout_is_row_or_column(self):
        with pytest.raises(ValidationError, match="layout is one of"):
            Legend(["A"], layout="grid")


# ----------------------------------------------------------------------
# #338 — a section's source line
# ----------------------------------------------------------------------


def _source_lines(html: str) -> list[str]:
    return re.findall(r'<p class="fine-print section-source"[^>]*>(.*?)</p>', html, re.S)


class TestASectionSource:
    def test_it_renders_one_line_at_the_foot_of_a_full_width_section(self):
        section = FullWidth(
            title="Rates", content=TextBlock("<p>Body.</p>"), source="Source: BoE", as_of="1 Oct"
        )
        html = email(section).render()
        assert _source_lines(html) == ["Source: BoE as of 1 Oct"]
        assert html.index("Body.") < html.index("Source: BoE")

    @pytest.mark.parametrize("medium", ["email", "paper"])
    def test_it_renders_under_a_splits_columns(self, medium):
        section = TwoColumn(
            left=TextBlock("<p>Left.</p>"), right=TextBlock("<p>Right.</p>"), source="Source: ONS"
        )
        html = (email if medium == "email" else paper)(section).render()
        assert _source_lines(html) == ["Source: ONS"]
        assert html.index("Right.") < html.index("Source: ONS")

    def test_four_columns_take_one_too(self):
        section = FourColumn([TextBlock("<p>a</p>")] * 4, source="Source: four")
        assert _source_lines(email(section).render()) == ["Source: four"]

    def test_its_copy_is_escaped(self):
        html = email(FullWidth(content=TextBlock("<p>x</p>"), source="S&P <500>")).render()
        assert _source_lines(html) == ["S&amp;P &lt;500&gt;"]

    def test_the_text_prints_it_after_the_blocks(self):
        section = FullWidth(
            title="Rates", content=TextBlock("<p>Body.</p>"), source="Source: BoE", as_of="1 Oct"
        )
        assert email(section).text().count("Body.\n\nSource: BoE as of 1 Oct") == 1

    def test_a_note_and_a_citation_in_it_are_numbered_by_the_walk(self):
        from pyhermes.builder import Bibliography, Reference

        cited = FullWidth(
            content=TextBlock("<p>First.[^1]</p>", notes=["Block note."]),
            source="Source: BoE [@boe][^1]",
            source_notes=["Section note."],
        )
        refs = FullWidth(content=Bibliography([Reference("boe", ["Bank of England"], 2026, "R")]))
        document = email(cited, refs)
        text = document.text()
        assert "Source: BoE (Bank of England 2026)[2]" in text
        assert "[1] Block note." in text and "[2] Section note." in text
        assert 'href="#ref-boe"' in document.render()

    def test_an_unset_source_renders_nothing(self):
        bare = email(FullWidth(content=TextBlock("<p>x</p>"))).render()
        assert "section-source" not in bare

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"as_of": "1 Oct"}, "as_of date but no source"),
            ({"source": 3}, "source is plain text"),
            ({"source": "S[^1]"}, "no note|carries 0 note"),
            ({"source": "S", "source_notes": ["orphan"]}, "no marker"),
        ],
    )
    def test_a_refusal(self, kwargs, message):
        with pytest.raises(ValidationError, match=message):
            FullWidth(content=TextBlock("<p>x</p>"), **kwargs)

    def test_on_a_slide_it_is_kept_apart_from_the_slides_line(self):
        deck = Deck(PAPER, title_slide=EmptyTitleSlide(), closing_slide=EmptyClosingSlide())
        deck.add_slide(
            [FullWidth(content=TextBlock("<p>Body.</p>"), source="Source: section")],
            title="Slide",
            source="Source: slide",
        )
        html = deck.render()
        assert _source_lines(html) == ["Source: section"]
        assert "Source: slide" in html
        text = deck.text()
        assert text.index("Source: section") < text.index("Source: slide")

    def test_a_deck_refuses_a_note_in_one(self):
        deck = Deck(PAPER, title_slide=EmptyTitleSlide(), closing_slide=EmptyClosingSlide())
        section = FullWidth(content=TextBlock("<p>x</p>"), source="S[^1]", source_notes=["n"])
        with pytest.raises(ValidationError, match="cannot carry footnotes"):
            deck.add_slide([section], title="Slide")

    @requires_pdf
    @pytest.mark.parametrize("split", [False, True])
    def test_on_paper_it_never_opens_a_sheet_alone(self, split):
        """The lead-in grows until the sourced section crosses onto the next sheet."""
        landed = set()
        body = "".join(f"<p>Body {n}.</p>" for n in range(4))
        for lead in range(38, 50):
            content = (
                TwoColumn(left=TextBlock(body), right=TextBlock(body), source="Source: probe")
                if split
                else FullWidth(content=TextBlock(body), source="Source: probe")
            )
            lines = "".join(f"<p>Line {n}.</p>" for n in range(lead))
            sheets = _sheets(paper(FullWidth(TextBlock(lines)), content))
            [(at, sheet)] = [(i, t) for i, t in enumerate(sheets) if "Source: probe" in t]
            assert "Body 3." in sheet, f"the source line opened sheet {at + 1} at {lead} lines"
            landed.add(at)
        assert len(landed) > 1, "the sweep never moved the source line across a sheet"


# ----------------------------------------------------------------------
# #339 — the research note carries all three in both media
# ----------------------------------------------------------------------


class TestTheResearchNote:
    @pytest.mark.parametrize("build", [research_note.build, a4_research_note.build])
    def test_each_medium_anchors_every_panel(self, build):
        html = build().render()
        for anchor in PANELS:
            assert html.count(f'id="{anchor}"') == 1

    def test_both_media_number_the_grids_alike(self):
        def headings(text: str) -> list[str]:
            return [line for line in text.splitlines() if line in EXHIBITS]

        email_text, paper_text = research_note.build().text(), a4_research_note.build().text()
        assert headings(email_text)[-len(EXHIBITS) :] == EXHIBITS
        assert headings(paper_text)[-len(EXHIBITS) :] == EXHIBITS

    @requires_pdf
    def test_the_panel_cross_reference_reads_its_page(self):
        sheets = _sheets(a4_research_note.build())
        on = next(n for n, text in enumerate(sheets, 1) if "(b) Europe" in text)
        assert any(f"Exhibit 3(b) (p. {on})" in " ".join(text.split()) for text in sheets)
