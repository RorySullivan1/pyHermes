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
# Email builder + engine
from . import formats
from .components import (
    AuthorBlock,
    CardGroup,
    ChartBlock,
    Component,
    ContactBlock,
    Contents,
    DataTable,
    ImageBlock,
    KpiStrip,
    MathBlock,
    NumberedList,
    PullQuote,
    TextBlock,
)
from .composition import Columns, Only, Stack

# Containers
from .containers import (
    Appendices,
    Container,
    FlowedColumns,
    FourColumn,
    FullWidth,
    OnlySections,
    ThreeColumn,
    TwoColumn,
    content_width,
)
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
    Tone,
    Trend,
    TwoColumnRatio,
    VerticalAlign,
)

# Exceptions
from .exceptions import (
    EmailBuilderError,
    PrintQualityWarning,
    SizeError,
    SizeWarning,
    TemplateError,
    ValidationError,
)
from .exhibits import FigureGrid, Legend, LegendEntry
from .glance import BarItem, BarList, HeroStat, Sparkline

# Images
from .images import (
    EmailImage,
    ImageAsset,
)

# Medium
from .medium import DEFAULT_MEDIUM, Constraint, Medium

# Models
from .models import (
    Badge,
    Card,
    Cell,
    Column,
    ColumnGroup,
    DocumentMetadata,
    EmailMetadata,
    HeatScale,
    KpiItem,
    NumberedItem,
    SectionConfig,
    Series,
    TableRow,
    tone_of,
    trend_of,
)
from .organising import Event, FactList, Teaser, TeaserList, Timeline

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
from .research import Bibliography, Glossary, Reference, Term

# Sizing
from .sizing import (
    COMPACT_SIZES,
    DEFAULT_PAGE,
    DENSE_SIZES,
    SIZE_SCHEMES,
    SPACIOUS_SIZES,
    STANDARD_SIZES,
    ComponentScale,
    FrameGeometry,
    PageFormat,
    PageMargin,
    SizeScheme,
    Spacing,
    SpacingScale,
    TypeScale,
)
from .surfaces import Aside, Button, Callout, Divider, QrCode, TagRow
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
    # Number formatting (#177)
    "formats",
    # Engine
    "TemplateEngine",
    # Medium
    "Medium",
    "Constraint",
    "DEFAULT_MEDIUM",
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
    "PageFormat",
    "PageMargin",
    "DEFAULT_PAGE",
    "STANDARD_SIZES",
    "COMPACT_SIZES",
    "SPACIOUS_SIZES",
    "DENSE_SIZES",
    "SIZE_SCHEMES",
    "Spacing",
    # Regions
    "Region",
    "Banner",
    "BoxSurface",
    "MinimalBanner",
    "Footer",
    "Header",
    "EmptyHeader",
    # Models
    "DocumentMetadata",
    "EmailMetadata",
    "Card",
    "KpiItem",
    "Badge",
    "TableRow",
    "Tone",
    "tone_of",
    "Trend",
    "trend_of",
    "Column",
    "ColumnGroup",
    "HeatScale",
    "Cell",
    "Series",
    "NumberedItem",
    "SectionConfig",
    # Components
    "Component",
    "CardGroup",
    "KpiStrip",
    "MathBlock",
    "DataTable",
    "ChartBlock",
    "ImageBlock",
    "TextBlock",
    "PullQuote",
    "NumberedList",
    "AuthorBlock",
    "ContactBlock",
    "Contents",
    "Stack",
    "Columns",
    "Only",
    "Callout",
    "Aside",
    "Button",
    "Divider",
    "TagRow",
    "QrCode",
    # Exhibits that group (#335)
    "FigureGrid",
    "Legend",
    "LegendEntry",
    # Organising content (#329)
    "FactList",
    "Timeline",
    "Event",
    "TeaserList",
    "Teaser",
    # Data at a glance (#318)
    "BarList",
    "BarItem",
    "Sparkline",
    "HeroStat",
    # The research apparatus (#220)
    "Bibliography",
    "Reference",
    "Glossary",
    "Term",
    # Containers
    "Appendices",
    "Container",
    "FlowedColumns",
    "FourColumn",
    "content_width",
    "FullWidth",
    "OnlySections",
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
    "VerticalAlign",
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
    "SizeWarning",
    "PrintQualityWarning",
]
