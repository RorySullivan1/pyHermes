"""
The research note as an email: ``a4_research_note``'s content in an inbox (#312).

No sheets, so its two lists are ``Contents`` components at the top, the list of
exhibits linking where paper adds a page. Its golden pins that every exhibit,
appendix and citation reads as it does on paper.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Contents, Email, EmailBuilder, TwoColumn

from . import _research


def build(template_dir: Path | None = None) -> Email:
    """Build the research-note email. Deterministic: same bytes every call."""
    builder = (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": "Momentum After Costs",
                "firm_name": "Hermes Research",
                "campaign_name": "Momentum After Costs",
                "header_disclaimer": "For illustrative purposes. Not investment advice.",
            }
        )
        .section(
            TwoColumn(
                title="In This Note",
                left=Contents(subtitle="Sections"),
                right=Contents(subtitle="Tables and figures", of="exhibits", label="Exhibit"),
            )
        )
    )
    for section in _research.sections():
        builder.section(section)
    return builder.build()
