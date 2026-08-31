"""
The email-client lint pass (#60).

Two halves, and both matter:

* **the gate** — every gallery fixture lints clean, so a regression in the
  templates fails here rather than in a reader's Outlook;
* **the proof each rule bites** — a deliberately-broken snippet per rule. A
  linter whose rules have never been seen to fire is a linter nobody can trust
  to be silent, which is the same discipline the goldens (#58) and the
  ``kitchen_sink`` completeness tests are held to.
"""

from __future__ import annotations

import re

import pytest

from qa.fixtures import all_fixtures
from qa.lint import (
    DEFERRED_RULES,
    SOURCES,
    Finding,
    Severity,
    errors,
    format_findings,
    lint_email,
    lint_html,
    size_report,
)
from svc.builder import Email, FullWidth, TextBlock
from svc.config import config_override

FIXTURE_NAMES = sorted(all_fixtures())


def rule_ids(findings: list[Finding]) -> set[str]:
    return {finding.rule_id for finding in findings}


class TestTheGalleryLintsClean:
    """
    #60 required this to land green: a linter that arrives red teaches
    everyone to ignore it. Rules whose findings cannot be fixed today are
    deferred (see DEFERRED_RULES / #78), not downgraded to warnings.
    """

    @pytest.mark.parametrize("name", FIXTURE_NAMES)
    def test_no_findings(self, name):
        findings = lint_email(all_fixtures()[name]())
        assert not findings, format_findings(findings)


class TestImgWidthAttr:
    def test_a_missing_width_fires(self):
        findings = lint_html('<img src="a.png" alt="A chart">')
        assert rule_ids(findings) == {"img-width-attr"}
        assert findings[0].severity is Severity.ERROR

    def test_a_non_integer_width_fires(self):
        """Outlook reads the attribute as pixels; "100%" is not that."""
        findings = lint_html('<img src="a.png" alt="A chart" width="100%">')
        assert rule_ids(findings) == {"img-width-attr"}

    def test_a_css_only_width_does_not_satisfy_it(self):
        """The whole point: max-width in CSS is what Outlook ignores."""
        findings = lint_html('<img src="a.png" alt="A" style="max-width:100px">')
        assert "img-width-attr" in rule_ids(findings)

    def test_an_integer_width_passes(self):
        assert not lint_html('<img src="a.png" alt="A chart" width="320">')


class TestImgAlt:
    @pytest.mark.parametrize(
        "tag",
        [
            '<img src="a.png" width="10">',
            '<img src="a.png" width="10" alt="">',
            '<img src="a.png" width="10" alt="   ">',
        ],
    )
    def test_missing_or_blank_alt_fires(self, tag):
        assert "img-alt" in rule_ids(lint_html(tag))

    def test_real_alt_passes(self):
        assert not lint_html('<img src="a.png" width="10" alt="Factor returns">')

    def test_a_declared_decorative_image_passes(self):
        """
        ``alt=""`` is correct for an image carrying no information — but in
        the render it is indistinguishable from a forgotten alt, so the rule
        reads the annotation, exactly as ``table-role`` does (#149).
        """
        assert not lint_html('<img src="a.png" width="10" alt="" role="presentation">')

    def test_the_declaration_alone_does_not_suppress_the_rule(self):
        """
        The mirror case, and the reason this is a two-way rule: an image that
        says a screen reader should skip it and then supplies text for one is
        making both claims at once.
        """
        tag = '<img src="a.png" width="10" alt="Factor returns" role="presentation">'
        assert "img-alt" in rule_ids(lint_html(tag))


