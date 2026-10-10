"""
The second projection of the section tree (#109), epic #53's core.

The bar these tests hold: the text part is built from the same *structure*
``Email.assets()`` walks, never from the rendered HTML — and every component
has a projection, because one that does not would vanish from the text part
of every email that uses it without anything failing.
"""

from __future__ import annotations

import inspect

import pytest

import pyhermes.builder as builder
from pyhermes.builder import (
    AuthorBlock,
    Banner,
    CardGroup,
    ChartBlock,
    ContactBlock,
    DataTable,
    EmptyHeader,
    Footer,
    FullWidth,
    Header,
    ImageBlock,
    NumberedList,
    TextBlock,
    ThreeColumn,
    TwoColumn,
)
from pyhermes.builder.components import Component, descendants
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.models import Card, FooterLink, LinkRow, NumberedItem, TableRow
from qa.fixtures import DEPRECATED_COMPONENTS, all_fixtures, kitchen_sink


def _public_components() -> list[type[Component]]:
    return [
        obj
        for name in builder.__all__
        if isinstance(obj := getattr(builder, name), type)
        and issubclass(obj, Component)
        and obj is not Component
        and name not in DEPRECATED_COMPONENTS
    ]


def _components_in(email) -> list[Component]:
    """Every component, nested ones included (#261)."""
    return descendants([c for section in email._sections for c in section.components()])


class TestEveryComponentHasAProjection:
    """
    The `images()` rule with the opposite default: absent images are empty,
    an absent projection is an error.
    """

    def test_the_base_raises_naming_the_subclass(self):
        class Orphan(Component):
            template_path = "nowhere.html"

        with pytest.raises(NotImplementedError, match="Orphan"):
            Orphan().text()

    def test_the_message_says_what_would_break(self):
        """
        A `NotImplementedError` with no explanation sends the next
        contributor to read this module. The message names the consequence
        and where the format lives.
        """

        class Orphan(Component):
            pass

        with pytest.raises(NotImplementedError) as caught:
            Orphan().text()
        assert "plain-text part" in str(caught.value)
        assert "textgen" in str(caught.value)

    def test_every_public_component_projects_something(self):
        """
        Introspective, in the `kitchen_sink` pattern, and automatic: the
        fixture must contain every public component (a separate test enforces
        that), and `Email.text()` walks them all — so a new component with no
        projection fails here without anyone extending a list.
        """
        found = {type(c) for c in _components_in(kitchen_sink.build())}
        missing = [cls.__name__ for cls in _public_components() if cls not in found]
        assert not missing, f"not exercised by kitchen_sink: {missing}"

        for component in _components_in(kitchen_sink.build()):
            assert component.text().strip(), f"{type(component).__name__} projects nothing"


class TestTheSubtitleIsAComponentField:
    """
    `subtitle` belongs to the *component*, not the container: `FullWidth` and
    the splits take a `title` and nothing else. Nine of the ten public
    components carry one; `ContactBlock` is the exception.
    """

    def test_no_container_has_a_subtitle(self):
        for container in (FullWidth, TwoColumn, ThreeColumn):
            params = inspect.signature(container.__init__).parameters
            assert "subtitle" not in params, container.__name__
            assert "title" in params, container.__name__

    def test_every_projection_routes_through_the_shared_helper(self):
        """
        Mechanical rather than remembered. Asserting the *behaviour* per class
        would mean hand-constructing all nine, which is the hand-list the
        repo's introspective tests exist to avoid — so this asserts each
        projection composes `_with_subtitle` instead of spelling the
        standfirst itself, which is what a new component would forget.
        """
        for cls in _public_components():
            source = inspect.getsource(cls.text)
            assert "_with_subtitle" in source, f"{cls.__name__}.text() bypasses _with_subtitle"

    def test_the_subtitle_leads_the_projection(self):
        projected = CardGroup([Card("A", "1"), Card("B", "2")], subtitle="Standfirst").text()
        assert projected.startswith("Standfirst\n\n")

    def test_a_component_without_a_subtitle_field_still_projects(self):
        """`ContactBlock` has no such field; the helper reads it defensively."""
        assert "subtitle" not in inspect.signature(ContactBlock.__init__).parameters
        assert ContactBlock("Heading", cta_url="https://x.com").text()

    def test_every_fixture_subtitle_reaches_the_text(self):
        email = kitchen_sink.build()
        subtitles = [s for c in _components_in(email) if (s := getattr(c, "subtitle", None))]
        assert subtitles, "the fixture no longer exercises any subtitle"
        projected = email.text()
        for subtitle in subtitles:
            assert subtitle in projected


