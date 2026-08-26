"""
pyHermes Email Builder Service
==============================

Object-oriented email assembly using Jinja2 templates.

Quick start::

    from pathlib import Path

    from svc.builder import CardGroup, EmailBuilder, FullWidth, TextBlock
    from svc.builder.models import KpiItem

    # email_subject, firm_name and campaign_name are required; the rest of
    # EmailMetadata is optional.  metadata() must be called before section().
    email = (EmailBuilder()
        .metadata({
            "email_subject": "Weekly Market Wrap",
            "firm_name": "Research & Strategy",
            "campaign_name": "weekly-wrap",
        })
        .section(FullWidth(
            content=CardGroup([
                KpiItem("S&P 500", "5,234", "#4A7C59", "+1.42%"),
                KpiItem("UST 10Y", "4.28%", "#B85450", "+6 bps"),
                KpiItem("VIX", "14.32", "#4A7C59", "-2.18 pts"),
            ]),
            title="Market Snapshot",
            highlight=True,
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
    CardGroup,
    ChartBlock,
    Component,
    DataTable,
    ImageBlock,
    KpiStrip,
    NumberedList,
    TextBlock,
)

# Containers
from .containers import (
    Container,
    FullWidth,
    ThreeColumn,
    TwoColumn,
)

# Email builder + engine
from .email import Email, EmailBuilder
from .engine import TemplateEngine

# Enums
from .enums import (
    CardOrientation,
    EmbedStrategy,
    ImageAlign,
    ThreeColumnRatio,
    TwoColumnRatio,
)

# Exceptions
from .exceptions import (
    EmailBuilderError,
    SizeError,
    TemplateError,
    ValidationError,
)

# Images
from .images import (
    EmailImage,
    ImageAsset,
)

# Models
from .models import (
    Card,
    EmailMetadata,
    KpiItem,
    NumberedItem,
    SectionConfig,
    TableRow,
)

# Regions
from .regions import (
    Header,
    MinimalHeader,
)

__all__ = [
    # Engine
    "TemplateEngine",
    # Regions
    "Header",
    "MinimalHeader",
    # Models
    "EmailMetadata",
    "Card",
    "KpiItem",
    "TableRow",
    "NumberedItem",
    "SectionConfig",
    # Components
    "Component",
    "CardGroup",
    "KpiStrip",
    "DataTable",
    "ChartBlock",
    "ImageBlock",
    "TextBlock",
    "NumberedList",
    "AuthorBlock",
    # Containers
    "Container",
    "FullWidth",
    "TwoColumn",
    "ThreeColumn",
    # Enums
    "TwoColumnRatio",
    "ThreeColumnRatio",
    "CardOrientation",
    "EmbedStrategy",
    "ImageAlign",
    # Images
    "EmailImage",
    "ImageAsset",
    # Email
    "Email",
    "EmailBuilder",
    # Exceptions
    "EmailBuilderError",
    "TemplateError",
    "ValidationError",
    "SizeError",
]
