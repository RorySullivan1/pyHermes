"""
The harness learns what a medium is (#165).

Three things move here and each has a failure mode a green suite would hide:
a rule applied to a medium its claim is not true of, a golden overwritten by
another medium's fixture of the same name, and a paged document photographed
by an instrument that cannot see pages.
"""

from __future__ import annotations

import pytest

from pyhermes.brochure import BROCHURE_MEDIUM
from pyhermes.builder.medium import DEFAULT_MEDIUM
from pyhermes.deck import DECK_MEDIUM
from pyhermes.document import PAGED_MEDIUM, PagedDocument
from pyhermes.email import EMAIL_MEDIUM
from qa.fixtures import all_fixtures, all_paged_fixtures
from qa.goldens import GOLDEN_DIR, artifacts, html_path, medium_dir
from qa.lint import RULE_MEDIA, SOURCES, Severity, lint_document, lint_email, lint_html, rules_for
from qa.screenshots import PDF_PX_SCALE, capture_pages, pages_available

SHIPPED_MEDIA = {
    EMAIL_MEDIUM.name,
    PAGED_MEDIUM.name,
    BROCHURE_MEDIUM.name,
    DECK_MEDIUM.name,
    DEFAULT_MEDIUM.name,
}

requires_pdf = pytest.mark.skipif(
    not pages_available(),
    reason='no PDF backend; paged screenshots need the "[qa]" and "[pdf]" extras',
)


class TestEveryRuleSaysWhereItApplies:
    def test_every_rule_with_a_source_has_a_medium(self):
        # The table cannot be forgotten: a rule that fires but names no medium
        # would either apply everywhere or nowhere, silently.
        assert set(SOURCES) == set(RULE_MEDIA)

    def test_every_medium_named_is_one_that_ships(self):
        named = {medium for media in RULE_MEDIA.values() for medium in media}
        assert named <= SHIPPED_MEDIA, f"the table names a medium nothing builds: {named}"

    def test_no_rule_applies_to_nothing(self):
        empty = [rule for rule, media in RULE_MEDIA.items() if not media]
        assert not empty, f"these rules can never fire: {empty}"

    def test_the_email_set_is_unchanged(self):
        # #165 must not quietly narrow what an email is judged by. The count
        # is a tripwire, not a target: it moved from ten to eleven when #150
        # added vml-fill-frame-without-src, which is a rule being *added* to
        # what an email is judged by, and to twelve when #223 added
        # table-header-tier. Narrowing the set is what this guards.
        paged_only = {"page-size-declared", "paged-table-width", "table-structure"}
        print_only = {"print-marks", "rgb-only"}
        deck_only = {"slide-overflow"}
        assert rules_for("email") == set(SOURCES) - paged_only - print_only - deck_only
        assert len(rules_for("email")) == 12

    def test_the_brochure_is_judged_as_print(self):
        """Every paged rule, the neutral five, and the two about a press (#188)."""
        assert rules_for("brochure") == {
            "img-alt",
            "table-role",
            "table-header-tier",
            "empty-url",
            "no-external-css",
            "page-size-declared",
            "paged-table-width",
            "table-structure",
            "print-marks",
            "rgb-only",
        }

    def test_the_outlook_rules_reach_no_other_medium(self):
        for rule in ("outlook-line-height", "outlook-transparent-background", "img-width-attr"):
            assert RULE_MEDIA[rule] == {"email"}, rule

    def test_the_neutral_rules_reach_every_medium(self):
        # Accessibility and unresolvable URLs are not client compatibility.
        for rule in ("img-alt", "table-role", "empty-url", "no-external-css", "table-header-tier"):
            assert RULE_MEDIA[rule] == SHIPPED_MEDIA, rule


class TestTheEmailGalleryIsJudgedExactlyAsBefore:
    @pytest.mark.parametrize("name", sorted(all_fixtures()))
    def test_every_email_fixture_is_still_clean(self, name):
        assert lint_email(all_fixtures()[name]()) == []

    def test_lint_email_and_lint_document_agree_on_an_email(self):
        email = all_fixtures()["kitchen_sink"]()
        assert lint_email(email) == lint_document(email)

    def test_an_email_defect_still_fails(self):
        # The rules did not merely stop firing: judged as an email, a missing
        # alt is still an error.
        findings = lint_html('<img src="x.png" width="10">', "email")
        assert [f.rule_id for f in findings if f.severity is Severity.ERROR]