class TestPerComponentProjections:
    def test_a_card_is_label_value_and_sublabel(self):
        group = CardGroup([Card("S&P 500", "5,234", sublabel="+1.4%"), Card("VIX", "14.3")])
        assert group.text() == "S&P 500: 5,234 (+1.4%)\nVIX: 14.3"

    def test_a_card_body_goes_through_the_degrader(self):
        group = CardGroup(
            [Card("A", "1", body="<p>Prose <strong>here</strong>.</p>"), Card("B", "2")]
        )
        assert "Prose here." in group.text()

    def test_orientation_projects_to_nothing(self):
        """
        One card per line either way — the mobile collapse already made that
        the canonical linear order, so plain text inherits it.
        """
        cards = [Card("A", "1"), Card("B", "2")]
        assert CardGroup(cards, orientation="horizontal").text() == (
            CardGroup(cards, orientation="vertical").text()
        )

    def test_a_table_aligns_its_columns(self):
        table = DataTable(
            ["Factor", "1M"],
            [TableRow(["Value", "+1.8%"]), TableRow(["Momentum", "-11.2%"])],
        )
        lines = table.text().splitlines()
        assert lines[0] == "Factor        1M"
        assert lines[1] == "--------  ------"
        assert lines[2] == "Value      +1.8%"
        assert lines[3] == "Momentum  -11.2%"

    def test_the_first_column_is_left_and_the_rest_right(self):
        """
        Not a guess about the data: it is the convention the HTML template
        already encodes with `loop.first`, read off the same rule so the two
        projections cannot disagree about which column is the label.
        """
        table = DataTable(["A", "B"], [TableRow(["x", "1"]), TableRow(["longer", "22"])])
        header, rule, *rows = table.text().splitlines()
        assert header == "A        B"
        assert rule == "------  --"
        assert rows[0] == "x        1"
        assert rows[1] == "longer  22"

    def test_a_table_does_not_wrap_inside_a_cell(self):
        """
        A too-wide table overflows the line-width policy rather than
        corrupting the alignment that is the only reason to render it.
        """
        wide = "x" * 90
        table = DataTable(["Header", "Wide"], [TableRow(["a", wide])])
        assert wide in table.text()
        assert max(len(line) for line in table.text().splitlines()) > 78

    def test_a_url_is_never_split_across_lines(self):
        # #433: textwrap's defaults broke this one at a hyphen.
        url = "https://research.example.com/reports/2026/q3/factor-returns-and-the-small-cap.html"
        block = TextBlock(f"<p>The quarter's detail is in the full note: see {url} for it.</p>")
        assert url in block.text().splitlines()

    def test_a_wrapped_bullet_keeps_its_hanging_indent(self):
        from pyhermes.builder.textgen import wrap

        first, second = wrap("- " + "word " * 18).splitlines()
        assert first.startswith("- ") and second.startswith("  word")

    def test_a_table_carries_its_attribution(self):
        table = DataTable(["A"], [TableRow(["x"])], source="Bloomberg", as_of="24 Aug")
        assert table.text().endswith("Bloomberg\n24 Aug")

    def test_a_chart_projects_its_alt_text(self):
        chart = ChartBlock("https://x.com/c.png", alt_text="Factor returns", source="Research")
        assert chart.text() == "[Factor returns]\n\nResearch"

    def test_an_image_projects_alt_caption_and_link(self):
        block = ImageBlock(
            "https://x.com/i.png",
            alt_text="Thumbnail",
            caption="A caption",
            link_url="https://x.com/go",
        )
        assert block.text() == "[Thumbnail] (https://x.com/go)\n\nA caption"

    def test_alignment_projects_to_nothing(self):
        left = ImageBlock("https://x.com/i.png", alt_text="A", align="left")
        centre = ImageBlock("https://x.com/i.png", alt_text="A", align="center")
        assert left.text() == centre.text()

    def test_a_text_block_goes_through_the_degrader(self):
        assert TextBlock("<p>One</p><p>Two</p>").text() == "One\n\nTwo"

    def test_a_numbered_item_keeps_the_ordinal_the_caller_chose(self):
        """
        The ordinals are *data* on this component, which is exactly why #108
        can project an `ol` as plain bullets without losing anything.
        """
        listing = NumberedList([NumberedItem("07", "Positioning", "<p>Extended.</p>")])
        assert listing.text() == "07. Positioning\n\nExtended."

    def test_an_author_is_name_then_role_and_address(self):
        author = AuthorBlock("A. Analyst", "Head of Research", "research@example.com")
        assert author.text() == "A. Analyst\nHead of Research · research@example.com"

    def test_a_contact_block_ends_with_its_call_to_action(self):
        contact = ContactBlock("Talk to us", "Reach the desk.", "Email", "https://x.com/c")
        assert contact.text() == "Talk to us\n\nReach the desk.\n\nEmail: https://x.com/c"

    def test_a_contact_description_is_not_degraded(self):
        """
        Unlike the five blessed surfaces it is escaped into the template, so
        it is plain text already — degrading it would decode entities the
        caller wrote literally.
        """
        contact = ContactBlock("H", "Bass &amp; Co", cta_url="https://x.com")
        assert "Bass &amp; Co" in contact.text()


