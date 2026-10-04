"""
``Page`` and the paged medium's regions (#163).

The managed elements an email never had. What each test here holds is the
thing a golden cannot see: that a page break *flattens* where pages do not
exist, that a region cannot shadow a fact, that CSS is escaped as CSS, and
that a projection left empty was a decision rather than an omission.
"""

from __future__ import annotations

import dataclasses

import pytest

from pyhermes.builder import Email, FullWidth, TextBlock
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import EmailImage
from pyhermes.builder.medium import DEFAULT_MEDIUM
from pyhermes.document import (
    BackMatter,
    ContentsPage,
    Cover,
    EmptyBackMatter,
    EmptyCover,
    EmptyRunningFooter,
    EmptyRunningHeader,
    ExhibitsPage,
    Page,
    PagedDocument,
    RunningFooter,
    RunningHeader,
)
from pyhermes.document.document import BACK_MATTER_FACTS, COVER_FACTS, RUNNING_FACTS
from pyhermes.document.medium import PAGED_MEDIUM
from pyhermes.document.regions import MARGIN_BOXES
from qa.fixtures import _paged, all_paged_fixtures

TEMPLATE_DIR = TemplateEngine().template_dir
DOCUMENT_REGIONS = (Cover, ContentsPage, ExhibitsPage, RunningHeader, RunningFooter, BackMatter)


def section(body: str = "<p>Body.</p>", title: str | None = None) -> FullWidth:
    return FullWidth(content=TextBlock(body), title=title)


class TestAPageFlattensWherePagesDoNotExist:
    """
    #157's decision, made mechanical: one tree, two outputs.

    The break is decided in Python rather than left to CSS. ``break-before``
    is inert in a mail client, so emitting it would *look* harmless — but the
    wrapper element around it is not, and an email would carry markup that
    exists for a medium it is not being read in.
    """

    @pytest.fixture()
    def engine(self) -> TemplateEngine:
        return TemplateEngine(search_path=PAGED_MEDIUM.template_search_path)

    def test_it_renders_exactly_its_sections_in_a_non_paged_medium(self, engine):
        inner = [section("<p>One.</p>", "First"), section("<p>Two.</p>", "Second")]
        bound = engine.bound(medium=DEFAULT_MEDIUM)
        flattened = Page(inner).render(bound)
        bare = "\n".join(s.render(bound) for s in inner)
        assert flattened == bare, "flattening must be byte-exact, not merely similar"

    def test_it_carries_both_break_spellings_in_a_paged_medium(self, engine):
        html = Page([section()], break_before=True, break_after=True).render(
            engine.bound(medium=PAGED_MEDIUM)
        )
        for declaration in (
            "break-before:page",
            "page-break-before:always",
            "break-after:page",
            "page-break-after:always",
        ):
            assert declaration in html

    def test_a_page_asking_for_no_break_emits_no_style(self, engine):
        html = Page([section()], break_before=False, break_after=False).render(
            engine.bound(medium=PAGED_MEDIUM)
        )
        assert "break-before" not in html and "break-after" not in html

    def test_a_page_opening_the_body_drops_only_its_leading_break(self):
        # The body starts a sheet already. The second page keeps its break,
        # the first keeps its trailing one, and the caller's page is untouched.
        first = Page([section()], break_after=True)
        document = PagedDocument(_paged.facts(), cover=EmptyCover(), back_matter=EmptyBackMatter())
        html = document.add_section(first).add_section(Page([section()])).render()
        assert html.count("break-before:page") == 1
        assert "break-after:page" in html
        assert first.break_before is True

    def test_add_page_is_add_section_of_a_page(self):
        # Every argument at a non-default value, so none can be dropped quietly.
        options = {
            "break_before": False,
            "break_after": True,
            "title": "Appendix",
            "background_color": "#F4F1EA",
            "align": "center",
        }

        def build() -> PagedDocument:
            return PagedDocument(_paged.facts(), cover=EmptyCover()).add_section(section())

        shortcut = build().add_page([section("<p>Two.</p>")], **options)
        spelled = build().add_section(Page([section("<p>Two.</p>")], **options))
        assert shortcut.render() == spelled.render()
        assert shortcut.text() == spelled.text()

    def test_add_page_chains(self):
        document = PagedDocument(_paged.facts())
        assert document.add_page([section()]) is document

    def test_only_the_paged_medium_offers_add_page(self):
        # An email has no sheets; its callers put a Page in the tree, which flattens.
        assert not hasattr(Email, "add_page")

    def test_its_wrapper_declares_itself_a_layout_table(self, engine):
        # Standing rule 8, on the one template this phase adds to the body.
        html = Page([section()]).render(engine.bound(medium=PAGED_MEDIUM))
        assert '<table role="presentation"' in html

    def test_a_page_in_an_email_moves_no_golden(self, valid_metadata):
        # Exercised by a test rather than a fixture, deliberately: putting a
        # Page in kitchen_sink would move an email golden, and phases 1-5
        # spent their whole budget proving none of them moves.
        plain = Email(valid_metadata)
        plain.add_section(section("<p>Only section.</p>", "Title"))
        paged_tree = Email(valid_metadata)
        paged_tree.add_section(Page([section("<p>Only section.</p>", "Title")]))
        assert paged_tree.render() == plain.render()


