"""
The editorial primitives (#189), and the degradation each states for email.

Each primitive renders on paper and degrades in an email, and each email
degradation is a test here rather than a golden someone has to read.
"""

from __future__ import annotations

import pytest

from pyhermes.builder import (
    EmailBuilder,
    FlowedColumns,
    FullWidth,
    ImageBlock,
    PullQuote,
    TextBlock,
)
from pyhermes.builder.components import _with_drop_cap, descendants
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import EmailImage
from pyhermes.document import PagedDocument
from qa.fixtures import all_brochure_fixtures, all_fixtures, all_paged_fixtures
from qa.fixtures._png import solid_png

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


def figure(wrap: str = "right", **kwargs) -> ImageBlock:
    image = EmailImage.attached(solid_png(120, 90, (1, 2, 3)), alt="Desk", width=120)
    return ImageBlock(image, align="right", wrap=wrap, **kwargs)


class TestTheWrappedFigure:
    PROSE = "<p>The desk keeps the steepener on.</p>"

    def test_an_email_sets_it_above_the_prose_with_its_align_and_no_float(self):
        html = email_of(FullWidth(TextBlock(self.PROSE, figure=figure()))).render()
        at = html.index('class="wrapped-figure"')
        assert '<div class="wrapped-figure">' in html
        assert html.index('align="right"', at) < html.index("The desk keeps", at)
        assert "wrap-right" not in html

    def test_paper_floats_it_at_its_display_width(self):
        html = paged_of(FullWidth(TextBlock(self.PROSE, figure=figure("left")))).render()
        assert '<div class="wrapped-figure wrap-left" style="width:120px;">' in html

    def test_a_text_block_without_one_is_untouched_in_every_medium(self):
        for render in (email_of, paged_of):
            assert "wrapped-figure" not in render(FullWidth(TextBlock(self.PROSE))).render()

    def test_its_image_reaches_the_manifest(self):
        """Standing rule 7: the block that hosts an image declares it."""
        block = TextBlock(self.PROSE, figure=figure())
        assert block.images() == [block.figure.image]
        assert [a.content_id for a in email_of(FullWidth(block)).assets()] == [
            block.figure.image.content_id
        ]

    def test_the_text_part_is_the_figure_then_the_prose(self):
        assert TextBlock(self.PROSE, figure=figure()).text() == (
            "[Desk]\n\nThe desk keeps the steepener on."
        )

    def test_a_wrap_needs_a_width(self):
        with pytest.raises(ValidationError, match="needs a display width"):
            ImageBlock("https://example.com/a.png", alt_text="A", wrap="left")

    def test_an_unknown_wrap_is_refused(self):
        with pytest.raises(ValidationError, match="Unsupported wrap"):
            figure("centre")

    def test_the_figure_must_be_an_image_block(self):
        with pytest.raises(ValidationError, match="takes an ImageBlock"):
            TextBlock(self.PROSE, figure=TextBlock("<p>x</p>"))  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "kwargs", [{"label": "Figure"}, {"caption": "Desk[^1]", "notes": ["n"]}]
    )
    def test_a_figure_cannot_be_numbered_or_noted(self, kwargs):
        with pytest.raises(ValidationError, match="cannot be numbered or carry notes"):
            TextBlock(self.PROSE, figure=figure(**kwargs))


class TestEveryPrimitiveIsInTheGallery:
    """Standing rules 1 and 9, across all three galleries: each at a non-default value."""

    def test_a_pull_quote_is_in_every_gallery(self):
        for gallery in (all_fixtures(), all_paged_fixtures(), all_brochure_fixtures()):
            assert any(
                isinstance(component, PullQuote)
                for build in gallery.values()
                for section in build()._flat_sections()
                # A block a Stack holds counts: the document reads leaves (#261).
                for component in descendants(section.components())
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

    def test_a_wrapped_figure_is_in_every_gallery_and_both_sides_are_used(self):
        for gallery in (all_fixtures(), all_paged_fixtures(), all_brochure_fixtures()):
            assert any(
                getattr(component, "figure", None) is not None
                for build in gallery.values()
                for section in build()._flat_sections()
                for component in section.components()
            )
        sides = {c.figure.wrap for c in every_gallery_component() if getattr(c, "figure", None)}
        assert sides == {"left", "right"}

    def test_a_drop_cap_is_set_on_paper_and_in_an_email(self):
        for gallery in (all_fixtures(), all_paged_fixtures(), all_brochure_fixtures()):
            assert any(
                getattr(component, "drop_cap", False)
                for build in gallery.values()
                for section in build()._flat_sections()
                for component in section.components()
            )
