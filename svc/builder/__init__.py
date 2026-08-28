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
    ContactBlock,
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
    ColumnAlign,
    ColumnKind,
    EmbedStrategy,
    ImageAlign,
    SizeTheme,
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
    Cell,
    Column,
    EmailMetadata,
    KpiItem,
    NumberedItem,
    SectionConfig,
    TableRow,
)

# Regions
from .regions import (
    Banner,
    BoxSurface,
    EmptyHeader,
    Footer,
    Header,
    MinimalBanner,
    Region,
)

# Sizing
from .sizing import (
    COMPACT_SIZES,
    SIZE_SCHEMES,
    SPACIOUS_SIZES,
    STANDARD_SIZES,
    ComponentScale,
    FrameGeometry,
    SizeScheme,
    SpacingScale,
    TypeScale,
)
from .theming import (
    DEFAULT_THEME,
    SLATE_THEME,
    THEMES,
    BannerPalette,
    Palette,
    Rgba,
    SemanticColors,
    ShadowStyle,
    TextColors,
    Theme,
)

# Theming
from .typography import (
    DEFAULT_FONTS,
    FONT_THEMES,
    MODERN_FONTS,
    FontStack,
    FontTheme,
)

__all__ = [
    # Engine
    "TemplateEngine",
    # Theming
    "Theme",
    "Palette",
    "TextColors",
    "SemanticColors",
    "ShadowStyle",
    "Rgba",
    "FontStack",
    "FontTheme",
    "DEFAULT_FONTS",
    "MODERN_FONTS",
    "FONT_THEMES",
    "BannerPalette",
    "DEFAULT_THEME",
    "SLATE_THEME",
    "THEMES",
    # Sizing
    "SizeScheme",
    "TypeScale",
    "SpacingScale",
    "ComponentScale",
    "FrameGeometry",
    "STANDARD_SIZES",
    "COMPACT_SIZES",
    "SPACIOUS_SIZES",
    "SIZE_SCHEMES",
    # Regions
    "Region",
    "Banner",
    "BoxSurface",
    "MinimalBanner",
    "Footer",
    "Header",
    "EmptyHeader",
    # Models
    "EmailMetadata",
    "Card",
    "KpiItem",
    "TableRow",
    "Column",
    "Cell",
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
    "ContactBlock",
    # Containers
    "Container",
    "FullWidth",
    "TwoColumn",
    "ThreeColumn",
    # Enums
    "TwoColumnRatio",
    "ThreeColumnRatio",
    "ColumnAlign",
    "ColumnKind",
    "CardOrientation",
    "EmbedStrategy",
    "ImageAlign",
    "SizeTheme",
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