class TestVmlFillEmptySrc:
    """
    The one rule that reads conditional-comment text for VML (#150).

    ``[if mso]`` markup is otherwise not linted at all — judging VML by
    standard-HTML rules fires on markup that is correct precisely because it
    is non-standard. This reaches in for one specific defect, the exception
    ``no-external-css`` already makes for an ``@import``.
    """

    def test_an_empty_src_fires(self):
        html = '<!--[if mso]><v:fill type="frame" src="" color="#111"/><![endif]-->'
        assert "vml-fill-empty-src" in rule_ids(lint_html(html))

    def test_a_real_src_passes(self):
        html = '<!--[if mso]><v:fill type="frame" src="https://a/b.png"/><![endif]-->'
        assert not rule_ids(lint_html(html))

    def test_an_absent_src_passes(self):
        """The shape the fix emits: the attribute is gated, not emptied."""
        html = '<!--[if mso]><v:fill type="frame" color="#111" opacity="65%"/><![endif]-->'
        assert not rule_ids(lint_html(html))

    def test_other_vml_is_left_alone(self):
        """
        The scope guarantee. A rule that grew into linting VML generally
        would fire on markup that is correct because it is non-standard.
        """
        html = '<!--[if mso]><v:roundrect arcsize="8%" stroke="false"></v:roundrect><![endif]-->'
        assert not rule_ids(lint_html(html))


class TestNoExternalCss:
    def test_a_stylesheet_link_fires(self):
        findings = lint_html('<link rel="stylesheet" href="https://example.com/a.css">')
        assert rule_ids(findings) == {"no-external-css"}

    def test_an_import_in_a_style_block_fires(self):
        findings = lint_html("<style>@import url('https://example.com/a.css');</style>")
        assert rule_ids(findings) == {"no-external-css"}

    def test_an_import_hidden_in_a_conditional_comment_fires(self):
        """
        mso conditional comments carry real CSS for Outlook, so an @import in
        one is exactly as external as any other.
        """
        findings = lint_html("<!--[if mso]><style>@import url('x.css');</style><![endif]-->")
        assert rule_ids(findings) == {"no-external-css"}

    def test_a_non_stylesheet_link_passes(self):
        assert not lint_html('<link rel="icon" href="favicon.ico">')


class TestOutlookUnsupportedCss:
    @pytest.mark.parametrize(
        "style",
        ["display:flex", "display:grid", "display:inline-flex", "position:absolute"],
    )
    def test_unsupported_layout_fires(self, style):
        findings = lint_html(f'<div style="{style}">x</div>')
        assert rule_ids(findings) == {"outlook-unsupported-css"}

    def test_it_is_case_and_space_insensitive(self):
        assert "outlook-unsupported-css" in rule_ids(
            lint_html('<div style="DISPLAY:  Flex">x</div>')
        )

    def test_max_width_is_deliberately_allowed(self):
        """
        The repo pairs max-width with a width= attribute on purpose, so denying
        it would fire on correct code. A noisy rule gets switched off, which is
        worse than no rule; img-width-attr covers what actually matters.
        """
        markup = '<table role="presentation" style="max-width:680px"><tr><td>x</td></tr></table>'
        assert "outlook-unsupported-css" not in rule_ids(lint_html(markup))
        assert not lint_html(markup)

    def test_ordinary_table_styling_passes(self):
        assert not lint_html('<td style="padding:16px 12px; background-color:#FFFFFF;">x</td>')


class TestOutlookLineHeight:
    """#78's first finding, now a shipped rule."""

    def test_a_unitless_line_height_is_an_error(self):
        findings = lint_html('<p style="line-height:1.5">x</p>')
        assert [f.rule_id for f in findings] == ["outlook-line-height"]

    def test_the_message_names_the_replacement(self):
        """
        A rule that says only "this is wrong" costs the reader the arithmetic.
        """
        (finding,) = lint_html('<p style="line-height:1.72">x</p>')
        assert "150%" not in finding.message
        assert "172%" in finding.message

    @pytest.mark.parametrize("value", ["172%", "38px", "1.2em", "normal", "inherit"])
    def test_a_value_with_a_unit_is_fine(self, value):
        assert not lint_html(f'<p style="line-height:{value}">x</p>')

    def test_zero_is_deliberately_allowed(self):
        """
        The accent rule's spacer cell collapses a row with ``line-height:0``.
        Zero is unambiguous without a unit, and ``0%`` would say the same
        thing less clearly — so the rule permits it rather than forcing a
        cosmetic edit on markup that is already correct.
        """
        assert not lint_html('<td style="font-size:0; line-height:0">&nbsp;</td>')

    def test_the_gallery_emits_percentages(self):
        """The templates' side of the same claim, on rendered output."""
        html = all_fixtures()["kitchen_sink"]().render()
        assert "line-height:1.72" not in html and "line-height: 1.72" not in html
        assert "line-height: 172%" in html


