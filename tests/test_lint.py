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
        assert not lint_html('<table style="max-width:680px"><tr><td>x</td></tr></table>')

    def test_ordinary_table_styling_passes(self):
        assert not lint_html('<td style="padding:16px 12px; background-color:#FFFFFF;">x</td>')


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

    def test_deferred_rules_are_named_and_explained(self):
        """
        The deferred set is a recorded decision, not an oversight — each entry
        says why it cannot land green yet and where the finding is filed.
        """
        assert DEFERRED_RULES
        for rule_id, reason in DEFERRED_RULES.items():
            assert rule_id not in SOURCES, f"{rule_id} is both shipped and deferred"
            assert "#78" in reason, f"{rule_id} does not point at its filed issue"