class TestContainers:
    def test_a_section_title_is_underlined(self):
        section = FullWidth(TextBlock("<p>Body</p>"), title="Overview")
        assert section.text() == "Overview\n--------\n\nBody"

    def test_an_untitled_section_is_just_its_component(self):
        assert FullWidth(TextBlock("<p>Body</p>")).text() == "Body"

    def test_columns_become_sequential_blocks(self):
        section = TwoColumn(left=TextBlock("<p>Left</p>"), right=TextBlock("<p>Right</p>"))
        assert section.text() == "Left\n\nRight"

    def test_a_half_filled_split_projects_only_what_is_there(self):
        assert TwoColumn(left=TextBlock("<p>Only</p>")).text() == "Only"

    def test_three_columns_run_left_to_right(self):
        section = ThreeColumn(
            left=TextBlock("<p>One</p>"),
            center=TextBlock("<p>Two</p>"),
            right=TextBlock("<p>Three</p>"),
        )
        assert section.text() == "One\n\nTwo\n\nThree"

    def test_presentation_projects_to_nothing(self):
        plain = FullWidth(TextBlock("<p>Body</p>"), title="T")
        dressed = FullWidth(
            TextBlock("<p>Body</p>"), title="T", background_color="#FF0000", highlight=True
        )
        assert plain.text() == dressed.text()

    def test_the_ratio_projects_to_nothing(self):
        left, right = TextBlock("<p>L</p>"), TextBlock("<p>R</p>")
        assert TwoColumn("50-50", left, right).text() == TwoColumn("70-30", left, right).text()


