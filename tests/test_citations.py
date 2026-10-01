"""
Citations and the bibliography (#310): a record cited by key, resolved by the walk.

Every label is computed once, so each test reads the markup and the text part
against the same expected spelling.
"""

from __future__ import annotations

import re

import pytest

from pyhermes.builder import (
    Bibliography,
    ChartBlock,
    DataTable,
    FullWidth,
    NumberedList,
    Reference,
    Stack,
    TextBlock,
    ValidationError,
)
from pyhermes.builder.apparatus import CITATION, cited_keys, split_markers
from pyhermes.builder.email import Email
from pyhermes.builder.models import NumberedItem, TableRow
from pyhermes.config import Config
from pyhermes.document import PagedDocument

FACTS = {"email_subject": "Subject", "firm_name": "Hermes", "campaign_name": "Review"}

FAMA = Reference(
    "fama1993",
    ["Fama, Eugene F.", "French, Kenneth R."],
    1993,
    "Common risk factors in the returns on stocks and bonds",
    "Journal of Financial Economics",
    doi="10.1016/0304-405X(93)90023-5",
)
CARHART = Reference(
    "carhart1997", ["Carhart, Mark M."], 1997, "On persistence in mutual fund performance"
)
JT = Reference(
    "jt1993",
    ["Jegadeesh, Narasimhan", "Titman, Sheridan", "Moskowitz, Tobias J."],
    1993,
    "Returns to buying winners and selling losers",
    "The Journal of Finance",
    url="https://example.com/jt",
)
UNCITED = Reference("asness2013", ["Asness, Clifford S."], 2013, "Value and momentum everywhere")

PROSE = (
    "<p>Size and value [@fama1993] and momentum [@jt1993; @carhart1997] "
    "explain returns; see again [@fama1993].</p>"
)


def note(style: str, prose: str = PROSE, document=None) -> Email:
    built = document if document is not None else Email(FACTS)
    built.add_section(FullWidth(title="Body", content=TextBlock(prose)))
    built.add_section(
        FullWidth(
            title="References",
            content=Bibliography([JT, UNCITED, CARHART, FAMA], style=style),
        )
    )
    return built


def body_text(document) -> str:
    text = document.text()
    return text[text.index("Body\n----") : text.index("References\n----")]


def references_text(document) -> str:
    text = document.text()
    return text[text.index("References\n----") :].split("\n\n\n")[0]


class TestTheMarker:
    def test_it_names_one_key_or_several(self):
        assert cited_keys("x [@a] y [@b; @c-1]") == ["a", "b", "c-1"]

    @pytest.mark.parametrize("copy", ["[@]", "[@ a]", "[@a;b]", "@a", "[^1]"])
    def test_anything_else_is_copy(self, copy):
        assert not CITATION.search(copy)

    def test_copy_without_one_is_one_run_as_before(self):
        assert split_markers("Plain copy.", []) == [
            {
                "text": "Plain copy.",
                "note": 0,
                "note_text": "",
                "cites": [],
                "citing": split_markers("", [])[0]["citing"],
            }
        ]


