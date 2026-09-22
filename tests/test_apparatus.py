"""
The document apparatus (#171): anchors, exhibit numbers, footnotes, contents,
cross-references. Everything here is computed in Python before render, so each
test reads one projection against the other rather than trusting either alone.
"""

from __future__ import annotations

import pytest

from svc.builder import FullWidth, TextBlock, ThreeColumn, TwoColumn, ValidationError
from svc.builder.apparatus import slugify
from svc.builder.email import Email
from svc.document import Page

FACTS = {"email_subject": "Subject", "firm_name": "Hermes", "campaign_name": "Review"}


def email(*sections) -> Email:
    built = Email(FACTS)
    for section in sections:
        built.add_section(section)
    return built


def prose(copy: str = "<p>Copy.</p>") -> TextBlock:
    return TextBlock(copy)


class TestSectionAnchors:
    """#183, first commit: every titled section's heading is a destination."""

    @pytest.mark.parametrize(
        ("title", "slug"),
        [
            ("Factor Returns", "factor-returns"),
            ("  Q3: What the curve priced?  ", "q3-what-the-curve-priced"),
            ("Café & Crème", "cafe-creme"),
            ("2026 outlook", "section-2026-outlook"),
            ("★★★", "section"),
        ],
    )
    def test_a_title_slugs_to_a_valid_id(self, title, slug):
        assert slugify(title) == slug

    def test_the_heading_carries_the_slug(self):
        html = email(FullWidth(title="Factor Returns", content=prose())).render()
        assert '<h2 id="factor-returns" ' in html

    def test_a_split_heading_carries_one_too(self):
        html = email(TwoColumn(title="Positioning", left=prose())).render()
        assert '<h2 id="positioning" ' in html

    def test_the_caller_may_override_it(self):
        html = email(FullWidth(title="Factor Returns", anchor="factors", content=prose()))
        assert '<h2 id="factors" ' in html.render()

    def test_an_untitled_section_claims_nothing(self):
        section = FullWidth(anchor="ignored", content=prose())
        assert section.resolved_anchor() == ""
        assert "<h2" not in email(section).render()

    @pytest.mark.parametrize("bad", ["1st", "has space", "a#b", "-lead", 'x"y'])
    def test_a_malformed_override_raises_at_construction(self, bad):
        with pytest.raises(ValidationError, match="container.anchor"):
            FullWidth(title="T", anchor=bad, content=prose())

    def test_two_sections_with_one_slug_raise_when_the_second_is_added(self):
        document = email(FullWidth(title="Factor Returns", content=prose()))
        with pytest.raises(ValidationError, match="'factor-returns' is claimed twice"):
            document.add_section(ThreeColumn(title="Factor returns!", left=prose()))

    def test_the_rejected_section_is_not_kept(self):
        document = email(FullWidth(title="Outlook", content=prose()))
        with pytest.raises(ValidationError):
            document.add_section(FullWidth(title="Outlook", content=prose()))
        assert len(document._sections) == 1
        document.add_section(FullWidth(title="Outlook", anchor="outlook-2", content=prose()))

    def test_a_pages_sections_are_checked_as_the_documents_own(self):
        document = email(FullWidth(title="Method", content=prose()))
        page = Page([FullWidth(title="Method", content=prose())], title="Appendix")
        with pytest.raises(ValidationError, match="'method'"):
            document.add_section(page)

    def test_a_pages_own_title_is_never_rendered_so_claims_no_anchor(self):
        page = Page([FullWidth(content=prose())], title="Appendix")
        assert page.resolved_anchor() == ""
        email(FullWidth(title="Appendix", content=prose()), page)
