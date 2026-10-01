"""
The size report names each body section, and both commands report on an email over 102 KB (#259).
"""

from __future__ import annotations

import textwrap
import warnings
from pathlib import Path

import pytest

from pyhermes.builder import Email, FullWidth, TextBlock
from pyhermes.builder.exceptions import SizeError
from pyhermes.check import lint_document, render_for_check, size_report
from pyhermes.check.__main__ import main as check_main
from qa.fixtures import all_brochure_fixtures, all_fixtures, all_paged_fixtures
from qa.preview import EXIT_BUILD_FAILED, EXIT_LINT_ERRORS
from qa.preview import main as preview_main

FACTS = {"email_subject": "Rates Weekly", "firm_name": "Acme", "campaign_name": "Rates"}

#: Four sections of different weights, about 150 KB in all: over the limit.
WORDS = {"Outlook": 2_000, "Market wrap": 6_000, "Positioning": 12_000, "Appendix": 8_000}

DRAFT = f"""
    from pyhermes.builder import Email, FullWidth, TextBlock

    def build():
        email = Email({FACTS!r})
        for title, words in {WORDS!r}.items():
            email.add_section(FullWidth(TextBlock("<p>" + "word " * words + "</p>"), title=title))
        return email
"""


def heavy_email() -> Email:
    email = Email(FACTS)
    for title, words in WORDS.items():
        email.add_section(FullWidth(TextBlock("<p>" + "word " * words + "</p>"), title=title))
    return email


@pytest.fixture
def draft(tmp_path: Path) -> Path:
    path = tmp_path / "heavy.py"
    path.write_text(textwrap.dedent(DRAFT), encoding="utf-8")
    return path


class TestTheReportNamesEachSection:
    def test_heaviest_first_by_title(self):
        email = heavy_email()
        html = render_for_check(email)
        report = size_report(html, email.rendered_sections())
        names = [region.name for region in report.heaviest(4)]
        assert names == [
            "section 3: Positioning",
            "section 4: Appendix",
            "section 2: Market wrap",
            "section 1: Outlook",
        ]

    def test_the_regions_still_sum_to_the_total(self):
        email = heavy_email()
        report = size_report(render_for_check(email), email.rendered_sections())
        assert sum(region.bytes for region in report.regions) == report.total_bytes

    def test_the_lint_finding_carries_the_breakdown(self):
        (finding,) = [f for f in lint_document(heavy_email()) if f.rule_id == "size-budget"]
        assert "section 3: Positioning" in finding.message
        assert finding.message.index("Positioning") < finding.message.index("Outlook")

    def test_an_untitled_section_is_named_by_position_and_class(self):
        email = Email(FACTS).add_section(FullWidth(TextBlock("<p>Body.</p>")))
        assert [label for label, _ in email.rendered_sections()] == ["section 1: FullWidth"]

    def test_without_sections_the_report_is_what_it_was(self):
        html = all_fixtures()["kitchen_sink"]().render()
        assert size_report(html) == size_report(html, None) == size_report(html, [])


class TestEverySectionIsFound:
    """Each section's markup must be the bytes the document renders, or the report is silent."""

    @pytest.mark.parametrize(
        "name, build", sorted({**all_fixtures(), **all_paged_fixtures()}.items())
    )
    def test_in_every_email_and_paged_fixture(self, name, build):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            document = build()
            html = document.render()
            sections = document.rendered_sections()
        offsets = [html.find(markup) for _, markup in sections]
        assert -1 not in offsets, f"{name}: a section renders differently on its own"
        assert offsets == sorted(offsets)
        report = size_report(html, sections)
        assert sum(region.bytes for region in report.regions) == report.total_bytes

    def test_a_brochure_falls_back_to_the_markers(self):
        """Its panels are laid out by imposition, so no section is found, and nothing breaks."""
        brochure = all_brochure_fixtures()["tri_fold_letter"]()
        html = brochure.render()
        report = size_report(html, brochure.rendered_sections())
        assert sum(region.bytes for region in report.regions) == report.total_bytes


class TestTheRefusedMarkupIsKept:
    def test_size_error_carries_the_html(self):
        with pytest.raises(SizeError) as caught:
            heavy_email().render()
        assert caught.value.html is not None
        assert caught.value.html.startswith("<!DOCTYPE")

    def test_render_for_check_returns_it(self):
        html = render_for_check(heavy_email())
        assert len(html.encode("utf-8")) / 1024 > 102

    def test_render_itself_still_refuses(self):
        with pytest.raises(SizeError, match="exceeds 102 KB"):
            heavy_email().render()


class TestTheCommandsReportOverTheLimit:
    def test_preview_lint_prints_the_breakdown_and_fails(self, draft, tmp_path, capsys):
        code = preview_main([f"{draft}:build", "--lint", "--out", str(tmp_path)])
        out = capsys.readouterr().out
        assert code == EXIT_LINT_ERRORS
        assert "size-budget" in out
        assert out.index("section 3: Positioning") < out.index("section 1: Outlook")
        assert (tmp_path / "heavy-build.html").stat().st_size > 102 * 1024

    def test_preview_without_lint_still_stops_and_says_how_to_see_why(
        self, draft, tmp_path, capsys
    ):
        code = preview_main([f"{draft}:build", "--out", str(tmp_path)])
        err = capsys.readouterr().err
        assert code == EXIT_BUILD_FAILED
        assert "SizeError" in err and "--lint" in err

    def test_the_shipped_check_prints_the_breakdown_and_fails(self, draft, tmp_path, capsys):
        code = check_main([f"{draft}:build", "--out", str(tmp_path)])
        out = capsys.readouterr().out
        assert code == EXIT_LINT_ERRORS
        assert "section 3: Positioning" in out