class TestAuthorYear:
    def test_the_markup_links_each_citation_to_its_entry(self):
        html = note("author-year").render()
        cites = re.findall(r'<a href="#(ref-[\w-]+)" class="citation"[^>]*>([^<]+)</a>', html)
        assert cites == [
            ("ref-fama1993", "Fama and French 1993"),
            ("ref-jt1993", "Jegadeesh et al. 1993"),
            ("ref-carhart1997", "Carhart 1997"),
            ("ref-fama1993", "Fama and French 1993"),
        ]
        for anchor, _ in cites:
            assert f'<p id="{anchor}"' in html

    def test_the_text_spells_them_the_same(self):
        assert body_text(note("author-year")) == (
            "Body\n----\n\nSize and value (Fama and French 1993) and momentum (Jegadeesh et al. "
            "1993;\nCarhart 1997) explain returns; see again (Fama and French 1993).\n\n\n"
        )

    def test_entries_sort_by_first_author_then_year(self):
        assert references_text(note("author-year")) == (
            "References\n----------\n\n"
            "Asness, Clifford S. 2013. Value and momentum everywhere.\n"
            "Carhart, Mark M. 1997. On persistence in mutual fund performance.\n"
            "Fama, Eugene F., and Kenneth R. French. 1993. Common risk factors in the\n"
            "    returns on stocks and bonds. Journal of Financial Economics.\n"
            "    https://doi.org/10.1016/0304-405X(93)90023-5\n"
            "Jegadeesh, Narasimhan, Sheridan Titman, and Tobias J. Moskowitz. 1993. Returns\n"
            "    to buying winners and selling losers. The Journal of Finance.\n"
            "    https://example.com/jt"
        )

    def test_a_shared_author_and_year_is_lettered(self):
        second = Reference(
            "fama1993b", ["Fama, Eugene F.", "French, Kenneth R."], 1993, "A second paper"
        )
        document = Email(FACTS)
        document.add_section(FullWidth(content=TextBlock("<p>[@fama1993; @fama1993b]</p>")))
        document.add_section(FullWidth(content=Bibliography([FAMA, second])))
        assert "(Fama and French 1993b; Fama and French 1993a)" in document.text()
        assert "French. 1993a. A second paper." in document.text()

    def test_et_al_follows_the_house_limit(self):
        document = note("author-year", document=Email(FACTS, config=Config(citation_authors=3)))
        assert "(Jegadeesh, Titman and Moskowitz 1993; Carhart 1997)" in (
            body_text(document).replace("\n", " ")
        )


class TestNumeric:
    def test_numbers_follow_first_citation_and_reuse(self):
        assert body_text(note("numeric")) == (
            "Body\n----\n\nSize and value [1] and momentum [2, 3] explain returns; see "
            "again [1].\n\n\n"
        )

    def test_the_markup_numbers_them_identically(self):
        html = note("numeric").render()
        numbers = re.findall(r'class="citation"[^>]*>(\d+)</a>', html)
        assert numbers == ["1", "2", "3", "1"]

    def test_entries_list_in_number_order_the_uncited_last(self):
        assert references_text(note("numeric")) == (
            "References\n----------\n\n"
            "[1] Fama, Eugene F., and Kenneth R. French. 1993. Common risk factors in the\n"
            "    returns on stocks and bonds. Journal of Financial Economics.\n"
            "    https://doi.org/10.1016/0304-405X(93)90023-5\n"
            "[2] Jegadeesh, Narasimhan, Sheridan Titman, and Tobias J. Moskowitz. 1993.\n"
            "    Returns to buying winners and selling losers. The Journal of Finance.\n"
            "    https://example.com/jt\n"
            "[3] Carhart, Mark M. 1997. On persistence in mutual fund performance.\n"
            "[4] Asness, Clifford S. 2013. Value and momentum everywhere."
        )

    def test_a_label_wider_than_one_digit_keeps_the_hang_aligned(self):
        references = [
            Reference(f"r{n}", [f"Author{n}, A."], 2000 + n, f"Paper {n}") for n in range(10)
        ]
        document = Email(FACTS)
        document.add_section(FullWidth(content=Bibliography(references, style="numeric")))
        lines = document.text().splitlines()
        assert "[1]  Author0, A. 2000. Paper 0." in lines
        assert "[10] Author9, A. 2009. Paper 9." in lines


