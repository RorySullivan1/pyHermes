"""
pyHermes Email Builder Service
==============================

Object-oriented email assembly using Jinja2 templates.

Quick start::

    from pathlib import Path

    from svc.builder import EmailBuilder, FullWidth, Highlight, KpiStrip, TextBlock
    from svc.builder.models import KpiItem

    # email_subject, firm_name and campaign_name are required; the rest of
    # EmailMetadata is optional.  metadata() must be called before section().
    email = (EmailBuilder()
        .metadata({
            "email_subject": "Weekly Market Wrap",
            "firm_name": "Research & Strategy",
            "campaign_name": "weekly-wrap",
        })
        .section(Highlight(
            content=KpiStrip([
                KpiItem("S&P 500", "5,234", "#4A7C59", "+1.42%"),
                KpiItem("UST 10Y", "4.28%", "#B85450", "+6 bps"),
                KpiItem("VIX", "14.32", "#4A7C59", "-2.18 pts"),
            ]),
            title="Market Snapshot",
        ))
        .section(FullWidth(
            content=TextBlock("Equity markets advanced..."),
            title="Week in Review",
        ))
        .build()
    )

    email.save(Path("output.html"))
"""

# Components
from .components import (
    AuthorBlock,
    ChartBlock,
    Component,
    DataTable,
    KpiStrip,
    NumberedList,
    TextBlock,
)

# Containers
from .containers import (
    Container,
    FullWidth,
    Highlight,
    TwoColumn,
)

# Email builder + engine
from .email import Email, EmailBuilder
from .engine import TemplateEngine

# Exceptions
from .exceptions import (
    EmailBuilderError,
    SizeError,
    TemplateError,
    ValidationError,
)

# Models
from .models import (
    EmailMetadata,
    KpiItem,
    NumberedItem,
    SectionConfig,
    TableRow,
)

__all__ = [
    # Engine
    "TemplateEngine",
    # Models
    "EmailMetadata",
    "KpiItem",
    "TableRow",
    "NumberedItem",
    "SectionConfig",
    # Components
    "Component",
    "KpiStrip",
    "DataTable",
    "ChartBlock",
    "TextBlock",
    "NumberedList",
    "AuthorBlock",
    # Containers
    "Container",
    "FullWidth",
    "Highlight",
    "TwoColumn",
    # Email
    "Email",
    "EmailBuilder",
    # Exceptions
    "EmailBuilderError",
    "TemplateError",
    "ValidationError",
    "SizeError",
]
