"""
The deck medium (#218): slides, dividers, the title and closing slides, and notes.

What the markup and the projections can answer. Where each slide lands, and
whether it overflows, needs the print engine and lives in ``test_deck_pdf.py``.
"""

from __future__ import annotations

import dataclasses

import pytest

from pyhermes.builder import (
    Contents,
    DataTable,
    Email,
    FullWidth,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.exceptions import ValidationError
from pyhermes.deck import (
    DECK_MEDIUM,
    SLIDE_4_3,
    SLIDE_16_9,
    ClosingSlide,
    Deck,
    DividerSlide,
    EmptyClosingSlide,
    EmptyTitleSlide,
    Slide,
    TitleSlide,
    deck_medium,
)
from pyhermes.deck.document import CLOSING_FACTS, TITLE_FACTS
from pyhermes.document import Page, PagedDocument
from qa.fixtures import all_deck_fixtures, pitch_16_9
from qa.goldens import artifacts, check_fixture
from qa.lint import errors, lint_html, rules_for

FACTS = {
    "firm_name": "Hermes Research",
    "campaign_name": "Quarterly Review",
    "header_disclaimer": "<p>Not investment advice.</p>",
}

DECK_NAMES = sorted(all_deck_fixtures())


def _sections(marker: str = "Body copy") -> list:
    return [FullWidth(content=TextBlock(f"<p>{marker}.</p>"))]


def _bare(*, page=SLIDE_16_9) -> Deck:
    """A deck with neither the title slide nor the disclosures, so sheets are slides."""
    return Deck(FACTS, page=page, title_slide=EmptyTitleSlide(), closing_slide=EmptyClosingSlide())


# ----------------------------------------------------------------------
# #296 — the medium, the slide and the deck
# ----------------------------------------------------------------------


class TestTheMedium:
    def test_it_is_paged_and_names_its_own_regions(self):
        assert DECK_MEDIUM.name == "deck"
        assert DECK_MEDIUM.paged and not DECK_MEDIUM.email
        assert DECK_MEDIUM.slots == ("title_slide", "closing_slide")
        assert DECK_MEDIUM.page_format is SLIDE_16_9

    def test_the_4_3_page_sits_beside_the_16_9(self):
        assert (SLIDE_4_3.width, SLIDE_4_3.height) == (1024, 768)
        assert deck_medium(SLIDE_4_3).page_format is SLIDE_4_3
        assert Deck(FACTS, page=SLIDE_4_3).medium.page_format is SLIDE_4_3

    def test_the_skeleton_is_the_decks_own(self):
        html = _bare().add_slide(_sections(), "One").render()
        assert 'class="sheet slide"' in html
        assert "@page {\n      size: 1280px 720px;\n      margin: 0;" in html

    def test_a_continuous_page_is_refused(self):
        from pyhermes.builder.sizing import DEFAULT_PAGE

        with pytest.raises(ValidationError, match="fixed sheet"):
            Deck(FACTS, page=DEFAULT_PAGE)


class TestASlide:
    def test_it_holds_containers_only(self):
        with pytest.raises(ValidationError, match="holds containers"):
            Slide([TextBlock("<p>x</p>")])  # type: ignore[list-item]

    def test_it_needs_a_section(self):
        with pytest.raises(ValidationError, match="at least one section"):
            Slide([])

    def test_it_may_not_hold_a_boundary(self):
        with pytest.raises(ValidationError, match="may not contain a page"):
            Slide([Page(_sections())])
        with pytest.raises(ValidationError, match="may not contain a slide"):
            Slide([Slide(_sections())])

    def test_its_notes_are_plain_text(self):
        with pytest.raises(ValidationError, match="plain text"):
            Slide(_sections(), notes=3)  # type: ignore[arg-type]

    def test_it_flattens_in_an_email_byte_for_byte(self):
        bare = Email({**FACTS, "email_subject": "S"})
        for section in _sections():
            bare.add_section(section)
        slid = Email({**FACTS, "email_subject": "S"})
        slid.add_section(Slide(_sections(), title="Never printed", notes="Never printed either"))
        assert slid.render() == bare.render()

    def test_it_flattens_in_a_paged_document_byte_for_byte(self):
        bare = PagedDocument(FACTS)
        for section in _sections():
            bare.add_section(section)
        slid = PagedDocument(FACTS)
        slid.add_section(Slide(_sections(), title="Never printed"))
        assert slid.render() == bare.render()

    def test_a_divider_flattens_to_nothing_and_projects_its_title(self):
        email = Email({**FACTS, "email_subject": "S"})
        email.add_section(DividerSlide("Part one"))
        assert "Part one" not in email.render().split("<body")[1]
        assert "Part one\n--------" in email.text()


class TestTheDeck:
    def test_a_bare_section_is_refused_naming_add_slide(self):
        with pytest.raises(ValidationError, match="add_slide"):
            _bare().add_section(FullWidth(content=TextBlock("<p>x</p>")))

    def test_each_slide_is_one_sheet_with_its_title_and_number(self):
        deck = _bare()
        for title in ("Alpha", "Beta", "Gamma"):
            deck.add_slide(_sections(), title)
        html = deck.render()
        assert html.count('class="sheet slide"') == 3
        for number, title in enumerate(("Alpha", "Beta", "Gamma"), start=1):
            sheet = html.split(f'data-slide="{number}"')[1].split('class="sheet')[0]
            assert (
                f'>{title}<span class="slide-title-end" id="slide-{number}-title-end"></span></h2>'
                in sheet
            )
            assert f'<span class="slide-number" style="float:right;">{number}</span>' in sheet

    def test_the_title_slide_is_sheet_one(self):
        deck = Deck(FACTS).add_slide(_sections(), "First")
        assert deck.number(deck.slides[0]) == 2
        bare = _bare().add_slide(_sections(), "First")
        assert bare.number(bare.slides[0]) == 1

    def test_a_slide_not_in_the_deck_has_no_number(self):
        with pytest.raises(ValidationError, match="not in this deck"):
            _bare().number(Slide(_sections()))

    def test_add_slide_takes_a_slide_or_its_arguments_not_both(self):
        with pytest.raises(ValidationError, match="not both"):
            _bare().add_slide(Slide(_sections()), title="Twice")

    def test_a_footnote_is_refused_and_the_deck_left_as_it_was(self):
        deck = _bare()
        with pytest.raises(ValidationError, match="footnotes"):
            deck.add_slide(
                [FullWidth(content=TextBlock("<p>Noted.[^1]</p>", notes=["A note."]))], "Noted"
            )
        assert deck.slides == []

    def test_a_slide_claims_the_anchor_its_title_band_prints(self):
        html = _bare().add_slide(_sections(), "Where rates stand").render()
        assert 'id="where-rates-stand"' in html

    def test_two_slides_with_one_title_are_refused(self):
        deck = _bare().add_slide(_sections(), "Twice")
        with pytest.raises(ValidationError, match="Twice"):
            deck.add_slide(_sections(), "Twice")

    def test_the_text_part_underlines_each_slides_title(self):
        text = _bare().add_slide(_sections("Body copy"), "Alpha").text()
        assert "Alpha\n-----\n\n" in text
        assert text.index("Alpha") < text.index("Body copy")


class TestTheDensityIsTheDecks:
    def test_a_mapping_defaults_to_presentation(self):
        assert Deck(FACTS).metadata.size_theme == "presentation"

    def test_presentation_is_refused_everywhere_else(self):
        for build in (
            lambda: Email({**FACTS, "email_subject": "S", "size_theme": "presentation"}),
            lambda: PagedDocument({**FACTS, "size_theme": "presentation"}),
        ):
            with pytest.raises(ValidationError, match="deck medium alone"):
                build()

    def test_the_email_switch_does_not_admit_it(self):
        from pyhermes.config import Config, config_override

        with config_override(Config(allow_custom_email_density=True)):
            with pytest.raises(ValidationError, match="deck medium alone"):
                Email({**FACTS, "email_subject": "S", "size_theme": "presentation"})

    def test_a_deck_takes_any_other_density(self):
        assert Deck({**FACTS, "size_theme": "spacious"}).metadata.size_theme == "spacious"

    def test_its_type_is_larger_than_spacious_everywhere_a_reader_reads(self):
        from pyhermes.builder.sizing import PRESENTATION_SIZES, SPACIOUS_SIZES

        for token in ("title", "section", "body", "secondary", "small", "label", "micro"):
            assert getattr(PRESENTATION_SIZES.type, token) > getattr(SPACIOUS_SIZES.type, token)
        assert PRESENTATION_SIZES.component.kpi_value > SPACIOUS_SIZES.component.kpi_value


# ----------------------------------------------------------------------
# #298 — the title slide, dividers and the disclosures
# ----------------------------------------------------------------------


class TestTheOpeningAndClosingSlides:
    def test_the_deck_opens_on_the_title_and_closes_on_the_disclosures(self):
        html = Deck(FACTS).add_slide(_sections(), "Middle").render()
        body = html.split("<body>")[1]
        assert body.index("title-slide") < body.index("Middle") < body.index("closing-slide")
        assert "Not investment advice." in body.split("closing-slide")[1]

    @pytest.mark.parametrize(
        ("region", "facts"), [(TitleSlide, TITLE_FACTS), (ClosingSlide, CLOSING_FACTS)]
    )
    def test_each_regions_keys_and_its_facts_are_disjoint(self, region, facts):
        presentation = {field.name for field in dataclasses.fields(region)}
        assert not presentation & set(facts)

    def test_the_title_slide_resolves_to_the_facts(self):
        slide = TitleSlide()
        assert slide.resolved_title("Quarterly Review") == "Quarterly Review"
        assert slide.resolved_subtitle("Hermes Research") == "Hermes Research"
        assert TitleSlide(title="Own").resolved_title("Quarterly Review") == "Own"

    def test_the_title_slide_reads_the_resolved_keys_never_the_facts(self):
        from pathlib import Path

        import pyhermes.builder

        template = (
            Path(pyhermes.builder.__file__).parent / "templates/deck/regions/title-slide.html"
        ).read_text(encoding="utf-8")
        assert "{{ campaign_name" not in template and "{{ firm_name" not in template

    def test_the_title_slide_projects_through_its_text(self):
        text = Deck({**FACTS, "department": "Rates", "date_range": "Q3"}).text()
        assert text.startswith("Quarterly Review\n================\n\nHermes Research\nRates · Q3")

    def test_the_empty_variants_fill_no_slot(self):
        deck = _bare().add_slide(_sections(), "Only")
        assert "title-slide" not in deck.render() and "closing-slide" not in deck.render()
        assert "Disclosures" not in deck.text()

    def test_a_divider_is_set_on_the_dark_ground(self):
        from pyhermes.builder.theming import DEFAULT_THEME

        html = _bare().add_divider("Part one", "Why it matters").render()
        divider = html.split('class="sheet slide divider"')[1]
        assert DEFAULT_THEME.palette.header_bg in divider.split(">")[0]
        assert ">Part one</h2>" in divider and "Why it matters" in divider

    def test_the_slides_after_a_divider_follow_it_in_the_footer(self):
        deck = _bare().add_slide(_sections(), "Before")
        deck.add_divider("Part one").add_slide(_sections(), "After")
        html = deck.render()
        before = html.split('data-slide="1"')[1].split('data-slide="2"')[0]
        after = html.split('data-slide="3"')[1]
        assert "Hermes Research</span>" in before and "Part one" not in before
        assert "Hermes Research · Part one</span>" in after

    def test_a_divider_needs_a_title(self):
        with pytest.raises(ValidationError, match="needs a title"):
            DividerSlide("  ")

    def test_a_contents_on_slide_two_lists_every_titled_slide_and_divider(self):
        deck = Deck(FACTS).add_slide([FullWidth(content=Contents())], "Agenda")
        deck.add_divider("Part one").add_slide(_sections(), "Alpha")
        deck.add_slide(_sections()).add_slide(_sections(), "Beta")
        contents = deck.slides[0].sections[0].content
        assert [title for title, _ in contents.entries] == ["Part one", "Alpha", "Beta"]
        assert [anchor for _, anchor in contents.entries] == ["part-one", "alpha", "beta"]


# ----------------------------------------------------------------------
# #299 — speaker notes
# ----------------------------------------------------------------------


class TestSpeakerNotes:
    def test_notes_come_one_block_a_slide_under_its_number_and_title(self):
        deck = Deck(FACTS).add_slide(_sections(), "Alpha", notes="Open slowly.")
        deck.add_slide(_sections(), "Beta").add_slide(_sections(), notes="Untitled, noted.")
        assert deck.notes() == (
            "Slide 2: Alpha\n--------------\n\nOpen slowly.\n\n\n"
            "Slide 4\n-------\n\nUntitled, noted."
        )

    def test_a_deck_without_notes_has_none(self):
        assert _bare().add_slide(_sections(), "Alpha").notes() == ""

    def test_notes_reach_neither_the_markup_nor_the_text(self):
        deck = pitch_16_9.build()
        assert "ZEBRANOTES7" in deck.notes()
        assert "ZEBRANOTES7" not in deck.render()
        assert "ZEBRANOTES7" not in deck.text()

    def test_the_numbering_matches_the_sheet(self):
        deck = pitch_16_9.build()
        chart = next(slide for slide in deck.slides if slide.notes == pitch_16_9.CHART_NOTES)
        number = deck.number(chart)
        assert f"Slide {number}: The term premium" in deck.notes()
        assert f'data-slide="{number}"' in deck.render().split("The term premium</h2>")[0]


# ----------------------------------------------------------------------
# #297 and #301 — the rule table, and the gallery
# ----------------------------------------------------------------------


class TestTheRuleTable:
    def test_the_deck_is_judged_as_a_page_with_its_own_overflow_rule(self):
        assert rules_for("deck") == {
            "img-alt",
            "table-role",
            "table-header-tier",
            "empty-url",
            "no-external-css",
            "page-size-declared",
            "paged-table-width",
            "table-structure",
            "slide-overflow",
        }

    def test_the_overflow_rule_reaches_no_other_medium(self):
        for medium in ("email", "document", "brochure", "html"):
            assert "slide-overflow" not in rules_for(medium)

    def test_without_the_backend_the_check_says_it_could_not_measure(self, monkeypatch):
        import pyhermes.pdf.exporter as exporter
        from pyhermes.check import layout_findings
        from pyhermes.pdf import BackendMissingError

        def missing():
            raise BackendMissingError("no backend")

        monkeypatch.setattr(exporter, "_backend", missing)
        findings = layout_findings(_bare().add_slide(_sections(), "One"))
        assert [(f.rule_id, f.severity.value) for f in findings] == [("slide-overflow", "warning")]
        assert "not measured" in findings[0].message

    def test_the_markup_rules_pass_the_deck(self):
        deck = pitch_16_9.build()
        assert errors(lint_html(deck.render(), "deck")) == []


@pytest.fixture(params=DECK_NAMES)
def deck_name(request: pytest.FixtureRequest) -> str:
    return str(request.param)


class TestEveryDeckFixtureMatchesItsGolden:
    def test_every_artifact_is_unchanged(self, deck_name, request):
        document = all_deck_fixtures()[deck_name]()
        if request.config.getoption("--update-goldens"):
            from qa.goldens import write_fixture

            written = write_fixture(deck_name, document)
            pytest.skip(f"regenerated {', '.join(p.name for p in written)}")
        mismatches = check_fixture(deck_name, document)
        assert not mismatches, "\n\n".join(str(m) for m in mismatches)

    def test_every_golden_is_checked_in_including_the_notes(self, deck_name):
        document = all_deck_fixtures()[deck_name]()
        pinned = artifacts(deck_name, document)
        assert [label for label, _, _ in pinned][-1] == "speaker notes"
        for _, path, _ in pinned:
            assert path.is_file(), f"{path} is missing; run `pytest --update-goldens`."
            assert path.parent.name == "deck"


class TestEveryDeckFieldIsExercised:
    """Standing rule 9, for the deck's two containers and two regions."""

    def test_each_slide_field_is_set_away_from_its_default_somewhere(self):
        slides = pitch_16_9.build().slides
        for name in ("title", "notes", "background_color", "align", "anchor"):
            assert any(getattr(slide, name) for slide in slides), name
        assert any(getattr(slide, "subtitle", "") for slide in slides)
        # valign is never falsy, so each kind's default is named (#355).
        assert any(type(s) is Slide and s.valign != "top" for s in slides)
        assert any(isinstance(s, DividerSlide) and s.valign != "bottom" for s in slides)

    @pytest.mark.parametrize("region", ["title_slide", "closing_slide"])
    def test_each_region_field_differs_from_its_default(self, region):
        built = getattr(pitch_16_9.build(), region)
        default = type(built)()
        for field in dataclasses.fields(built):
            assert getattr(built, field.name) != getattr(default, field.name), field.name

    def test_the_fixture_holds_every_kind_of_slide_the_issue_names(self):
        deck = pitch_16_9.build()
        dividers = [slide for slide in deck.slides if isinstance(slide, DividerSlide)]
        assert len(dividers) == 2
        kinds = {type(c).__name__ for slide in deck.slides for c in slide.components()}
        assert {"CardGroup", "DataTable", "ChartBlock", "Contents"} <= kinds
        assert any(isinstance(s, TwoColumn) for slide in deck.slides for s in slide.sections)
        assert isinstance(deck.slides[0].sections[0].content, Contents)
        assert any(isinstance(c, DataTable) for c in deck.slides[3].components())
