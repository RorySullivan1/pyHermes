#!/usr/bin/env python3
"""
Test script: Recreate the weekly market wrap using the OO email builder.
"""

from pathlib import Path

from svc.builder import (
    AuthorBlock,
    ChartBlock,
    DataTable,
    EmailBuilder,
    FullWidth,
    Highlight,
    KpiStrip,
    NumberedList,
    TextBlock,
    TwoColumn,
)
from svc.builder.models import KpiItem, NumberedItem, TableRow

output = (
    EmailBuilder()
    .metadata(
        {
            "preheader_text": "Weekly perspective: equity markets, rates, and positioning for the week ahead.",
            "header_disclaimer": "For informational purposes only. Does not constitute investment advice.",
            "header_bg_image_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=680&q=80&auto=format",
            "logo_url": "https://via.placeholder.com/90x36/FFFFFF/2C3E50?text=LOGO",
            "firm_name": "Weekly QIS Wrap",
            "campaign_name": "Barclays Quantitative Investment Strategies",
            "email_subject": "[Weekly Market Perspective] — March 28th 2026 - Barclays QIS ",
            "date_range": "March 28th 2026",
            "issue_label": "Vol. 1 · No. 10",
            "contact_description": "Our research and strategy team is available to discuss the themes covered in this report or answer questions about your portfolio.",
            "contact_url": "https://example.com/contact",
            "footer_disclaimer": "This material is provided for informational purposes only and does not constitute investment advice, an offer, or a solicitation. Past performance is not indicative of future results. For institutional and professional investor use only. Not for redistribution.",
            "current_year": "2026",
            "unsubscribe_url": "https://example.com/unsubscribe",
            "view_in_browser_url": "https://example.com/view-in-browser",
        }
    )
    # 1. KPI Strip in highlight container
    .section(
        Highlight(
            content=KpiStrip(
                [
                    KpiItem("S&P 500", "5,234.18", "#4A7C59", "+1.42% WoW"),
                    KpiItem("UST 10Y", "4.28%", "#B85450", "+6 bps"),
                    KpiItem("VIX", "14.32", "#4A7C59", "-2.18 pts"),
                ]
            ),
            title="Market Snapshot",
        )
    )
    # 2. Narrative text block
    .section(
        FullWidth(
            content=TextBlock(
                "Equity markets advanced for the third consecutive week as cooling "
                "inflation data reinforced expectations that the Federal Reserve will "
                "begin easing policy later this quarter. The S&amp;P 500 posted a "
                "weekly gain of 1.42%, led by cyclical sectors, while breadth improved "
                "notably with the equal-weighted index outperforming its cap-weighted "
                "counterpart by 38 basis points. Treasuries sold off modestly, with "
                "the 10-year yield rising 6 basis points to 4.28%, as stronger-than-"
                "expected retail sales tempered rate-cut enthusiasm. Credit markets "
                "remained constructive, with investment-grade spreads tightening 3 "
                "basis points to 92 bps over Treasuries."
            ),
            title="Week in Review",
        )
    )
    # 3. Data table
    .section(
        TwoColumn(
            title="Asset Returns",
            ratio="50-50",
            left=DataTable(
                subtitle="Major Benchmarks",
                headers=["Asset Class", "Level", "WoW", "YTD"],
                rows=[
                    TableRow(
                        ["S&P 500", "5,234.18", "+1.42%", "+8.73%"],
                        ["", "#5A5A5A", "#4A7C59", "#4A7C59"],
                    ),
                    TableRow(
                        ["US 10Y Treasury", "4.28%", "+6 bps", "+22 bps"],
                        ["", "#5A5A5A", "#B85450", "#B85450"],
                    ),
                    TableRow(
                        ["IG Credit (OAS)", "92 bps", "-3 bps", "-14 bps"],
                        ["", "#5A5A5A", "#4A7C59", "#4A7C59"],
                    ),
                    TableRow(
                        ["WTI Crude", "$78.42", "-0.87%", "+4.21%"],
                        ["", "#5A5A5A", "#B85450", "#4A7C59"],
                    ),
                ],
                source="Source: Bloomberg",
                as_of="March 28, 2026",
            ),
            right=DataTable(
                subtitle="Commodities",
                headers=["Asset Class", "Level", "WoW", "YTD"],
                rows=[
                    TableRow(
                        ["S&P 500", "5,234.18", "+1.42%", "+8.73%"],
                        ["", "#5A5A5A", "#4A7C59", "#4A7C59"],
                    ),
                    TableRow(
                        ["US 10Y Treasury", "4.28%", "+6 bps", "+22 bps"],
                        ["", "#5A5A5A", "#B85450", "#B85450"],
                    ),
                    TableRow(
                        ["IG Credit (OAS)", "92 bps", "-3 bps", "-14 bps"],
                        ["", "#5A5A5A", "#4A7C59", "#4A7C59"],
                    ),
                    TableRow(
                        ["WTI Crude", "$78.42", "-0.87%", "+4.21%"],
                        ["", "#5A5A5A", "#B85450", "#4A7C59"],
                    ),
                ],
                source="Source: Bloomberg",
                as_of="March 28, 2026",
            ),
        )
    )
    # 4. Chart
    .section(
        FullWidth(
            content=ChartBlock(
                image_url="https://via.placeholder.com/616x300/F8F7F5/3B3B3B?text=Factor+Returns+Chart",
                alt_text="Bar chart showing weekly factor returns",
                source="Chart data: Bloomberg, internal calculations",
            ),
            title="Exhibit 1 — Factor Returns",
        )
    )
    # 5. Key themes
    .section(
        FullWidth(
            content=NumberedList(
                [
                    NumberedItem(
                        "1",
                        "Disinflation Trend Intact",
                        "Core PCE decelerated to 2.6% year-over-year, the lowest reading "
                        "since early 2024. The three-month annualized rate fell to 2.3%, "
                        "reinforcing the view that the disinflationary trend remains on "
                        "track despite sticky shelter components.",
                    ),
                    NumberedItem(
                        "2",
                        "Market Breadth Improving",
                        "The percentage of S&P 500 constituents trading above their "
                        "200-day moving average rose to 68%, up from 54% at the February "
                        "low. Small-cap participation also improved, with the Russell 2000 "
                        "outperforming large caps by 82 bps on the week.",
                    ),
                    NumberedItem(
                        "3",
                        "Credit Spreads Signal Risk Appetite",
                        "Investment-grade credit spreads tightened to 92 bps, the lowest "
                        "level since November 2024. High-yield spreads also compressed, "
                        "falling 8 bps to 312 bps, suggesting healthy risk appetite and "
                        "limited concern about near-term recession.",
                    ),
                ]
            ),
            title="Key Themes",
        )
    )
    # 6. Author block
    .section(
        FullWidth(
            content=AuthorBlock(
                name="Jonathan R. Mercer, CFA",
                job_title="Chief Market Strategist",
                email="j.mercer@example.com",
            ),
            title="Contact",
        )
    )
    .save(Path("weekly_market_wrap_v2.html"))
)

print(f"Output: {output}")