class TestOutlookTransparentBackground:
    """#78's second finding."""

    @pytest.mark.parametrize(
        "value", ["rgba(1,2,3,0.5)", "rgba( 1, 2, 3, .5 )", "hsla(1,2%,3%,0.5)", "#11223344"]
    )
    def test_an_alpha_channel_is_an_error(self, value):
        findings = lint_html(f'<div style="background-color:{value}">x</div>')
        assert [f.rule_id for f in findings] == ["outlook-transparent-background"]

    @pytest.mark.parametrize("value", ["#112233", "rgb(1,2,3)", "transparent"])
    def test_an_opaque_colour_is_fine(self, value):
        assert not lint_html(f'<div style="background-color:{value}">x</div>')


class TestEmptyUrl:
    """#78's third finding."""

    @pytest.mark.parametrize("value", ["url('')", 'url("")', "url()", "url(  )"])
    def test_an_empty_url_is_an_error(self, value):
        # The attribute takes whichever quote the value does not, or the
        # value would close it and the parser would never see the
        # declaration at all.
        quote = "'" if '"' in value else '"'
        findings = lint_html(f"<div style={quote}background-image:{value}{quote}>x</div>")
        assert [f.rule_id for f in findings] == ["empty-url"]

    def test_a_real_url_is_fine(self):
        assert not lint_html('<div style="background-image:url(a.png)">x</div>')

    def test_the_masthead_never_emits_one(self):
        """
        ``minimal`` sets no header background image, which is the case that
        used to render ``url('')``.
        """
        assert "url('')" not in all_fixtures()["minimal"]().render()


class TestTableRole:
    """
    The rule fires **both ways**, which is the whole point: a check that only
    demanded the presentational role would be satisfied by marking every
    table, stripping the semantics from the one table a reader should
    actually navigate.
    """

    def test_a_layout_table_with_no_role_fires(self):
        html = "<table><tr><td>Copy</td></tr></table>"
        assert "table-role" in rule_ids(lint_html(html))

    def test_a_marked_layout_table_passes(self):
        html = '<table role="presentation"><tr><td>Copy</td></tr></table>'
        assert not lint_html(html)

    def test_role_none_is_accepted_as_the_synonym_it_is(self):
        html = '<table role="none"><tr><td>Copy</td></tr></table>'
        assert not lint_html(html)

    def test_a_data_table_passes_unmarked(self):
        html = "<table><tr><th>Factor</th></tr><tr><td>Value</td></tr></table>"
        assert not lint_html(html)

    def test_a_data_table_marked_presentational_fires(self):
        """
        The mirror case, and the one a naive fix introduces: the role strips
        exactly the semantics a screen reader needs to associate each cell
        with its column.
        """
        html = '<table role="presentation"><tr><th>Factor</th></tr></table>'
        findings = [f for f in lint_html(html) if f.rule_id == "table-role"]
        assert findings
        assert "data table" in findings[0].message

    def test_a_data_table_nested_in_layout_tables_classifies_each_correctly(self):
        """
        Not hypothetical — it is exactly how the gallery renders. A flat flag
        would let the inner table's ``th`` mark its ancestors as data too, and
        the whole document would pass while every layout table stayed unmarked.
        """
        html = (
            '<table role="presentation"><tr><td>'
            '<table role="presentation"><tr><td>'
            "<table><tr><th>Factor</th></tr></table>"
            "</td></tr></table>"
            "</td></tr></table>"
        )
        assert not lint_html(html)

    def test_the_outer_layout_table_still_fires_when_it_is_the_unmarked_one(self):
        html = "<table><tr><td><table><tr><th>Factor</th></tr></table></td></tr></table>"
        findings = [f for f in lint_html(html) if f.rule_id == "table-role"]
        assert len(findings) == 1, "only the outer layout table should fire"

    def test_it_reports_the_opening_tag_not_the_closing_one(self):
        """
        The parser only knows the verdict at the close tag, but a reader
        needs the line the table *starts* on to find it.
        """
        html = "<p>one</p>\n<p>two</p>\n<table>\n<tr><td>x</td></tr>\n</table>"
        findings = [f for f in lint_html(html) if f.rule_id == "table-role"]
        assert "line 3" in findings[0].location

    def test_an_unclosed_table_does_not_crash_the_pass(self):
        assert isinstance(lint_html("<table><tr><td>never closed"), list)


