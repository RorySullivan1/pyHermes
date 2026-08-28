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

from pathlib import Path
from typing import Any

from svc.builder import (
    AuthorBlock,
    Banner,
    BannerPalette,
    CardGroup,
    ChartBlock,
    ContactBlock,
    DataTable,
    Email,
    EmailBuilder,
    Footer,
    FullWidth,
    Header,
    ImageBlock,
    NumberedList,
    Rgba,
    TextBlock,
    ThreeColumn,
    TwoColumn,
)
from svc.builder.enums import CardOrientation, ImageAlign, ThreeColumnRatio, TwoColumnRatio
from svc.builder.images import EmailImage
from svc.builder.models import Card, FooterLink, KpiItem, LinkRow, NumberedItem, TableRow

from ._png import solid_png

#: Fixed so the render never moves. A fixture that reads the clock cannot be
#: snapshotted.
_YEAR = "2026"

_GAIN = "#4A7C59"
_LOSS = "#B85450"

_CHART_PNG = solid_png(320, 120, (42, 61, 84))
_THUMB_PNG = solid_png(96, 96, (184, 84, 80))


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


def build(template_dir: Path | None = None, **metadata_overrides: Any) -> Email:
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
        EmailBuilder(template_dir=template_dir)
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
                    copyright="2026 Hermes Research — all rights reserved",
                    links=[
                        FooterLink("Privacy", "https://example.com/privacy"),
                        FooterLink("Stop receiving this", "https://example.com/unsubscribe"),
                        FooterLink("Contact", "mailto:research@example.com"),
                    ],
                ),
            )
        )
        # FullWidth + horizontal CardGroup + highlight.
        .section(
            FullWidth(
                title="Market Snapshot",
                highlight=True,
                content=CardGroup(
                    [
                        KpiItem("S&P 500", "5,234", _GAIN, "+1.42%"),
                        KpiItem("UST 10Y", "4.28%", _LOSS, "+6 bps"),
                        KpiItem("Gold", "2,411", _GAIN, "+0.85%"),
                        KpiItem("VIX", "14.32", _GAIN, "-2.18 pts"),
                    ],
                    orientation=CardOrientation.HORIZONTAL,
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
        # DataTable, with per-cell colours.
        .section(
            FullWidth(
                title="Factor Returns",
                content=DataTable(
                    headers=["Factor", "1M", "YTD"],
                    rows=[
                        TableRow(cells=["Value", "+1.8%", "+7.4%"], colors=["", _GAIN, _GAIN]),
                        TableRow(cells=["Momentum", "-0.4%", "+11.2%"], colors=["", _LOSS, _GAIN]),
                        TableRow(cells=["Quality", "+0.9%", "+5.1%"], colors=["", _GAIN, _GAIN]),
                    ],
                    source="Hermes Research",
                    as_of="24 August 2026",
                    subtitle="Long-short, gross of costs",
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
                ),
            )
        )
        # TwoColumn — all three ratios.
        .section(
            TwoColumn(
                ratio=TwoColumnRatio.EQUAL,
                title="Equal Columns",
                left=TextBlock("<p>The left half of a 50-50 split.</p>"),
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
                    caption="A 30% column",
                    align=ImageAlign.LEFT,
                ),
                right=TextBlock("<p>Commentary occupying the wider 70% column.</p>"),
            )
        )
        .section(
            TwoColumn(
                ratio=TwoColumnRatio.WIDE_NARROW,
                title="Wide then Narrow",
                left=TextBlock("<p>Commentary occupying the wider 70% column.</p>"),
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
                            "01", "Inflation prints", "<p>Core services remain sticky.</p>"
                        ),
                        NumberedItem("02", "Earnings revisions", "<p>Breadth is narrowing.</p>"),
                        NumberedItem("03", "Positioning", "<p>Futures length is extended.</p>"),
                    ],
                    subtitle="Three themes into next week",
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
