"""
Labels and status (#324): the badge on a card, a cell and a section title, a
status column drawn as dots, a row of tags, and the fixtures that carry them
(#325–#328).
"""

from __future__ import annotations

import importlib.util

import pytest

from pyhermes.builder import (
    Badge,
    CardGroup,
    Column,
    DataTable,
    Email,
    FullWidth,
    TagRow,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.enums import ColumnKind
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.models import Cell, KpiItem, TableRow
from pyhermes.builder.theming import DEFAULT_THEME
from pyhermes.config import config_override
from pyhermes.pdf import available as pdf_available
from qa.fixtures import all_fixtures, all_paged_fixtures
from qa.lint import errors, lint_document

ENGINE = TemplateEngine()

FACTS = {"email_subject": "Labels", "firm_name": "Hermes Research", "campaign_name": "Labels"}

STATUSES = {"On track": "positive", "Watch": "neutral", "Breach": "negative"}

requires_pdf = pytest.mark.skipif(
    not pdf_available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)


def _email(*sections) -> Email:
    email = Email(FACTS)
    for section in sections:
        email.add_section(section)
    return email


def _status_table(*words: str) -> DataTable:
    return DataTable(
        ["Book", Column("Status", kind="status", statuses=STATUSES)],
        [TableRow([f"Book {n}", word]) for n, word in enumerate(words, start=1)],
    )


# ----------------------------------------------------------------------
# #325 — the badge
# ----------------------------------------------------------------------


class TestABadge:
    def test_it_takes_a_tone_and_defaults_to_neutral(self):
        assert Badge("New").tone == "neutral"
        with pytest.raises(ValidationError, match="tone"):
            Badge("New", "#FF0000").validate()

    def test_a_label_over_the_limit_is_refused_naming_the_switch(self):
        with pytest.raises(ValidationError, match=r"at most 24 \(Config.badge_max_chars\)"):
            KpiItem("10Y", "4.21%", badge="A label far too long for a badge")
        with config_override(badge_max_chars=40):
            KpiItem("10Y", "4.21%", badge="A label far too long for a badge")

    def test_an_empty_label_is_refused(self):
        with pytest.raises(ValidationError, match="needs a label"):
            Cell("A", badge=" ")

    def test_a_bare_label_is_a_neutral_badge(self):
        assert Cell("A", badge="New").badge == Badge("New", "neutral")

    def test_anything_else_is_refused(self):
        with pytest.raises(ValidationError, match="must be a Badge or a label"):
            KpiItem("10Y", "4.21%", badge=3)

    def test_it_draws_on_its_tones_tint_in_its_tone(self):
        html = _render_card(Badge("Upgrade", "positive"))
        badge = html[html.index('class="badge"') :].split(">")[0]
        assert f"color:{DEFAULT_THEME.semantic.positive};" in badge
        assert "background-color:#" in badge and "border-radius:3px" in badge

    def test_outlook_pads_it_with_spaces_since_the_word_engine_drops_padding(self):
        html = _render_card(Badge("New"))
        assert "<!--[if mso]>&nbsp;<![endif]-->New<!--[if mso]>&nbsp;<![endif]--></span>" in html

    def test_the_label_is_escaped(self):
        assert "R&amp;D" in _render_card(Badge("R&D"))


def _render_card(badge: Badge) -> str:
    return CardGroup([KpiItem("10Y", "4.21%", badge=badge), KpiItem("2s10s", "38")]).render(ENGINE)


class TestABadgeInEachPlace:
    def test_a_card_carries_it_beside_its_label_and_the_text_brackets_it(self):
        group = CardGroup([KpiItem("10Y", "4.21%", badge="Upgrade"), KpiItem("2s10s", "38")])
        assert "10Y [UPGRADE]: 4.21%" in group.text()
        html = group.render(ENGINE)
        assert html.index("10Y") < html.index(">Upgrade<") < html.index("4.21%")

    def test_a_cell_carries_it_after_its_text(self):
        table = DataTable(
            ["Name", Column("Rating", kind="text")],
            [TableRow(["Gilts", Cell("A", badge=Badge("Upgrade", "positive"))])],
        )
        assert "A [UPGRADE]" in table.text()
        html = table.render(ENGINE)
        assert html.index(">A") < html.index(">Upgrade<")

    @pytest.mark.parametrize("split", [False, True], ids=["full-width", "split"])
    def test_a_section_carries_it_after_its_title(self, split):
        content = TextBlock("<p>Body.</p>")
        if split:
            section = TwoColumn(title="Outlook", badge="Preliminary", left=content)
        else:
            section = FullWidth(content, title="Outlook", badge="Preliminary")
        assert section.text().startswith("Outlook [PRELIMINARY]\n")
        html = _email(section).render()
        assert html.index("Outlook") < html.index(">Preliminary<") < html.index("</h2>")

    def test_a_section_badge_needs_a_title(self):
        with pytest.raises(ValidationError, match="give the section a title"):
            FullWidth(TextBlock("<p>x</p>"), badge="New")

    def test_unset_nothing_is_drawn(self):
        html = _email(FullWidth(TextBlock("<p>x</p>"), title="T")).render()
        assert 'class="badge"' not in html


# ----------------------------------------------------------------------
# #326 — a status column
# ----------------------------------------------------------------------


class TestAStatusColumn:
    def test_each_cell_draws_a_dot_in_its_statuss_tone_then_the_word(self):
        html = _status_table("On track", "Watch", "Breach").render(ENGINE)
        for word, tone in STATUSES.items():
            ink = getattr(DEFAULT_THEME.semantic, tone)
            assert f"background-color:{ink};" in html.split(word)[0].rsplit("<td", 1)[-1]

    def test_an_unmapped_value_is_refused_naming_it(self):
        with pytest.raises(ValidationError, match=r"'Status' has no status 'Late'"):
            _status_table("On track", "Late")

    def test_the_text_prints_the_word_alone(self):
        text = _status_table("On track", "Breach").text()
        assert "On track" in text and "Breach" in text

    def test_it_is_left_aligned_and_set_like_text(self):
        column = Column("Status", kind="status", statuses=STATUSES)
        assert column.resolved_align(3) == "left"
        assert column.resolved_kind(3) is ColumnKind.STATUS

    def test_kind_and_statuses_go_together(self):
        with pytest.raises(ValidationError, match="go together"):
            Column("Status", kind="status").validate()
        with pytest.raises(ValidationError, match="go together"):
            Column("Status", statuses=STATUSES).validate()

    def test_a_status_takes_a_tone_never_a_hex(self):
        with pytest.raises(ValidationError, match="must be one of"):
            Column("Status", kind="status", statuses={"Late": "#FFBF00"}).validate()

    def test_a_subhead_and_an_empty_cell_draw_no_dot(self):
        table = DataTable(
            ["Book", Column("Status", kind="status", statuses=STATUSES)],
            [TableRow(["Rates", ""], kind="subhead"), TableRow(["Gilts", ""])],
        )
        assert "status-dot" not in table.render(ENGINE)


# ----------------------------------------------------------------------
# #327 — a row of tags
# ----------------------------------------------------------------------


class TestATagRow:
    def test_the_text_lists_the_tags(self):
        assert TagRow(["Rates", "Credit", "FX"]).text() == "Tags: Rates, Credit, FX"

    @pytest.mark.parametrize("count", [1, 13])
    def test_it_takes_two_to_twelve(self, count):
        with pytest.raises(ValidationError, match="2 to 12 tags"):
            TagRow([f"Tag {n}" for n in range(count)])

    def test_every_tag_is_a_neutral_badge(self):
        html = TagRow(["Rates", "Credit"]).render(ENGINE)
        assert html.count('class="badge"') == 2
        assert html.count(f"color:{DEFAULT_THEME.semantic.neutral};") == 2

    def test_a_tag_over_the_limit_is_refused(self):
        with pytest.raises(ValidationError, match="badge_max_chars"):
            TagRow(["Rates", "x" * 25])


# ----------------------------------------------------------------------
# #328 — the fixtures
# ----------------------------------------------------------------------


class TestTheFixtures:
    @pytest.mark.parametrize(
        "document",
        [all_fixtures()["labelled_layout"], all_paged_fixtures()["a4_labelled_layout"]],
        ids=["email", "paged"],
    )
    def test_each_lints_clean(self, document):
        assert errors(lint_document(document())) == []

    def test_every_new_object_is_in_the_email(self):
        html = all_fixtures()["labelled_layout"]().render()
        for tone in ("positive", "neutral", "negative"):
            assert f"color:{getattr(DEFAULT_THEME.semantic, tone)};" in html
        assert html.count("status-dot") == 4
        assert html.count('class="tag-row"') == 2


@requires_pdf
class TestOnPaper:
    def test_the_labels_and_statuses_print(self):
        import pypdfium2

        from pyhermes.pdf import render_pdf

        pdf = pypdfium2.PdfDocument(render_pdf(all_paged_fixtures()["a4_labelled_layout"]()))
        text = " ".join(page.get_textpage().get_text_range() for page in pdf)
        for word in ("PRELIMINARY", "UPGRADE", "DOWNGRADE", "On track", "Breach", "SECURITISED"):
            assert word in text, word