class TestTheTemplatesAreAnnotated:
    """
    The render side of #114, which the raw-HTML tests above cannot see: every
    layout table the gallery actually emits is marked, and the data table is
    not. Riding the fixtures means a new template is covered without anyone
    extending a list.
    """

    def test_no_gallery_fixture_renders_an_unannotated_table(self):
        for name, build in all_fixtures().items():
            findings = [f for f in lint_email(build()) if f.rule_id == "table-role"]
            assert not findings, f"{name}: {[f.message for f in findings]}"

    def test_the_data_table_is_still_a_data_table(self):
        """
        The asymmetry, asserted positively rather than inferred from the
        absence of a finding: marking everything would pass the test above.
        """
        html = all_fixtures()["kitchen_sink"]().render()
        unmarked = [t for t in re.findall(r"<table[^>]*?>", html, re.S) if "role=" not in t]
        assert len(unmarked) == 1, "exactly one table should be left with data semantics"
        assert "<th" in html

    def test_every_header_cell_is_scoped(self):
        """
        Without ``scope``, a screen reader has no defined association even
        once the table is correctly exposed as data. Both directions since
        #120: ``col`` on the heading row, ``row`` on the label column.
        """
        html = all_fixtures()["kitchen_sink"]().render()
        scoped = html.count('scope="col"') + html.count('scope="row"')
        assert html.count("<th") == scoped
        assert html.count('scope="col"'), "the heading row"
        assert html.count('scope="row"'), "the label column"


class TestMarkupOutlookCannotSee:
    """
    ``<!--[if !mso]><!-->`` is *downlevel-revealed*: the comment ends at once,
    so what follows is real HTML to every parser — and to every client except
    Outlook. An Outlook-specific rule therefore has nothing to say about it.
    """

    HIDDEN = '<!--[if !mso]><!--><p style="line-height:1.5">x</p><!--<![endif]-->'

    def test_an_outlook_rule_is_suppressed_there(self):
        assert not lint_html(self.HIDDEN)

    def test_the_same_markup_outside_still_fires(self):
        """The negative control: the suppression is scoped, not a hole."""
        assert [f.rule_id for f in lint_html('<p style="line-height:1.5">x</p>')] == [
            "outlook-line-height"
        ]

    def test_it_reopens_after_the_endif(self):
        html = self.HIDDEN + '<p style="line-height:1.5">y</p>'
        assert [f.rule_id for f in lint_html(html)] == ["outlook-line-height"]

    def test_a_rule_that_is_not_about_outlook_still_fires(self):
        """
        ``img-alt`` is suppressed by nothing: a reader with images off sees
        the missing alt in every client, Outlook or not. That is why the
        suppression set is named rather than matched on a rule-id prefix.
        """
        html = '<!--[if !mso]><!--><img src="a.png" width="10"><!--<![endif]-->'
        assert [f.rule_id for f in lint_html(html)] == ["img-alt"]

    def test_the_masthead_scrim_uses_it(self):
        """
        The shipped case: the rgba scrim is still rendered for every other
        client, and Outlook gets the same scrim from ``v:fill`` instead.
        """
        html = all_fixtures()["kitchen_sink"]().render()
        assert '<!--[if !mso]><!--><div style="background-color:rgba' in html
        assert not lint_html(html)