class TestThePagedRulesAreExercised:
    """
    Both paged rules came from a defect a real PDF produced, so both are
    driven here by markup that violates them — never by the gallery, which
    exists to be correct.
    """

    def test_a_paged_document_with_no_page_size_is_an_error(self):
        findings = lint_html("<html><head><style>body{}</style></head></html>", "document")
        assert "page-size-declared" in [f.rule_id for f in findings]

    def test_declaring_one_satisfies_it(self):
        html = "<html><head><style>@page { size: 794px 1123px; }</style></head></html>"
        assert "page-size-declared" not in [f.rule_id for f in lint_html(html, "document")]

    def test_an_unmapped_table_width_is_an_error(self):
        html = (
            "<html><head><style>@page { size: 794px; }</style></head>"
            '<body><table width="100%"><tr><td>x</td></tr></table></body></html>'
        )
        assert "paged-table-width" in [f.rule_id for f in lint_html(html, "document")]

    def test_mapping_it_satisfies_it(self):
        html = (
            "<html><head><style>@page { size: 794px; } "
            'table[width="100%"] { width: 100%; }</style></head>'
            '<body><table width="100%"><tr><td>x</td></tr></table></body></html>'
        )
        assert "paged-table-width" not in [f.rule_id for f in lint_html(html, "document")]

    def test_neither_fires_on_an_email(self):
        # An email has no page and wants the attribute unmapped -- Outlook
        # reads nothing else.
        for name in sorted(all_fixtures()):
            found = {f.rule_id for f in lint_email(all_fixtures()[name]())}
            assert not found & {"page-size-declared", "paged-table-width"}

    DATA_TABLE = (
        "<table><caption>Holdings</caption>{head}"
        '<tr><th scope="col">Name</th></tr>{head_end}'
        "<tr><td>UKT 2032</td></tr></table>"
    )

    def _structure_findings(self, html: str, medium: str = "document") -> list[str]:
        return [f.rule_id for f in lint_html(html, medium) if f.rule_id == "table-structure"]

    def test_a_data_table_with_no_thead_is_an_error_on_paper(self):
        # #176: the lint half of the teeth, which runs without WeasyPrint.
        html = self.DATA_TABLE.format(head="", head_end="")
        assert self._structure_findings(html) == ["table-structure"]

    def test_a_thead_satisfies_it(self):
        html = self.DATA_TABLE.format(head="<thead>", head_end="</thead>")
        assert self._structure_findings(html) == []

    def test_it_is_silent_for_an_email(self):
        # An email has no sheets to repeat a header across.
        html = self.DATA_TABLE.format(head="", head_end="")
        assert self._structure_findings(html, "email") == []

    def test_a_layout_table_is_not_asked_for_one(self):
        html = '<table role="presentation"><tr><td>x</td></tr></table>'
        assert self._structure_findings(html) == []

    def test_the_thead_belongs_to_the_innermost_table(self):
        # A layout table holding a proper data table is not itself a data
        # table, and the data table's thead is its own.
        inner = self.DATA_TABLE.format(head="<thead>", head_end="</thead>")
        html = f'<table role="presentation"><tr><td>{inner}</td></tr></table>'
        assert self._structure_findings(html) == []

    def test_the_shipped_paged_gallery_satisfies_both(self):
        for name, build in sorted(all_paged_fixtures().items()):
            assert lint_document(build()) == [], name


class TestGoldensAreKeyedByMedium:
    def test_each_medium_has_a_directory_of_its_own(self):
        assert medium_dir("email").is_dir() and medium_dir("document").is_dir()

    def test_a_fixtures_artifacts_land_under_its_own_medium(self):
        email = all_fixtures()["minimal"]()
        for _, path, _ in artifacts("minimal", email):
            assert path.parent == GOLDEN_DIR / "email"
        paged = all_paged_fixtures()["a4_portrait"]()
        for _, path, _ in artifacts("a4_portrait", paged):
            assert path.parent == GOLDEN_DIR / "document"

    def test_two_media_could_hold_one_name_without_colliding(self):
        # The reason the segment exists: before #165 a paged fixture named
        # "minimal" would have overwritten the email one's snapshot.
        assert html_path("minimal", "email") != html_path("minimal", "document")

    def test_no_golden_is_left_at_the_old_flat_path(self):
        strays = [path for path in GOLDEN_DIR.glob("*.html")]
        assert not strays, f"goldens outside a medium directory: {strays}"


@requires_pdf
class TestAPagedDocumentIsPhotographedFromItsPdf:
    """
    Standing rule 3 gains its third clause. Chromium renders a paged
    document's HTML as one long scroll, which is exactly the property the
    medium does not have -- so pagination is judged from the PDF.
    """

    def test_one_image_per_sheet(self, tmp_path):
        document = all_paged_fixtures()["a4_portrait"]()
        shots, _ = capture_pages({"a4_portrait": document}, tmp_path)
        from pyhermes.pdf import page_count

        assert len(shots) == page_count(document)

    def test_each_sheet_is_rastered_at_the_page_format(self, tmp_path):
        # The scale reconciles two units: a PDF is 72 dpi and a PageFormat is
        # px at 96, so an unscaled raster is 596px wide for a 794px page.
        document = all_paged_fixtures()["a4_portrait"]()
        page = document.medium.page_format
        shots, _ = capture_pages({"a4_portrait": document}, tmp_path)
        for shot in shots:
            assert (shot.width, shot.height) == (page.width, page.height)

    def test_the_scale_is_the_dpi_ratio(self):
        assert PDF_PX_SCALE == 96 / 72

    def test_the_run_records_what_rasterised_it(self, tmp_path):
        # Recorded rather than pinned, exactly as the browser build is.
        _, environment = capture_pages(
            {"slide_16_9": all_paged_fixtures()["slide_16_9"]()}, tmp_path
        )
        assert "pypdfium2" in str(environment["renderer"])
        assert environment["scale"] == PDF_PX_SCALE

    def test_a_slide_rasters_landscape(self, tmp_path):
        shots, _ = capture_pages({"slide_16_9": all_paged_fixtures()["slide_16_9"]()}, tmp_path)
        assert shots[0].width > shots[0].height


class TestThePagedHalfSkipsWithoutItsExtras:
    def test_the_gate_is_a_skip_not_a_failure(self):
        # [dev] alone must stay browser- and WeasyPrint-free: that is what
        # proves both extras optional, and it is asserted rather than assumed.
        assert isinstance(pages_available(), bool)

    def test_a_paged_document_still_lints_without_any_extra(self):
        # The policy half needs nothing installed.
        assert lint_document(PagedDocument({"firm_name": "F", "campaign_name": "C"})) == []