class TestAPageRefusesWhatItCannotMean:
    def test_a_page_may_not_hold_a_page(self):
        with pytest.raises(ValidationError, match="may not contain a page"):
            Page([Page([section()])])

    def test_a_page_needs_a_section(self):
        with pytest.raises(ValidationError, match="at least one section"):
            Page([])

    def test_a_page_holds_containers_not_components(self):
        with pytest.raises(ValidationError, match="holds containers"):
            Page([TextBlock("<p>Not a container.</p>")])  # type: ignore[list-item]


class TestAPageProjectsAndWalksItsSections:
    def test_text_is_the_title_then_the_sections(self):
        page = Page([section("<p>Alpha.</p>"), section("<p>Beta.</p>")], title="Appendix")
        text = page.text()
        assert "Appendix" in text and "Alpha." in text and "Beta." in text

    def test_a_break_projects_to_nothing(self):
        # Plain text has no sheets -- the same reason the email medium flattens.
        with_break = Page([section()], break_before=True, break_after=True).text()
        without = Page([section()], break_before=False, break_after=False).text()
        assert with_break == without

    def test_it_walks_its_sections_for_components_images_and_assets(self, png_bytes):
        from pyhermes.builder import ChartBlock

        chart = ChartBlock(EmailImage.attached(png_bytes, alt="Chart", width=100))
        page = Page([FullWidth(content=chart)])
        assert len(page.components()) == 1
        assert len(page.images()) == 1
        assert len(page.assets()) == 1

    def test_a_documents_manifest_reaches_through_a_page(self, png_bytes):
        from pyhermes.builder import ChartBlock

        document = PagedDocument(_paged.facts(), cover=EmptyCover())
        document.add_section(
            Page([FullWidth(content=ChartBlock(EmailImage.attached(png_bytes, alt="C", width=90)))])
        )
        assert len(document.assets()) == 1


