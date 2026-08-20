"""
Data models for the email builder.

Uses dataclasses for structured configuration with validation.
These models define the shape of data flowing through the builder —
metadata for the email skeleton, typed data for each component, etc.
"""

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .exceptions import ValidationError

# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _require(value: Any, name: str) -> None:
    """Raise if value is None or empty string."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"'{name}' is required and cannot be empty.")


def _validate_color(value: str, name: str) -> None:
    """Raise if value is not a valid hex color."""
    if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
        raise ValidationError(f"'{name}' must be a hex color (e.g. #4A7C59), got: {value}")


# ──────────────────────────────────────────────────────────────────────
# Email-level metadata
# ──────────────────────────────────────────────────────────────────────

@dataclass
class EmailMetadata:
    """
    Top-level metadata for the email skeleton (header, footer, preheader).

    Every field maps to a variable in ``templates/base.html``.
    """
    email_subject: str = ""
    preheader_text: str = ""
    header_disclaimer: str = ""
    header_bg_image_url: str = ""
    logo_url: str = ""
    firm_name: str = ""
    campaign_name: str = ""
    date_range: str = ""
    issue_label: str = ""
    contact_description: str = ""
    contact_url: str = ""
    footer_disclaimer: str = ""
    current_year: str = ""
    unsubscribe_url: str = ""
    view_in_browser_url: str = ""

    def validate(self) -> None:
        """Validate required fields."""
        for fname in ("email_subject", "firm_name", "campaign_name"):
            _require(getattr(self, fname), fname)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ──────────────────────────────────────────────────────────────────────
# Component data models
# ──────────────────────────────────────────────────────────────────────

@dataclass
class KpiItem:
    """A single KPI stat (label, value, color, sublabel)."""
    label: str
    value: str
    color: str = "#5A5A5A"
    sublabel: str = ""

    def validate(self) -> None:
        _require(self.label, "kpi.label")
        _require(self.value, "kpi.value")
        _validate_color(self.color, "kpi.color")


@dataclass
class TableRow:
    """A single row in a data table."""
    cells: List[str] = field(default_factory=list)
    colors: List[str] = field(default_factory=list)

    def validate(self) -> None:
        # colors is index-aligned with cells; the template indexes it directly
        # (row.colors[loop.index0]), so a short list raises under StrictUndefined.
        # Empty means "no colors" and is allowed.
        if self.colors and len(self.colors) != len(self.cells):
            raise ValidationError(
                f"'table_row.colors' must be empty or the same length as 'cells' "
                f"({len(self.cells)}), got {len(self.colors)}."
            )
        for c in self.colors:
            if c:
                _validate_color(c, "table_row.color")


@dataclass
class NumberedItem:
    """A single item in a numbered list."""
    number: str
    title: str
    body: str

    def validate(self) -> None:
        _require(self.title, "numbered_item.title")
        _require(self.body, "numbered_item.body")


# ──────────────────────────────────────────────────────────────────────
# Section configuration
# ──────────────────────────────────────────────────────────────────────

@dataclass
class SectionConfig:
    """
    Configuration for one email section.

    Attributes:
        container:   Container template name (e.g. ``"full-width"``).
        component:   Component template path relative to templates/
                     (e.g. ``"analysis/kpi-strip"``).
        data:        Data dict passed to the component template.
        title:       Optional section heading.
        background_color: Optional background color override.
    """
    container: str
    component: str
    data: Dict[str, Any] = field(default_factory=dict)
    title: Optional[str] = None
    background_color: Optional[str] = None

    def validate(self) -> None:
        _require(self.container, "section.container")
        _require(self.component, "section.component")
        if self.background_color:
            _validate_color(self.background_color, "section.background_color")
