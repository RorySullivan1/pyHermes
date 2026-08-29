"""
The pyHermes email builder: object-oriented assembly over Jinja2 templates.

Compose an :class:`Email` from sections, then render it to HTML and a
manifest of the images that HTML references::

    email = (EmailBuilder()
        .metadata({"email_subject": ..., "firm_name": ..., "campaign_name": ...})
        .section(FullWidth(title="Market Snapshot", content=CardGroup([...])))
        .build())
    html, assets, text = email.render(), email.assets(), email.text()

``metadata()`` takes the email's facts and must precede ``section()``; only
``email_subject``, ``firm_name`` and ``campaign_name`` are required.
`.claude/rules/builder-architecture.md` carries the four-layer model.
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
    RowKind,
    SizeTheme,
    TextAlign,
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
    "RowKind",
    "CardOrientation",
    "EmbedStrategy",
    "ImageAlign",
    "SizeTheme",
    "TextAlign",
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