class TestTheCoverPresentsFactsItCannotOwn:
    def test_its_keys_and_its_facts_are_disjoint(self):
        presentation = {f.name for f in dataclasses.fields(Cover)}
        assert not (presentation & set(COVER_FACTS)), (
            "a region field sharing a fact's name could shadow it"
        )

    def test_an_unset_headline_resolves_to_the_facts(self):
        cover = Cover()
        assert cover.resolved_title("Hermes Research") == "Hermes Research"
        assert cover.resolved_subtitle("Quarterly Review") == "Quarterly Review"

    def test_its_own_copy_wins(self):
        cover = Cover(title="Q3 Outlook", subtitle="What the curve is pricing")
        assert cover.resolved_title("Hermes Research") == "Q3 Outlook"

    def test_the_template_reads_the_resolved_keys_never_the_facts(self):
        # The grep test #91 introduced, ported. Reading {{ firm_name }} again
        # would render correctly for every document that sets no title, and
        # make the field unreachable with nothing failing.
        source = (TEMPLATE_DIR / "document" / "regions" / "cover.html").read_text(encoding="utf-8")
        assert "cover_title" in source and "cover_subtitle" in source
        assert "{{ firm_name" not in source and "{{ campaign_name" not in source

    def test_it_declares_its_images(self):
        # Standing rule 7: undeclared bytes never reach assets().
        cover = Cover(
            logo_url=EmailImage.hosted("https://cdn.example.com/m.png", alt="M", width=40)
        )
        assert len(cover.images()) == 1

    def test_an_empty_cover_fills_no_slot_and_projects_nothing(self):
        assert EmptyCover().TEMPLATE_PATHS == {}
        assert EmptyCover().text({"firm_name": "Hermes"}) == ""

    def test_it_projects_the_resolved_headline(self):
        # Standing rule 10, read off the chain rather than the field.
        text = Cover().text({"firm_name": "Hermes Research", "campaign_name": "Review"})
        assert "Hermes Research" in text


class TestTheRunningBoxesAreCssNotMarkup:
    def test_a_style_close_in_a_fact_cannot_break_out_of_the_stylesheet(self):
        # The trap css_string exists for. An HTML-escaped entity would render
        # literally inside a stylesheet, and neither filter's absence would
        # stop this closing the block early.
        facts = {**_paged.facts(), "firm_name": "Bad</style><script>x</script> Co"}
        document = PagedDocument(facts, cover=EmptyCover(), back_matter=EmptyBackMatter())
        html = document.render()
        assert "</style><script>" not in html
        assert "\\3C /style>" in html

    def test_the_box_must_be_one_css_defines(self):
        with pytest.raises(ValidationError, match="must be one of"):
            RunningHeader(box="middle-left")

    @pytest.mark.parametrize("box", MARGIN_BOXES)
    def test_every_named_box_is_accepted(self, box):
        assert RunningHeader(box=box).resolved_box() == box

    def test_each_box_falls_back_to_its_own_fact(self):
        # The header names the series, the footer the firm -- different
        # defaults because they answer different questions on the page.
        assert RunningHeader.LABEL_FACT == "campaign_name"
        assert RunningFooter.LABEL_FACT == "firm_name"
        assert RunningHeader().resolved_label("Quarterly Review") == "Quarterly Review"

    def test_the_folio_appears_only_when_asked_for(self):
        engine = TemplateEngine(search_path=PAGED_MEDIUM.template_search_path).bound(
            medium=PAGED_MEDIUM
        )
        facts = {name: "x" for name in RUNNING_FACTS}
        with_folio = RunningFooter(show_page_number=True).render_slots(engine, facts)
        without = RunningFooter(show_page_number=False).render_slots(engine, facts)
        assert "counter(page)" in with_folio["running_footer_html"]
        assert "counter(page)" not in without["running_footer_html"]

    def test_their_projection_is_empty_by_decision(self):
        # Implemented rather than left to raise: a running box is chrome, and
        # a page number counts sheets plain text does not have.
        assert RunningHeader().text({"campaign_name": "Review"}) == ""
        assert RunningFooter().text({"firm_name": "Hermes"}) == ""

    def test_an_empty_running_box_fills_no_slot(self):
        assert EmptyRunningHeader().TEMPLATE_PATHS == {}
        assert EmptyRunningFooter().TEMPLATE_PATHS == {}