class TestSizeBudget:
    """
    Note the shape of these: the HTML is rendered under the *real* config, and
    only the lint call runs under an override. Email.render() enforces the same
    limit itself, so rendering under a 2 KB limit raises SizeError before the
    linter ever sees the document — the two checks are layered, not parallel,
    and the test has to respect that.
    """

    @pytest.fixture
    def html(self) -> str:
        email = Email(
            metadata={
                "email_subject": "Budget",
                "firm_name": "Hermes Research",
                "campaign_name": "budget",
            }
        )
        email.add_section(FullWidth(content=TextBlock("<p>Body.</p>")))
        return email.render()

    def test_a_comfortable_email_reports_nothing(self, html):
        assert not lint_html(html)

    def test_it_warns_over_the_warn_threshold(self, html):
        with config_override(size_warn_kb=1, size_limit_kb=1000):
            findings = lint_html(html)

        assert rule_ids(findings) == {"size-budget"}
        assert findings[0].severity is Severity.WARNING

    def test_it_errors_over_the_limit(self, html):
        with config_override(size_warn_kb=1, size_limit_kb=2, inline_image_limit_kb=1):
            findings = lint_html(html)

        assert findings[0].severity is Severity.ERROR
        assert errors(findings) == findings

    def test_the_failure_names_the_heaviest_regions_with_bytes(self, html):
        """
        _validate_size reports a total, which tells you an email is too big
        without telling you what to cut. This is the part that says where.
        """
        with config_override(size_warn_kb=1, size_limit_kb=2, inline_image_limit_kb=1):
            (finding,) = lint_html(html)

        assert "heaviest regions" in finding.message
        assert "KB" in finding.message
        assert "FOOTER" in finding.message

    def test_it_reads_the_config_at_call_time(self, html):
        """An override installed after import must still be seen."""
        assert not lint_html(html)
        with config_override(size_warn_kb=1, size_limit_kb=1000):
            assert lint_html(html)
        assert not lint_html(html)


class TestSizeReport:
    def test_regions_sum_to_the_total(self):
        html = all_fixtures()["kitchen_sink"]().render()

        report = size_report(html)

        assert sum(region.bytes for region in report.regions) == report.total_bytes

    def test_it_names_the_section_that_spent_the_budget(self):
        html = all_fixtures()["kitchen_sink"]().render()

        heaviest = size_report(html).heaviest()[0]

        assert "SECTIONS" in heaviest.name
        assert heaviest.kb > 10

    def test_decorative_rules_are_not_regions(self):
        """
        The templates use <!-- ══════ --> as visual separators. Counted as
        sections, the heaviest "region" was a row of box-drawing characters —
        a breakdown that names nothing explains nothing.
        """
        names = [region.name for region in size_report("<!-- ═══ -->body").regions]

        assert names == ["(document head)"] or all(any(c.isalpha() for c in n) for n in names)

    def test_html_with_no_markers_still_reports_a_total(self):
        report = size_report("<p>no markers here</p>")

        assert report.total_bytes == len("<p>no markers here</p>")
        assert report.regions == []


class TestEveryRuleIsSourced:
    """
    An unsourced rule asserting something about a mail client is a preference
    wearing a rule's clothes. #60: "an unsourced rule doesn't ship."
    """

    def test_every_rule_that_can_fire_has_a_source(self):
        broken = (
            '<img src="a.png"><link rel="stylesheet" href="a.css"><div style="display:flex">x</div>'
        )
        fired = rule_ids(lint_html(broken)) | {"size-budget"}

        assert fired <= set(SOURCES), f"unsourced: {sorted(fired - set(SOURCES))}"
        for rule_id in fired:
            assert SOURCES[rule_id].strip(), f"{rule_id} has an empty source"

    def test_findings_carry_their_source_into_the_report(self):
        report = format_findings(lint_html('<img src="a.png">'))

        assert "source:" in report

    def test_nothing_is_both_shipped_and_deferred(self):
        """
        The deferred set is a recorded decision, not an oversight — each entry
        says why it cannot land green yet and where the finding is filed.

        It is **empty** today, and that is the state this asserts holds
        *consistently* rather than the state it demands: the three entries it
        carried were #78, all three are fixed, and all three rules moved into
        ``SOURCES``. A rule may not sit in both places, and a deferred one
        must still name its filed issue.
        """
        for rule_id, reason in DEFERRED_RULES.items():
            assert rule_id not in SOURCES, f"{rule_id} is both shipped and deferred"
            assert "#" in reason, f"{rule_id} does not point at its filed issue"

    def test_the_three_findings_from_78_now_ship(self):
        """
        The rules #78 unblocked. Each is only meaningful once its finding is
        gone from the gallery, which ``TestTheGalleryIsClean`` asserts — this
        is the other half: they are switched on rather than quietly dropped.
        """
        for rule_id in (
            "outlook-line-height",
            "outlook-transparent-background",
            "empty-url",
        ):
            assert rule_id in SOURCES, f"{rule_id} was dropped rather than shipped"
            assert rule_id not in DEFERRED_RULES


