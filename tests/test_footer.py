"""
The footer region — extraction, model, rendering, and the MinimalFooter variant.

Covers epic #55: ``email > header | body | footer``. The byte-identity bar the
epic promises lives in ``tests/test_goldens.py``; this module covers the
structure that bar is silent about, and the compliance floor no golden can
express (a *variant* that dropped the unsubscribe link would have its own
golden, and the golden would happily pin the omission).
"""

import pytest

from svc.builder.engine import TemplateEngine

TEMPLATE_DIR = TemplateEngine().template_dir


def _template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


class TestTheFooterLeftTheSkeleton:
    """#63: the pure template split — the markup moved, the output did not."""

    @pytest.mark.parametrize("name", ["footer-contact.html", "footer-legal.html"])
    def test_the_region_templates_ship_in_the_package(self, name):
        assert (TEMPLATE_DIR / "regions" / name).is_file()

    def test_base_html_keeps_only_the_holes(self):
        base = _template("base.html")
        assert "{{ footer_contact_html }}" in base
        assert "{{ footer_legal_html }}" in base
        for moved in ("FOOTER PART 1", "FOOTER PART 2", "v:roundrect", "footer_disclaimer"):
            assert moved not in base, f"base.html still carries footer markup: {moved!r}"

    def test_the_split_is_where_the_dom_splits(self):
        """
        The reason there are two templates rather than one: the contact card
        is a ``<tr>`` inside the body table and the legal block is a sibling
        table below it. The tags the skeleton keeps between the two holes are
        the ones a single fragment would have had to close.
        """
        base = _template("base.html")
        between = base.split("{{ footer_contact_html }}")[1].split("{{ footer_legal_html }}")[0]
        assert "</table>" in between and "/Main container" in between

        contact = _template("regions/footer-contact.html")
        legal = _template("regions/footer-legal.html")
        assert contact.lstrip().startswith("<!--") and "<tr>" in contact
        assert "<table" in legal and "<tr>" not in legal.split("<table", 1)[0]

    def test_the_fragile_outlook_markup_moved_intact(self):
        """
        The dual emission — ``v:roundrect`` for Outlook, an anchor for
        everyone else — is the footer's equivalent of the header's VML hero,
        and the most diff-sensitive markup in the move.
        """
        contact = _template("regions/footer-contact.html")
        for vml in ("<!--[if mso]>", "<v:roundrect", "</v:roundrect>", "<![endif]-->"):
            assert vml in contact
        assert "<!--[if !mso]><!-->" in contact and "<!--<![endif]-->" in contact

    def test_no_vml_leaked_into_the_legal_block(self):
        assert "v:" not in _template("regions/footer-legal.html")

    def test_the_escaping_split_survived_the_move(self):
        """
        ``footer_disclaimer`` is an HTML field and stays raw; every other
        footer variable keeps its ``escape_html`` filter. A move that
        silently escaped the disclaimer would render callers' markup as text.
        """
        legal = _template("regions/footer-legal.html")
        assert "{{footer_disclaimer}}" in legal
        contact = _template("regions/footer-contact.html")
        for escaped in (
            "contact_heading",
            "contact_description",
            "contact_url",
            "contact_cta_label",
        ):
            assert f"{{{{ {escaped} | escape_html }}}}" in contact
        for escaped in ("current_year", "firm_name", "unsubscribe_label", "unsubscribe_url"):
            assert f"{{{{ {escaped} | escape_html }}}}" in legal