class TestEveryFieldThatTakesAFootnoteTakesACitation:
    @pytest.mark.parametrize(
        "component",
        [
            DataTable(
                ["Factor [@fama1993]", "1M"],
                [TableRow(cells=["Value [@fama1993]", "1.8"])],
                caption="Returns [@fama1993]",
                source="Source [@fama1993]",
                label="Exhibit",
            ),
            ChartBlock(
                "https://example.com/c.png",
                "Chart",
                source="After [@fama1993]",
                caption="Curve [@fama1993]",
            ),
            NumberedList([NumberedItem("1", "Item", "<p>Body [@fama1993].</p>")]),
            Stack([TextBlock("<p>Inside a stack [@fama1993].</p>")]),
        ],
    )
    def test_it_resolves_in_both_projections(self, component):
        document = Email(FACTS)
        document.add_section(FullWidth(content=component))
        document.add_section(FullWidth(content=Bibliography([FAMA])))
        assert "[@" not in document.render()
        assert "[@" not in document.text()
        assert "(Fama and French 1993)" in document.text()

    def test_the_list_of_exhibits_leaves_it_out(self):
        table = DataTable(
            ["A"], [TableRow(cells=["1"])], caption="Returns [@fama1993]", label="Exhibit"
        )
        assert table.listed() == "Returns"


class TestRefusals:
    def test_an_unknown_key_is_named_by_validate(self):
        document = note("author-year", prose="<p>Cited [@nobody2020].</p>")
        with pytest.raises(ValidationError, match=r"\[@nobody2020\]"):
            document.validate()

    def test_a_citation_without_a_bibliography_is_refused(self):
        document = Email(FACTS)
        document.add_section(FullWidth(content=TextBlock("<p>[@fama1993]</p>")))
        with pytest.raises(ValidationError, match="no Bibliography"):
            document.text()

    def test_a_second_bibliography_is_refused_at_add_section(self):
        document = note("author-year")
        with pytest.raises(ValidationError, match="one Bibliography"):
            document.add_section(FullWidth(content=Bibliography([FAMA])))
        assert len(document._sections) == 2

    def test_a_key_listed_twice_is_refused(self):
        with pytest.raises(ValidationError, match="twice"):
            Bibliography([FAMA, FAMA])

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"key": "has space"},
            {"authors": "Fama, Eugene F."},
            {"authors": []},
            {"authors": [" "]},
            {"year": " "},
            {"title": ""},
            {"url": "javascript:alert(1)"},
            {"doi": "not-a-doi"},
        ],
    )
    def test_a_malformed_reference_is_refused(self, kwargs):
        fields = {"key": "k", "authors": ["A, B."], "year": 2020, "title": "T", **kwargs}
        with pytest.raises(ValidationError):
            Reference(**fields)

    def test_an_unknown_style_is_refused(self):
        with pytest.raises(ValidationError, match="style"):
            Bibliography([FAMA], style="chicago")


class TestNoNewRawSurface:
    def test_a_reference_is_escaped_wherever_it_prints(self):
        hostile = Reference("x", ["<b>Evil</b>, A."], 2020, "<script>t</script>", "<i>v</i>")
        document = Email(FACTS)
        document.add_section(FullWidth(content=TextBlock("<p>[@x]</p>")))
        document.add_section(FullWidth(content=Bibliography([hostile])))
        html = document.render()
        assert "<script>" not in html and "<b>Evil" not in html and "<i>v" not in html
        assert "&lt;b&gt;Evil&lt;/b&gt; 2020" in html

    def test_a_marker_in_a_plain_field_is_escaped_like_any_text(self):
        table = DataTable(["A"], [TableRow(cells=["1"])], caption="A & B [@x]")
        document = Email(FACTS)
        document.add_section(FullWidth(content=table))
        document.add_section(
            FullWidth(content=Bibliography([Reference("x", ["Q & A"], 2020, "T")]))
        )
        html = document.render()
        assert "A &amp; B (" in html and ">Q &amp; A 2020</a>" in html


class TestOnPaper:
    def test_a_paged_document_resolves_them_too(self):
        document = note("numeric", document=PagedDocument({"firm_name": "H", "campaign_name": "R"}))
        assert body_text(document).startswith("Body\n----\n\nSize and value [1]")
        assert 'href="#ref-fama1993" class="citation"' in document.render()