class TestCommentaryDoesNotShipToTheReader:
    """#137. A comment inside rendered HTML is downloaded by every recipient and
    counts against the 102 KB clipping limit. Build-time reasoning belongs in a
    Jinja comment, which costs nothing; only short named markers ship.
    """

    #: Ceiling on non-conditional comment bytes in one rendered email. Today's
    #: worst fixture is 391 — the named section markers and nothing else. The
    #: headroom is for a genuinely new region, not for prose.
    MAX_COMMENT_BYTES = 450

    #: A marker is what `_MARKER` will match, so the cap is `_MARKER`'s own.
    MAX_MARKER_CHARS = 60

    @staticmethod
    def _shipped(html: str) -> list[str]:
        conditional = re.compile(r"<!--\s*\[if\s|<!\[endif\]", re.IGNORECASE)
        return [c for c in re.findall(r"<!--.*?-->", html, re.S) if not conditional.search(c)]

    def test_no_email_ships_more_than_its_markers(self) -> None:
        for name, build in sorted(all_fixtures().items()):
            html = build().render()
            shipped = sum(len(c) for c in self._shipped(html))
            assert shipped <= self.MAX_COMMENT_BYTES, (
                f"{name} ships {shipped} bytes of commentary. Move the reasoning to a "
                f"Jinja comment — it reaches a template author and not a recipient."
            )

    def test_every_shipped_comment_is_a_short_named_marker(self) -> None:
        html = all_fixtures()["kitchen_sink"]().render()
        for comment in self._shipped(html):
            assert len(comment) <= self.MAX_MARKER_CHARS + 10, (
                f"shipped comment is prose, not a marker: {comment[:70]!r}"
            )
            assert re.search(r"[A-Za-z]", comment), (
                f"a decorative rule ships bytes and names no region: {comment!r}"
            )


class TestTheSizeBudgetStillNamesItsRegions:
    """`size_report` degrades *silently*: strip the markers and it reports one
    anonymous blob, still passing every other test. #137 removed comments next to
    those markers, so the attribution needs an assertion of its own.
    """

    EXPECTED = (
        "Preheader",
        "Outer wrapper",
        "HEADER: Disclaimer bar",
        "HEADER: Background image + text overlay",
        "Accent rule",
        "Date / Issue bar",
        "SECTIONS: Insert containers here",
        "FOOTER: copyright, links and optional disclaimer",
    )

    def test_the_named_regions_survive(self) -> None:
        report = size_report(all_fixtures()["kitchen_sink"]().render())
        names = {region.name for region in report.regions}
        missing = [name for name in self.EXPECTED if name not in names]
        assert not missing, f"section markers lost, byte attribution degraded: {missing}"

    def test_the_body_is_still_attributed_to_the_sections_marker(self) -> None:
        report = size_report(all_fixtures()["kitchen_sink"]().render())
        heaviest = report.heaviest(1)[0]
        assert heaviest.name == "SECTIONS: Insert containers here", (
            f"the heaviest region is {heaviest.name!r} — attribution has drifted"
        )
