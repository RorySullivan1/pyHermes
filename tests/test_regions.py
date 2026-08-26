"""
The header region — extraction, model, rendering, and the MinimalHeader variant.

Covers epic #38: ``email > header | body``. The byte-identity bar the epic
promises lives in ``tests/test_goldens.py``; this module covers the structure
that bar is silent about.
"""

import pytest

from svc.builder.engine import TemplateEngine

TEMPLATE_DIR = TemplateEngine().template_dir


def _template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


class TestTheHeaderLeftTheSkeleton:
    """#33: the pure template split — the markup moved, the output did not."""

    def test_the_region_template_ships_in_the_package(self):
        assert (TEMPLATE_DIR / "regions" / "header.html").is_file()

    def test_base_html_keeps_only_the_hole(self):
        base = _template("base.html")
        assert "{{ header_html }}" in base
        for moved in ("HEADER: Disclaimer bar", "HEADER: Background image", "v:rect"):
            assert moved not in base, f"base.html still carries header markup: {moved!r}"

    def test_the_fragile_outlook_markup_moved_intact(self):
        header = _template("regions/header.html")
        for vml in ("<v:rect", "<v:fill", "<v:textbox", "</v:textbox>", "</v:rect>"):
            assert vml in header

    @pytest.mark.parametrize(
        "variable",
        [
            "header_disclaimer",
            "firm_name",
            "campaign_name",
            "date_range",
            "issue_label",
        ],
    )
    def test_the_skeleton_no_longer_names_a_header_only_variable(self, variable):
        """
        ``firm_name`` is the exception that proves the rule — the footer's
        copyright line still names it, which is why facts stay email-level.
        """
        base = _template("base.html")
        header = _template("regions/header.html")
        assert variable in header
        if variable != "firm_name":
            assert variable not in base

    def test_the_footer_deliberately_stayed(self):
        """Epic non-goal: the footer is the same kind of candidate, later."""
        base = _template("base.html")
        assert "FOOTER PART 1" in base and "FOOTER PART 2" in base
