"""
Organising content (#329): fact lists, timelines, teaser lists and section kickers,
and the fixtures that carry them (#330–#334).
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from pyhermes.builder import (
    Email,
    EmailImage,
    Event,
    FactList,
    FullWidth,
    Teaser,
    TeaserList,
    TextBlock,
    Timeline,
    TwoColumn,
)
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.models import Cell
from pyhermes.builder.theming import DEFAULT_THEME
from pyhermes.config import config_override
from pyhermes.document import PagedDocument
from pyhermes.pdf import available as pdf_available
from qa.fixtures import all_deck_fixtures, all_fixtures, all_paged_fixtures
from qa.fixtures._png import solid_png
from qa.lint import errors, lint_document
from qa.screenshots import _launch, _load_playwright, available

FACTS = {"email_subject": "S", "firm_name": "Hermes", "campaign_name": "Organised"}
PAPER = {"firm_name": "Hermes", "campaign_name": "Organised"}

requires_pdf = pytest.mark.skipif(
    not pdf_available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)
requires_browser = pytest.mark.skipif(
    not available(), reason='no browser; screenshots are the optional "[qa]" extra'
)


def email(*sections) -> Email:
    built = Email(FACTS)
    for section in sections:
        built.add_section(section)
    return built


def paper(*sections) -> PagedDocument:
    built = PagedDocument(PAPER)
    for section in sections:
        built.add_section(section)
    return built


def _sheets(document) -> list[str]:
    import pypdfium2

    from pyhermes.pdf import render_pdf

    pdf = pypdfium2.PdfDocument(render_pdf(document))
    return [page.get_textpage().get_text_range() for page in pdf]


def _thumb(rgb: tuple[int, int, int] = (90, 138, 154)) -> EmailImage:
    return EmailImage.attached(solid_png(36, 20, rgb), alt="Cover", width=180)


# ----------------------------------------------------------------------
# #330 — FactList
# ----------------------------------------------------------------------


class TestAFactList:
    def test_a_mapping_keeps_its_insertion_order(self):
        facts = {"Zeta": "1", "Alpha": "2", "Mid": "3"}
        assert [fact.label for fact in FactList(facts).facts] == ["Zeta", "Alpha", "Mid"]

    def test_pairs_are_taken_too(self):
        listed = FactList([("ISIN", "GB00B1"), ("Fee", "0.45%")])
        assert [(f.label, f.value) for f in listed.facts] == [("ISIN", "GB00B1"), ("Fee", "0.45%")]

    def test_the_text_aligns_the_values_after_the_labels(self):
        text = FactList({"Inception": "12 March 2019", "AUM": "GBP 1.2bn"}).text()
        assert text == "Inception:  12 March 2019\nAUM:        GBP 1.2bn"

    def test_the_title_projects_above_the_rows(self):
        assert FactList({"A": "1"}, title="Fund facts").text() == "Fund facts\n\nA:  1"

    def test_a_figure_is_written_and_set_in_the_numeric_face(self):
        listed = FactList({"AUM": 1234.5})
        assert listed.facts[0].value == "1,235" and listed.facts[0].numeric

    def test_a_cell_keeps_its_tone(self):
        html = FactList({"1Y": Cell("+3.4%", tone="positive")}).render(TemplateEngine().bound())
        theme = DEFAULT_THEME
        assert f"color: {theme.semantic.positive}" in html

    @pytest.mark.parametrize("columns", [1, 2, 3])
    def test_the_facts_flow_down_then_across(self, columns):
        listed = FactList({str(n): str(n) for n in range(7)}, columns=columns)
        flowed = [[fact.label for fact in column] for column in listed.flowed()]
        assert sum(flowed, []) == [str(n) for n in range(7)]
        assert len(flowed) == columns and flowed[0] == [str(n) for n in range(len(flowed[0]))]

    @pytest.mark.parametrize(
        ("facts", "kwargs", "message"),
        [
            ({}, {}, "at least one fact"),
            ({"A": "1"}, {"columns": 4}, "columns of 1, 2 or 3"),
            ({"A": "1"}, {"columns": True}, "columns of 1, 2 or 3"),
            ({"A": "1"}, {"columns": 2}, "1 item"),
            ({"": "1"}, {}, "needs a label"),
            ({"A": ""}, {}, "a string, a number or a Cell"),
            ({"A": Cell("1", color="#FF0000")}, {}, "a tone, not a colour"),
            ([("A",)], {}, "pair"),
        ],
    )
    def test_a_bad_list_is_refused_at_construction(self, facts, kwargs, message):
        with pytest.raises(ValidationError, match=message):
            FactList(facts, **kwargs)

    def test_it_is_a_layout_table_with_no_anchors(self):
        html = FactList({"A": "1", "B": "2"}, columns=2).render(TemplateEngine().bound())
        assert 'class="fact-list" role="presentation"' in html and " id=" not in html
        assert html.count('class="stack-column"') == 3  # two columns and the gutter


# ----------------------------------------------------------------------
# #331 — Timeline
# ----------------------------------------------------------------------

SIX = [
    Event("2 Oct", "Review", "Rolled into Q4.", state="done"),
    Event("9 Oct", "Auction", state="done"),
    Event("14 Oct", "CPI", "September print.", state="next"),
    ("29 Oct", "FOMC", "A hold is priced."),
    ("6 Nov", "Bank of England"),
    ("10 Dec", "ECB", "Last of the year."),
]


class TestATimeline:
    def test_the_text_is_one_line_an_event_with_its_state(self):
        text = Timeline([Event("2026-10-14", "Earnings", "Q3 results", state="done")]).text()
        assert text == "2026-10-14  Earnings — Q3 results (done)"

    def test_the_dates_align_and_a_long_line_wraps_under_its_title(self):
        long = "word " * 30
        lines = Timeline([("1 Oct", "A", long), ("10 Oct", "B")]).text().split("\n")
        assert lines[0].startswith("1 Oct   A — word")
        assert lines[1].startswith("        word") and lines[-1] == "10 Oct  B"

    @pytest.mark.parametrize(
        ("events", "message"),
        [
            ([], "at least one event"),
            ([Event("", "A")], "date"),
            ([Event("1 Oct", "")], "title"),
            ([Event("1 Oct", "A", state="late")], "state"),
            (["1 Oct"], "Event or a"),
        ],
    )
    def test_a_bad_event_is_refused_at_construction(self, events, message):
        with pytest.raises(ValidationError, match=message):
            Timeline(events)

    def test_the_body_is_plain_text_and_escaped(self):
        html = Timeline([("1 Oct", "A", "<b>bold</b> & more")]).render(TemplateEngine().bound())
        assert "&lt;b&gt;bold&lt;/b&gt; &amp; more" in html and "<b>" not in html

    def test_the_rule_runs_between_markers_and_not_past_the_ends(self):
        html = Timeline(SIX).render(TemplateEngine().bound())
        assert html.count("border-left: 2px solid") == 5  # five gaps for six events

    def test_on_paper_no_event_splits_and_in_an_email_nothing_says_so(self):
        doc = paper(FullWidth(Timeline(SIX)))
        assert doc.render().count("break-inside: avoid; page-break-inside: avoid;") >= 6
        assert "break-inside" not in Timeline(SIX).render(TemplateEngine().bound())

    def test_each_state_draws_its_own_marker(self):
        theme = DEFAULT_THEME
        html = Timeline(SIX).render(TemplateEngine().bound())
        done = f"background-color: {theme.palette.accent}; border: 2px solid {theme.palette.accent}"
        ahead = f"background-color: {theme.palette.surface}; border: 2px solid"
        assert html.count(done) == 4 and f"{ahead} {theme.palette.rule_dark}" in html


# ----------------------------------------------------------------------
# #332 — TeaserList
# ----------------------------------------------------------------------


def _teasers(count: int = 3, image: bool = True) -> list[Teaser]:
    return [
        Teaser(
            f"Note {n}",
            f"https://example.com/{n}",
            f"{n} Oct 2026",
            f"Summary {n}.",
            image=_thumb((n * 40, 90, 120)) if image else None,
            tags=["Rates"] if n == 1 else (),
        )
        for n in range(1, count + 1)
    ]


class TestATeaserList:
    def test_every_thumbnail_reaches_the_manifest(self):
        built = email(FullWidth(TeaserList(_teasers(), columns=3)))
        html = built.render()
        assert len(built.assets()) == 3
        for asset in built.assets():
            assert f"cid:{asset.content_id}" in html

    def test_the_text_prints_each_title_url_and_date(self):
        text = TeaserList(_teasers(2, image=False)).text()
        assert text == (
            "Note 1: https://example.com/1\n1 Oct 2026 — Summary 1.\nTags: Rates\n\n"
            "Note 2: https://example.com/2\n2 Oct 2026 — Summary 2."
        )

    @pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,x", "file:///x"])
    def test_an_unsafe_url_is_refused(self, url):
        with pytest.raises(ValidationError, match="unsupported URL scheme"):
            TeaserList([Teaser("T", url)])

    @pytest.mark.parametrize(
        ("teasers", "kwargs", "message"),
        [
            ([], {}, "at least one teaser"),
            ([Teaser("T", "")], {}, "url is required"),
            ([Teaser("", "https://example.com")], {}, "title is required"),
            ([Teaser("T", "https://example.com", tags="Rates")], {}, "list of labels"),
            ([Teaser("T", "https://example.com")], {"columns": 2}, "1 item"),
            (["T"], {}, "must be a Teaser"),
        ],
    )
    def test_a_bad_list_is_refused_at_construction(self, teasers, kwargs, message):
        with pytest.raises(ValidationError, match=message):
            TeaserList(teasers, **kwargs)

    def test_three_across_in_an_email_and_one_column_on_paper(self):
        listed = TeaserList(_teasers(), columns=3)
        across = email(FullWidth(listed)).render()
        down = paper(FullWidth(listed)).render()
        assert across.count('class="teaser-list"') == 1  # one row of three
        assert down.count('class="teaser-list"') == 3  # three rows of one
        assert all(f'href="https://example.com/{n}"' in down for n in (1, 2, 3))

    def test_a_short_last_row_keeps_its_columns_the_others_width(self):
        html = email(FullWidth(TeaserList(_teasers(4, image=False), columns=3))).render()
        rows = re.findall(r'<table class="teaser-list".*?</table>', html, re.S)
        assert [row.count('class="stack-column"') for row in rows] == [5, 5]


# ----------------------------------------------------------------------
# #333 — the kicker
# ----------------------------------------------------------------------


class TestAKicker:
    def test_it_sits_above_the_title_in_its_table(self):
        html = email(FullWidth(TextBlock("<p>x</p>"), title="Rates", kicker="Week 40")).render()
        table = re.search(r'<table class="section-title".*?</table>', html, re.S)
        assert table and table.group(0).index("Week 40") < table.group(0).index("Rates")

    def test_it_never_sits_inside_the_heading_the_running_header_reads(self):
        html = paper(FullWidth(TextBlock("<p>x</p>"), title="Rates", kicker="Week 40")).render()
        heading = re.search(r"<h2[^>]*>(.*?)</h2>", html, re.S)
        assert heading and "Week 40" not in heading.group(1)

    def test_its_case_is_the_css_and_the_text_keeps_the_callers(self):
        built = email(FullWidth(TextBlock("<p>x</p>"), title="Rates", kicker="Markets · Week 40"))
        assert "text-transform:uppercase" in built.render()
        assert "Markets · Week 40\nRates\n-----" in built.text()

    @pytest.mark.parametrize(
        "section",
        [
            lambda: FullWidth(TextBlock("<p>x</p>"), kicker="K"),
            lambda: TwoColumn("50-50", TextBlock("<p>a</p>"), TextBlock("<p>b</p>"), kicker="K"),
        ],
    )
    def test_an_untitled_section_refuses_one(self, section):
        with pytest.raises(ValidationError, match="kicker sits above its title"):
            section()

    @pytest.mark.parametrize("kicker", ["", "   ", 7])
    def test_it_is_plain_text(self, kicker):
        with pytest.raises(ValidationError, match="plain text"):
            FullWidth(TextBlock("<p>x</p>"), title="T", kicker=kicker)

    def test_it_is_capped_by_config(self):
        with config_override(kicker_max_chars=5), pytest.raises(ValidationError, match="at most 5"):
            FullWidth(TextBlock("<p>x</p>"), title="T", kicker="Longer")

    def test_it_is_escaped(self):
        html = email(FullWidth(TextBlock("<p>x</p>"), title="T", kicker="<b>&</b>")).render()
        assert "&lt;b&gt;&amp;&lt;/b&gt;" in html

    def test_it_follows_its_sections_alignment(self):
        html = email(
            FullWidth(TextBlock("<p>x</p>"), title="T", kicker="Week 40", align="center")
        ).render()
        cell = re.search(r'<td align="center"[^>]*>\s*<p class="kicker"', html)
        assert cell, "the kicker is not in the centred title cell"

    def test_on_a_dark_ground_it_takes_the_rebound_type(self):
        theme = DEFAULT_THEME
        dark = email(
            FullWidth(TextBlock("<p>x</p>"), title="T", kicker="K", background_color="#1B2A38")
        ).render()
        light = email(FullWidth(TextBlock("<p>x</p>"), title="T", kicker="K")).render()
        kicker = r'<p class="kicker"[^>]*color:(#[0-9A-F]{6})'
        assert re.search(kicker, light).group(1) == theme.palette.accent
        assert re.search(kicker, dark).group(1) == theme.text.on_dark_secondary

    def test_a_slide_sets_it_in_the_title_band_and_keeps_the_titles_line(self):
        deck = all_deck_fixtures()["pitch_16_9"]()
        html = deck.render()
        band = re.search(r'slide-title-band"[^>]*>\s*<p class="kicker"[^>]*>Positioning</p>', html)
        assert band, "the slide's kicker is not in its title band"
        assert "Positioning\nThe view in brief\n---" in deck.text()


# ----------------------------------------------------------------------
# #334 — the fixtures, in every medium
# ----------------------------------------------------------------------


class TestTheFixtures:
    def test_the_email_and_paper_twins_lint_clean(self):
        for document in (
            all_fixtures()["organised_layout"](),
            all_paged_fixtures()["a4_organised_layout"](),
        ):
            assert not errors(lint_document(document))

    def test_the_email_stays_well_under_the_warning(self):
        assert len(all_fixtures()["organised_layout"]().render().encode()) < 60 * 1024


_RAIL = """() => [...document.querySelectorAll('.timeline-event')].map(t => {
  const [top, foot] = t.rows;
  const box = cell => cell.getBoundingClientRect();
  return {
    capsule: [box(top.cells[1]).left, box(top.cells[2]).right, box(top.cells[1]).top,
              box(top.cells[1]).bottom],
    rule: [box(foot.cells[2]).left, box(foot.cells[2]).top, box(foot.cells[2]).bottom,
           parseFloat(getComputedStyle(foot.cells[2]).borderLeftWidth)],
  };
})"""

#: Each column cell's left and top, the gutters between them left out.
_COLUMNS = """() => [...document.querySelectorAll('.fact-list, .teaser-list')]
  .flatMap(table => [...table.rows[0].cells])
  .filter(td => td.getBoundingClientRect().width > 40)
  .map(td => [Math.round(td.getBoundingClientRect().left),
              Math.round(td.getBoundingClientRect().top)])"""


def _measure(html: str, script: str, width: int):
    with _load_playwright()() as playwright:
        browser = _launch(playwright)
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.route("**/*", lambda route: route.abort())
        page.set_content(html)
        measured = page.evaluate(script)
        scroll = page.evaluate("() => document.documentElement.scrollWidth")
        browser.close()
    return measured, scroll


@requires_browser
class TestInABrowser:
    def test_the_rule_meets_every_marker_and_runs_through_its_centre(self):
        events, _ = _measure(email(FullWidth(Timeline(SIX))).render(), _RAIL, 760)
        for here, after in zip(events, events[1:], strict=False):
            left, right, _, bottom = here["capsule"]
            rule_left, rule_top, rule_bottom, weight = here["rule"]
            assert weight == 2 and rule_top == pytest.approx(bottom, abs=0.5)
            assert rule_bottom == pytest.approx(after["capsule"][2], abs=0.5)
            assert rule_left + weight / 2 == pytest.approx((left + right) / 2, abs=0.5)
        assert events[-1]["rule"][3] == 0

    @pytest.mark.parametrize(
        "listing",
        [
            lambda: FactList({str(n): str(n) for n in range(6)}, columns=3),
            lambda: TeaserList(_teasers(), columns=3),
        ],
    )
    def test_columns_sit_across_on_a_desktop_and_stack_on_a_phone(self, listing):
        html = email(FullWidth(listing())).render()
        desk, _ = _measure(html, _COLUMNS, 1000)
        phone, scroll = _measure(html, _COLUMNS, 375)
        assert len({top for _, top in desk}) == 1 and len({left for left, _ in desk}) == 3
        assert len({left for left, _ in phone}) == 1 and scroll <= 375


@requires_pdf
class TestOnPaper:
    def test_no_event_splits_across_a_sheet(self):
        events = [Event(f"D{n:02d}", f"Event {n:02d}", f"Body {n:02d}.") for n in range(60)]
        sheets = _sheets(paper(FullWidth(Timeline(events), title="Calendar")))
        assert len(sheets) > 2, "the timeline did not cross a sheet"
        for n in range(60):
            [sheet] = [text for text in sheets if f"Event {n:02d}" in text]
            assert f"D{n:02d}" in sheet and f"Body {n:02d}." in sheet

    def test_a_kicker_never_ends_a_sheet_without_its_title(self):
        """The lead-in grows until the kicked section crosses onto the next sheet."""
        landed = set()
        for lead in range(30, 50):
            sheets = _sheets(
                paper(
                    FullWidth(TextBlock("".join(f"<p>Line {n}.</p>" for n in range(lead)))),
                    FullWidth(TextBlock("<p>After.</p>"), title="Titled", kicker="Kicked"),
                )
            )
            [(at, sheet)] = [(i, text) for i, text in enumerate(sheets) if "KICKED" in text.upper()]
            assert "Titled" in sheet and "After." in sheet, f"split at {lead} lines"
            landed.add(at)
        assert len(landed) > 1, "the sweep never moved the section across a sheet"
