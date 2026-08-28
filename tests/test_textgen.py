"""
The HTML-subset degrader (#108), the first step of the plain-text epic #53.

The rule the suite holds to: every element in the blessed set has a test, and
so does every element *outside* it, because "unknown markup vanishes" is the
decision that keeps this converter from growing into a second rendering
engine. A closed set nobody checks is a closed set that opens.
"""

from __future__ import annotations

import pytest

from svc.builder.textgen import format_link, html_to_text


class TestTheBlessedSet:
    """One test per element the docstring blesses, and its projection."""

    def test_a_paragraph_is_a_block(self):
        assert html_to_text("<p>One</p><p>Two</p>") == "One\n\nTwo"

    def test_br_is_a_line_break(self):
        assert html_to_text("A<br>B") == "A\nB"

    def test_a_self_closed_br_is_the_same_break(self):
        """
        ``HTMLParser`` routes the XHTML spelling through ``handle_startendtag``
        rather than start-then-end, so a converter that only implements the
        first pair drops ``<br/>`` silently — and callers write both.
        """
        assert html_to_text("A<br/>B") == html_to_text("A<br>B")

    @pytest.mark.parametrize("tag", ["strong", "b", "em", "i"])
    def test_emphasis_markers_are_dropped(self, tag):
        """
        Plain text has no emphasis, and ``*stars*`` are a Markdown
        affectation rather than this house's style.
        """
        assert html_to_text(f"very <{tag}>bold</{tag}> claim") == "very bold claim"

    @pytest.mark.parametrize("tag", ["ul", "ol"])
    def test_a_list_item_is_a_dash_line(self, tag):
        html = f"<{tag}><li>Alpha</li><li>Beta</li></{tag}>"
        assert html_to_text(html) == "- Alpha\n- Beta"

    def test_an_ordered_list_takes_the_same_marker_deliberately(self):
        """
        ``ol`` and ``ul`` project identically, and nothing is lost: the one
        surface that carries ordinals is ``NumberedList``, which holds them as
        data and never routes through this converter.
        """
        assert html_to_text("<ol><li>x</li></ol>") == html_to_text("<ul><li>x</li></ul>")


class TestLinksCarryTheirUrl:
    def test_a_labelled_link_emits_both(self):
        html = 'See <a href="https://example.com/policy">our policy</a> for detail.'
        assert html_to_text(html) == "See our policy (https://example.com/policy) for detail."

    def test_a_link_labelled_with_its_own_url_emits_once(self):
        html = '<a href="https://example.com">https://example.com</a>'
        assert html_to_text(html) == "https://example.com"

    def test_a_link_with_no_href_is_just_its_label(self):
        assert html_to_text("<a>plain</a>") == "plain"

    def test_the_label_is_degraded_before_it_is_spelled(self):
        """The label reaches ``format_link`` collapsed, not as raw markup."""
        html = '<a href="http://x">our\n   <strong>policy</strong></a>'
        assert html_to_text(html) == "our policy (http://x)"

    def test_the_spelling_is_a_seam_number_109_can_move(self):
        """
        #108 implements the policy behind one callable so #109 can change the
        spelling without reopening the parser. If this stops being injectable,
        the formatting policy has leaked into the converter.
        """
        html = '<a href="http://x">label</a>'
        assert html_to_text(html, link_format=lambda label, url: f"{label} <{url}>") == (
            "label <http://x>"
        )

    def test_the_default_formatter_is_callable_on_its_own(self):
        assert format_link("label", "http://x") == "label (http://x)"
        assert format_link("", "http://x") == "http://x"
        assert format_link("label", "") == "label"


class TestTheSetRefusesToGrow:
    @pytest.mark.parametrize("tag", ["table", "div", "span", "h1", "blockquote"])
    def test_an_unknown_element_contributes_text_and_drops_markup(self, tag):
        assert html_to_text(f"<{tag}>copy</{tag}>") == "copy"

    def test_a_table_degrades_to_its_cell_text_run_together(self):
        """
        The documented imperfect degradation, asserted rather than assumed —
        it is what the closed set costs, and the cost should be visible.
        """
        html = "<table><tr><td>A</td><td>B</td></tr></table>"
        assert html_to_text(html) == "AB"

    @pytest.mark.parametrize("tag", ["script", "style"])
    def test_code_is_dropped_whole_rather_than_contributed(self, tag):
        """
        The two exceptions, and they cut the other way. A browser renders no
        text for either, so contributing their content would be *less*
        faithful — a stylesheet or a script body reaching a plain-text reader
        is a defect, not a degradation.
        """
        assert html_to_text(f"<{tag}>payload here</{tag}>Body") == "Body"


