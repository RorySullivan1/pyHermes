"""
An email's lines carry no indentation (#474): the medium strips it before the size check.

Line indentation was 9% of ``kitchen_sink`` and 23% of ``minimal``, spent against Gmail's
102 KB clip on bytes no reader sees. The email medium's one finisher removes it; every
line break stays, so whitespace that rendered as a space still does, and a ``pre`` or a
``textarea`` keeps its own.
"""

from __future__ import annotations

import warnings
from dataclasses import replace

import pytest

from octavo.builder import FullWidth, TextBlock
from octavo.builder.email import Email
from octavo.builder.exceptions import SizeWarning
from octavo.builder.medium import DEFAULT_MEDIUM, SHIPPED_MEDIA
from octavo.config import config_override
from octavo.email import EMAIL_MEDIUM, strip_indentation
from qa.fixtures import all_fixtures
from qa.screenshots import VIEWPORTS, _launch, _load_playwright, available, inline_cid_images

FACTS = {"email_subject": "S", "firm_name": "F", "campaign_name": "C"}
FIXTURE_NAMES = sorted(all_fixtures())


def unfinished(email: Email) -> Email:
    """The same email on a medium with no finisher: the markup as the templates wrote it."""
    raw = Email(
        email.metadata,
        header=email.header,
        banner=email.banner,
        footer=email.footer,
        medium=replace(EMAIL_MEDIUM, finishers=()),
    )
    for section in email._sections:
        raw.add_section(section)
    return raw


class TestTheTransform:
    def test_it_strips_each_lines_edges_and_its_blank_lines(self):
        assert strip_indentation("  <p>a</p>  \n\n\t<b>z</b>\t\n") == "<p>a</p>\n<b>z</b>\n"

    def test_every_line_break_stays(self):
        html = "<td>\n    <span>a</span>\n    <span>b</span>\n</td>"
        assert strip_indentation(html).count("\n") == html.count("\n")

    @pytest.mark.parametrize("tag", ["pre", "PRE", 'pre class="code"', "textarea"])
    def test_a_whitespace_block_passes_through_whole(self, tag):
        name = tag.split()[0]
        block = f"<{tag}>\n    def f():\n\n        return 1  \n</{name}>"
        assert strip_indentation(f"  <div>\n{block}\n  </div>") == f"<div>\n{block}\n</div>"

    def test_it_is_idempotent(self):
        html = all_fixtures()["kitchen_sink"]().render()
        assert strip_indentation(html) == html


class TestTheEmailMedium:
    def test_it_is_the_only_shipped_medium_that_finishes(self):
        from octavo.brochure.medium import BROCHURE_MEDIUM
        from octavo.deck.medium import DECK_MEDIUM
        from octavo.document.medium import PAGED_MEDIUM

        shipped = (DEFAULT_MEDIUM, EMAIL_MEDIUM, PAGED_MEDIUM, BROCHURE_MEDIUM, DECK_MEDIUM)
        media = {m.name: m for m in shipped}
        assert set(media) == set(SHIPPED_MEDIA)
        assert {name: m.finishers for name, m in media.items()} == {
            "html": (),
            "email": (strip_indentation,),
            "document": (),
            "brochure": (),
            "deck": (),
        }

    @pytest.mark.parametrize("name", FIXTURE_NAMES)
    def test_no_rendered_line_is_indented_or_blank(self, name):
        lines = all_fixtures()[name]().render().split("\n")[:-1]  # the file's final newline
        assert not [n for n, line in enumerate(lines, 1) if not line or line != line.strip(" \t")]

    @pytest.mark.parametrize("name", FIXTURE_NAMES)
    def test_the_finished_email_is_the_template_markup_stripped(self, name):
        email = all_fixtures()[name]()
        assert email.render() == strip_indentation(unfinished(email).render())

    def test_a_callers_pre_keeps_its_whitespace(self):
        code = "<pre>\n    x = 1\n\n    y = 2\n</pre>"
        email = Email(FACTS).add_section(FullWidth(TextBlock(f"<p>Code:</p>{code}")))
        assert code in email.render()

    def test_the_size_check_measures_the_finished_markup(self):
        # kitchen_sink is about 82.5 KB finished and 88.8 KB as the templates wrote it.
        email = all_fixtures()["kitchen_sink"]()
        with config_override(size_warn_kb=86), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            email.render()
            assert not [w for w in caught if issubclass(w.category, SizeWarning)]
            unfinished(email).render()
            assert [w for w in caught if issubclass(w.category, SizeWarning)]

    def test_each_section_of_the_size_report_is_finished_too(self):
        email = all_fixtures()["kitchen_sink"]()
        html = email.render()
        assert all(markup in html for _, markup in email.rendered_sections())


@pytest.mark.skipif(not available(), reason='no browser; screenshots are the optional "[qa]" extra')
class TestNoPixelMoves:
    """Measured across the gallery when this shipped: 48 of 48 screenshots identical."""

    @pytest.mark.parametrize("name", ["kitchen_sink", "minimal", "glance_layout"])
    def test_finished_and_unfinished_render_identically(self, name):
        email = all_fixtures()[name]()
        pages = [inline_cid_images(e.render(), email) for e in (unfinished(email), email)]
        with _load_playwright()() as playwright:
            browser = _launch(playwright)
            for width, height in VIEWPORTS.values():
                shots = []
                for html in pages:
                    page = browser.new_page(viewport={"width": width, "height": height})
                    page.route("**/*", lambda route: route.abort())
                    page.set_content(html)
                    shots.append(page.screenshot(full_page=True))
                    page.close()
                assert shots[0] == shots[1], f"{name} moved at {width}px"
            browser.close()
