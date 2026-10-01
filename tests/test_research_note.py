"""
The research note (#312): every long-form piece at once, in an email and on paper.

The two fixtures share their sections, so each test reads one medium's
apparatus against the other's: what a cross-piece regression would break.
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from pyhermes.pdf import available, render_pdf
from qa.fixtures import _research, all_fixtures, all_paged_fixtures

requires_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

CITATION = re.compile(r"\((?:[A-Z][\w.-]*(?:,? (?:and )?[A-Z][\w.-]*)*(?: et al\.)? \d{4};? ?)+\)")


@pytest.fixture(scope="module")
def email():
    return all_fixtures()["research_note"]()


@pytest.fixture(scope="module")
def paper():
    return all_paged_fixtures()["a4_research_note"]()


def apparatus(text: str) -> dict[str, list[str]]:
    """What a reader navigates by, read off one text part."""
    body = text[text.index("Summary\n-------") :]
    return {
        "exhibits": re.findall(r"^Exhibit (?:[A-Z]\.)?\d+ · .+$", body, re.M),
        "appendices": re.findall(r"^Appendix [A-Z]: .+$", body, re.M),
        "citations": CITATION.findall(" ".join(body.split())),
    }


class TestTheMediaAgree:
    def test_every_exhibit_appendix_and_citation_reads_the_same(self, email, paper):
        assert apparatus(email.text()) == apparatus(paper.text())
        assert len(apparatus(email.text())["citations"]) == 8

    def test_the_exhibits_are_the_ones_the_note_promises(self, email):
        assert apparatus(email.text())["exhibits"] == _research.EXHIBITS
        assert apparatus(email.text())["appendices"] == [
            "Appendix A: Data sources",
            "Appendix B: Robustness",
        ]

    def test_both_lists_of_exhibits_agree_with_the_exhibits(self, email, paper):
        email.validate()
        paper.validate()
        listing = next(c for c in email._components() if getattr(c, "of", "") == "exhibits")
        assert [heading for heading, _ in listing.entries] == _research.EXHIBITS
        assert [heading for heading, _ in paper._listing("exhibits", "Exhibit")] == (
            _research.EXHIBITS
        )

    def test_the_markup_numbers_them_in_both(self, email, paper):
        for document in (email, paper):
            html = document.render()
            for anchor in ("exhibit-1", "exhibit-2", "exhibit-a-1", "exhibit-b-1"):
                assert f'id="{anchor}"' in html
            assert html.count('class="citation"') == 8


@requires_pdf
class TestOnPaper:
    @pytest.fixture(scope="class")
    def pages(self, paper):
        import pypdfium2

        pdf = pypdfium2.PdfDocument(render_pdf(paper))
        return [
            [line.strip() for line in sheet.get_textpage().get_text_range().splitlines()]
            for sheet in pdf
        ]

    @pytest.mark.parametrize("heading", ["Contents", "Tables and Figures"])
    def test_every_listed_page_is_the_sheet_it_names(self, pages, heading):
        listed = next(lines for lines in pages if heading in lines)
        start = listed.index(heading) + 1
        entries = [re.fullmatch(r"(.+?)\s*\.{3,}\s*(\d+)", line) for line in listed[start:]]
        cited = [(m.group(1), int(m.group(2))) for m in entries if m]
        assert cited
        for title, page in cited:
            on = next(n for n, lines in enumerate(pages, 1) if title in lines)
            assert page == on, f"{title!r} listed at p. {page}, printed on p. {on}"

    def test_each_appendix_sheet_is_headed_by_its_letter(self, pages):
        sheet = next(lines for lines in pages if "Appendix A: Data sources" in lines)
        assert sheet[0] == "Appendix A: Data sources"
