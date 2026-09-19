"""
The paged medium: the first render that is not an email (#162).

Three claims worth a test. The paged skeleton carries none of the email's
client accommodations; the medium's page reaches both ``@page`` and the body
table; and the same section tree renders onto two different pages with
nothing but the dimensions between them.
"""

from __future__ import annotations

import pytest

from qa.fixtures import _paged, all_paged_fixtures
from qa.goldens import artifacts, check_fixture
from svc.builder.document import Document
from svc.builder.engine import TemplateEngine
from svc.builder.medium import DEFAULT_MEDIUM
from svc.builder.models import EmailMetadata
from svc.builder.sizing import A4_PORTRAIT, PAGE_FORMATS, SLIDE_16_9
from svc.document import PAGED_MEDIUM, paged_medium
from svc.email import EMAIL_MEDIUM

PAGED_NAMES = sorted(all_paged_fixtures())


@pytest.fixture(params=PAGED_NAMES)
def paged_name(request: pytest.FixtureRequest) -> str:
    return str(request.param)


class TestEveryPagedFixtureMatchesItsGolden:
    def test_every_artifact_is_unchanged(self, paged_name, request):
        document = all_paged_fixtures()[paged_name]()
        if request.config.getoption("--update-goldens"):
            from qa.goldens import write_fixture

            written = write_fixture(paged_name, document)
            pytest.skip(f"regenerated {', '.join(p.name for p in written)}")
        mismatches = check_fixture(paged_name, document)
        assert not mismatches, "\n\n".join(str(m) for m in mismatches)

    def test_every_golden_is_checked_in(self, paged_name):
        document = all_paged_fixtures()[paged_name]()
        for _, path, _ in artifacts(paged_name, document):
            assert path.is_file(), f"{path} is missing; run `pytest --update-goldens`."


class TestThePagedSkeletonIsNotAnEmail:
    """
    What the skeleton leaves out is the point. Every accommodation below
    exists for a client that is not rendering this document.
    """

    @pytest.fixture()
    def bare_skeleton(self) -> str:
        # A document with no sections, so what is left is the skeleton and
        # nothing else. Asserting over a *populated* render would be a claim
        # about the shared component templates, which is a different one --
        # see TestTheSharedMarkupStillCarriesEmailBaggage.
        return Document(_paged.facts(), medium=PAGED_MEDIUM).render()

    @pytest.fixture()
    def email_html(self) -> str:
        from qa.fixtures import all_fixtures

        return all_fixtures()["kitchen_sink"]().render()

    @pytest.mark.parametrize("accommodation", ["[if mso]", "v:rect", "v:fill", "@media"])
    def test_the_paged_skeleton_carries_no_client_accommodation(self, bare_skeleton, accommodation):
        assert accommodation not in bare_skeleton

    @pytest.mark.parametrize("accommodation", ["[if mso]", "v:rect", "v:fill", "@media"])
    def test_the_email_skeleton_still_carries_all_of_them(self, email_html, accommodation):
        # The mirror. Without it, deleting them from base.html too would
        # leave this file green while shipping a broken email.
        assert accommodation in email_html

    def test_the_paged_skeleton_has_no_preheader(self, bare_skeleton):
        # Inbox-preview text has no reader on a printed page.
        assert "display:none" not in bare_skeleton

    def test_a_layout_table_declares_itself(self, bare_skeleton):
        # Standing rule 8, on the new skeleton.
        assert '<table class="document-container" role="presentation"' in bare_skeleton


class TestTheSharedMarkupStillCarriesEmailBaggage:
    """
    The measurement #162 asked for rather than a defect to suppress.

    ``columns.html`` opens an ``[if mso]`` block, so a paged render carries
    Outlook conditionals it has no use for. **This is waste, not breakage**:
    a downlevel-hidden conditional is an ordinary HTML comment to every
    parser but Word's, so WeasyPrint and every browser drop it — and bytes
    do not count against anything here the way they do against Gmail's
    102 KB.

    It therefore does **not** meet #160's bar for forking a template, which
    asks what the shared markup gets *wrong* for this medium. Recorded here
    so the day it does become a fork, the diff has a number to beat.
    """

    def test_the_count_is_known_and_comes_from_one_template(self):
        html = all_paged_fixtures()["a4_portrait"]().render()
        assert html.count("<!--[if mso]>") == 3, (
            "the paged render's Outlook baggage moved; if a fork landed, say "
            "in the PR what the shared template got wrong for this medium"
        )

    def test_it_is_inert_rather_than_rendered(self):
        # The reason it is waste and not breakage: every one of them is
        # inside a well-formed comment, so a non-Word parser skips it whole.
        html = all_paged_fixtures()["a4_portrait"]().render()
        assert html.count("<!--[if mso]>") == html.count("<![endif]-->")