class TestTheBackMatterRendersAFactItDoesNotOwn:
    def test_the_disclosure_copy_is_a_fact(self):
        # The blessed raw-HTML set stays closed at five: this gives an
        # existing surface a second place to render, it does not mint a sixth.
        assert BACK_MATTER_FACTS == ("header_disclaimer",)
        assert "header_disclaimer" not in {f.name for f in dataclasses.fields(BackMatter)}

    def test_raw_html_is_emitted_in_a_div_never_a_p(self):
        source = (TEMPLATE_DIR / "document" / "regions" / "back-matter.html").read_text(
            encoding="utf-8"
        )
        assert "<div" in source
        assert "<p" not in source.split("header_disclaimer")[0].split("<div")[-1]

    def test_it_degrades_the_html_for_the_text_part(self):
        text = BackMatter().text(
            {"header_disclaimer": "<p>Past performance <b>is not</b> a guide.</p>"}
        )
        assert "Past performance is not a guide." in text
        assert "<p>" not in text

    def test_its_alignment_is_validated(self):
        with pytest.raises(ValidationError, match="back_matter.align"):
            BackMatter(align="sideways")

    def test_an_empty_back_matter_fills_no_slot(self):
        assert EmptyBackMatter().TEMPLATE_PATHS == {}


class TestTheDocumentRegionsAreComplete:
    """
    Standing rules 1, 9 and 10, over the regions this phase adds.

    Introspective rather than hand-listed, so a field added later is covered
    the day it is added rather than the day somebody remembers this test.
    """

    @pytest.mark.parametrize("region_cls", DOCUMENT_REGIONS)
    def test_every_field_is_exercised_at_a_non_default_value(self, region_cls):
        # Across the paged gallery, as standing rule 9 words it: a field on a
        # base both margin boxes share cannot be non-default on both at once
        # in one document without the two saying the same thing (#185).
        attributes = {
            "Cover": ("cover",),
            # An exhibits sheet is a contents sheet in a slot of its own (#308),
            # so it exercises the listing fields the two share.
            "ContentsPage": ("contents", "exhibits"),
            "ExhibitsPage": ("exhibits",),
            "RunningHeader": ("running_header",),
            "RunningFooter": ("running_footer",),
            "BackMatter": ("back_matter",),
        }[region_cls.__name__]
        documents = [build() for build in all_paged_fixtures().values()]
        built = [getattr(d, attribute) for d in documents for attribute in attributes]
        default = region_cls()
        # A field with one legal value on this class has no other value to set.
        fixed = {"ExhibitsPage": {"of"}}.get(region_cls.__name__, set())
        for field in dataclasses.fields(region_cls):
            if field.name in fixed:
                continue
            assert any(getattr(b, field.name) != getattr(default, field.name) for b in built), (
                f"{region_cls.__name__}.{field.name} is never set to anything but its "
                "default in the paged gallery, so no golden can pin it"
            )

    @pytest.mark.parametrize("region_cls", DOCUMENT_REGIONS)
    def test_every_region_projects_text(self, region_cls):
        # Rule 10: absence must fail loudly, not vanish from the text part.
        facts = {name: "x" for name in COVER_FACTS + RUNNING_FACTS + BACK_MATTER_FACTS}
        region_cls().text(facts)  # must not raise NotImplementedError

    @pytest.mark.parametrize("region_cls", DOCUMENT_REGIONS)
    def test_every_region_fills_the_slot_it_declares(self, region_cls):
        assert set(region_cls.TEMPLATE_PATHS) == set(region_cls.SLOTS)

    def test_the_medium_claims_exactly_these_regions(self):
        assert PAGED_MEDIUM.region_types == DOCUMENT_REGIONS

    def test_the_skeleton_names_every_slot_the_regions_fill(self):
        skeleton = (TEMPLATE_DIR / "document" / "base.html").read_text(encoding="utf-8")
        for slot in PAGED_MEDIUM.slots:
            assert f"{{{{ {slot}_html }}}}" in skeleton
