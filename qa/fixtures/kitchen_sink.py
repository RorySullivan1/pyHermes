"""
Every public component, in every container geometry, with every metadata field set.

The broadest fixture in the gallery, and the one a golden snapshot is worth
the most on: a change to any component template, container ratio or skeleton
variable moves this render. Two completeness tests keep it honest — a new
``Component`` subclass or a new ``EmailMetadata`` field that never joins this
fixture fails the suite rather than silently going unpinned forever.

**This fixture is also #32's characterization referee.** #32 asked for one
representative email pinning the surfaces the header epic restructures
(``base.html``, ``EmailMetadata``, ``Email.render()``); #58 said the two must
resolve to one harness rather than two. So the metadata below is exhaustive on
purpose: every field carries a distinctive non-default value, which is what
makes a golden diff point at the field that moved.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

from pyhermes.builder import (
    AuthorBlock,
    Banner,
    BannerPalette,
    BarList,
    Bibliography,
    Button,
    Callout,
    CardGroup,
    ChartBlock,
    Columns,
    ContactBlock,
    Contents,
    DataTable,
    Divider,
    Email,
    EmailBuilder,
    FlowedColumns,
    Footer,
    FullWidth,
    Glossary,
    Header,
    HeroStat,
    ImageBlock,
    MathBlock,
    NumberedList,
    Only,
    PullQuote,
    Reference,
    Rgba,
    Spacing,
    Sparkline,
    Stack,
    Term,
    TextBlock,
    ThreeColumn,
    TwoColumn,
)
from pyhermes.builder.engine import TemplateOverlay
from pyhermes.builder.enums import (
    CardOrientation,
    ImageAlign,
    ThreeColumnRatio,
    Tone,
    TwoColumnRatio,
)
from pyhermes.builder.formats import bps, delta, number, pct
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import (
    Card,
    Cell,
    Column,
    FooterLink,
    KpiItem,
    LinkRow,
    NumberedItem,
    TableRow,
    tone_of,
)

from ._png import solid_png

#: Fixed so the render never moves. A fixture that reads the clock cannot be
#: snapshotted.
_YEAR = "2026"

_GAIN = "#4A7C59"
_LOSS = "#B85450"
_RETURN = partial(pct, dp=1, sign=True)

_CHART_PNG = solid_png(320, 120, (42, 61, 84))
_EQUATION_PNG = solid_png(440, 96, (59, 59, 59))
_TAIL_PNG = solid_png(410, 114, (59, 59, 59))
_THUMB_PNG = solid_png(96, 96, (184, 84, 80))
#: The wrapped figure's portrait (#189): its own bytes, so its asset is its own.
_DESK_PNG = solid_png(120, 150, (91, 138, 154))


#: A hosted logo, carrying alt text and a width of its own that the explicit
#: metadata below deliberately overrides. The two differ so the golden records
#: *which* branch of the resolution chain won — explicit metadata beats the
#: image's own value, which beats the firm name and the default width.
_LOGO = EmailImage.hosted(
    "https://cdn.example.com/hermes-logo.png",
    alt="Hermes Research logotype",
    width=110,
)


def _metadata() -> dict[str, Any]:
    """
    Every ``EmailMetadata`` field, each with a distinctive non-default value.

    Exhaustive by rule, not by accident: ``TestKitchenSinkCompleteness`` in
    ``tests/test_fixtures.py`` introspects the dataclass and fails if a field
    added later never lands here. An unset field is one the golden cannot
    pin, and pinning the skeleton is half of what #32 asked for.

    The banner's own fields moved out of here in #91: ``title`` and
    ``subtitle`` have no flat spelling — the flat keywords exist for
    back-compatibility with a pre-split call site, and a field added after
    the split has none — so the fixture builds the region explicitly, the way
    it already builds the footer. What that costs is golden coverage of the
    flat path, and ``TestTheFlatKeywordsStillWork`` buys it back with a
    stronger guarantee than a golden gave: the two spellings must render the
    *same bytes*, not merely each their own stable ones.
    """
    return {
        "email_subject": "Kitchen Sink — every component, every geometry",
        "preheader_text": "One fixture exercising the whole component library.",
        # A real, honest non-default: this fixture's copy is British English
        # ("Week ending 24 August"). A fixture claiming "fr" would pin the
        # mechanism while making the golden say something untrue about the
        # email it renders.
        "language": "en-GB",
        "firm_name": "Hermes Research",
        "campaign_name": "kitchen-sink",
        "department": "Rates Strategy",
        "date_range": "Week ending 24 August",
        "issue_label": "Issue 001",
        "header_disclaimer": "For illustrative purposes. Not investment advice.",
        # Named rather than omitted, so this golden pins that the string
        # path resolves to the same bytes as the default object — true of all
        # three design-system axes.
        "theme": "classic",
        "size_theme": "standard",
        "font_theme": "classic",
        "current_year": _YEAR,
        "unsubscribe_url": "https://example.com/unsubscribe",
        "view_in_browser_url": "https://example.com/archive/001",
    }


def build(
    template_dir: Path | None = None,
    template_overlay: TemplateOverlay = None,
    **metadata_overrides: Any,
) -> Email:
    """
    Build the kitchen-sink email. Deterministic: same bytes every call.

    ``metadata_overrides`` replaces individual metadata fields, which is how
    ``compact_size`` and ``spacious_size`` render *this exact email* at
    another density. Reusing the content rather than hand-writing two more
    emails is what makes those goldens a true A/B: byte-for-byte the same
    copy, one field different, so every difference in the diff is the
    density and nothing else. Both extra parameters are optional, so the
    ``FixtureBuilder`` contract — callable with no arguments — still holds.
    """
    return (
        EmailBuilder(template_dir=template_dir, template_overlay=template_overlay)
        .metadata(_metadata() | metadata_overrides)
        .header(
            Header(
                # Distinctive on every axis, because the golden can only pin
                # a value the fixture actually moves — and here that is
                # forced rather than chosen: the region-completeness test
                # fails on any field left at its default. The fixtures that
                # leave the header alone are what pin the theme's own band.
                align="left",
                background_color="#1E2B38",
                text_color="#B8C6CE",
            )
        )
        .banner(
            Banner(
                # The two image fields take different shapes on purpose —
                # ``logo_url`` an EmailImage, ``background_image_url`` a bare
                # URL string — so the golden covers both branches of the
                # collapse to a ``src`` in ``Region.context()``.
                background_image_url="https://cdn.example.com/header-bg.png",
                logo_url=_LOGO,
                logo_alt="Hermes Research — weekly research letter",
                logo_width=128,
                # Distinct from firm_name / campaign_name on purpose: the
                # golden then pins that the masthead renders its own copy
                # while the facts still reach everywhere else they appear —
                # the footer's copyright line most visibly (#91).
                title="Q3 Outlook",
                subtitle="What the curve is pricing",
                # Every role at a non-default, because the golden can only
                # pin a colour the fixture actually moves — and here that is
                # forced rather than chosen: `palette` is a `Banner` field,
                # and the region-completeness test fails on any field left at
                # its default. What it pins is the *mechanism*, one role per
                # site. The fixtures that leave it unset — `slate_theme` most
                # usefully, since its tokens differ from the default's — are
                # what pin the inheritance.
                palette=BannerPalette(
                    band="#3A2B3F",
                    title="#FDF6E3",
                    subtitle="#D8C7CF",
                    meta="#A8909B",
                    accent="#C48A5A",
                    scrim=Rgba("#241A28", 0.55),
                    title_shadow=Rgba("#1A121D", 0.45),
                    subtitle_shadow=Rgba("#1A121D", 0.35),
                ),
            )
        )
        .footer(
            Footer(
                # The shared box surface, distinctively — the same three
                # fields the header above sets, which is the parity this
                # golden pins in the one place both boxes are visible.
                align="left",
                background_color="#F2F1EE",
                text_color="#5C574E",
                border=True,
                border_color="#D6D2CB",
                image=EmailImage.hosted(
                    "https://cdn.example.com/hermes-mark.png",
                    alt="Hermes Research mark",
                    width=80,
                ),
                image_alt="Hermes Research mark",
                image_width=80,
                disclaimer="<p>Distributed to registered recipients only.</p>",
                unsubscribe_label="Stop receiving this",
                view_in_browser_label="Read it in a browser",
                # A row that differs from the default on every axis the
                # object added: its own copyright wording, and a link set
                # that is neither the default pair nor the same length —
                # which is the whole reason the row became an object.
                # `minimal_footer` leaves it None, pinning the resolution
                # path and #64's label fields with it.
                link_row=LinkRow(
                    copyright="© 2026 Hermes Research — all rights reserved",
                    links=[
                        FooterLink("Privacy", "https://example.com/privacy"),
                        FooterLink("Stop receiving this", "https://example.com/unsubscribe"),
                        FooterLink("Contact", "mailto:research@example.com"),
                    ],
                ),
            )
        )
        .section(
            FullWidth(
                title="In This Issue",
                content=Contents(subtitle="Every section below, linked to its heading"),
            )
        )
        # FullWidth + horizontal CardGroup + highlight.
        .section(
            FullWidth(
                title="Market Snapshot",
                highlight=True,
                content=CardGroup(
                    [
                        # Figures go through pyhermes.builder.formats (#177), and each
                        # value is coloured by a tone the theme resolves (#178):
                        # the sign where the sign is the claim, stated where not.
                        KpiItem(
                            "S&P 500",
                            number(5234),
                            sublabel=pct(0.0142, sign=True),
                            tone=tone_of(0.0142),
                        ),
                        # Rising yields hurt the bond book: up, and still negative. Its
                        # change is drawn as an arrow and its quarter as a trend (#318).
                        KpiItem.from_number(
                            "UST 10Y",
                            0.0428,
                            pct,
                            change=0.0006,
                            change_fmt=bps,
                            good="down",
                            arrow=True,
                            trend=[0.0409, 0.0415, 0.0422, 0.0428],
                        ),
                        KpiItem(
                            "Gold",
                            number(2411),
                            sublabel=pct(0.0085, sign=True),
                            tone=tone_of(0.0085),
                        ),
                        # A falling VIX is good news: down, and still positive.
                        KpiItem(
                            "VIX",
                            number(14.32, 2),
                            sublabel=delta(-2.18, unit="pts"),
                            tone=Tone.POSITIVE,
                        ),
                    ],
                    orientation=CardOrientation.HORIZONTAL,
                    # A per-object override (#215), by a token the strip reads.
                    spacing={"kpi_pad_y": 10},
                ),
            )
        )
        # Vertical CardGroup — the same cards, stacked, carrying prose bodies.
        .section(
            FullWidth(
                title="Sector Notes",
                content=CardGroup(
                    [
                        Card(
                            "Technology",
                            "+2.1%",
                            _GAIN,
                            "week",
                            body="<p>Semiconductor strength led the advance.</p>",
                        ),
                        Card(
                            "Energy",
                            "-0.7%",
                            _LOSS,
                            "week",
                            body="<p>Crude gave back the prior week's gain.</p>",
                        ),
                    ],
                    orientation=CardOrientation.VERTICAL,
                    subtitle="Relative performance",
                ),
            )
        )
        # PullQuote (#189): centred, attributed, the same band in every medium.
        .section(
            FullWidth(
                title="In Their Words",
                content=PullQuote(
                    "Duration earned its place in the book again this quarter.",
                    attribution="Head of Rates Strategy",
                    align="center",
                ),
            )
        )
        # A figure the prose wraps round on paper (#189); in an email it sits
        # above the prose, placed by its own align.
        .section(
            FullWidth(
                title="Desk Note",
                content=TextBlock(
                    "<p>The desk's view in brief: the steepener stays on into the next "
                    "meeting, and linkers are the next addition.</p>",
                    figure=ImageBlock(
                        EmailImage.attached(_DESK_PNG, alt="The desk", width=120),
                        align="right",
                        wrap="right",
                    ),
                ),
            )
        )
        # Every tag a prose field is styled on (#280), one left as the author styled it.
        .section(
            FullWidth(
                title="Desk Detail",
                content=TextBlock(
                    "<h3>What changed this week</h3>"
                    "<p>Three moves, set out in the "
                    '<a href="https://example.com/rates">rates note</a>:</p>'
                    "<ul><li>The front end repriced two cuts out.</li>"
                    "<li>Breakevens widened on the energy print.</li></ul>"
                    "<h4>What we would do</h4>"
                    "<ol><li>Hold the steepener.</li><li>Add linkers on weakness.</li></ol>"
                    "<blockquote>The curve is pricing a pause, not a pivot.</blockquote>"
                    "<hr>"
                    '<p>Levels as of the <a href="https://example.com/close" '
                    'style="color: inherit;">London close</a>.</p>'
                ),
            )
        )
        # FlowedColumns (#189): one passage through columns on paper, and in an
        # email exactly the FullWidth it degrades to.
        .section(
            FlowedColumns(
                title="Long Read",
                content=TextBlock(
                    "<p>On paper this passage runs down one column and on into the "
                    "next, the way a newspaper sets its copy. In an email it is one "
                    "column, because Outlook's Word engine has no multi-column layout.</p>"
                ),
            )
        )
        # The glance objects (#318): every token they read renders here.
        .section(
            FullWidth(
                title="At a Glance",
                content=Stack(
                    [
                        HeroStat(
                            "+38 bps",
                            "2s10s",
                            "steepest since 2022",
                            tone="positive",
                            align="center",
                        ),
                        BarList(
                            [("Duration", 0.0042), ("Curve", 0.0018)],
                            value_format=partial(pct, dp=2, sign=True),
                            tone="auto",
                        ),
                        Sparkline(
                            [3.9, 4.0, 4.2], tone="negative", value_format=partial(number, dp=1)
                        ),
                    ]
                ),
            )
        )
        # DataTable, with per-cell colours.
        .section(
            FullWidth(
                title="Factor Returns",
                # A section tightened for itself (#214), and its table's rows (#215).
                spacing=Spacing(content_top=10, content_bottom=8),
                content=DataTable(
                    # A bar (#227): the exhaustive fixture is where every size
                    # token must render, and the bar's thickness is one.
                    headers=["Factor", "1M", Column("YTD", bar=True)],
                    rows=[
                        TableRow(
                            cells=[
                                "Value",
                                pct(0.018, 1, sign=True),
                                Cell(pct(0.074, 1, sign=True), value=0.074),
                            ],
                            colors=["", _GAIN, _GAIN],
                        ),
                        # The first row keeps the flat `colors=` spelling; these
                        # two are formatted once and toned by their sign (#178).
                        TableRow(
                            cells=[
                                "Momentum",
                                Cell.from_number(-0.004, _RETURN),
                                Cell.from_number(0.112, _RETURN),
                            ]
                        ),
                        TableRow(
                            cells=[
                                "Quality",
                                Cell.from_number(0.009, _RETURN),
                                Cell.from_number(0.051, _RETURN),
                            ]
                        ),
                    ],
                    source="Hermes Research[^1]",
                    as_of="24 August 2026",
                    subtitle="Long-short, gross of costs",
                    caption="Style factor returns",
                    label="Exhibit",
                    anchor="factor-table",
                    notes=["Each factor is equal-weighted across the top and bottom quintiles."],
                    disclosure=(
                        "Factor returns are shown gross of fees and transaction "
                        "costs. Past performance is not indicative of future "
                        "results. Figures are estimates and subject to revision."
                    ),
                    spacing={"table_cell_pad": 7},
                ),
            )
        )
        # ChartBlock — attached, so the fixture also exercises Email.assets().
        .section(
            FullWidth(
                title="Cumulative Performance",
                content=ChartBlock(
                    EmailImage.attached(_CHART_PNG, alt="Cumulative factor performance", width=320),
                    source="Hermes Research",
                    subtitle="Indexed to 100",
                    caption="Cumulative factor performance",
                    label="Exhibit",
                    disclosure=(
                        "The chart above is indexed to 100 at inception and "
                        "excludes the effect of the 0.75% management fee."
                    ),
                ),
            )
        )
        # MathBlock (#229) — solid bytes, never a real render, so the golden
        # does not depend on matplotlib. Every field is set.
        .section(
            FullWidth(
                title="Portfolio Variance",
                content=MathBlock(
                    _EQUATION_PNG,
                    latex=r"\sigma_p^2 = w^\top \Sigma w",
                    width=110,
                    caption="Portfolio variance[^1]",
                    label="Equation",
                    anchor="variance-identity",
                    notes=["The covariance matrix is estimated over 36 months."],
                    disclosure="The estimate assumes stable correlations.",
                    align="left",
                    spacing={"caption_gap": 5},
                ),
            )
        )
        # A multi-line display (#232), one image, right-aligned as a block.
        .section(
            FullWidth(
                title="Tail Risk",
                content=MathBlock(
                    _TAIL_PNG,
                    lines=[
                        r"\text{VaR}_{99\%} = -q_{0.01}(r)",
                        r"\text{ES}_{99\%} = \mathbb{E}[r \mid r \leq q_{0.01}]",
                    ],
                    width=103,
                    caption="Value at risk and expected shortfall",
                ),
            )
        )
        # TwoColumn — all three ratios.
        .section(
            TwoColumn(
                ratio=TwoColumnRatio.EQUAL,
                title="Equal Columns",
                spacing={"column_bottom": 14},
                left=TextBlock(
                    '<p>The left half of a 50-50 split, below <a class="xref" '
                    'href="#exhibit-2">Exhibit 2</a>.</p>',
                    # Paper only (#189): this email renders exactly as without it.
                    drop_cap=True,
                ),
                right=TextBlock("<p>The right half of a 50-50 split.</p>"),
            )
        )
        .section(
            TwoColumn(
                ratio=TwoColumnRatio.NARROW_WIDE,
                title="Narrow then Wide",
                highlight=True,
                left=ImageBlock(
                    EmailImage.attached(_THUMB_PNG, alt="Thumbnail", width=96),
                    caption="A 30% column[^1]",
                    label="Figure",
                    notes=["The thumbnail is a placeholder, not a chart."],
                    align=ImageAlign.LEFT,
                    disclosure="Illustrative only; not a recommendation to buy or sell.",
                ),
                right=TextBlock("<p>Commentary occupying the wider 70% column.</p>"),
            )
        )
        .section(
            TwoColumn(
                ratio=TwoColumnRatio.WIDE_NARROW,
                title="Wide then Narrow",
                # Two blocks in one column (#262), at a gap of its own.
                left=Stack(
                    [
                        TextBlock("<p>Commentary occupying the wider 70% column.</p>"),
                        TextBlock("<p>A second block in the same column.</p>"),
                        # And a split inside the column (#263).
                        Columns(
                            [TextBlock("<p>Nested left.</p>"), TextBlock("<p>Nested right.</p>")],
                            ratio=(1, 2),
                        ),
                    ],
                    spacing={"block_gap": 8},
                ),
                right=AuthorBlock(
                    "A. Analyst",
                    job_title="Head of Research",
                    email="research@example.com",
                ),
            )
        )
        # ThreeColumn — all four ratios.
        .section(
            ThreeColumn(
                ratio=ThreeColumnRatio.EQUAL,
                title="Three Equal",
                anchor="thirds",
                left=TextBlock("<p>First third.</p>"),
                center=TextBlock("<p>Second third.</p>"),
                right=TextBlock("<p>Final third.</p>"),
            )
        )
        .section(
            ThreeColumn(
                ratio=ThreeColumnRatio.WIDE_LEFT,
                title="Wide Left",
                left=TextBlock("<p>The 50% column.</p>"),
                center=TextBlock("<p>Quarter.</p>"),
                right=TextBlock("<p>Quarter.</p>"),
            )
        )
        .section(
            ThreeColumn(
                ratio=ThreeColumnRatio.WIDE_CENTER,
                title="Wide Centre",
                left=TextBlock("<p>Quarter.</p>"),
                center=TextBlock("<p>The 50% column.</p>"),
                right=TextBlock("<p>Quarter.</p>"),
            )
        )
        .section(
            ThreeColumn(
                ratio=ThreeColumnRatio.WIDE_RIGHT,
                title="Wide Right",
                left=TextBlock("<p>Quarter.</p>"),
                center=TextBlock("<p>Quarter.</p>"),
                right=TextBlock("<p>The 50% column.</p>"),
            )
        )
        # NumberedList.
        .section(
            FullWidth(
                title="What We Are Watching",
                content=NumberedList(
                    [
                        NumberedItem(
                            "01",
                            "Inflation prints",
                            "<p>Core services remain sticky.[^1]</p>",
                            notes=["Core services excluding housing, three-month annualised."],
                        ),
                        NumberedItem("02", "Earnings revisions", "<p>Breadth is narrowing.</p>"),
                        NumberedItem("03", "Positioning", "<p>Futures length is extended.</p>"),
                    ],
                    subtitle="Three themes into next week",
                ),
            )
        )
        # Callout, Divider and Button in a bordered band (#265).
        .section(
            FullWidth(
                title="Bottom Line",
                border=True,
                content=Stack(
                    [
                        TextBlock("<p>Duration has paid for its carry this quarter.</p>"),
                        Callout(
                            TextBlock("<p>Stay long the belly; fade the long end.</p>"),
                            tone="positive",
                            label="Key takeaway",
                        ),
                        Divider(),
                        # Shown in an email alone (#365), so this golden is unmoved by it.
                        Only(
                            Button(
                                "Read the full note", "https://example.com/note", align="center"
                            ),
                            media="email",
                        ),
                    ]
                ),
            )
        )
        # Citations, a numeric Bibliography and a Glossary (#310, #311).
        .section(
            FullWidth(
                title="Sources and Terms",
                content=Stack(
                    [
                        TextBlock(
                            "<p>Momentum persists [@jt1993; @carhart1997], though its "
                            '<a href="#term-crash-risk">crash risk</a> is well '
                            "documented [@jt1993].</p>"
                        ),
                        Bibliography(
                            [
                                Reference(
                                    "carhart1997",
                                    ["Carhart, Mark M."],
                                    1997,
                                    "On persistence in mutual fund performance",
                                    "The Journal of Finance",
                                    doi="10.1111/j.1540-6261.1997.tb03808.x",
                                ),
                                Reference(
                                    "jt1993",
                                    ["Jegadeesh, Narasimhan", "Titman, Sheridan"],
                                    1993,
                                    "Returns to buying winners and selling losers",
                                    url="https://example.com/jt1993",
                                ),
                            ],
                            style="numeric",
                            title="References",
                        ),
                        Glossary(
                            [
                                Term("Momentum", "Past winners continuing to outperform."),
                                Term("Crash risk", "A sudden, deep reversal of a trend."),
                            ],
                            title="Terms",
                            sort=False,
                        ),
                    ]
                ),
            )
        )
        # ContactBlock — body component for a contact call-to-action.
        .section(
            FullWidth(
                content=ContactBlock(
                    heading="Questions about this note?",
                    description="Reach the research desk with any questions.",
                    cta_label="Email the desk",
                    cta_url="https://example.com/contact",
                ),
            )
        )
        .build()
    )