class TestRegionsProjectResolvedState:
    BANNER_FACTS = {
        "firm_name": "Example Capital",
        "campaign_name": "Weekly Wrap",
        "department": "Global Macro",
        "date_range": "25-29 Aug",
        "issue_label": "Issue 42",
    }
    FOOTER_FACTS = {
        "firm_name": "Example Capital",
        "current_year": "2026",
        "unsubscribe_url": "https://example.com/u",
        "view_in_browser_url": "https://example.com/v",
    }

    def test_the_banner_headline_comes_from_the_resolution_chain(self):
        """
        Reading `title` directly would work for every email that sets one and
        print nothing for every email that does not.
        """
        assert Banner().text(self.BANNER_FACTS).startswith("Example Capital\n===")
        assert Banner(title="Q3 Outlook").text(self.BANNER_FACTS).startswith("Q3 Outlook\n===")

    def test_the_banner_subtitle_falls_back_to_the_campaign(self):
        assert "Weekly Wrap" in Banner().text(self.BANNER_FACTS)
        assert "Own line" in Banner(subtitle="Own line").text(self.BANNER_FACTS)

    def test_the_banner_carries_its_metadata_line(self):
        assert "Global Macro · 25-29 Aug · Issue 42" in Banner().text(self.BANNER_FACTS)

    def test_an_absent_department_collapses_rather_than_blanking(self):
        facts = {**self.BANNER_FACTS, "department": ""}
        assert "25-29 Aug · Issue 42" in Banner().text(facts)
        assert " ·  · " not in Banner().text(facts)

    def test_the_logo_and_background_project_to_nothing(self):
        bare = Banner().text(self.BANNER_FACTS)
        dressed = Banner(
            logo_url="https://example.com/logo.png",
            logo_alt="A logo",
            background_image_url="https://example.com/hero.jpg",
        ).text(self.BANNER_FACTS)
        assert bare == dressed

    def test_the_strip_goes_through_the_degrader(self):
        facts = {"header_disclaimer": "<p>For <strong>professional</strong> clients.</p>"}
        assert Header().text(facts) == "For professional clients."

    def test_the_box_surface_projects_to_nothing(self):
        facts = {"header_disclaimer": "<p>Copy</p>"}
        assert Header().text(facts) == Header(
            align="left", background_color="#123456", text_color="#FFFFFF"
        ).text(facts)

    def test_a_variant_that_fills_no_slot_projects_nothing(self):
        """
        The same rule `render_slots` applies, read once for the whole region:
        `EmptyHeader` omits the strip from the HTML, and the text part agrees
        without anyone remembering to make it.
        """
        assert EmptyHeader().text({"header_disclaimer": "<p>Set, and still absent</p>"}) == ""

    def test_the_copyright_entity_becomes_the_character(self):
        """
        The inversion, end to end: `resolved_copyright_html` emits `&copy;`
        on purpose for the HTML part, and the text part degrades that same
        single source rather than branching.
        """
        assert "© 2026 Example Capital" in Footer().text(self.FOOTER_FACTS)
        assert "&copy;" not in Footer().text(self.FOOTER_FACTS)

    def test_a_caller_copyright_line_is_used_verbatim(self):
        footer = Footer(link_row=LinkRow(copyright="2026 Example — all rights reserved"))
        assert "2026 Example — all rights reserved" in footer.text(self.FOOTER_FACTS)

    def test_a_caller_line_round_trips_through_the_references(self):
        """
        The inversion above, for the branch #148 changed: the HTML part
        spells these as references and the text part degrades that same
        source back to the characters the caller wrote — which is the whole
        argument for escaping on the way out rather than asking callers to
        supply two spellings.
        """
        footer = Footer(link_row=LinkRow(copyright="© 2026 Zürich — Example"))
        assert "© 2026 Zürich — Example" in footer.text(self.FOOTER_FACTS)

    def test_the_default_links_carry_their_urls(self):
        projected = Footer().text(self.FOOTER_FACTS)
        assert "Unsubscribe: https://example.com/u" in projected
        assert "View in browser: https://example.com/v" in projected

    def test_a_default_link_with_no_url_is_left_out(self):
        """#258: an unset URL fact drops its default link from both parts."""
        projected = Footer().text({"firm_name": "F", "current_year": "2026"})
        assert "Unsubscribe" not in projected and "View in browser" not in projected

    def test_an_explicit_link_with_no_url_emits_its_label_alone(self):
        """
        pyHermes does not require an unsubscribe destination (#100), so a
        caller's link with none must not project a dangling colon.
        """
        footer = Footer(link_row=LinkRow(links=[FooterLink("Unsubscribe", "")]))
        projected = footer.text({"firm_name": "F", "current_year": "2026"})
        assert "Unsubscribe" in projected
        assert "Unsubscribe:" not in projected

    def test_the_footer_disclaimer_goes_through_the_degrader(self):
        footer = Footer(disclaimer="<p>Not <em>advice</em>.</p>")
        assert "Not advice." in footer.text(self.FOOTER_FACTS)

    def test_the_sign_off_image_projects_to_nothing(self):
        bare = Footer().text(self.FOOTER_FACTS)
        dressed = Footer(image="https://example.com/mark.png", image_alt="Mark").text(
            self.FOOTER_FACTS
        )
        assert bare == dressed