class TestCharacterReferences:
    def test_the_copyright_entity_becomes_the_character(self):
        """
        **#100's decision, deliberately inverted, and the direction is the
        whole point.** That issue kept ``&copy;`` as an entity in the HTML
        because U+00A9 mis-decoded as latin-1 renders as a mojibake pair. The
        text part travels in a charset-declared MIME part, so here the real
        character is correct and an undecoded entity would be the bug.

        Entity in, character out — not the other way round.
        """
        assert html_to_text("&copy; 2026 Example Capital") == "© 2026 Example Capital"

    def test_an_ampersand_decodes_too(self):
        assert html_to_text("Example &amp; Co") == "Example & Co"

    def test_an_escaped_angle_bracket_decodes_without_becoming_markup(self):
        assert html_to_text("a &lt;b&gt; c") == "a <b> c"


class TestWhitespace:
    def test_a_paragraph_across_source_lines_is_one_line_of_copy(self):
        """
        The part that is easy to get wrong: a newline in the *source* is
        layout, and a browser collapses it to a space. Only ``br`` and ``li``
        break a line.
        """
        html = "<p>\n    Indented   copy\n    across lines\n</p>"
        assert html_to_text(html) == "Indented copy across lines"

    def test_source_newlines_between_list_items_do_not_add_blank_lines(self):
        assert html_to_text("<ul>\n  <li>A</li>\n  <li>B</li>\n</ul>") == "- A\n- B"

    def test_two_breaks_are_a_gap_the_caller_asked_for(self):
        assert html_to_text("A<br><br>B") == "A\n\nB"

    def test_there_is_no_leading_or_trailing_whitespace(self):
        assert html_to_text("  <p>  Copy  </p>  ") == "Copy"

    def test_an_empty_paragraph_contributes_no_block(self):
        assert html_to_text("<p></p><p>Only</p>") == "Only"

    def test_loose_text_between_blocks_becomes_its_own_block(self):
        assert html_to_text("<p>A</p>loose<p>B</p>") == "A\n\nloose\n\nB"


class TestMalformedInputDegrades:
    """
    Callers pass arbitrary HTML by contract, so a stray tag must not fail the
    render of an otherwise valid email. ``HTMLParser`` is lenient by design;
    these pin that this function is too.
    """

    def test_an_unclosed_tag_does_not_raise(self):
        assert html_to_text("<p>Unclosed") == "Unclosed"

    def test_an_unclosed_link_still_carries_its_url(self):
        assert html_to_text('<p>See <a href="http://x">here') == "See here (http://x)"

    def test_a_stray_angle_bracket_survives_as_text(self):
        assert html_to_text("a < b") == "a < b"

    def test_an_empty_string_is_empty(self):
        assert html_to_text("") == ""

    def test_whitespace_only_input_is_empty(self):
        assert html_to_text("  \n  ") == ""

    def test_a_stray_end_tag_does_not_raise(self):
        assert html_to_text("copy</p></div>") == "copy"


class TestDeterminism:
    """
    #110's text goldens rest on this, and so does the golden discipline
    behind them: the same input twice must be byte-identical.
    """

    @pytest.mark.parametrize(
        "html",
        [
            "<p>Past performance is <strong>not</strong> a guide.</p>",
            '<ul><li><a href="http://a">A</a></li><li>B</li></ul>',
            "&copy; 2026 Example Capital &amp; Co",
            "<p>One</p><p>Two<br>Three</p>",
        ],
    )
    def test_the_same_input_twice_is_byte_identical(self, html):
        assert html_to_text(html) == html_to_text(html)


class TestTheDocstringCarriesTheDecision:
    def test_the_closed_set_is_stated_in_the_module(self):
        """
        The epic names this converter as its scope magnet, so "the set is
        closed" has to live where the next contributor reads it — not only in
        an issue they will never open.
        """
        from svc.builder import textgen

        assert textgen.__doc__ is not None
        assert "refuses to grow" in textgen.__doc__


class TestItChangesNothingElse:
    def test_it_is_a_pure_module_with_no_builder_imports(self):
        """
        #108 is a freestanding piece: no API surface, no render change, no
        golden moves. Importing anything from the builder would make it part
        of the render path and give it a reason to move a golden later.
        """
        import ast
        import pathlib

        from svc.builder import textgen

        source = pathlib.Path(textgen.__file__).read_text()
        imported = {
            node.module
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not any(name.startswith("svc") for name in imported), imported
