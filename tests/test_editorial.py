"""
The editorial primitives (#189), and the degradation each states for email.

Each primitive renders on paper and degrades in an email, and each email
degradation is a test here rather than a golden someone has to read.
"""

from __future__ import annotations

import pytest

from qa.fixtures import all_brochure_fixtures, all_fixtures, all_paged_fixtures
from svc.builder import EmailBuilder, FlowedColumns, FullWidth, PullQuote, TextBlock
from svc.builder.components import _with_drop_cap
from svc.builder.exceptions import ValidationError
from svc.document import PagedDocument

FACTS = {"firm_name": "Hermes", "campaign_name": "Editorial", "email_subject": "S"}


def email_of(*sections):
    builder = EmailBuilder().metadata(FACTS)
    for section in sections:
        builder = builder.section(section)
    return builder.build()


def paged_of(*sections):
    document = PagedDocument({k: v for k, v in FACTS.items() if k != "email_subject"})
    for section in sections:
        document.add_section(section)
    return document


def every_gallery_section():
    for gallery in (all_fixtures(), all_paged_fixtures(), all_brochure_fixtures()):
        for build in gallery.values():
            yield from build()._flat_sections()


def every_gallery_component():
    for section in every_gallery_section():
        yield from section.components()


class TestThePullQuote:
    def test_it_requires_text(self):
        with pytest.raises(ValidationError, match="PullQuote requires text"):
            PullQuote("")

    def test_its_text_is_escaped(self):
        html = email_of(FullWidth(PullQuote("<b>bold</b> & more", attribution="A & B"))).render()
        assert "&lt;b&gt;bold&lt;/b&gt; &amp; more" in html
        assert "&mdash; A &amp; B" in html

    def test_the_same_markup_in_email_and_on_paper(self):
        """The band is the degradation: nothing about it needs a print engine."""
        quote = FullWidth(PullQuote("Carry paid.", attribution="Desk"))
        email, paged = email_of(quote).render(), paged_of(quote).render()
        block = email[
            email.index('class="pull-quote"') : email.index(
                "</table>", email.index('class="pull-quote"')
            )
        ]
        assert block in paged

    def test_its_text_is_indented_with_the_attribution_beneath(self):
        assert (
            PullQuote("Carry paid.", attribution="Desk").text() == '    "Carry paid."\n    -- Desk'
        )

    def test_without_an_attribution_it_is_the_quote_alone(self):
        assert PullQuote("Carry paid.").text() == '    "Carry paid."'


class TestTheDropCap:
    COPY = "<p>The curve steepened.</p><p>Carry paid.</p>"

    def test_an_email_renders_byte_for_byte_as_without_it(self):
        with_cap = email_of(FullWidth(TextBlock(self.COPY, drop_cap=True))).render()
        without = email_of(FullWidth(TextBlock(self.COPY))).render()
        assert with_cap == without

    def test_paper_wraps_the_first_letter(self):
        html = paged_of(FullWidth(TextBlock(self.COPY, drop_cap=True))).render()
        assert '<p><span class="drop-cap">T</span>he curve steepened.</p>' in html

    def test_paper_without_it_is_untouched(self):
        assert '<span class="drop-cap">' not in paged_of(FullWidth(TextBlock(self.COPY))).render()

    def test_the_text_part_is_unchanged(self):
        assert TextBlock(self.COPY, drop_cap=True).text() == TextBlock(self.COPY).text()

    @pytest.mark.parametrize(
        ("html", "expected"),
        [
            ("Plain", '<span class="drop-cap">P</span>lain'),
            ("  <p> <em>Q</em>uote", '  <p> <em><span class="drop-cap">Q</span></em>uote'),
            ("&ldquo;Carry", '<span class="drop-cap">&ldquo;</span>Carry'),
            ("<p></p>", "<p></p>"),
        ],
    )
    def test_the_first_visible_character_or_entity_is_the_one_wrapped(self, html, expected):
        assert _with_drop_cap(html) == expected

    def test_markers_still_number_after_the_wrap(self):
        block = TextBlock("<p>Carry paid.[^1]</p>", notes=["A note."], drop_cap=True)
        html = paged_of(FullWidth(block)).render()
        assert '<span class="drop-cap">C</span>arry paid.' in html
        assert 'id="note-ref-1"' in html


class TestFlowedColumns:
    COPY = "<p>One passage, flowed.</p><p>And on into the next column.</p>"

    def test_an_email_is_one_column_byte_for_byte(self):
        """The #189 done-when: the email golden for a FlowedColumns is one column."""
        flowed = email_of(FlowedColumns(TextBlock(self.COPY), count=3, title="Read")).render()
        plain = email_of(FullWidth(TextBlock(self.COPY), title="Read")).render()
        assert flowed == plain

    def test_paper_flows_the_content_through_its_columns(self):
        html = paged_of(FlowedColumns(TextBlock(self.COPY), count=3)).render()
        assert '<div class="flowed-columns" style="column-count:3; column-gap:16px;">' in html

    def test_a_full_width_on_paper_is_not_flowed(self):
        assert 'class="flowed-columns"' not in paged_of(FullWidth(TextBlock(self.COPY))).render()

    def test_the_text_part_is_the_prose_once(self):
        assert FlowedColumns(TextBlock(self.COPY), title="Read").text() == (
            FullWidth(TextBlock(self.COPY), title="Read").text()
        )

    @pytest.mark.parametrize("count", [1, 5, True, "2"])
    def test_the_count_is_two_to_four(self, count):
        with pytest.raises(ValidationError, match="2 to 4 columns"):
            FlowedColumns(TextBlock(self.COPY), count=count)

    def test_it_holds_one_component_not_several(self):
        """Not a split: the docstring's when-to-use, as a fact about the type."""
        block = TextBlock(self.COPY)
        assert FlowedColumns(block).components() == [block]


class TestEveryPrimitiveIsInTheGallery:
    """Standing rules 1 and 9, across all three galleries: each at a non-default value."""

    def test_a_pull_quote_is_in_every_gallery(self):
        for gallery in (all_fixtures(), all_paged_fixtures(), all_brochure_fixtures()):
            assert any(
                isinstance(component, PullQuote)
                for build in gallery.values()
                for section in build()._flat_sections()
                for component in section.components()
            )

    def test_a_pull_quote_sets_its_attribution_and_alignment(self):
        quotes = [c for c in every_gallery_component() if isinstance(c, PullQuote)]
        assert any(q.attribution for q in quotes) and any(q.align for q in quotes)

    def test_flowed_columns_are_in_every_gallery_and_some_count_is_not_two(self):
        for gallery in (all_fixtures(), all_paged_fixtures(), all_brochure_fixtures()):
            assert any(
                isinstance(section, FlowedColumns)
                for build in gallery.values()
                for section in build()._flat_sections()
            )
        flowed = [s for s in every_gallery_section() if isinstance(s, FlowedColumns)]
        assert any(section.count != 2 for section in flowed)

    def test_a_drop_cap_is_set_on_paper_and_in_an_email(self):
        for gallery in (all_fixtures(), all_paged_fixtures(), all_brochure_fixtures()):
            assert any(
                getattr(component, "drop_cap", False)
                for build in gallery.values()
                for section in build()._flat_sections()
                for component in section.components()
            )