class TestEmailText:
    def test_the_order_is_the_skeletons(self):
        text = kitchen_sink.build().text()
        header = text.index("For illustrative purposes")
        banner = text.index("Q3 Outlook")
        section = text.index("Market Snapshot")
        footer = text.index("Privacy:")
        assert header < banner < section < footer

    @pytest.mark.parametrize("name", sorted(all_fixtures()))
    def test_every_fixture_projects_deterministically(self, name):
        build = all_fixtures()[name]
        assert build().text() == build().text()

    @pytest.mark.parametrize("name", sorted(all_fixtures()))
    def test_no_fixture_has_leading_or_trailing_whitespace(self, name):
        text = all_fixtures()[name]().text()
        assert text == text.strip()

    def test_the_widest_fixture_carries_its_content(self):
        email = kitchen_sink.build()
        text = email.text()

        assert email.banner.resolved_title(email.metadata.firm_name) in text
        assert email.metadata.department in text

        for section in email._sections:
            if section.title:
                assert section.title in text, section.title

        for component in _components_in(email):
            if isinstance(component, CardGroup):
                for card in component.cards:
                    assert card.label in text
            if isinstance(component, DataTable):
                for row in component.rows:
                    for cell in row.cells:
                        assert cell.text in text

    def test_every_content_url_the_html_carries_reaches_the_text(self):
        email = kitchen_sink.build()
        text = email.text()
        for link in email.footer.resolved_links(email.metadata.footer_facts()):
            if link.url:
                assert link.url in text, link.url
        for component in _components_in(email):
            if isinstance(component, ContactBlock):
                assert component.cta_url in text

    def test_no_header_carries_no_strip_content(self):
        email = all_fixtures()["no_header"]()
        assert email.metadata.header_disclaimer, "the fixture must set one to prove it is omitted"
        assert email.metadata.header_disclaimer not in email.text()

    def test_custom_footer_carries_its_own_wording_and_full_link_set(self):
        email = all_fixtures()["custom_footer"]()
        text = email.text()
        links = email.footer.resolved_links(email.metadata.footer_facts())
        assert len(links) != 2, "the fixture's point is a link set that is not the default pair"
        for link in links:
            assert link.label in text
            assert link.url in text

    def test_the_three_design_axes_do_not_reach_the_text(self):
        """
        Colour, density and typeface are HTML concerns by construction, so
        the same email projects identically under every one of them. That is
        what makes "one house format" possible rather than lucky.
        """
        fixtures = all_fixtures()
        baseline = fixtures["kitchen_sink"]().text()
        for name in ("compact_size", "spacious_size", "modern_fonts"):
            assert fixtures[name]().text() == baseline, name


class TestTheTextPathNeverRenders:
    def test_no_template_is_loaded_anywhere_in_the_projection(self, monkeypatch):
        """
        The epic's central claim, asserted rather than trusted: the text part
        is a second projection of the tree, never a degradation of the first.
        Stripping rendered HTML is exactly what would turn a KPI strip and a
        data table into garbage.
        """

        def explode(*args, **kwargs):
            raise AssertionError("the text path rendered HTML")

        monkeypatch.setattr(TemplateEngine, "render", explode)
        for name, build in all_fixtures().items():
            assert build().text(), name


class TestThereIsNoOverride:
    def test_no_public_class_takes_a_text_override(self):
        """
        Epic #53's principle 2: derived text cannot drift from the HTML
        content, so there is no hand-authored escape hatch to drift with.
        """
        for name in builder.__all__:
            obj = getattr(builder, name)
            if not isinstance(obj, type):
                continue
            params = inspect.signature(obj.__init__).parameters
            offenders = [p for p in params if "text_override" in p]
            assert not offenders, f"{name} takes {offenders}"