class TestThePageReachesTheRender:
    def test_the_page_rules_the_css_and_the_table(self):
        html = all_paged_fixtures()["a4_portrait"]().render()
        assert f"size: {A4_PORTRAIT.width}px {A4_PORTRAIT.height}px;" in html
        assert f'width="{A4_PORTRAIT.width}"' in html

    def test_a_slide_is_the_same_medium_at_another_page(self):
        slide = all_paged_fixtures()["slide_16_9"]()
        assert slide.medium.name == PAGED_MEDIUM.name
        assert slide.medium.page_format is SLIDE_16_9
        assert slide.medium.page_format.orientation == "landscape"

    def test_the_two_pages_differ_only_in_their_dimensions(self):
        """
        The A/B the pair exists for: same copy, one ``PageFormat`` apart.

        Every differing line must be a dimension. A difference anywhere else
        would mean the page had reached something that is not geometry --
        a colour, a face, a piece of copy -- which is the failure the axes
        are separate to prevent.
        """
        import difflib

        a4 = all_paged_fixtures()["a4_portrait"]().render().splitlines()
        slide = all_paged_fixtures()["slide_16_9"]().render().splitlines()
        changed = [
            line
            for line in difflib.unified_diff(a4, slide, lineterm="", n=0)
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
        ]
        assert changed, "the two pages rendered identically; the page reached nothing"
        for line in changed:
            assert "width" in line or "size:" in line, (
                f"a non-dimension moved with the page: {line.strip()[:120]}"
            )

    def test_the_page_reaches_the_computed_column_widths(self):
        # The composition proved end to end: a split's column width is
        # derived from frame.inner, which is the medium's width less the
        # density's padding. Neither owner alone can produce this number.
        a4 = all_paged_fixtures()["a4_portrait"]().render()
        inner = A4_PORTRAIT.width - 2 * 32
        assert f'width="{inner}"' in a4

    def test_the_text_projection_is_the_same_on_either_page(self):
        # A page is a markup concern; the second projection cannot see it.
        assert (
            all_paged_fixtures()["a4_portrait"]().text()
            == all_paged_fixtures()["slide_16_9"]().text()
        )


class TestTheMediumIsWired:
    def test_the_paged_medium_is_paged_and_not_an_email(self):
        assert PAGED_MEDIUM.paged and not PAGED_MEDIUM.email
        assert EMAIL_MEDIUM.email and not EMAIL_MEDIUM.paged

    def test_it_runs_no_gmail_constraint(self):
        # Nothing clips a PDF at 102 KB, so the check is not merely unused
        # here -- it would be wrong.
        assert PAGED_MEDIUM.constraints == ()

    def test_its_skeleton_resolves_through_the_document_overlay(self):
        # The fork mechanism #160 shipped, doing the job it exists for: the
        # medium names "base.html" and gets its own.
        engine = TemplateEngine(search_path=PAGED_MEDIUM.template_search_path)
        assert PAGED_MEDIUM.skeleton == EMAIL_MEDIUM.skeleton == "base.html"
        paged = engine.render(
            PAGED_MEDIUM.skeleton, {"language": "en", "campaign_name": "x", "sections_html": ""}
        )
        assert "@page" in paged
        # ...and the same name, without the overlay, is still the email's.
        # The context comes from to_dict() so the three axes stay off it and
        # the engine's own floor supplies them, as in a real render.
        email_ctx = EmailMetadata(**_paged.facts(), email_subject="s").to_dict()
        assert "@page" not in TemplateEngine().render(
            EMAIL_MEDIUM.skeleton,
            {
                **email_ctx,
                "sections_html": "",
                "header_bar_html": "",
                "banner_html": "",
                "footer_html": "",
            },
        )

    def test_a_document_with_no_medium_gets_plain_html(self):
        assert Document({"firm_name": "F", "campaign_name": "C"}).medium is DEFAULT_MEDIUM

    def test_every_shipped_page_is_in_the_registry(self):
        assert set(PAGE_FORMATS.values()) >= {A4_PORTRAIT, SLIDE_16_9}
        assert paged_medium(PAGE_FORMATS["letter_portrait"]).page_format.orientation == "portrait"


class TestWhatTheEmailLintMakesOfAPagedDocument:
    """
    The measurement #162 asked for, and it is narrower than expected.

    The prediction was "expect some lint findings on the paged render". The
    reality: a realistic paged document lints **clean** against all ten email
    rules. The shared component markup already satisfies them, and the
    Outlook-only rules are suppressed inside the conditional comments they
    live in.

    Exactly one rule misfires, and only past a threshold nothing enforces
    here: ``size-budget`` is Gmail's 102 KB, and a PDF is not clipped at any
    size. That is the whole of #165's problem, stated as a number.
    """

    def test_a_realistic_paged_document_lints_clean(self):
        from qa.lint import lint_email

        assert lint_email(all_paged_fixtures()["a4_portrait"]()) == []

    def test_only_the_gmail_size_rule_misfires_and_only_past_its_threshold(self):
        from qa.lint import lint_email
        from svc.builder import FullWidth, TextBlock

        oversized = Document(_paged.facts(), medium=PAGED_MEDIUM)
        oversized.add_section(FullWidth(content=TextBlock("<p>" + "x" * 110 * 1024 + "</p>")))
        assert [f.rule_id for f in lint_email(oversized)] == ["size-budget"]
